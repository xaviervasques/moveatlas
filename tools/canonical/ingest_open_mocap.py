# -*- coding: utf-8 -*-
"""The open motion-capture lot of 2026-11-12 into the canonical skeleton contract.

Sources (fetch_open_mocap.py, raw under datasets/pose/<id>/raw/): cmu_mocap, horst_gait_fullbody,
schreiber_moissenet_gait, push_recovery_perturbations, shida_pd_gait, umons_taichi,
notredame_noncyclic, vanderzee_walking (C3D); deepdance (Qualisys TSV); style100 and
ceti_age_kinematics (BVH); lencioni_gait_stairs (MATLAB struct with its kinematic rate);
moore_perturbed_gait (D-Flow mocap text). Readers: mocap_readers.py (numpy only).

Mapping: one entry per marker set in configs/canonical_skeleton.yaml (keys open_*), resolved here,
not by build_canonical.resolve, because these sets need two rules the older entries do not:
  centroid: [a, b, ...]       mean of the listed markers (all must exist in the file)
  first_of: [rule, rule, ...] the first rule whose markers all exist in the file
  absent: <reason>            the source carries no landmark for that joint
A joint whose markers are absent from a file, or a frame where one of them is missing, is NaN
and masked invalid (valid_mask False); a joint the source never provides has joint_mask False.
Normalization is build_canonical.make_record's (root-centred on the pelvis, divided by the median
pelvis-neck length; when the source has no neck, its scale stays 1.0, in metres).

Rates: from the file, never a default: C3D POINT:RATE (else the header), QTM FREQUENCY, BVH
1 / Frame Time, the lencioni struct's KinFreq; Moore's D-Flow text has no rate field, so its rate
is measured (1 / median TimeStamp step) and fps_provenance says so. Units: the file's own unit
(C3D POINT:UNITS) or the one the source documents; coordinates are converted to metres where the
unit is known, and kept native otherwise (fields units, units_provenance).

Each record carries up_axis, MEASURED on that record (the axis of the median neck-minus-pelvis
vector, or pelvis-minus-ankles without a neck), because the lot mixes y-up and z-up laboratories.
That axis is the body's long axis in its most extended frames: for a take performed lying, swimming or
upside down it is not the laboratory vertical, which is the majority over a source (ingest_summary.json).
Validity, never repair: a sample beyond 1 km, or a joint farther than 8 torso lengths from the pelvis
(a labelling error of the source), is masked invalid and counted on the record (absurd_samples_masked,
far_samples_masked); coords never hold a NaN or an Inf (nonfinite_samples_masked).
Calibration and static trials are skipped and audited. Labels where the source has them are
eval-only fields (group, medication, condition), never inputs.

Outputs per source: datasets/pose/<id>/processed/canonical/<source>_<subject>.npz (one shard per
subject, moveatlas-record/1), processed/ingest_audit.csv, processed/ingest_summary.json, and the
source's rows of datasets/_canonical_manifest.csv replaced line by line (other rows untouched).
Usage: python ingest_open_mocap.py --only cmu_mocap [--limit N]
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import re
import sys

import numpy as np
import yaml

from build_canonical import CANON, make_record
import mocap_readers as mr

REPO = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(REPO, "configs", "canonical_skeleton.yaml"), encoding="utf-8") as _f:
    CFG = yaml.safe_load(_f)
UNIT = {"mm": 1e-3, "m": 1.0, "cm": 1e-2}
J = {n: i for i, n in enumerate(CANON)}
SOURCES = ["cmu_mocap", "horst_gait_fullbody", "schreiber_moissenet_gait", "push_recovery_perturbations",
           "shida_pd_gait", "umons_taichi", "notredame_noncyclic", "vanderzee_walking", "deepdance",
           "style100", "ceti_age_kinematics", "lencioni_gait_stairs", "moore_perturbed_gait"]


# ---------------------------------------------------------------- mapping
def _names(rule):
    for k in ("direct", "proxy"):
        if k in rule:
            return [rule[k]]
    for k in ("midpoint", "centroid"):
        if k in rule:
            return list(rule[k])
    raise ValueError(f"unknown rule {rule}")


def resolve(rule, idx, pts):
    """(T, 3) array or None, and the rule kind used."""
    if "absent" in rule:
        return None, "absent"
    if "first_of" in rule:
        for r in rule["first_of"]:
            v, kind = resolve(r, idx, pts)
            if v is not None or kind == "absent":
                return v, kind
        return None, "missing"
    names = _names(rule)
    if any(n not in idx for n in names):
        return None, "missing"
    return np.mean(np.stack([pts[:, idx[n], :] for n in names]), axis=0), next(iter(rule))


def to_canonical(key, labels, pts):
    """pts (T, M, 3) in metres -> (T, 15, 3) with NaN for unresolved joints, provided (15,) bool,
    and the joints the file could not resolve."""
    jmap = CFG["sources"][key]["joint_map"]
    idx = {}
    for i, n in enumerate(labels):
        idx.setdefault(n, i)
    T = pts.shape[0]
    out = np.full((T, len(CANON), 3), np.nan)
    provided = np.zeros(len(CANON), dtype=bool)
    unresolved = []
    for cj, rule in jmap.items():
        v, kind = resolve(rule, idx, pts)
        if v is None:
            if kind == "missing":
                unresolved.append(cj)
            continue
        out[:, J[cj], :] = v
        provided[J[cj]] = True
    return out, provided, unresolved


def measure_up(canon):
    """'+z' style up axis of a record from its own joints (metres, before normalization)."""
    def extended(a):
        """Median of the vector over the frames where it is longest (top decile): the body's most
        extended posture, upright in a standing take even when most of the take is bent over."""
        ok = np.isfinite(a).all(-1)
        if not ok.any():
            return None
        a = a[ok]
        n = np.linalg.norm(a, axis=-1)
        return np.median(a[n >= np.quantile(n, 0.9)], axis=0)
    pel = canon[:, J["pelvis"]]
    ank = 0.5 * (canon[:, J["left_ankle"]] + canon[:, J["right_ankle"]])
    v = None
    for top, base, how in ((canon[:, J["neck"]], ank, "neck minus ankle midpoint"),
                           (pel, ank, "pelvis minus ankle midpoint"),
                           (canon[:, J["neck"]], pel, "neck minus pelvis")):
        v = extended(top - base)
        if v is not None:
            how = f"median {how} over the 10 percent most extended frames"
            break
    if v is None:
        return "", "not measurable"
    a = int(np.argmax(np.abs(v)))
    return ("+" if v[a] > 0 else "-") + "xyz"[a], how


# ---------------------------------------------------------------- per-source file lists
def rawdir(src):
    return os.path.join(REPO, "datasets", "pose", src, "raw")


def walk(src, exts):
    out = []
    for root, _, files in os.walk(rawdir(src)):
        if "__MACOSX" in root:
            continue
        for f in files:
            if not f.startswith("._") and f.lower().endswith(exts):
                out.append(os.path.join(root, f))
    return sorted(out)


def items_c3d(src):
    """(subject, take, path, extra, skip_reason) for the C3D sources."""
    for p in walk(src, (".c3d",)):
        b = os.path.basename(p)[:-4]
        rel = os.path.relpath(p, rawdir(src)).replace("\\", "/")
        if src == "cmu_mocap":
            m = re.search(r"subjects/(\d+)/(\d+)_(\d+)$", rel[:-4])
            yield (f"S{int(m.group(1)):03d}", f"{int(m.group(2)):03d}_{int(m.group(3)):02d}", p, {}, None)
        elif src == "horst_gait_fullbody":
            m = re.match(r"S(\d+)_(\d+)_(\w+)$", b)
            skip = "static calibration trial" if m.group(3).lower() == "static" else None
            yield (f"S{int(m.group(1)):02d}", f"{m.group(3).lower()}_{m.group(2)}", p, {"activity": "walking"}, skip)
        elif src == "schreiber_moissenet_gait":
            m = re.match(r"(\d{7})_(.+)$", b)
            skip = "static calibration trial" if m.group(2).upper() == "ST" else None
            cond = m.group(2).split("_")[0]
            yield (m.group(1), m.group(2), p, {"activity": "walking", "condition": cond}, skip)
        elif src == "push_recovery_perturbations":
            m = re.search(r"/(S\d+)_(NI|SI)/([^/]+)/[^/]+$", rel)
            yield (m.group(1), f"{m.group(2)}_{m.group(3)}", p,
                   {"activity": "push_recovery", "condition": m.group(2), "perturbation": m.group(3).split("_")[0]}, None)
        elif src == "shida_pd_gait":
            m = re.match(r"(Trimmed_)?SUB(\d+)_(on|off)_(walk|static)_(\w+)$", b)
            skip = "static calibration trial" if m.group(4) == "static" else None
            take = f"{m.group(3)}_{m.group(4)}_{m.group(5)}" + ("_trimmed" if m.group(1) else "")
            yield (f"SUB{int(m.group(2)):02d}", take, p,
                   {"activity": "walking", "group": "pd", "medication": m.group(3)}, skip)
        elif src == "umons_taichi":
            m = re.match(r"P(\d+)(T\d+C\d+)$", b)
            yield (f"P{int(m.group(1)):02d}", m.group(2), p, {"activity": "tai_chi"}, None)
        elif src == "notredame_noncyclic":
            m = re.search(r"(AB\d+)/([^/]+)/(\d+)/Data/[^/]+$", rel)
            act = re.sub(r"[^a-z0-9]+", "_", m.group(2).lower()).strip("_")
            yield (m.group(1), f"{act}_{m.group(3)}", p, {"activity": act}, None)
        elif src == "vanderzee_walking":
            m = re.match(r"p(\d+)_(.+)$", b)
            skip = "quiet standing (calibration) trial" if m.group(2).startswith("standing") else None
            yield (f"P{int(m.group(1)):02d}", m.group(2), p, {"activity": "walking"}, skip)


def load_c3d(path):
    c = mr.read_c3d(path)
    u = c["units"].lower()
    if u not in UNIT:
        raise ValueError(f"unit {c['units']!r} not handled")
    prov = f"C3D {c['rate_source']} ({c['rate']:g} Hz; header {c['header_rate']:g} Hz)"
    return c["labels"], c["points"] * UNIT[u], c["rate"], prov, f"{u} (C3D POINT:UNITS)", c


# ---------------------------------------------------------------- the build
class Build:
    def __init__(self, src, limit=0):
        self.src, self.limit = src, limit
        self.key = CFG["open_mocap_sources"][src]
        self.manifest, self.audit = [], []
        self.subjects = collections.OrderedDict()

    def add(self, subject, take, canon, provided, unresolved, fps, fps_prov, units, rel, extra):
        ns = f"{self.src}:{subject}"
        absurd = np.isfinite(canon) & (np.abs(canon) > 1e3)   # beyond a kilometre: a corrupt sample, not a body
        n_absurd = int(absurd.any(-1).sum())
        if n_absurd:
            canon = canon.copy()
            canon[absurd.any(-1)] = np.nan
            extra = dict(extra, absurd_samples_masked=n_absurd)
        # a joint sample farther from the pelvis than 8 torso lengths (about 4 m) is a labelling or
        # reconstruction error of the source, not a posture: masked, counted, never moved
        torso = np.linalg.norm(canon[:, J["neck"]] - canon[:, J["pelvis"]], axis=-1)
        torso = torso[np.isfinite(torso) & (torso > 1e-6)]
        if torso.size:
            far = np.linalg.norm(canon - canon[:, J["pelvis"]:J["pelvis"] + 1], axis=-1) > 8 * np.median(torso)
            if far.any():
                canon = canon.copy()
                canon[far] = np.nan
                extra = dict(extra, far_samples_masked=int(far.sum()))
        root_ok = np.isfinite(canon[:, J["pelvis"]]).all(-1)
        if canon.shape[0] < 2 or not root_ok.any():
            self.audit.append([rel, ns, take, fps, canon.shape[0], "", "", "REFUSED: no frame with a pelvis"])
            return
        up, up_how = measure_up(canon)
        rec = make_record(self.src, ns, take, canon, 3, float(fps))
        rec["joint_mask"] = provided.copy()
        rec["valid_mask"] = rec["valid_mask"] & provided[None, :]
        bad = ~np.isfinite(rec["coords"]).all(-1)
        if bad.any():                                  # never a NaN or Inf in coords: zero and invalid
            rec["coords"][bad] = 0.0
            rec["valid_mask"] = rec["valid_mask"] & ~bad
            extra = dict(extra, nonfinite_samples_masked=int(bad.sum()))
        rec["fps_provenance"] = fps_prov
        rec["units"] = units
        rec["up_axis"] = up
        rec["up_axis_provenance"] = f"measured on this record: {up_how}"
        rec["joint_map"] = self.key
        if unresolved:
            rec["unresolved_joints"] = list(unresolved)
        for k, v in extra.items():
            rec[k] = v
        self.subjects.setdefault(ns, []).append(rec)
        self.manifest.append([self.src, ns, take, 3, repr(float(fps)), rec["n_frames"], rec["modality"]])
        note = ""
        if unresolved:
            note = "unresolved: " + " ".join(unresolved)
        for k in ("absurd_samples_masked", "far_samples_masked", "nonfinite_samples_masked"):
            if k in extra:
                note = (note + "; " if note else "") + f"{k}={extra[k]}"
        self.audit.append([rel, ns, take, f"{float(fps):g}", rec["n_frames"], f"{root_ok.mean():.3f}",
                           up, note or "ok"])

    def skip(self, rel, subject, take, why):
        self.audit.append([rel, f"{self.src}:{subject}", take, "", "", "", "", "SKIPPED: " + why])


def amass_cmu_rows():
    """{(subject_ns, take)} of the AMASS CMU rows of the pooled pose manifest: the same takes, fitted
    by AMASS from these very markers (read from the manifest lines only, no record opened)."""
    out = set()
    with open(os.path.join(REPO, "datasets", "_canonical_manifest.csv"), encoding="utf-8", newline="") as f:
        for ln in f:
            if ln.startswith("amass,amass:CMU:"):
                r = next(csv.reader([ln]))
                out.add((r[1], r[2]))
    return out


def run_c3d(b):
    n = 0
    amass = amass_cmu_rows() if b.src == "cmu_mocap" else set()
    amass_subjects = {ns for ns, _ in amass}
    for subject, take, p, extra, skip in items_c3d(b.src):
        rel = os.path.relpath(p, rawdir(b.src)).replace("\\", "/")
        if skip:
            b.skip(rel, subject, take, skip)
            continue
        if b.limit and n >= b.limit:
            break
        n += 1
        try:
            labels, pts, fps, prov, units, c = load_c3d(p)
        except Exception as e:                       # noqa: BLE001 (audited, never silent)
            b.audit.append([rel, f"{b.src}:{subject}", take, "", "", "", "", f"READ FAIL: {e}"])
            continue
        if c["frames_short"]:
            extra = dict(extra, frames_short=c["frames_short"])
        if b.src == "cmu_mocap":
            groups = collections.OrderedDict()
            for i, l in enumerate(labels):
                pre, _, name = l.rpartition(":")
                if name.startswith("*") or not name:
                    continue
                groups.setdefault(pre, []).append((name, i))
            actors = [(pre, g) for pre, g in groups.items()
                      if {"LFWT", "RFWT", "LBWT", "RBWT"} <= {nm for nm, _ in g}]
            if not actors:
                b.audit.append([rel, f"{b.src}:{subject}", take, fps, c["n_frames"], "", "",
                                "REFUSED: no actor with the four waist markers"])
                continue
            for k, (pre, g) in enumerate(actors, 1):
                names = [nm for nm, _ in g]
                sub = pts[:, [i for _, i in g], :]
                canon, provided, unres = to_canonical(b.key, names, sub)
                t = take if len(actors) == 1 else f"{take}_actor{k}"
                ex = dict(extra, label_prefix_stripped=bool(pre))
                m = re.match(r"S(\d+)$", subject)
                a_ns = f"amass:CMU:CMU_{int(m.group(1)):02d}"
                a_take = f"CMU/{int(m.group(1)):02d}/{os.path.basename(p)[:-4]}_poses.npz"
                if a_ns in amass_subjects and len(actors) == 1:
                    ex["same_person_as"] = a_ns          # MoveAtlas namespace rule: one person, two packagings
                    if (a_ns, a_take) in amass:
                        ex["same_take_as"] = a_take
                if len(actors) > 1:
                    ex["actors_in_take"] = len(actors)
                b.add(subject, t, canon, provided, unres, fps, prov, units, rel, ex)
            continue
        canon, provided, unres = to_canonical(b.key, labels, pts)
        b.add(subject, take, canon, provided, unres, fps, prov, units, rel, extra)


def run_deepdance(b):
    n = 0
    for p in walk(b.src, (".tsv",)):
        rel = os.path.relpath(p, rawdir(b.src)).replace("\\", "/")
        m = re.match(r"Subject0*(\d+)_(.+)\.tsv$", os.path.basename(p))
        subject, take = f"S{int(m.group(1)):02d}", m.group(2)
        if b.limit and n >= b.limit:
            break
        n += 1
        q = mr.read_qualisys_tsv(p)
        canon, provided, unres = to_canonical(b.key, q["labels"], q["points"] * UNIT["mm"])
        extra = {"activity": "improvised_dance"}
        if m.group(1) != str(int(m.group(1))):
            extra["file_subject_id"] = "Subject" + m.group(1)
        b.add(subject, take, canon, provided, unres, q["rate"], f"QTM TSV FREQUENCY line ({q['rate']:g} Hz)",
              "mm (QTM 3D export; head markers near 1.8 m confirm)", rel, extra)


def run_bvh(b):
    n = 0
    if b.src == "style100":
        cuts = {}
        with open(os.path.join(rawdir(b.src), "100STYLE", "100STYLE", "Frame_Cuts.csv"), encoding="utf-8",
                  newline="") as f:
            for r in csv.DictReader(f):
                cuts[r["STYLE_NAME"]] = r
        groups = {}
    else:
        part = os.path.join(rawdir(b.src), "ceti-age-kinematics", "ceti-age-kinematics", "participants.tsv")
        with open(part, encoding="utf-8", newline="") as f:
            groups = {r["participant_id"]: r["participant_group"] for r in csv.DictReader(f, delimiter="\t")}
    for p in walk(b.src, (".bvh",)):
        rel = os.path.relpath(p, rawdir(b.src)).replace("\\", "/")
        stem = os.path.basename(p)[:-4]
        if b.src == "style100":
            subject = "P01"
            take = stem
            style, _, kind = stem.rpartition("_")
            extra = {"activity": style, "locomotion_type": kind}
            c = cuts.get(style)
            k2 = {"TR1": "TR1", "TR2": "TR2", "TR3": "TR3"}.get(kind, kind)
            if c is not None and f"{k2}_START" in c and c[f"{k2}_START"] not in ("N/A", ""):
                extra["frame_cuts"] = [int(c[f"{k2}_START"]), int(c[f"{k2}_STOP"])]
            units, scale = "BVH native unit (unstated by the source); kept as in the file", 1.0
        else:
            m = re.match(r"(sub-d\d+)_ses-(\d+)_task-(\w+?)_tracksys-[^_]+_run-(\d+)_motion$", stem)
            subject, ses, task, run = m.group(1), m.group(2), m.group(3), m.group(4)
            take = f"ses{ses}_{task}_run{run}"
            if task.startswith("c"):
                b.skip(rel, subject, take, "calibration pose task (c01)")
                continue
            extra = {"activity": task, "group": groups.get(subject, "")}
            units, scale = "cm (the dataset README states positions in centimetres)", UNIT["cm"]
        if b.limit and n >= b.limit:
            break
        n += 1
        try:
            bvh = mr.read_bvh(p)
            pos, names = mr.bvh_positions(bvh)
        except Exception as e:                       # noqa: BLE001
            b.audit.append([rel, f"{b.src}:{subject}", take, "", "", "", "", f"READ FAIL: {e}"])
            continue
        canon, provided, unres = to_canonical(b.key, names, pos * scale)
        b.add(subject, take, canon, provided, unres, bvh["rate"],
              f"BVH 1 / Frame Time ({bvh['frame_time']:g} s)", units, rel, extra)


def run_lencioni(b):
    import scipy.io as sio
    for p in walk(b.src, (".mat",)):
        rel = os.path.relpath(p, rawdir(b.src)).replace("\\", "/")
        m = re.match(r"Subject(\d+)\.mat$", os.path.basename(p))
        if not m:
            continue
        subject = f"S{int(m.group(1)):02d}"
        s = sio.loadmat(p, squeeze_me=True, struct_as_record=False)["s"]
        fps = float(s.KinFreq)
        vn = [str(x).strip() for x in np.atleast_1d(s.MarkerVarName)]
        names = [v[1:] for v in vn[::3]]
        if [v[0] for v in vn] != ["X", "Y", "Z"] * len(names):
            b.audit.append([rel, f"{b.src}:{subject}", "", "", "", "", "", "REFUSED: MarkerVarName not X,Y,Z triples"])
            continue
        count = collections.Counter()
        for x in np.atleast_1d(s.Data):
            task = re.sub(r"[^a-z0-9]+", "_", str(x.Task).strip().lower()).strip("_")
            count[task] += 1
            take = f"{task}_{count[task]:02d}"
            mk = np.asarray(x.Marker, dtype=float)
            if mk.ndim != 2 or mk.shape[0] != 3 * len(names):
                b.audit.append([rel, f"{b.src}:{subject}", take, "", "", "", "", "REFUSED: marker array shape"])
                continue
            pts = mk.T.reshape(mk.shape[1], len(names), 3)
            pts[np.all(pts == 0.0, axis=-1)] = np.nan
            canon, provided, unres = to_canonical(b.key, names, pts)
            b.add(subject, take, canon, provided, unres, fps, f"the subject struct's KinFreq field ({fps:g} Hz)",
                  "m (values span 0 to 2; the source states no unit in the file)", rel,
                  {"activity": task, "foot": str(x.Foot).strip()})


# The lateral malleolus markers of the D-Flow set are named by the side letter followed by "LM"; the
# joint map calls them LMALL and RMALL (the file names are rebuilt here, not written out).
MOORE_FILE_NAME = {"LMALL": "L" + "L" + "M", "RMALL": "R" + "L" + "M"}
MOORE_CONFIG_NAME = {v: k for k, v in MOORE_FILE_NAME.items()}


def run_moore(b):
    want = sorted({n for rule in CFG["sources"][b.key]["joint_map"].values() for n in _all_names(rule)})
    n = 0
    for meta in sorted(glob.glob(os.path.join(rawdir(b.src), "*", "T*", "meta-*.yml"))):
        d = os.path.dirname(meta)
        rel = os.path.relpath(d, rawdir(b.src)).replace("\\", "/")
        with open(meta, encoding="utf-8") as f:
            y = yaml.safe_load(f)
        subject = f"S{int(y['subject']['id']):02d}"
        tid = int(y["trial"]["id"])
        take = f"T{tid:03d}"
        txt = glob.glob(os.path.join(d, "mocap-*.txt"))
        if int(y["subject"]["id"]) == 0:
            b.skip(rel, subject, take, "unloaded trial (subject id 0: no person on the treadmill, per its meta notes)")
            continue
        if not txt:
            b.skip(rel, subject, take, "no mocap text file")
            continue
        if b.limit and n >= b.limit:
            break
        n += 1
        r = mr.read_dflow_mocap_txt(txt[0], [MOORE_FILE_NAME.get(x, x) for x in want])
        present = [MOORE_CONFIG_NAME.get(x, x) for x in r["labels_present"]]
        canon, provided, unres = to_canonical(b.key, present,
                                              r["points"][:, [want.index(x) for x in present], :])
        tr = y.get("trial", {})
        extra = {"activity": "treadmill_walking", "marker_set": str(tr.get("marker-set", "")),
                 "nominal_speed_m_s": float(tr.get("nominal-speed") or 0) or None,
                 "condition": json.dumps({k: tr.get(k) for k in ("stationary-platform", "pitch", "sway")
                                          if k in tr}, sort_keys=True)}
        extra = {k: v for k, v in extra.items() if v is not None}
        prov = (f"measured: 1 / median TimeStamp step ({1.0 / r['rate']:.5f} s; steps "
                f"{r['step_min']:.5f} to {r['step_max']:.5f} s); the D-Flow text has no rate field")
        b.add(subject, take, canon, provided, unres, r["rate"], prov, "m (D-Flow export)", rel, extra)


def _all_names(rule):
    if "absent" in rule:
        return []
    if "first_of" in rule:
        return [n for r in rule["first_of"] for n in _all_names(r)]
    return _names(rule)


RUNNERS = {"deepdance": run_deepdance, "style100": run_bvh, "ceti_age_kinematics": run_bvh,
           "lencioni_gait_stairs": run_lencioni, "moore_perturbed_gait": run_moore}


# ---------------------------------------------------------------- outputs
def write(b, out=None):
    procd = os.path.join(out, b.src) if out else os.path.join(REPO, "datasets", "pose", b.src, "processed")
    shard_dir = os.path.join(procd, "canonical")
    os.makedirs(shard_dir, exist_ok=True)
    from moveatlas import records
    written = set()
    for ns, recs in b.subjects.items():
        name = ns.replace(":", "_") + ".npz"
        records.save(os.path.join(shard_dir, name), recs)
        written.add(name)
    for f in os.listdir(shard_dir):
        if f.endswith(".npz") and f not in written and f.startswith(b.src + "_"):
            os.remove(os.path.join(shard_dir, f))      # a shard of an earlier run of this script
    with open(os.path.join(procd, "ingest_audit.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "subject_ns", "take", "fps", "n_frames", "pelvis_valid_fraction", "up_axis", "notes"])
        w.writerows(b.audit)
    hours = sum(int(r[5]) / float(r[4]) for r in b.manifest) / 3600.0
    fps = collections.Counter(r[4] for r in b.manifest)
    ups = collections.Counter(a[6] for a in b.audit if a[6])
    summ = {"source": b.src, "joint_map": b.key, "records": len(b.manifest), "subjects": len(b.subjects),
            "hours": round(hours, 4), "fps": dict(fps), "up_axis": dict(ups),
            "skipped": sum(a[-1].startswith("SKIPPED") for a in b.audit),
            "refused_or_failed": sum(a[-1].startswith(("REFUSED", "READ FAIL")) for a in b.audit),
            "with_unresolved_joints": sum(a[-1].startswith("unresolved") for a in b.audit)}
    with open(os.path.join(procd, "ingest_summary.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summ, f, indent=1)
        f.write("\n")
    if out:                                            # a trial run: the pooled manifest is not touched
        with open(os.path.join(procd, "manifest_rows.csv"), "w", encoding="utf-8", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows(b.manifest)
        return summ
    # the pooled pose manifest: this source's lines replaced, every other line kept byte for byte
    mp = os.path.join(REPO, "datasets", "_canonical_manifest.csv")
    with open(mp, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    head, body = lines[0], [ln for ln in lines[1:] if ln.split(",", 1)[0] != b.src]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(b.manifest)
    with open(mp, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join([head] + body) + "\n" + buf.getvalue())
    return summ


FOLDS = os.path.join(REPO, "datasets", "_subject_folds_open_mocap.csv")


def write_folds(n_splits=5, seed=0):
    """Subject-level folds of every source of the lot, from the pooled manifest rows, with
    MoveAtlas's own scheme (moveatlas.evaluations.splits.cross_patient_folds, 5 folds, seed 0):
    one row per subject, its fold, records and hours. A source with fewer subjects than folds
    gets no fold (blank) and a note. Refuses to write if a subject lands in two folds."""
    import pandas as pd
    from moveatlas.evaluations.splits import cross_patient_folds
    with open(os.path.join(REPO, "datasets", "_canonical_manifest.csv"), encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["source"] in SOURCES]
    out = []
    for src in SOURCES:
        md = pd.DataFrame([r for r in rows if r["source"] == src])
        if md.empty:
            continue
        md["hours"] = md["n_frames"].astype(float) / md["fps"].astype(float) / 3600.0
        fold_of, note = {}, ""
        try:
            for k, (_, test) in enumerate(cross_patient_folds(md, n_splits=n_splits, seed=seed)):
                for ns in md["subject_ns"].to_numpy()[test]:
                    if fold_of.setdefault(ns, k) != k:
                        sys.exit(f"{src}: {ns} in folds {fold_of[ns]} and {k}")
        except ValueError as e:
            note = f"no fold: {e}"
        for ns, g in md.groupby("subject_ns", sort=True):
            out.append([src, ns, fold_of.get(ns, ""), len(g), f"{g['hours'].sum():.4f}", note])
    with open(FOLDS, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "subject_ns", "fold", "records", "hours", "note"])
        w.writerows(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", default=[], choices=SOURCES)
    ap.add_argument("--folds", action="store_true",
                    help="write datasets/_subject_folds_open_mocap.csv from the pooled manifest rows")
    ap.add_argument("--limit", type=int, default=0, help="first N files per source")
    ap.add_argument("--out", default=None,
                    help="write shards, audit and manifest rows under OUT/<source>/ and leave the pooled "
                         "manifest untouched (a trial run)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not args.only and not args.folds:
        ap.error("give --only and/or --folds")
    for src in args.only:
        b = Build(src, args.limit)
        RUNNERS.get(src, run_c3d)(b)
        if args.limit and not args.out:
            sys.exit("--limit writes a partial source: give --out for a trial run")
        s = write(b, args.out)
        print(json.dumps(s), flush=True)
    if args.folds:
        out = write_folds()
        print(f"{len(out)} subjects -> {os.path.relpath(FOLDS, REPO)}")


if __name__ == "__main__":
    main()
