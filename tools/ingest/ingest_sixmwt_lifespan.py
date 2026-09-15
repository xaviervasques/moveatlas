# -*- coding: utf-8 -*-
"""Ingest the 6MWT lifespan dataset (60 healthy adults, lower-back IMU) into the
canonical IMU contract.

Source: figshare collection 7954157, file 6MWT_IMU_Dataset.zip (148 MB, CC BY 4.0,
license verified on the figshare item 2026-08-22). Serves cell C1/C3 (age-conditioned
normality): 60 healthy subjects, 10 per decade from 21 to 75.

FORMAT, verified on real files 2026-08-22 (not from the paper):
  6MWT_IMU_Dataset/DATA/Subject <n>/Data.mat   one MATLAB v5 struct per subject
    Data.RawData.Frequency   int, 100 (Hz) for every subject checked
    Data.RawData.Time        (T,)   seconds, dt verified 0.0100 s
    Data.RawData.Acc         (T, 3)
    Data.RawData.Gyr         (T, 3)
    Data.Age, BodyHeight, BodyWeight, SensorDistanceFromGround, SixMWTDistance,
    Sp02_pre/post, HR_pre/post, BorgScale   scalars
    Data.SegmentedData.Path / .Turn, Data.GaitEvents, Data.GaitMetrics
                             derived products of the authors' own pipeline

UNITS, established by MEASUREMENT rather than assumed. The naive test (median
norm of Acc) is WRONG here: over a 6-minute walk the median is inflated by the
subject's own motion, reaching 13.0 for the briskest walkers, which a tight band
rejects as "unit undetermined". The reliable estimator is the CALM WINDOW: split
the record into 1 s windows, take the least variable 5%, and read their median
norm. That lands at 9.92-10.08 for every one of the 60 subjects, i.e. gravity in
m/s2, so acc is divided by 9.80665 to reach the contract's g. Gyr p99 is 165-344,
which is deg/s (rad/s would sit near 3-6), so gyro is passed through. Both the
calm-window and the plain median are recorded per subject in the audit so the
claim stays checkable.

SENSOR LOCATION: lower back. The dataset ships SensorDistanceFromGround (~94 cm,
i.e. lumbar height on a standing adult) and the source describes a single trunk
sensor, so the canonical location is lower_back. One sensor, one record per
subject.

Data.Sex is a MATLAB string object that scipy cannot decode from a v5 struct; it
is therefore reported as unknown rather than guessed. Age and the anthropometrics
ARE plain numerics and are carried through.

The authors' GaitMetrics/GaitEvents are NOT ingested: they are derived features,
not signal, and the contract stores signal. They stay in the zip.

Outputs (datasets/imu/sixmwt_lifespan/processed/):
  canonical_imu.pkl                            canonical IMU records
  sixmwt_ingest_audit.csv                      per-subject verification
  ../../_canonical_imu_manifest_sixmwt_lifespan.csv   manifest rows to merge

Env: /Users/xavi/.venvs/kinefm (numpy, scipy). Usage:
    python ingest_sixmwt_lifespan.py [--repo PATH] [--dry]
"""
import argparse
import csv
import io
import os
import pickle
import re
import zipfile

import numpy as np
import scipy.io as sio

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
G = 9.80665                 # m/s2 per g, exact by definition
LOCATION = "lower_back"


