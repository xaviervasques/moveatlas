# -*- coding: utf-8 -*-
"""Ingest PADS (Parkinson's Disease Smartwatch dataset, 469 subjects) into the
canonical IMU contract.

RE-EXAMINED 2026-08-22 (v1 had deferred it after looking at raw/preprocessed/,
whose 7-column normalized series are undocumented). The raw/movement/ tree is
FULLY SELF-DESCRIBING and was verified on real files this session:

  raw/patients/patient_XXX.json      469 subjects: condition (Healthy,
                                     Parkinson's, Other Movement Disorders,
                                     ...), disease_comment (free text), age,
                                     gender, handedness, kinship, alcohol effect
  raw/movement/observation_XXX.json  per subject: device (Apple Watch Series 4),
                                     sampling_rate 100 Hz, 11 tasks (Relaxed,
                                     RelaxedTask, StretchHold, LiftHold,
                                     HoldWeight, PointFinger, DrinkGlas,
                                     CrossArms, TouchIndex, TouchNose,
                                     Entrainment), per wrist, with channel names
                                     AND units declared: Time s, Accelerometer
                                     g, Gyroscope rad/s, file_name pointer
  raw/movement/timeseries/*.txt      comma CSV, 7 cols (t, acc xyz, gyro xyz),
                                     2048 rows (~20.5 s), dt verified 10 ms
  raw/questionnaire/*.json           NMS non-motor symptom questionnaires

MEASURED CAVEAT (flagged, not a blocker): accelerometer gravity norm is ~0.004 g
at rest -> CoreMotion userAcceleration, GRAVITY REMOVED AT SOURCE. Units are
still g; the contract mapping records acc_content: linear_no_gravity.

Mapping to configs/canonical_imu.yaml: locations wrist_L / wrist_R (one record
PER WRIST, the two watches are not co-sampled; no cross-device resampling),
channels acc_x..gyro_z (gyro converted rad/s -> deg/s), fps 100, labels: subject
condition kept in the subject table and copied onto records as eval-only
metadata. Splits stay at patient level via subject_ns pads:XXX.

Outputs (datasets/imu/pads/processed/):
  canonical_imu.pkl            canonical records (schema of build_canonical_imu /
                               ingest_multimodal_fog: signal (T, L, 9),
                               location_ids, channel_mask, fps, subject_ns...)
  pads_subject_table.csv       469 subjects x condition/demographics/NMS count
  pads_ingest_audit.csv
  ../../_canonical_imu_manifest_pads.csv    manifest rows to merge

Env: atlas-mouvement (numpy). Usage: python ingest_pads.py [--repo PATH] [--limit N]
"""
import argparse
import csv
import glob
import json
import os
import pickle
import numpy as np

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L",
             "thigh_R", "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L",
             "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
WRIST = {"LeftWrist": "wrist_L", "RightWrist": "wrist_R"}
RAD2DEG = 180.0 / np.pi
EXPECTED_CH = ["Time", "Accelerometer_X", "Accelerometer_Y", "Accelerometer_Z",
               "Gyroscope_X", "Gyroscope_Y", "Gyroscope_Z"]
