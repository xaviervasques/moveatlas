#!/usr/bin/env python3
"""
Li/Taati (Parkinson's Pose Estimation Dataset) ingestion.

Reads the authors' JSON task exports (2D pose trajectories normalized in image
space) and writes a normalized structure to processed/, comparable to the
CARE-PD output but 2D:

    processed/
        communication_pose.pkl
        drinking_pose.pkl
        leg_agility_pose.pkl
        toe_tapping_optflow.pkl     # optical flow, separate modality/stream
        ratings.json                # UDysRS, UPDRS, CAPSIT, sn_numbers verbatim
        li_taati_joint_names.json   # joint order per task
        manifest.csv

Per pose task, each record is stored as:
    { "joints2d":   (T, J, 2) float32, image-normalized 0..1,
      "resp":       (T, J)    float32, per-joint confidence,
      "joint_names": [...],
      "subject":    int,
      "take":       int | None,
      "note":       str | None,       # e.g. "shake", "occl"
      "n_frames":   int }

Toe tapping is kept separate as raw optical flow (Lank/Rank, shape (3, T)); it
is NOT joint positions.

Run inside the 'atlas-mouvement' env. Idempotent: overwrites its own outputs
only, never touches raw/.

Usage:
    python ingest_li_taati.py
"""

import csv
import json
import os
import re
import pickle

import numpy as np

RAW = "datasets/pose/li_taati/raw/UDysRS_UPDRS_Export"
OUT = "datasets/pose/li_taati/processed"

POSE_TASKS = {
    "communication": "Communication_all_export.txt",
    "drinking": "Drinking_all_export.txt",
    "leg_agility": "LA_split_all_export.txt",
}
OPTFLOW_TASK = ("toe_tapping", "TT_opt_flow_export.txt")
RATING_FILES = {
    "UDysRS": "UDysRS.txt",
    "UPDRS": "UPDRS.txt",
    "CAPSIT": "CAPSIT.txt",
    "sn_numbers": "sn_numbers.txt",
}

# key like "26-1", "217", "21 (shake)", "28 (occl)"
KEY_RE = re.compile(r"^\s*(\d+)(?:-(\d+))?\s*(?:\(([^)]*)\))?\s*$")


def load_json(name):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)


def parse_key(key):
    """Return (subject:int, take:int|None, note:str|None). Falls back gracefully."""
    m = KEY_RE.match(key)
    if not m:
        return None, None, key.strip()
    subj = int(m.group(1))
    take = int(m.group(2)) if m.group(2) else None
    note = m.group(3).strip() if m.group(3) else None
    return subj, take, note


def stack_joints(position_dict, resp_dict):
    """Order joints deterministically, stack to (T, J, 2) and (T, J)."""
    joint_names = sorted(position_dict.keys())
    cols = [np.asarray(position_dict[j], dtype=np.float32) for j in joint_names]
    T = cols[0].shape[0]
    if any(c.shape[0] != T for c in cols):
        # ragged: align to the shortest to stay safe
        T = min(c.shape[0] for c in cols)
        cols = [c[:T] for c in cols]
    joints2d = np.stack(cols, axis=1)  # (T, J, 2)
    if resp_dict is not None:
        r = []
        for j in joint_names:
            rv = np.asarray(resp_dict.get(j, []), dtype=np.float32)
            if rv.shape[0] < T:
                rv = np.concatenate([rv, np.full(T - rv.shape[0], np.nan, np.float32)])
            r.append(rv[:T])
        resp = np.stack(r, axis=1)  # (T, J)
    else:
        resp = None
    return joints2d, resp, joint_names


def ingest_pose_task(name, fname, manifest_rows):
    data = load_json(fname)
    result = {}
    joint_names_ref = None
    for key, rec in data.items():
        subj, take, note = parse_key(key)
        joints2d, resp, jnames = stack_joints(rec["position"], rec.get("resp"))
        joint_names_ref = joint_names_ref or jnames
        entry = {
            "joints2d": joints2d,
            "resp": resp,
            "joint_names": jnames,
            "subject": subj,
            "take": take,
            "note": note,
            "n_frames": int(joints2d.shape[0]),
        }
        # leg agility carries per-joint rest/active frame indices
        if "idx" in rec:
            entry["idx"] = rec["idx"]
        result[key] = entry
        manifest_rows.append([name, key, subj, take if take is not None else "",
                              note or "", joints2d.shape[0], joints2d.shape[1]])
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{name}_pose.pkl"), "wb") as f:
        pickle.dump(result, f)
    return len(result), joint_names_ref


def ingest_optflow(name, fname, manifest_rows):
    data = load_json(fname)
    result = {}
    for key, rec in data.items():
        subj, take, note = parse_key(key)
        streams = {k: np.asarray(v, dtype=np.float32) for k, v in rec.items()}
        n = max((v.shape[-1] for v in streams.values()), default=0)
        result[key] = {"optflow": streams, "subject": subj, "take": take,
                       "note": note, "n_frames": int(n)}
        manifest_rows.append([name, key, subj, take if take is not None else "",
                              note or "", n, len(streams)])
    with open(os.path.join(OUT, f"{name}_optflow.pkl"), "wb") as f:
        pickle.dump(result, f)
    return len(result)


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest_rows = []
    joint_names_by_task = {}

    for name, fname in POSE_TASKS.items():
        n, jnames = ingest_pose_task(name, fname, manifest_rows)
        joint_names_by_task[name] = jnames
        print(f"  {name}: {n} records, {len(jnames)} joints")

    on, ofn = OPTFLOW_TASK
    n = ingest_optflow(on, ofn, manifest_rows)
    print(f"  {on} (optical flow, separate): {n} records")

    ratings = {k: load_json(v) for k, v in RATING_FILES.items()}
    with open(os.path.join(OUT, "ratings.json"), "w") as f:
        json.dump(ratings, f, indent=2)

    with open(os.path.join(OUT, "li_taati_joint_names.json"), "w") as f:
        json.dump(joint_names_by_task, f, indent=2)

    with open(os.path.join(OUT, "manifest.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task", "record_key", "subject", "take", "note",
                    "n_frames", "n_joints"])
        w.writerows(manifest_rows)

    print(f"\nDone. {len(manifest_rows)} records ingested to {OUT}")


if __name__ == "__main__":
    main()