def calm_gravity(nrm, fs, window_s=1.0, quietest_frac=0.05):
    """Median |acc| over the least variable windows: a walking record's plain
    median is inflated by the subject's own motion, the calm windows read gravity."""
    w = max(4, int(window_s * fs))
    m = (len(nrm) // w) * w
    if m < w * 4:
        return float(np.median(nrm))
    win = nrm[:m].reshape(-1, w)
    k = max(1, int(len(win) * quietest_frac))
    calm = win[np.argsort(win.std(axis=1))[:k]]
    return float(np.median(calm))


def subject_of(path):
    m = re.search(r"Subject[ _]*(\d+)", path)
    return f"sixmwt_lifespan:S{int(m.group(1)):02d}" if m else None


def scalar(struct, name):
    """Plain numeric field or '' (MATLAB string objects are not decodable here)."""
    v = getattr(struct, name, None)
    if v is None:
        return ""
    try:
        if isinstance(v, np.ndarray) and v.dtype == object:
            return ""
        f = float(v)
        return "" if np.isnan(f) else f
    except (TypeError, ValueError):
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true", help="audit only, write no pkl")
    args = ap.parse_args()

    base = os.path.join(args.repo, "datasets", "imu", "sixmwt_lifespan")
    rawd = os.path.join(base, "raw")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)

    zips = [f for f in sorted(os.listdir(rawd))
            if f.endswith(".zip") and not f.startswith("._")] if os.path.isdir(rawd) else []
    if not zips:
        raise SystemExit(f"no zip under {rawd}; run fetch_p2_lot.py --only sixmwt_lifespan")
    zpath = os.path.join(rawd, zips[0])

    recs, manifest, audit = [], [], []
    with zipfile.ZipFile(zpath) as z:
        mats = sorted(n for n in z.namelist()
                      if n.endswith(".mat") and not os.path.basename(n).startswith("._"))
        print(f"{os.path.basename(zpath)}: {len(mats)} subject files")
        for name in mats:
            ns = subject_of(name)
            notes = []
            if ns is None:
                audit.append([name, "", "", "", "", "", "SKIP: no subject id in path"])
                continue
            try:
                d = sio.loadmat(io.BytesIO(z.read(name)), squeeze_me=True,
                                struct_as_record=False)["Data"]
                raw = d.RawData
                acc = np.asarray(raw.Acc, np.float64)
                gyr = np.asarray(raw.Gyr, np.float64)
                t = np.asarray(raw.Time, np.float64)
                fs = float(raw.Frequency)
            except Exception as e:
                audit.append([name, ns, "", "", "", "", "", f"UNREADABLE: {e}"])
                print(f"  {ns}: FAILED ({e})")
                continue

            if acc.ndim != 2 or acc.shape[1] != 3 or gyr.shape != acc.shape:
                audit.append([name, ns, "", "", "", "", "",
                              f"REFUSED: acc {acc.shape} gyr {gyr.shape}, expected (T,3)"])
                continue
            T = acc.shape[0]

            dt = float(np.median(np.diff(t))) if t.size > 10 else None
            if dt and abs(1.0 / dt - fs) > 1.0:
                notes.append(f"declared fs {fs} vs dt-implied {1.0 / dt:.2f}")
            nrm = np.linalg.norm(acc, axis=1)
            gnorm = float(np.median(nrm))
            gcalm = calm_gravity(nrm, fs)
            # the measurement that decides the unit; refuse silently-wrong scaling
            if 8.5 <= gcalm <= 11.0:
                acc_g = acc / G
                acc_unit_in = "m/s2"
            elif 0.85 <= gcalm <= 1.15:
                acc_g = acc
                acc_unit_in = "g"
            else:
                audit.append([name, ns, T, fs, f"{gnorm:.3f}", f"{gcalm:.3f}", "",
                              "REFUSED: calm-window |acc| is neither ~9.8 (m/s2) "
                              "nor ~1.0 (g); unit undetermined, not guessed"])
                print(f"  {ns}: REFUSED, calm-window |acc|={gcalm:.3f}")
                continue
            gyr_p99 = float(np.percentile(np.abs(gyr), 99))
            if gyr_p99 < 20:
                notes.append(f"gyro p99 {gyr_p99:.2f} looks like rad/s, not deg/s; "
                             "NOT converted, review")

            sig = np.zeros((T, 1, 9), np.float32)
            sig[:, 0, 0:3] = acc_g
            sig[:, 0, 3:6] = gyr
            cmask = np.zeros((1, 9), bool)
            cmask[0, :6] = True
            recs.append({"signal": sig,
                         "location_ids": np.array([LOC_I[LOCATION]]),
                         "channel_mask": cmask, "fps": fs,
                         "subject_ns": ns, "task": "6mwt",
                         "source": "sixmwt_lifespan", "n_frames": int(T),
                         "acc_content": "with_gravity",
                         "age": scalar(d, "Age"),
                         "body_height_cm": scalar(d, "BodyHeight"),
                         "body_weight_kg": scalar(d, "BodyWeight"),
                         "sensor_height_cm": scalar(d, "SensorDistanceFromGround"),
                         "sixmwt_distance_m": scalar(d, "SixMWTDistance")})
            manifest.append(["sixmwt_lifespan", ns, "6mwt", fs, T, LOCATION])
            audit.append([name, ns, T, fs, f"{gnorm:.3f}", f"{gcalm:.3f}",
                          acc_unit_in,
                          f"dur={T / fs:.0f}s gyro_p99={gyr_p99:.1f}deg/s "
                          f"age={scalar(d, 'Age')} " +
                          ("; ".join(notes) if notes else "ok")])
            print(f"  {ns}: T={T} ({T / fs:.0f} s) fs={fs} acc_in={acc_unit_in}")

    if not args.dry:
        pickle.dump(recs, open(os.path.join(outd, "canonical_imu.pkl"), "wb"))
        mp = os.path.join(args.repo, "datasets",
                          "_canonical_imu_manifest_sixmwt_lifespan.csv")
        with open(mp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "subject_ns", "task", "fps", "n_frames", "locations"])
            w.writerows(manifest)
    with open(os.path.join(outd, "sixmwt_ingest_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "subject_ns", "n_frames", "fps", "median_acc_norm",
                    "calm_window_acc_norm", "acc_unit_in_source", "result"])
        w.writerows(audit)

    bad = [a for a in audit if str(a[-1]).startswith(("REFUSED", "UNREADABLE", "SKIP"))]
    print(f"\n{len(recs)} canonical IMU records / {len(recs)} subjects "
          f"(location {LOCATION}, acc m/s2 -> g, gyro deg/s passed through)")
    if bad:
        print(f"{len(bad)} file(s) NOT ingested; see sixmwt_ingest_audit.csv")
    print("audit -> processed/sixmwt_ingest_audit.csv")
    print("merge _canonical_imu_manifest_sixmwt_lifespan.csv into "
          "datasets/_canonical_imu_manifest.csv after review")


if __name__ == "__main__":
    main()
