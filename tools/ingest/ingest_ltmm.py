# -*- coding: utf-8 -*-
"""Ingest LTMM (PhysioNet ltmm 1.0.0): 71 community-dwelling elders, 3-day
lower-back accelerometry plus 1-minute lab walks. C3 aging cell; the faller /
non-faller split is a LABEL (eval only, R1), never pretraining material.

Layout expected under datasets/imu/ltmm/raw/ after unzipping ltmm-1.0.0.zip:
  <root>/CO001.dat + CO001.hea ...      non-fallers (controls)
  <root>/FO001.dat + FO001.hea ...      fallers (>=2 falls in the past year)
  <root>/LabWalks/*.dat|.hea            1-minute lab walks
  <root>/ClinicalDemogData_COFL.xlsx    demographics + clinical tests
WFDB MIT format, self-describing: fs, units and channel names come from each
.hea and are ENFORCED, not assumed. VERIFIED ON THE REAL HEADERS 2026-08-25:
six channels, not the three the PhysioNet abstract suggests, named
v/ml/ap-acceleration (unit g) and yaw/pitch/roll-velocity (unit degrees/s),
i.e. accelerometer AND gyroscope in anatomical axes. Axis mapping follows the
fog_turning precedent (x=ML, y=AP, z=SI/vertical), with each angular velocity
in the slot of the axis it rotates ABOUT: pitch(about ML)->gyro_x,
roll(about AP)->gyro_y, yaw(about vertical)->gyro_z. Any unexpected channel
name or unit refuses the record; a record whose median |acc| is not ~1 g
after conversion is refused too (the capture24 check).

STORAGE follows ingest_capture24.py: one shard per recording under
processed/canonical/, records cut into 1-hour segments (task h000, h001, ...)
so a 3-day recording does not become one 300 MB pickle. Lab walks are single
records with task lab_walk. Faller status rides on each record as
group = faller|control (a cohort attribute like capture24's age_band) AND as
the eval-only label 0/1.

Outputs:
  datasets/imu/ltmm/processed/canonical/<record>.pkl
  datasets/imu/ltmm/processed/ltmm_ingest_audit.csv
  datasets/_canonical_imu_manifest_ltmm.csv     rows merged by --merge

Usage: python ingest_ltmm.py [--repo PATH] [--limit N] [--merge]
"""
import argparse
import csv
import glob
import os
import pickle

import numpy as np

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
LOCATION = "lower_back"
G = 9.80665
# unit string in the .hea (lowercased) -> factor to g. Nothing else is accepted.
UNIT_TO_G = {"g": 1.0, "mg": 1e-3, "milli-g": 1e-3, "mili-g": 1e-3,
             "m/s^2": 1.0 / G, "m/s2": 1.0 / G, "ms^-2": 1.0 / G}
# channel-name -> (contract slot, expected unit family). Exact vocabulary read
# off the real headers; anything else refuses the record. Axis convention per
# the fog_turning precedent: x=ML, y=AP, z=SI(vertical); angular velocities go
# in the slot of the axis they rotate about.
CH_MAP = {"ml-acceleration": ("acc_x", "acc"),
          "ap-acceleration": ("acc_y", "acc"),
          "v-acceleration": ("acc_z", "acc"),
          "pitch-velocity": ("gyro_x", "gyro"),
          "roll-velocity": ("gyro_y", "gyro"),
          "yaw-velocity": ("gyro_z", "gyro")}
GYRO_UNITS = {"degrees/s": 1.0, "deg/s": 1.0, "degree/s": 1.0}


CH_SLOTS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z",
            "mag_x", "mag_y", "mag_z"]


def segment_records(chans, fs, ns, source, group, label, seg_frames, task_fmt):
    """chans {slot: (T,) in canonical units} -> contract records, 1-hour cuts."""
    out = []
    T = len(next(iter(chans.values())))
    present = [s for s in CH_SLOTS if s in chans]
    for k, s0 in enumerate(range(0, T, seg_frames)):
        s1 = min(s0 + seg_frames, T)
        if s1 - s0 < fs * 60 and T > seg_frames:   # drop a final sub-minute sliver
            break
        n = s1 - s0
        sig = np.zeros((n, 1, 9), np.float32)
        cmask = np.zeros((1, 9), bool)
        fin = np.ones((n, len(present)), bool)
        for ci, slot in enumerate(present):
            a = chans[slot][s0:s1]
            f = np.isfinite(a)
            fin[:, ci] = f
            sig[:, 0, CH_SLOTS.index(slot)] = np.where(f, a, 0.0)
            cmask[0, CH_SLOTS.index(slot)] = True
        sv = fin.all(axis=1)[:, None]
        rec = {"signal": sig, "location_ids": np.array([LOC_I[LOCATION]]),
               "channel_mask": cmask, "sample_valid": sv,
               "fps": float(fs), "subject_ns": ns, "task": task_fmt(k),
               "source": source, "n_frames": int(n),
               "acc_content": "with_gravity",
               "group": group, "label": np.int8(label)}
        if not sv.all():
            rec["dropout_fraction"] = float(1.0 - sv.mean())
        out.append(rec)
    return out


