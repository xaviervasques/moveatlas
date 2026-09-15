# -*- coding: utf-8 -*-
"""Ingest the Van Criekinge full-body gait dataset (figshare c.6503791,
50 stroke + 138 able-bodied) into the canonical skeleton contract.

Source layout, verified on the real zips 2026-08-27: per-cohort zips of
Plug-in Gait C3D trials (<cohort>/<SUBJxx>/<SUBJx (k)>.c3d, 100 Hz points in
mm, force plates and EMG on the analog side). The MAT/XLSX files are the
authors' time-normalized derivatives and are not ingested (no-resampling
policy). Joint mapping pig_vancriekinge in configs/canonical_skeleton.yaml,
identities established by measured geometry, not doc memory.

Cohort comes from the zip name (HealthyPiG vs Stroke); group is a cohort
attribute plus an eval-only label. Analog labels are recorded per trial in
the audit so the EMG/GRF pass can be scoped later without re-reading blind.

PREFIXED LABELS (2026-08-28 pass): 192 healthy C3Ds carry the same PiG model
outputs under a 'SUBJECTID:' label prefix; identities re-verified by measured
geometry on the prefixed files (LFEO~LKNE, LTIO~LANK, LRAO~LWRA, LHUO~LELB).
The prefix is stripped before mapping and NEVER propagated: it looks like a
birthdate-based Vicon ID and must not leave the raw zips. A handful of trials
lack head/elbow/wrist model outputs only; those joints are NaN-filled (the
valid mask carries the truth). Trials without the torso reference
(PELO+LSHO+RSHO) or the lower-body outputs stay refused.

Outputs: datasets/pose/stroke_gait_vancriekinge/processed/canonical.pkl
         + stroke_ingest_audit.csv, manifest rows merged (dedup by source).
Usage: python ingest_stroke_gait.py [--repo PATH] [--limit N]
"""
import argparse
import csv
import os
import pickle
import re
import tempfile
import zipfile

import numpy as np

from build_canonical import make_record, to_canonical

FPS_DOC = 100.0


