# -*- coding: utf-8 -*-
"""The canonical IMU contract (configs/canonical_imu.yaml) as a library:
the record maker and the writer, ported from the repository's
build_canonical_imu.py so a recipe can harmonize into a user store.

Only what the library recipes need is here; the repository builder keeps
every dataset mapping and stays the provenance record. The two must agree
on the record shape: signal (T, L, 9) float32 in g / deg/s / uT,
location_ids, channel_mask (L, 9), sample_valid (T, L), fps, subject_ns,
task, source, n_frames, and dropout_fraction when a sample is invalid.
"""
import csv
import os

import numpy as np

from moveatlas import records

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L",
             "thigh_R", "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L",
             "foot_R", "pocket"]
CHANNELS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z",
            "mag_x", "mag_y", "mag_z"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
CH_I = {n: i for i, n in enumerate(CHANNELS)}
G = 9.80665
MANIFEST_HEADER = ["source", "subject_ns", "task", "fps", "n_frames", "locations"]


def make_record(loc_data, fps, subject_ns, task, source, label=None):
    """loc_data: {location_name: {channel_name: np.array(T,)}}, same T for
    all. Three validity rules hold for every source (2026-08-23): a
    channel with no finite sample anywhere is an ABSENT sensor, masked
    off and zeroed; a location left with no valid channel is dropped; a
    channel that drops out for a stretch stays present, its non-finite
    samples zeroed and the record gains sample_valid (T, L). A channel
    whose finite samples are all exactly zero is absent as well
    (2026-09-17). The signal is therefore finite and nothing is inferred."""
    active = [l for l in LOCATIONS if l in loc_data]
    T = len(next(iter(next(iter(loc_data.values())).values())))
    sig = np.zeros((T, len(active), 9), np.float32)
    cmask = np.zeros((len(active), 9), bool)
    for li, loc in enumerate(active):
        for ch, arr in loc_data[loc].items():
            sig[:, li, CH_I[ch]] = arr
            cmask[li, CH_I[ch]] = True

    finite = np.isfinite(sig)
    dead = cmask & ~finite.any(axis=0)
    # a channel of exact zeros throughout is an absent sensor too (2026-09-17)
    dead |= cmask & ~np.any(finite & (sig != 0), axis=0)
    if dead.any():
        cmask = cmask & ~dead
    keep = [li for li in range(len(active)) if cmask[li].any()]
    if len(keep) != len(active):
        active = [active[li] for li in keep]
        sig, cmask = sig[:, keep], cmask[keep]
        finite = np.isfinite(sig)
    present = np.broadcast_to(cmask[None], sig.shape)
    sample_valid = np.all(finite | ~present, axis=2)
    sig = np.where(finite, sig, 0.0).astype(np.float32)

    rec = {"signal": sig, "location_ids": np.array([LOC_I[l] for l in active]),
           "channel_mask": cmask, "sample_valid": sample_valid,
           "fps": fps, "subject_ns": subject_ns,
           "task": task, "source": source, "n_frames": T}
    if not sample_valid.all():
        rec["dropout_fraction"] = float(1.0 - sample_valid.mean())
    if label is not None:
        rec["label"] = np.asarray(label)
    return rec


def save(root, source, recs, path=None):
    """Write the records as `<root>/<path>/processed/canonical_imu.npz`
    (moveatlas-record/1), `path` defaulting to datasets/imu/<source>, the
    dataset's registry path, which is where the generic loader looks.
    Merge the per-record rows into `<root>/datasets/_canonical_imu_manifest.csv`
    when that central manifest exists (an ingestion machine); a user store
    gets the rows in `processed/manifest.csv` instead. Returns the output
    path."""
    path = path or f"datasets/imu/{source}"
    out_dir = os.path.join(root, path.replace("/", os.sep), "processed")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "canonical_imu.npz")
    records.save(out, recs)
    rows = [[source, r["subject_ns"], r["task"],
             round(r["fps"], 2) if r["fps"] else "", r["n_frames"],
             "|".join(LOCATIONS[i] for i in r["location_ids"])] for r in recs]
    central = os.path.join(root, "datasets", "_canonical_imu_manifest.csv")
    if os.path.exists(central):
        with open(central, newline="", encoding="utf-8") as f:
            old = list(csv.reader(f))
        head, kept = old[0], [r for r in old[1:] if r and r[0] != source]
        with open(central, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(head)
            w.writerows(kept + rows)
    else:
        with open(os.path.join(out_dir, "manifest.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(MANIFEST_HEADER)
            w.writerows(rows)
    return out
