# -*- coding: utf-8 -*-
"""Ingest NONAN GaitPrint (figshare 27815034) into the canonical IMU contract.

FORMAT, verified on the real zips 2026-08-27: one zip per subject
(S###.zip), one CSV per trial (S###_G##_D##_B##_T##.csv), 321 self-describing
columns at 200 Hz (time column, dt 0.005 s measured per file): FOUR raw
sensors ("<Loc> Accel Sensor X/Y/Z (mG)": Head, Upper spine, Lower spine,
Pelvis) plus Noraxon MyoMotion SEGMENT streams (16 segments x acceleration /
gyroscope / trajectory), which are model outputs of the vendor's fusion, not
sensor readings.

Contract mapping: only the RAW sensors enter the canonical grid (mG -> g):
Head -> head, Upper spine -> trunk, Pelvis -> lower_back. The Lower spine
sensor has no honest slot in the 14-location grid (lower_back is taken by
the sacral Pelvis sensor) and rides in aux with every segment stream:
nothing is discarded, nothing is shoehorned.

DEPOSIT vs PAPER: the resolved article carries 10 subject archives; the
paper describes 41 subjects. The sibling articles (NONAN is published in
parts) are a hunt item, recorded on the datacard.

COHORTS (2026-08-28): --cohort older (default) reads the 41-subject
56+ y article (imu/nonan_gaitprint); --cohort young reads the 35-subject
young-adults collection (imu/nonan_gaitprint_young, owner go 2026-08-28).
Separate directories and namespaces ON PURPOSE: subject IDs collide
across cohorts (S009/S013/S019 exist in both with different content).
The format checks (mG unit, measured ~200 Hz, median |acc| ~1 g) verify
the young cohort's identical-protocol claim at run time; mismatches are
refused, never coerced.

Outputs: datasets/imu/<set>/processed/canonical/<subject>.pkl
         + aux/<subject>.pkl + nonan_ingest_audit.csv
         + rows merged into _canonical_imu_manifest.csv (dedup by source)
Usage: python ingest_nonan.py [--repo PATH] [--limit N] [--cohort older|young]
"""
import argparse
import csv
import io
import os
import pickle
import re
import zipfile

