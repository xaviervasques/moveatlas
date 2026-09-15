# -*- coding: utf-8 -*-
"""gait120 MotionCapture pass: per-step TRC marker trajectories into
the canonical pose contract + the OpenSim joint-angle .mot files as
per-subject aux shards.

Verified on the real archives 2026-09-03: 8 zips x ~10 subjects, per
subject MotionCapture/<Task>/TRC/Trial*/Step*.trc (39-marker full-body
Plug-in-Gait MARKER set, mm, 100 Hz, ~105-frame step segments) and
JointAngle/<Task>/Trial*/step*.mot (39 OpenSim coordinates, degrees).
Static trials are calibration poses, skipped and audited.

Mapping: configs/canonical_skeleton.yaml gait120_pig_markers; PELV_C
and HEAD_C virtual markers (4-marker centroids) are computed here
because resolve() supports two-point midpoints only. Surface-marker
proxies are documented in the config. subject_ns gait120:S### matches
the EMG pass exactly, so 120 subjects become pose+EMG multimodal.

Angles: NOT canonical (model-derived), stored per subject under
processed/angles/S###.pkl as {task: {"columns": [...],
"data": float32 (T, C), "in_degrees": True}}.

Usage: python ingest_gait120_pose.py [--repo PATH] [--limit N]
"""
import argparse
import csv
import io
import os
import pickle
import re
import zipfile

import numpy as np

from build_canonical import make_record, to_canonical

VIRTUAL = {"PELV_C": ["LASI", "RASI", "LPSI", "RPSI"],
           "HEAD_C": ["LFHD", "RFHD", "LBHD", "RBHD"]}
NEEDED = {"LSHO", "RSHO", "LELB", "RELB", "LWRA", "LWRB", "RWRA",
          "RWRB", "LASI", "RASI", "LPSI", "RPSI", "LKNE", "RKNE",
          "LANK", "RANK", "LFHD", "RFHD", "LBHD", "RBHD"}


def snake(s):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


def parse_trc(raw):
    lines = raw.decode("utf-8", "replace").splitlines()
    hdr = lines[2].split("\t")
    fps = float(hdr[0])
    unit = hdr[4].strip().lower()
    names = [x.strip() for x in lines[3].split("\t")]
    markers = [n for n in names[2:] if n]
    rows = []
    for ln in lines[5:]:
        if not ln.strip():
            continue
        f = ln.split("\t")
        vals = [float(v) if v.strip() not in ("", "nan", "NaN")
                else np.nan for v in f[2:2 + 3 * len(markers)]]
        if len(vals) < 3 * len(markers):
            vals += [np.nan] * (3 * len(markers) - len(vals))
        rows.append(vals)
    arr = np.asarray(rows, float).reshape(len(rows), len(markers), 3)
    return markers, unit, fps, arr


