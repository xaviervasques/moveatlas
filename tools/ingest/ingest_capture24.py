# -*- coding: utf-8 -*-
"""Ingest Capture-24 IN FULL: 151 healthy adults, free-living wrist accelerometry.

Replaces the v1 sampling. build_canonical_imu.ingest_capture24 read only the first
win*n_win = 60,000 lines of each subject, i.e. 10 minutes, and kept 20 windows of
30 s: 3,020 records, 25 hours. The corpus actually holds about 4,200 hours, so v1
was using 0.6 percent of a dataset already sitting on disk. It also discarded the
annotation column entirely.

VERIFIED ON THE REAL FILES 2026-08-23 (not from the paper):
  capture24.zip
    capture24/P###.csv.gz            151 subjects, columns time,x,y,z,annotation
                                     P001 alone is 10,020,002 rows = 27.8 h at 100 Hz
    capture24/metadata.csv           pid, age (banded), sex
    capture24/annotation-label-dictionary.csv
                                     206 free-text annotations mapped to the
                                     published coarse schemes (Willetts2018,
                                     Doherty2018, WillettsMET2018, ...)
  Accelerometer values are ALREADY IN g: median |acc| over P001 is 0.972, so
  nothing is rescaled. The contract's canonical acc unit is g.

LATERALITY IS UNRESOLVED, ON PURPOSE. The device is worn on the DOMINANT wrist and
the dataset does not distribute handedness, so no subject's side is knowable. The
14-location taxonomy has no side-agnostic wrist, so records keep v1's wrist_L slot
for continuity and carry laterality="unknown" plus worn_on="dominant_wrist". The
slot is NOMINAL: do not use this source for anything laterality-sensitive. Writing
wrist_R instead would be right for the right-handed majority and wrong for the
rest, which is a worse kind of wrong than saying nothing.

ANNOTATIONS are labels, so eval-only (R1), never pretraining. They are constant
over long stretches, so they are stored RUN-LENGTH ENCODED (start index, code)
against a per-record code table rather than one string per sample.

STORAGE: one shard per subject under processed/canonical/, the same layout the
socle sets use, because a single subject is ~28 h and a flat pkl would be
unwieldy. Records are 1-hour segments: long enough to keep sleep and activity
structure intact, small enough (360,000 frames, 13 MB) to load one at a time.
Consecutive hours of a subject are h000, h001, ... in order.

Outputs:
  datasets/imu/capture24/processed/canonical/<subject>.pkl   sharded records
  datasets/imu/capture24/processed/capture24_ingest_audit.csv
  datasets/_canonical_imu_manifest_capture24.csv             rows to merge

Env: /Users/xavi/.venvs/kinefm (numpy, pandas). Usage:
    python ingest_capture24.py [--repo PATH] [--limit N] [--hours H]
"""
import argparse
import csv
import gzip
import io
import os
import pickle
import zipfile

import numpy as np
import pandas as pd

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
LOCATION = "wrist_L"          # NOMINAL, see the laterality note above
FPS = 100.0
SEG = 360_000                 # 1 hour at 100 Hz