EXPECTED_UNITS = ["s", "g", "g", "g", "rad/s", "rad/s", "rad/s"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="subjects cap (0 = all)")
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "imu", "pads")
    rawd = os.path.join(base, "raw")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)

    # subject table
    table, cond_of = [], {}
    for pf in sorted(glob.glob(os.path.join(rawd, "patients", "patient_*.json"))):
        if os.path.basename(pf).startswith("._"):
            continue
        p = json.load(open(pf))
        pid = p.get("id")
        nms = 0
        qf = os.path.join(rawd, "questionnaire",
                          f"questionnaire_response_{pid}.json")
        if os.path.exists(qf):
            try:
                q = json.load(open(qf))
                nms = sum(1 for it in q.get("item", []) if it.get("answer") is True)
            except Exception:
                nms = ""
        cond_of[pid] = p.get("condition", "")
        table.append([f"pads:{pid}", p.get("condition", ""),
                      p.get("disease_comment", ""), p.get("age", ""),
                      p.get("age_at_diagnosis", ""), p.get("gender", ""),
                      p.get("handedness", ""),
                      p.get("appearance_in_kinship", ""),
                      p.get("effect_of_alcohol_on_tremor", ""), nms])
    with open(os.path.join(outd, "pads_subject_table.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_ns", "condition", "disease_comment", "age",
                    "age_at_diagnosis", "gender", "handedness",
                    "family_history", "alcohol_effect_on_tremor",
                    "nms_positive_count"])
        w.writerows(table)
    print(f"subject table: {len(table)} subjects")

    obs_files = sorted(glob.glob(os.path.join(rawd, "movement",
                                              "observation_*.json")))
    obs_files = [f for f in obs_files if not os.path.basename(f).startswith("._")]
    if args.limit:
        obs_files = obs_files[:args.limit]
    recs, manifest, audit = [], [], []
    for of in obs_files:
        o = json.load(open(of))
        pid = o.get("subject_id")
        ns = f"pads:{pid}"
        fs = float(o.get("sampling_rate", 0))
        if not (90 <= fs <= 110):
            audit.append([pid, "-", "-", f"SAMPLING RATE {fs}: skip subject"])
            continue
        for sess in o.get("session", []):
            task = sess.get("record_name", "?")
            for recmeta in sess.get("records", []):
                locname = WRIST.get(recmeta.get("device_location"))
                fn = recmeta.get("file_name", "")
                where = f"{pid}/{task}/{recmeta.get('device_location')}"
                if locname is None:
                    audit.append([pid, task, fn, "unknown device_location"])
                    continue
                if recmeta.get("channels") != EXPECTED_CH or \
                   recmeta.get("units") != EXPECTED_UNITS:
                    audit.append([pid, task, fn,
                                  "channels/units drift from documented layout; "
                                  "REFUSED (review)"])
                    continue
                path = os.path.join(rawd, "movement", fn)
                if not os.path.exists(path):
                    audit.append([pid, task, fn, "missing timeseries file"])
                    continue
                try:
                    a = np.loadtxt(path, delimiter=",")
                except Exception as e:
                    audit.append([pid, task, fn, f"load fail: {e}"])
                    continue
                if a.ndim != 2 or a.shape[1] != 7:
                    audit.append([pid, task, fn, f"shape {a.shape}, expected (T,7)"])
                    continue
                dt = float(np.median(np.diff(a[:, 0]))) if len(a) > 10 else None
                notes = []
                if dt is None or not (0.008 < dt < 0.012):
                    notes.append(f"dt {dt}")
                gnorm = float(np.median(np.linalg.norm(a[:, 1:4], axis=1)))
                T = a.shape[0]
                sig = np.zeros((T, 1, 9), np.float32)
                sig[:, 0, 0:3] = a[:, 1:4]
                sig[:, 0, 3:6] = a[:, 4:7] * RAD2DEG
                cmask = np.zeros((1, 9), bool)
                cmask[0, :6] = True
                recs.append({"signal": sig,
                             "location_ids": np.array([LOC_I[locname]]),
                             "channel_mask": cmask, "fps": fs,
                             "subject_ns": ns, "task": task, "source": "pads",
                             "n_frames": int(T),
                             "acc_content": "linear_no_gravity",
                             "condition": cond_of.get(pid, "")})
                manifest.append(["pads", ns, f"{task}_{locname}", fs, T, locname])
                audit.append([pid, task, fn,
                              f"T={T} med|acc|={gnorm:.4f}g "
                              f"{'; '.join(notes) if notes else 'ok'}"])
    pickle.dump(recs, open(os.path.join(outd, "canonical_imu.pkl"), "wb"))
    mp = os.path.join(args.repo, "datasets", "_canonical_imu_manifest_pads.csv")
    with open(mp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "task", "fps", "n_frames", "locations"])
        w.writerows(manifest)
    with open(os.path.join(outd, "pads_ingest_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "task", "file", "result"])
        w.writerows(audit)
    print(f"{len(recs)} canonical IMU records / "
          f"{len({r['subject_ns'] for r in recs})} subjects "
          f"(gravity-removed acc flagged via acc_content)")
    print("merge _canonical_imu_manifest_pads.csv into datasets/"
          "_canonical_imu_manifest.csv after review")


if __name__ == "__main__":
    main()