def read_c3d(zf, name):
    import ezc3d
    with tempfile.NamedTemporaryFile(suffix=".c3d", delete=False) as tmp:
        tmp.write(zf.read(name))
        p = tmp.name
    try:
        c = ezc3d.c3d(p)
    finally:
        os.unlink(p)
    labels = [x.strip() for x in c["parameters"]["POINT"]["LABELS"]["value"]]
    unit = c["parameters"]["POINT"]["UNITS"]["value"][0].strip().lower()
    rate = float(np.asarray(c["parameters"]["POINT"]["RATE"]["value"]).ravel()[0])
    pts = c["data"]["points"][:3]                 # (3, J, T)
    coords = np.transpose(pts, (2, 1, 0)).astype(float)   # (T, J, 3)
    coords[coords == 0.0] = np.nan                # c3d zero = missing
    ana = []
    if "ANALOG" in c["parameters"] and "LABELS" in c["parameters"]["ANALOG"]:
        ana = [x.strip() for x in c["parameters"]["ANALOG"]["LABELS"]["value"]]
    return labels, unit, rate, coords, ana


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="first N c3d per zip")
    args = ap.parse_args()
    rawd = os.path.join(args.repo, "datasets", "pose",
                        "stroke_gait_vancriekinge", "raw")
    zips = sorted(f for f in os.listdir(rawd)
                  if f.lower().endswith(".zip") and not f.startswith("._"))
    out, manifest, audit = [], [], []
    subjects = set()
    for zf_name in zips:
        z = zipfile.ZipFile(os.path.join(rawd, zf_name))
        c3ds = sorted(n for n in z.namelist() if n.lower().endswith(".c3d"))
        if not c3ds:
            continue
        low = zf_name.lower()
        if "healthy" in low or "ablebodied" in low:
            group, label = "able_bodied", 0
        elif "stroke" in low:
            group, label = "stroke", 1
        else:
            audit.append([zf_name, "", "", "", "SKIPPED ZIP: cohort not "
                          "identifiable from the name"])
            continue
        if args.limit:
            c3ds = c3ds[:args.limit]
        print(f"{zf_name}: {len(c3ds)} C3D ({group})")
        for name in c3ds:
            base = os.path.basename(name)
            if "cal" in base.lower():
                audit.append([zf_name, name, "", "",
                              "SKIPPED: calibration trial"])
                continue
            # subject = the containing directory (SUBJ01 healthy, TVC03
            # stroke); trial = the c3d stem ('SUBJ1 (2)' or 'BWA6')
            parts = name.split("/")
            subj_dir = parts[-2] if len(parts) >= 2 else ""
            m = re.search(r"(\d+)", subj_dir)
            if not m:
                audit.append([zf_name, name, "", "",
                              "SKIPPED: no subject number in the directory"])
                continue
            subj_num = int(m.group(1))
            trial = re.sub(r"[^A-Za-z0-9]+", "_", base[:-4]).strip("_")
            ns = f"stroke_gait:{group}:S{subj_num:03d}"
            try:
                labels, unit, rate, coords, ana = read_c3d(z, name)
            except Exception as e:
                audit.append([zf_name, name, "", "", f"READ FAIL: {e}"])
                continue
            if unit != "mm":
                audit.append([zf_name, name, unit, "",
                              "REFUSED: unit is not mm; no guessing"])
                continue
            if abs(rate - FPS_DOC) > 1:
                audit.append([zf_name, name, rate, "",
                              "REFUSED: point rate far from 100 Hz"])
                continue
            prefixed = any(":" in l for l in labels)
            if prefixed:
                labels = [l.split(":", 1)[-1] for l in labels]
            core = {"PELO", "LSHO", "RSHO", "LFEP", "RFEP", "LFEO", "RFEO",
                    "LTIO", "RTIO"}
            nanfill_ok = {"HEDO", "LHUO", "RHUO", "LRAO", "RRAO"}
            needed = core | nanfill_ok
            if any(labels.count(l) > 1 for l in needed):
                audit.append([zf_name, name, "", "",
                              "REFUSED: duplicate needed labels after "
                              "prefix strip"])
                continue
            missing = sorted(needed - set(labels))
            if missing:
                if set(missing) <= nanfill_ok and core <= set(labels):
                    T = coords.shape[0]
                    labels = labels + missing
                    coords = np.concatenate(
                        [coords, np.full((T, len(missing), 3), np.nan)], axis=1)
                else:
                    audit.append([zf_name, name, "", "",
                                  f"REFUSED: missing model outputs {missing[:5]}"])
                    continue
            canon = to_canonical("pig_vancriekinge", labels, coords / 1000.0)
            rec = make_record("stroke_gait_vancriekinge", ns,
                              f"gait_{trial}", canon, 3, rate)
            rec["group"] = group
            rec["label"] = np.int8(label)
            rec["analog_labels"] = ana
            rec["label_prefix_stripped"] = prefixed
            rec["nan_filled_joints"] = missing
            out.append(rec)
            subjects.add(ns)
            manifest.append(["stroke_gait_vancriekinge", ns, rec["take"], 3,
                             rate, rec["n_frames"], rec["modality"]])
            notes = f"{group}; analogs={len(ana)}"
            if prefixed:
                notes += "; prefixed labels stripped"
            if missing:
                notes += f"; NaN-filled {missing}"
            audit.append([zf_name, name, rate, rec["n_frames"], notes])
    procd = os.path.join(args.repo, "datasets", "pose",
                         "stroke_gait_vancriekinge", "processed")
    os.makedirs(procd, exist_ok=True)
    with open(os.path.join(procd, "canonical.pkl"), "wb") as f:
        pickle.dump(out, f)
    with open(os.path.join(procd, "stroke_ingest_audit.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["zip", "c3d", "rate_or_unit", "n_frames", "notes"])
        w.writerows(audit)
    mp = os.path.join(args.repo, "datasets", "_canonical_manifest.csv")
    with open(mp, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f)]
    head = rows[0]
    body = [r for r in rows[1:] if r and r[0] != "stroke_gait_vancriekinge"]
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(body + manifest)
    print(f"\n{len(out)} canonical pose records / {len(subjects)} subjects; "
          f"manifest {len(body) + len(manifest)} rows")


if __name__ == "__main__":
    main()