import numpy as np

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
RAW_MAP = {"Head": "head", "Upper spine": "trunk", "Pelvis": "lower_back"}
FPS_DOC = 200.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cohort", choices=["older", "young"], default="older")
    args = ap.parse_args()
    dset = ("nonan_gaitprint" if args.cohort == "older"
            else "nonan_gaitprint_young")
    rawd = os.path.join(args.repo, "datasets", "imu", dset, "raw")
    outd = os.path.join(args.repo, "datasets", "imu", dset, "processed")
    shard_dir = os.path.join(outd, "canonical")
    aux_dir = os.path.join(outd, "aux")
    os.makedirs(shard_dir, exist_ok=True)
    os.makedirs(aux_dir, exist_ok=True)
    zips = sorted(f for f in os.listdir(rawd)
                  if re.fullmatch(r"S\d+\.zip", f))
    if args.limit:
        zips = zips[:args.limit]
    manifest, audit = [], []
    n_rec, n_h = 0, 0.0
    print(f"{dset}: {len(zips)} subject zips")
    for si, zf_name in enumerate(zips, 1):
        subj = zf_name[:-4]
        ns = f"{dset}:{subj}"
        z = zipfile.ZipFile(os.path.join(rawd, zf_name))
        csvs = sorted(n for n in z.namelist() if n.endswith(".csv"))
        recs, auxs = [], []
        for name in csvs:
            trial = os.path.basename(name)[:-4].replace(subj + "_", "")
            f = io.TextIOWrapper(z.open(name), encoding="utf-8",
                                 errors="replace")
            header = f.readline().rstrip().split(",")
            raw_cols = {}
            for ci, col in enumerate(header):
                m = re.match(r"(.+?) Accel Sensor ([XYZ]) \((\w+)\)", col)
                if m and m.group(1) in RAW_MAP:
                    if m.group(3).lower() != "mg":
                        raw_cols = None
                        break
                    raw_cols.setdefault(m.group(1), {})[m.group(2)] = ci
            if raw_cols is None:
                audit.append([subj, trial, "", "REFUSED: raw accel unit is "
                              "not mG"])
                continue
            if len(raw_cols) != 3 or any(len(v) != 3
                                         for v in raw_cols.values()):
                audit.append([subj, trial, "",
                              f"REFUSED: raw sensor columns incomplete "
                              f"({sorted(raw_cols)})"])
                continue
            a = np.loadtxt(f, delimiter=",", dtype=np.float32, ndmin=2)
            t = a[:, 0]
            dt = np.diff(t)
            dt = dt[np.isfinite(dt) & (dt > 0)]
            fs = 1.0 / float(np.median(dt)) if dt.size else 0.0
            if not (0.95 * FPS_DOC <= fs <= 1.05 * FPS_DOC):
                audit.append([subj, trial, f"{fs:.2f}",
                              "REFUSED: measured rate is not ~200 Hz"])
                continue
            T = a.shape[0]
            sig = np.zeros((T, 3, 9), np.float32)
            cmask = np.zeros((3, 9), bool)
            loc_ids = []
            sv = np.ones((T, 3), bool)
            for li, (sensor, loc) in enumerate(sorted(
                    (s, RAW_MAP[s]) for s in raw_cols)):
                for ai, ax in enumerate("XYZ"):
                    v = a[:, raw_cols[sensor][ax]] / 1000.0    # mG -> g
                    fin = np.isfinite(v)
                    sv[:, li] &= fin
                    sig[:, li, ai] = np.where(fin, v, 0.0)
                    cmask[li, ai] = True
                loc_ids.append(LOC_I[loc])
            med = float(np.median(np.linalg.norm(sig[:, :, 0:3], axis=2)))
            if not (0.85 <= med <= 1.15):
                audit.append([subj, trial, f"{med:.3f}",
                              "REFUSED: median |acc| not ~1 g after mG -> g"])
                continue
            rec = {"signal": sig, "location_ids": np.array(loc_ids),
                   "channel_mask": cmask, "sample_valid": sv[:, :],
                   "fps": FPS_DOC, "subject_ns": ns, "task": trial.lower(),
                   "source": dset, "n_frames": int(T),
                   "acc_content": "with_gravity"}
            if not sv.all():
                rec["dropout_fraction"] = float(1.0 - sv.mean())
            recs.append(rec)
            manifest.append([dset, ns, rec["task"], FPS_DOC,
                             int(T), "|".join(LOCATIONS[i] for i in loc_ids)])
            n_rec += 1
            n_h += T / FPS_DOC / 3600
            # everything else (Lower spine raw sensor + all Noraxon segment
            # streams) is preserved per trial in the aux shard, header-keyed
            keep = [ci for ci, col in enumerate(header)
                    if ("Lower spine Accel Sensor" in col
                        or col.startswith("Noraxon MyoMotion"))]
            auxs.append({"task": rec["task"], "fps": FPS_DOC,
                         "columns": [header[ci] for ci in keep],
                         "data": a[:, keep]})
            audit.append([subj, trial, f"{med:.3f}",
                          f"ok, {T} frames, {len(keep)} aux cols"])
        if recs:
            with open(os.path.join(shard_dir, subj + ".pkl"), "wb") as fo:
                pickle.dump(recs, fo)
        if auxs:
            with open(os.path.join(aux_dir, subj + ".pkl"), "wb") as fo:
                pickle.dump({"subject_ns": ns, "trials": auxs,
                             "note": "Noraxon segment streams are vendor "
                                     "fusion outputs, units per column "
                                     "header; Lower spine raw sensor has no "
                                     "grid slot"}, fo)
        print(f"  [{si}/{len(zips)}] {subj}: {len(recs)} trials", flush=True)
    with open(os.path.join(outd, "nonan_ingest_audit.csv"), "w", newline="",
              encoding="utf-8") as fo:
        w = csv.writer(fo, lineterminator="\n")
        w.writerow(["subject", "trial", "check", "notes"])
        w.writerows(audit)
    mp = os.path.join(args.repo, "datasets", "_canonical_imu_manifest.csv")
    with open(mp, newline="", encoding="utf-8") as fo:
        rows = [r for r in csv.reader(fo)]
    head, body = rows[0], [r for r in rows[1:] if r and r[0] != dset]
    with open(mp, "w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo, lineterminator="\n")
        w.writerow(head)
        w.writerows(body + manifest)
    print(f"\n{n_rec} canonical IMU records / "
          f"{len({m[1] for m in manifest})} subjects, {n_h:.1f} h; "
          f"manifest {len(body) + len(manifest)} rows")


if __name__ == "__main__":
    main()
