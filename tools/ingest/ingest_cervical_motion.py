# -*- coding: utf-8 -*-
"""Ingest the multi-planar cervical motion dataset (Delsys Avanti, 15 subjects).

Source: figshare 26935900, Dataset.zip (409 MB), CC BY 4.0.
LICENCE, settled 2026-08-23: an earlier note flagged this as CC BY-NC-ND versus
CC BY. There was no conflict, the two strings describe different objects. Nature
states "This article is licensed under CC BY-NC-ND" about the Scientific Data
PAPER (10.1038/s41597-024-04351-4); the paper's own Data Records section points at
figshare 26935900, whose deposit is CC BY 4.0, and the deposit governs the data.
No longer evaluation-only.

FORMAT, verified on real files 2026-08-22 against the bundled Dataset/README.md:
  Dataset/<date>_<subject>/<date>_<subject>_<part>_<plane>.csv    127 files, 15 subjects
  20 columns = 10 signals, each preceded by ITS OWN X[s] time column, because the
  Delsys export interleaves channels sampled at different rates:
    Avanti sensor 1: EMG 1 (filtered, Remove Mean)   dt 0.00056 s -> 1785.7 Hz
    Avanti sensor 1: ORIENT.W/X/Y/Z 1                dt 0.0135  s ->   74.1 Hz
    Avanti sensor 2: EMG 2                           1785.7 Hz
    Avanti sensor 2: ORIENT.W/X/Y/Z 2                  74.1 Hz
  The two rates are NOT resampled onto each other: each stream keeps its own
  clock, as the contract requires (native fps per sample).

MEASURED, not assumed:
  - EMG amplitude is +-0.002 at most, i.e. VOLTS as Delsys exports them; scaled
    by 1000 to the contract's mV and the observed peak is recorded per file.
  - the orientation columns are true unit quaternions: |q| median 1.0000
    (min 0.9999, max 1.0001) over every file checked. Rows of trailing zeros
    from the ragged export are dropped, never interpolated.

WHAT IS DELIBERATELY LEFT UNRESOLVED (C-EMG-1 discipline):
  The bundled README documents the file naming and every column, but NOWHERE
  states where sensor 1 and sensor 2 were placed. A two-IMU cervical setup is
  conventionally head plus trunk, and the EMG is presumably a neck muscle, but
  the dataset does not say so. Muscle, side and body location therefore stay
  "unknown" and resolved=False, and the placement string records the raw channel
  name. Read the paper to resolve; do not guess from convention.

CONTRACT ROUTING (vidimu precedent, see ingest_vidimu.py): orientation
quaternions are NOT acc/gyro, so they do NOT enter the canonical IMU contract.
They are written as paired streams; only the EMG becomes canonical.

Outputs (datasets/imu/cervical_motion_multiplanar/processed/):
  canonical_emg/<record>.pkl                  canonical EMG records (identity unresolved)
  streams_orientation.pkl                     per-file quaternion streams, own clock
  cervical_ingest_audit.csv                   per-file verification
  ../../_canonical_emg_manifest_cervical_motion.csv   manifest rows to merge

Env: /Users/xavi/.venvs/kinefm (numpy). Usage:
    python ingest_cervical_motion.py [--repo PATH] [--dry]
"""
import argparse
import csv
import io
import os
import pickle
import re
import zipfile

import numpy as np

EMG_V_TO_MV = 1000.0
SENSORS = [{"emg_t": 0, "emg": 1, "quat_t": 2, "quat": (3, 5, 7, 9), "id": 1},
           {"emg_t": 10, "emg": 11, "quat_t": 12, "quat": (13, 15, 17, 19), "id": 2}]


