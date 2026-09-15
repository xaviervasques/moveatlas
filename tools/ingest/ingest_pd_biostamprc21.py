# -*- coding: utf-8 -*-
"""Ingest PD-BioStampRC21 (IEEE DataPort, 17 PD + 17 controls) into the
canonical IMU contract.

FORMAT, verified on the real zip 2026-08-26: FullDataSet_PD-BioStampRC21.zip,
one folder per subject id, five accelerometer CSVs (Timestampms, AccelXg,
AccelYg, AccelZg: the unit is in the column NAME, g) plus AnnotID<id>.csv
(EventType, Start/Stop Timestamp ms, Value: UPDRS task windows, medication
ON/OFF, body-area notes).

PLACEMENT, from the dataset page and Adams et al. 2021 (npj Parkinson's
Disease, "A real-world study of wearable sensors in Parkinson's disease"):
chest (ch), left/right anterior THIGH (ll/rl), left/right anterior FOREARM
(lh/rh), sampled at 31.25 Hz. The 14-location grid has no forearm slot, so
the forearm sensors use wrist_L/wrist_R as PROXY slots, exactly like
capture24's nominal wrist: the true placement is carried verbatim in
rec["placement"] and the slot must not be read as anatomy. Extending the grid
is a contract change and belongs to G2, not to an ingester.

DESIGN, per the pads precedent (one record per device, no cross-device
resampling): each sensor stream becomes its own record, cut into 1-hour
segments (ltmm/capture24 pattern). The five streams of a subject share
subject_ns; their Timestampms clocks are per-recording and are NOT assumed
aligned across sensors. fs is measured per file from the median dt and
refused when it strays from the documented 31.25 Hz. Annotations are stored
once per subject (processed/annotations/<id>.pkl), labels stay eval-only.

Usage: python ingest_pd_biostamprc21.py [--repo PATH] [--limit N] [--merge]
"""
import argparse
import csv
import io
import os
import pickle
import zipfile

import numpy as np

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
SENSORS = {"ch": ("trunk", "chest"),
           "ll": ("thigh_L", "left anterior thigh"),
           "rl": ("thigh_R", "right anterior thigh"),
           "lh": ("wrist_L", "left anterior forearm (PROXY slot wrist_L)"),
           "rh": ("wrist_R", "right anterior forearm (PROXY slot wrist_R)")}
FS_DOC = 31.25