def rle(codes):
    """(starts, values) for a run-length encoded int array."""
    codes = np.asarray(codes)
    if codes.size == 0:
        return np.array([], np.int64), np.array([], np.int32)
    change = np.flatnonzero(np.diff(codes)) + 1
    starts = np.concatenate(([0], change))
    return starts.astype(np.int64), codes[starts].astype(np.int32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="first N subjects only")
    ap.add_argument("--hours", type=float, default=0.0,
                    help="cap hours kept per subject (0 = all)")
    args = ap.parse_args()

    zpath = os.path.join(args.repo, "datasets", "socle", "capture24", "raw",
                         "capture24.zip")
    if not os.path.exists(zpath):
        raise SystemExit(f"missing {zpath}")
    outd = os.path.join(args.repo, "datasets", "imu", "capture24", "processed")
    shard_dir = os.path.join(outd, "canonical")
    os.makedirs(shard_dir, exist_ok=True)

    z = zipfile.ZipFile(zpath)
    meta = {}
    try:
        for r in csv.DictReader(io.StringIO(
                z.read("capture24/metadata.csv").decode("utf8", "replace"))):
            meta[r["pid"]] = {"age_band": r.get("age", ""), "sex": r.get("sex", "")}
    except KeyError:
        pass
    # coarse label schemes published with the corpus, keyed by the raw annotation
    labeldict = {}
    try:
        rows = list(csv.DictReader(io.StringIO(
            z.read("capture24/annotation-label-dictionary.csv").decode("utf8", "replace"))))
        for r in rows:
            labeldict[r["annotation"]] = {k: v for k, v in r.items() if k != "annotation"}
    except KeyError:
        pass

    names = sorted(x for x in z.namelist() if x.endswith(".csv.gz"))
    if args.limit:
        names = names[:args.limit]
    print(f"capture24: {len(names)} subjects, full ingestion "
          f"({'all hours' if not args.hours else f'{args.hours} h cap'})")

    manifest, audit, n_rec, n_h = [], [], 0, 0.0
    for si, name in enumerate(names, 1):
        subj = os.path.basename(name).split(".")[0]
        ns = f"capture24:{subj}"
        try:
            # annotation is read as plain string and factorized after:
            # pandas 3 rejects "category" as a read_csv dtype.
            df = pd.read_csv(io.BytesIO(gzip.decompress(z.read(name))),
                             usecols=["x", "y", "z", "annotation"],
                             dtype={"x": np.float32, "y": np.float32,
                                    "z": np.float32, "annotation": "str"})
        except Exception as e:
            audit.append([subj, "", "", "", f"UNREADABLE: {e}"])
            print(f"  {subj}: FAILED ({e})")
            continue

        acc = df[["x", "y", "z"]].to_numpy(np.float32)
        codes, cats = pd.factorize(df["annotation"], use_na_sentinel=False)
        codes = np.asarray(codes)
        cats = [str(c) for c in cats]
        del df
        T = acc.shape[0]
        if args.hours:
            T = min(T, int(args.hours * 3600 * FPS))
            acc, codes = acc[:T], codes[:T]

        finite = np.isfinite(acc).all(axis=1)
        gnorm = float(np.median(np.linalg.norm(acc[finite][:200000], axis=1))) \
            if finite.any() else 0.0
        if not (0.85 <= gnorm <= 1.15):
            audit.append([subj, T, f"{gnorm:.3f}", "",
                          "REFUSED: median |acc| is not ~1 g; unit undetermined"])
            print(f"  {subj}: REFUSED, median |acc|={gnorm:.3f}")
            continue

        recs = []
        for k, s0 in enumerate(range(0, T, SEG)):
            s1 = min(s0 + SEG, T)
            if s1 - s0 < FPS * 60:            # drop a final sliver under a minute
                break
            a = acc[s0:s1]
            n = a.shape[0]
            sig = np.zeros((n, 1, 9), np.float32)
            sig[:, 0, 0:3] = np.where(np.isfinite(a), a, 0.0)
            cmask = np.zeros((1, 9), bool)
            cmask[0, 0:3] = True
            sv = np.isfinite(a).all(axis=1)[:, None]
            starts, vals = rle(codes[s0:s1])
            rec = {"signal": sig, "location_ids": np.array([LOC_I[LOCATION]]),
                   "channel_mask": cmask, "sample_valid": sv,
                   "fps": FPS, "subject_ns": ns, "task": f"h{k:03d}",
                   "source": "capture24", "n_frames": int(n),
                   "acc_content": "with_gravity",
                   "laterality": "unknown", "worn_on": "dominant_wrist",
                   "annotation_rle": (starts, vals), "annotation_codes": cats,
                   "age_band": meta.get(subj, {}).get("age_band", ""),
                   "sex": meta.get(subj, {}).get("sex", "")}
            if not sv.all():
                rec["dropout_fraction"] = float(1.0 - sv.mean())
            recs.append(rec)
            manifest.append(["capture24", ns, f"h{k:03d}", FPS, n, LOCATION])
        with open(os.path.join(shard_dir, f"{subj}.pkl"), "wb") as f:
            pickle.dump(recs, f)
        hrs = T / FPS / 3600
        n_rec += len(recs); n_h += hrs
        audit.append([subj, T, f"{gnorm:.3f}", len(recs),
                      f"{hrs:.2f} h, {len(cats)} distinct annotations"])
        print(f"  [{si:3d}/{len(names)}] {subj}: {hrs:5.1f} h -> {len(recs):3d} records"
              f"  ({n_h:7.0f} h so far)", flush=True)

    mp = os.path.join(args.repo, "datasets", "_canonical_imu_manifest_capture24.csv")
    with open(mp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "task", "fps", "n_frames", "locations"])
        w.writerows(manifest)
    with open(os.path.join(outd, "capture24_ingest_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "n_frames", "median_acc_norm_g", "n_records", "result"])
        w.writerows(audit)
    if labeldict:
        with open(os.path.join(outd, "annotation_label_dictionary.pkl"), "wb") as f:
            pickle.dump(labeldict, f)

    print(f"\n{n_rec} canonical IMU records / {len({m[1] for m in manifest})} subjects, "
          f"{n_h:.0f} hours (v1 kept 25 h)")
    print(f"shards -> {shard_dir}")
    print("merge _canonical_imu_manifest_capture24.csv into "
          "datasets/_canonical_imu_manifest.csv after review")


if __name__ == "__main__":
    main()