def parse_mot(raw):
    lines = raw.decode("utf-8", "replace").splitlines()
    k = next(i for i, ln in enumerate(lines)
             if ln.strip().lower() == "endheader")
    cols = lines[k + 1].split("\t")
    cols = [c.strip() for c in cols if c.strip()]
    data = []
    for ln in lines[k + 2:]:
        if ln.strip():
            data.append([float(v) for v in ln.split()])
    return cols, np.asarray(data, np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "MOVEATLAS_REPO", os.environ.get(
            "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--limit", type=int, default=0,
                    help="first N TRC per zip")
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "emg", "gait120")
    rawd = os.path.join(base, "raw")
    outd = os.path.join(base, "processed")
    angd = os.path.join(outd, "angles")
    os.makedirs(angd, exist_ok=True)

    recs, manifest, audit = [], [], []
    n_static = n_fail = n_refused = 0
    zips = sorted(f for f in os.listdir(rawd)
                  if f.lower().endswith(".zip")
                  and f.startswith("Gait120"))
    for zn in zips:
        z = zipfile.ZipFile(os.path.join(rawd, zn))
        trcs = sorted(n for n in z.namelist() if n.endswith(".trc"))
        mots = sorted(n for n in z.namelist() if n.endswith(".mot")
                      and "/JointAngle/" in n)
        if args.limit:
            trcs = trcs[:args.limit]
            mots = mots[:args.limit]
        print(f"{zn}: {len(trcs)} trc, {len(mots)} mot", flush=True)
        angles = {}
        for name in trcs:
            parts = name.split("/")
            subj = parts[0]
            if "/Static/" in name:
                n_static += 1
                continue
            m = re.match(
                r"S(\d+)/MotionCapture/([^/]+)/TRC/Trial(\d+)/"
                r"Step(\d+)\.trc", name, re.I)
            if not m:
                audit.append([zn, name, "", "SKIP: unparsed path"])
                continue
            ns = f"gait120:S{int(m.group(1)):03d}"
            task = (f"{snake(m.group(2))}_trial{int(m.group(3)):02d}"
                    f"_step{int(m.group(4)):02d}")
            try:
                markers, unit, fps, arr = parse_trc(z.read(name))
            except Exception as e:
                n_fail += 1
                audit.append([zn, name, ns, f"READ FAIL {e}"])
                continue
            if unit != "mm":
                n_refused += 1
                audit.append([zn, name, ns,
                              f"REFUSED: unit {unit!r} not mm"])
                continue
            missing = NEEDED - set(markers)
            if missing:
                n_refused += 1
                audit.append([zn, name, ns,
                              f"REFUSED: missing {sorted(missing)[:5]}"])
                continue
            idx = {n2: i for i, n2 in enumerate(markers)}
            T = arr.shape[0]
            vlist = []
            for vname, comps in VIRTUAL.items():
                pts = np.stack([arr[:, idx[c]] for c in comps], axis=1)
                vlist.append(np.nanmean(pts, axis=1))
                markers = markers + [vname]
            arr = np.concatenate(
                [arr, np.stack(vlist, axis=1)], axis=1)
            canon = to_canonical("gait120_pig_markers", markers,
                                 arr / 1000.0)
            rec = make_record("gait120", ns, task, canon, 3, fps)
            recs.append(rec)
            manifest.append(["gait120", ns, task, 3, fps,
                             rec["n_frames"], rec["modality"]])
            audit.append([zn, name, ns,
                          f"ok T={T} valid={rec['valid_mask'].mean():.3f}"])
        for name in mots:
            m = re.match(r"S(\d+)/JointAngle/([^/]+)/Trial(\d+)/"
                         r"step(\d+)\.mot", name, re.I)
            if not m:
                continue
            subj = f"S{int(m.group(1)):03d}"
            task = (f"{snake(m.group(2))}_trial{int(m.group(3)):02d}"
                    f"_step{int(m.group(4)):02d}")
            try:
                cols, data = parse_mot(z.read(name))
            except Exception as e:
                audit.append([zn, name, subj, f"MOT FAIL {e}"])
                continue
            angles.setdefault(subj, {})[task] = {
                "columns": cols, "data": data, "in_degrees": True}
        for subj, d in angles.items():
            with open(os.path.join(angd, subj + ".pkl"), "wb") as f:
                pickle.dump(d, f)

    print(f"{len(recs)} pose records / "
          f"{len({r['subject_ns'] for r in recs})} subjects; "
          f"static skipped {n_static}, refused {n_refused}, "
          f"fail {n_fail}")
    with open(os.path.join(outd, "canonical.pkl"), "wb") as f:
        pickle.dump(recs, f)
    # merge into the MAIN pose manifest (replace prior gait120 rows)
    mp = os.path.join(args.repo, "datasets", "_canonical_manifest.csv")
    with open(mp, newline="", encoding="utf-8") as f:
        r = list(csv.reader(f))
    head, old = r[0], [x for x in r[1:] if x and x[0] != "gait120"]
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(old + manifest)
    print(f"_canonical_manifest.csv: {len(old) + len(manifest)} rows "
          f"(+{len(manifest)})")
    with open(os.path.join(outd, "pose_ingest_audit.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["zip", "file", "subject_ns", "notes"])
        w.writerows(audit)
    print("done.")


if __name__ == "__main__":
    main()