def sanitize(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def parse_name(path):
    """<date>_<subject>_<part>_<plane...>.csv -> (subject, task)."""
    b = os.path.basename(path)[:-4]
    m = re.match(r"([\d.]+)_([^_]+)_(part[AB])_(.+)$", b)
    if not m:
        return None, None
    _, subj, part, plane = m.groups()
    return subj, f"{part}_{plane}"


def clean(t, v):
    """Drop NaN rows and the trailing all-zero padding of the ragged export."""
    m = ~(np.isnan(t) | np.isnan(v))
    t, v = t[m], v[m]
    if t.size > 1:
        last = np.flatnonzero(np.abs(v) > 0)
        if last.size:
            keep = last[-1] + 1
            t, v = t[:keep], v[:keep]
    return t, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    base = os.path.join(args.repo, "datasets", "imu", "cervical_motion_multiplanar")
    rawd = os.path.join(base, "raw")
    outd = os.path.join(base, "processed")
    emgd = os.path.join(outd, "canonical_emg")
    os.makedirs(emgd, exist_ok=True)

    zips = [f for f in sorted(os.listdir(rawd))
            if f.endswith(".zip") and not f.startswith("._")] if os.path.isdir(rawd) else []
    if not zips:
        raise SystemExit(f"no zip under {rawd}; run fetch_p2_lot.py --only cervical_motion")

    streams, manifest, audit = [], [], []
    n_emg = 0
    with zipfile.ZipFile(os.path.join(rawd, zips[0])) as z:
        csvs = sorted(n for n in z.namelist()
                      if n.endswith(".csv") and not os.path.basename(n).startswith("._"))
        print(f"{zips[0]}: {len(csvs)} recordings")
        for name in csvs:
            subj, task = parse_name(name)
            if subj is None:
                audit.append([name, "", "", "", "", "SKIP: filename does not parse"])
                continue
            ns = f"cervical_motion:{subj}"
            try:
                a = np.genfromtxt(io.BytesIO(z.read(name)), delimiter=",", skip_header=1)
            except Exception as e:
                audit.append([name, ns, task, "", "", f"UNREADABLE: {e}"])
                continue
            if a.ndim != 2 or a.shape[1] != 20:
                audit.append([name, ns, task, "", "",
                              f"REFUSED: {a.shape[1] if a.ndim == 2 else '?'} columns, "
                              "expected the verified 20-column Delsys export"])
                continue
            notes = []
            emg_sigs, emg_fs, quats = [], [], {}
            for s in SENSORS:
                t, v = clean(a[:, s["emg_t"]], a[:, s["emg"]])
                if t.size < 100:
                    notes.append(f"sensor {s['id']}: EMG too short ({t.size})")
                    continue
                dt = float(np.median(np.diff(t)))
                emg_fs.append(1.0 / dt if dt > 0 else 0.0)
                emg_sigs.append((v * EMG_V_TO_MV).astype(np.float32))
                qt = a[:, s["quat_t"]]
                q = a[:, list(s["quat"])]
                m = ~(np.isnan(qt) | np.isnan(q).any(axis=1))
                qt, q = qt[m], q[m]
                keep = np.abs(q).sum(axis=1) > 0
                qt, q = qt[keep], q[keep]
                if qt.size:
                    nq = np.linalg.norm(q, axis=1)
                    if not (0.99 <= float(np.median(nq)) <= 1.01):
                        notes.append(f"sensor {s['id']}: |q| median {np.median(nq):.3f} "
                                     "is not a unit quaternion, review")
                    qdt = float(np.median(np.diff(qt))) if qt.size > 2 else 0.0
                    quats[s["id"]] = {"t": qt.astype(np.float32),
                                      "quat": q.astype(np.float32),
                                      "fps": (1.0 / qdt) if qdt > 0 else None}
            if not emg_sigs:
                audit.append([name, ns, task, "", "", "; ".join(notes) or "no usable EMG"])
                continue
            T = min(len(x) for x in emg_sigs)
            fs = float(np.median(emg_fs))
            if not (1500 < fs < 2100):
                notes.append(f"EMG fs {fs:.1f} outside the verified 1785.7 Hz")
            sig = np.stack([x[:T] for x in emg_sigs], axis=1)
            channels = [{"kind": "emg", "muscle": "unknown", "side": "unknown",
                         "placement": f"Avanti sensor {s['id']} EMG "
                                      "(placement NOT documented in the bundled README)",
                         "resolved": False} for s in SENSORS[:len(emg_sigs)]]
            rec = {"signal": sig, "channels": channels, "fps": fs, "unit": "mV",
                   "unit_scale": 1.0, "signal_kind": "filtered_remove_mean",
                   "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
                   "subject_ns": ns, "task": task, "source": "cervical_motion",
                   "n_frames": int(T), "label": None}
            rid = sanitize(f"cervical_motion__{ns}__{task}")
            if not args.dry:
                with open(os.path.join(emgd, rid + ".pkl"), "wb") as f:
                    pickle.dump(rec, f)
            manifest.append(["cervical_motion", ns, task, fs, T, len(channels), "emg",
                             os.path.relpath(os.path.join(emgd, rid + ".pkl"), args.repo)])
            streams.append({"subject_ns": ns, "task": task, "file": os.path.basename(name),
                            "orientation": quats,
                            "note": "unit quaternions per sensor, own 74 Hz clock; "
                                    "orientation only, no acc/gyro, so NOT canonical IMU"})
            n_emg += 1
            audit.append([name, ns, task, f"{fs:.1f}", T,
                          f"emg_peak={np.abs(sig).max():.4f}mV quat_sensors="
                          f"{sorted(quats)} " + ("; ".join(notes) if notes else "ok")])
            if n_emg % 25 == 0:
                print(f"  {n_emg}/{len(csvs)} done", flush=True)

    if not args.dry:
        with open(os.path.join(outd, "streams_orientation.pkl"), "wb") as f:
            pickle.dump(streams, f)
        mp = os.path.join(args.repo, "datasets",
                          "_canonical_emg_manifest_cervical_motion.csv")
        with open(mp, "w", newline="") as f:
            w = csv.writer(f)
            # column names must match datasets/_canonical_emg_manifest.csv exactly
            w.writerow(["source", "subject_ns", "task", "fps", "n_frames",
                        "n_channels", "kinds", "record_path"])
            w.writerows(manifest)
    with open(os.path.join(outd, "cervical_ingest_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "subject_ns", "task", "emg_fps", "n_frames", "result"])
        w.writerows(audit)

    subs = len({m[1] for m in manifest})
    print(f"\n{n_emg} canonical EMG records / {subs} subjects "
          f"(2 channels each, muscle and placement UNRESOLVED by design)")
    print(f"{len(streams)} orientation stream sets -> processed/streams_orientation.pkl")
    print("audit -> processed/cervical_ingest_audit.csv")
    print("merge _canonical_emg_manifest_cervical_motion.csv into "
          "datasets/_canonical_emg_manifest.csv after review")


if __name__ == "__main__":
    main()