def segment(acc, ts_ms, fs, ns, sensor, loc, placement, seg_s=3600):
    out = []
    T = acc.shape[0]
    seg_frames = int(fs * seg_s)
    for k, s0 in enumerate(range(0, T, seg_frames)):
        s1 = min(s0 + seg_frames, T)
        if s1 - s0 < fs * 60 and T > seg_frames:
            break
        a = acc[s0:s1]
        n = a.shape[0]
        sig = np.zeros((n, 1, 9), np.float32)
        fin = np.isfinite(a)
        sig[:, 0, 0:3] = np.where(fin, a, 0.0)
        cmask = np.zeros((1, 9), bool)
        cmask[0, 0:3] = True
        sv = fin.all(axis=1)[:, None]
        rec = {"signal": sig, "location_ids": np.array([LOC_I[loc]]),
               "channel_mask": cmask, "sample_valid": sv,
               "fps": float(fs), "subject_ns": ns,
               "task": f"{sensor}_h{k:03d}",
               "source": "pd_biostamprc21", "n_frames": int(n),
               "acc_content": "with_gravity",
               "placement": placement,
               "t0_ms": int(ts_ms[s0]),
               "annotations_ref": "processed/annotations/<subject>.pkl, "
                                  "same Timestampms clock as t0_ms"}
        if not sv.all():
            rec["dropout_fraction"] = float(1.0 - sv.mean())
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="first N subjects")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    zp = os.path.join(args.repo, "datasets", "imu", "pd_biostamprc21", "raw",
                      "FullDataSet_PD-BioStampRC21.zip")
    z = zipfile.ZipFile(zp)
    subs = sorted({n.split("/")[0] for n in z.namelist()
                   if "/" in n and n.split("/")[0].isdigit()})
    if args.limit:
        subs = subs[:args.limit]
    outd = os.path.join(args.repo, "datasets", "imu", "pd_biostamprc21",
                        "processed")
    shard_dir = os.path.join(outd, "canonical")
    ann_dir = os.path.join(outd, "annotations")
    os.makedirs(shard_dir, exist_ok=True)
    os.makedirs(ann_dir, exist_ok=True)
    manifest, audit = [], []
    n_rec, n_h = 0, 0.0
    print(f"pd_biostamprc21: {len(subs)} subjects")
    for si, sub in enumerate(subs, 1):
        ns = f"pd_biostamprc21:{sub}"
        recs_all = []
        # annotations first: stored once, referenced by every record
        ann_name = f"{sub}/AnnotID{sub}.csv"
        if ann_name in z.namelist():
            rows = list(csv.DictReader(
                io.TextIOWrapper(z.open(ann_name), encoding="utf-8",
                                 errors="replace")))
            with open(os.path.join(ann_dir, sub + ".pkl"), "wb") as f:
                pickle.dump({"subject_ns": ns, "events": rows,
                             "note": "EventType/Start/Stop in ms on the "
                                     "session clock; UPDRS windows and "
                                     "medication state; eval only"}, f)
        for sensor, (loc, placement) in SENSORS.items():
            fn = f"{sub}/{sensor}_ID{sub}Accel.csv"
            if fn not in z.namelist():
                audit.append([sub, sensor, "", "", "", "missing file"])
                continue
            raw = np.genfromtxt(io.TextIOWrapper(z.open(fn), encoding="utf-8",
                                                 errors="replace"),
                                delimiter=",", skip_header=1, dtype=np.float64)
            if raw.ndim != 2 or raw.shape[1] != 4 or raw.shape[0] < 100:
                audit.append([sub, sensor, raw.shape if raw.ndim else "",
                              "", "", "REFUSED: unexpected shape"])
                continue
            ts, acc = raw[:, 0], raw[:, 1:4].astype(np.float32)
            dt = np.diff(ts)
            dt = dt[np.isfinite(dt) & (dt > 0)]
            fs = 1000.0 / float(np.median(dt)) if dt.size else 0.0
            if not (0.9 * FS_DOC <= fs <= 1.1 * FS_DOC):
                audit.append([sub, sensor, raw.shape[0], f"{fs:.2f}", "",
                              "REFUSED: measured fs disagrees with the "
                              "documented 31.25 Hz"])
                continue
            fin = np.isfinite(acc).all(axis=1)
            med = float(np.median(np.linalg.norm(acc[fin][:200000], axis=1))) \
                if fin.any() else 0.0
            if not (0.85 <= med <= 1.15):
                audit.append([sub, sensor, raw.shape[0], f"{fs:.2f}",
                              f"{med:.3f}", "REFUSED: median |acc| not ~1 g "
                              "despite the g column names"])
                continue
            recs = segment(acc, ts, FS_DOC, ns, sensor, loc, placement)
            recs_all += recs
            hrs = raw.shape[0] / fs / 3600
            n_h += hrs
            audit.append([sub, sensor, raw.shape[0], f"{fs:.3f}",
                          f"{med:.3f}", f"{loc}, {hrs:.1f} h, {len(recs)} seg"])
        if recs_all:
            with open(os.path.join(shard_dir, sub + ".pkl"), "wb") as f:
                pickle.dump(recs_all, f)
            for r in recs_all:
                manifest.append(["pd_biostamprc21", r["subject_ns"], r["task"],
                                 round(r["fps"], 2), r["n_frames"],
                                 LOCATIONS[int(r["location_ids"][0])]])
            n_rec += len(recs_all)
        print(f"  [{si:2d}/{len(subs)}] {sub}: {len(recs_all)} records",
              flush=True)
    mp = os.path.join(args.repo, "datasets",
                      "_canonical_imu_manifest_pd_biostamprc21.csv")
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "subject_ns", "task", "fps", "n_frames",
                    "locations"])
        w.writerows(manifest)
    with open(os.path.join(outd, "biostamp_ingest_audit.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject", "sensor", "n_samples", "fs_measured",
                    "median_acc_norm_g", "notes"])
        w.writerows(audit)
    print(f"\n{n_rec} canonical IMU records / "
          f"{len({m[1] for m in manifest})} subjects, {n_h:.0f} sensor-hours")
    if args.merge and manifest:
        main_mp = os.path.join(args.repo, "datasets",
                               "_canonical_imu_manifest.csv")
        with open(main_mp, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f)]
        head, body = rows[0], [r for r in rows[1:]
                               if r and r[0] != "pd_biostamprc21"]
        with open(main_mp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(head)
            w.writerows(body + manifest)
        print(f"merged into {main_mp} ({len(body) + len(manifest)} rows)")


if __name__ == "__main__":
    main()