def read_channels(hea_path, audit_row):
    """WFDB record -> (dict contract_slot -> float32 array in canonical units,
    fs, err). Names AND units enforced against the surveyed vocabulary."""
    import wfdb
    rec = wfdb.rdrecord(hea_path[:-4])
    sig = rec.p_signal                                # physical units, float64
    chans = {}
    for i, (nm, u) in enumerate(zip(rec.sig_name, rec.units)):
        nml, ul = nm.strip().lower(), u.strip().lower()
        if nml not in CH_MAP:
            return None, None, f"channel {nm!r} not in the surveyed vocabulary"
        slot, fam = CH_MAP[nml]
        if fam == "acc":
            if ul not in UNIT_TO_G:
                return None, None, f"unit {u!r} on {nm!r} not a known acceleration unit"
            chans[slot] = (sig[:, i] * UNIT_TO_G[ul]).astype(np.float32)
        else:
            if ul not in GYRO_UNITS:
                return None, None, f"unit {u!r} on {nm!r} not a known angular-velocity unit"
            chans[slot] = (sig[:, i] * GYRO_UNITS[ul]).astype(np.float32)
    if not {"acc_x", "acc_y", "acc_z"} <= set(chans):
        return None, None, f"missing acceleration channels ({sorted(chans)})"
    audit_row.append("|".join(f"{n}[{u}]" for n, u in zip(rec.sig_name, rec.units)))
    return chans, float(rec.fs), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="first N recordings only")
    ap.add_argument("--merge", action="store_true",
                    help="merge the rows into datasets/_canonical_imu_manifest.csv")
    args = ap.parse_args()
    rawd = os.path.join(args.repo, "datasets", "imu", "ltmm", "raw")
    heas = sorted(p for p in glob.glob(os.path.join(rawd, "**", "*.hea"),
                                       recursive=True)
                  if not os.path.basename(p).startswith("._"))
    if not heas:
        raise SystemExit(f"no .hea under {rawd}; unzip ltmm-1.0.0.zip first")
    if args.limit:
        heas = heas[:args.limit]
    outd = os.path.join(args.repo, "datasets", "imu", "ltmm", "processed")
    shard_dir = os.path.join(outd, "canonical")
    os.makedirs(shard_dir, exist_ok=True)

    manifest, audit = [], []
    n_rec, n_h = 0, 0.0
    print(f"ltmm: {len(heas)} WFDB records")
    for i, hea in enumerate(heas, 1):
        base = os.path.splitext(os.path.basename(hea))[0]
        is_lab = "labwalk" in os.path.dirname(hea).lower()
        pfx = base[:2].upper()
        if pfx not in ("CO", "FO", "FL"):
            audit.append([base, "", "", "", f"SKIPPED: unrecognized prefix {pfx}"])
            continue
        group = "control" if pfx == "CO" else "faller"
        # SUBJECT IDENTITY: LabWalks files are lowercase with a _base suffix
        # (fl037_base) while home recordings are uppercase (FL037). The first
        # run kept the case and split every person into two subject_ns, which
        # is exactly the split-leak the identity check exists to prevent.
        # Uppercase the id so both recordings of one person share one subject.
        ns = f"ltmm:{base.split('_')[0][:5].upper()}"
        row = [base]
        try:
            chans, fs, err = read_channels(hea, row)
        except Exception as e:
            chans, fs, err = None, None, f"READ FAIL: {e}"
        if chans is None:
            audit.append([base, "", "", "", f"REFUSED: {err}"])
            print(f"  {base}: REFUSED, {err}")
            continue
        acc = np.stack([chans["acc_x"], chans["acc_y"], chans["acc_z"]], axis=1)
        T = acc.shape[0]
        finite = np.isfinite(acc).all(axis=1)
        med = float(np.median(np.linalg.norm(acc[finite][:200000], axis=1))) \
            if finite.any() else 0.0
        if not (0.85 <= med <= 1.15):
            audit.append([base, T, f"{med:.3f}", "",
                          "REFUSED: median |acc| is not ~1 g after unit conversion"])
            print(f"  {base}: REFUSED, median |acc|={med:.3f} g")
            continue
        seg = int(fs * 3600)
        if is_lab:
            recs = segment_records(chans, fs, ns, "ltmm", group,
                                   1 if group == "faller" else 0,
                                   seg_frames=max(T, 1),
                                   task_fmt=lambda k, b=base: f"lab_walk_{b}")
        else:
            recs = segment_records(chans, fs, ns, "ltmm", group,
                                   1 if group == "faller" else 0,
                                   seg_frames=seg, task_fmt=lambda k: f"h{k:03d}")
        with open(os.path.join(shard_dir, base + ".pkl"), "wb") as f:
            pickle.dump(recs, f)
        for r in recs:
            manifest.append(["ltmm", r["subject_ns"], r["task"],
                             round(r["fps"], 2), r["n_frames"], LOCATION])
        hrs = T / fs / 3600
        n_rec += len(recs)
        n_h += hrs
        audit.append([base, acc.shape[0], f"{med:.3f}", len(recs),
                      f"{group}, fs={fs}, {hrs:.2f} h, ch={row[-1]}"])
        print(f"  [{i:3d}/{len(heas)}] {base}: {hrs:5.1f} h at {fs:g} Hz -> "
              f"{len(recs):2d} records ({group})", flush=True)

    mp = os.path.join(args.repo, "datasets", "_canonical_imu_manifest_ltmm.csv")
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "subject_ns", "task", "fps", "n_frames", "locations"])
        w.writerows(manifest)
    with open(os.path.join(outd, "ltmm_ingest_audit.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["record", "n_frames", "median_acc_norm_g", "n_records", "notes"])
        w.writerows(audit)
    subs = {m[1] for m in manifest}
    print(f"\n{n_rec} canonical IMU records / {len(subs)} subjects, {n_h:.0f} hours")

    if args.merge and manifest:
        main_mp = os.path.join(args.repo, "datasets", "_canonical_imu_manifest.csv")
        with open(main_mp, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f)]
        head, body = rows[0], [r for r in rows[1:] if r and r[0] != "ltmm"]
        with open(main_mp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(head)
            w.writerows(body + manifest)
        print(f"merged into {main_mp} ({len(body) + len(manifest)} rows)")


if __name__ == "__main__":
    main()
