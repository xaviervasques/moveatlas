# -*- coding: utf-8 -*-
"""Ingest the Multimodal FoG dataset (Mendeley r8gmbtv7w2, filtered task_n.txt files).

UNBLOCKED 2026-08-22: the v1 deferral ("61 ambiguous columns, 14-zero block") is resolved.
The bundled README.docx documents the filtered format exactly, and every claim below was
verified against real files (docs/multimodal_fog_mapping.md has the evidence):

  on-disk column 0      pandas index
  column 1              wall-clock time HH:MM:SS(.mmm); median dt = 2.00 ms -> fs = 500 Hz
  columns 2..26   (25)  EEG uV: FP1,FP2,F3,F4,C3,C4,P3,P4,O1,O2,F7,F8,P7,P8,FZ,CZ,PZ,
                        FC1,FC2,CP1,CP2,FC5,FC6,CP5,CP6
  columns 27..31  (5)   EMG/ECG/EOG block; per-patient order (README table); col 29 is
                        ALWAYS IO (EOG), confirmed by its systematically smaller amplitude
  columns 32..59  (4x7) IMU blocks by POSITION: LShank, RShank, Waist, Arm; each block =
                        [acc_x,acc_y,acc_z,gyro_x,gyro_y,gyro_z,NC_or_SC]; 7th col is NC
                        (invalid) except the Arm block where it is skin conductance.
                        Patients wearing 2 sensors have all-zero blocks for the other two
                        (the v1 "14-zero block"). Active blocks are DETECTED per file.
  column 60             label: 1 = FoG, 0 = FoG-free (dense, 500 Hz, expert video labels)

Patient identity: RESOLVED 2026-08-22 (networked session). The local mirror flattened
the per-patient folders into <mendeley-file-id-prefix>__task_n.txt; querying the Mendeley
public API (folders/3 + files?folder_id=) rebuilds the original tree and maps all 56 local
files back to their true patient folder (configs/multimodal_fog_patient_index.csv, 56/56
matched). Ground truth: 12 patients 001-012, 13 experiments (008 recorded twice, OFF_1 and
OFF_2). subject_ns is the PATIENT, so 008/OFF_1 and 008/OFF_2 share one subject and can
never straddle a train/test split; the experiment is carried in the task field.
The previous wall-clock heuristic is kept only as a fallback for unmatched files and is
reported for audit: it split 12 of the 13 experiments across sessions (i.e. it would have
leaked nearly every patient), which is why the index is authoritative.

Outputs (datasets/imu/multimodal_fog/processed/):
  canonical_imu.pkl                 canonical IMU records (same schema as build_canonical_imu)
  streams_eeg_emg.pkl               paired EEG/EMG/SC/label streams (phase-3 alignment asset;
                                    NEVER enters movement pretraining)
  mapping_audit.csv                 per-file verification (fs, blocks, scales, labels)
  patient_grouping_report.csv       session groups with time evidence
  ../../_canonical_imu_manifest_multimodal_fog.csv   manifest rows to merge

Units: acc self-calibrated to g (gravity-norm estimate per sensor, reported in the audit);
gyro divided by 131.0 (MPU6050 default +-250 dps) -- ASSUMPTION, flagged in the audit.
Env: atlas-mouvement (numpy). Usage: python ingest_multimodal_fog.py [--repo PATH] [--dry]
"""
import argparse
import csv
import glob
import os
import pickle
import numpy as np

EEG_NAMES = ["FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "F7", "F8",
             "P7", "P8", "FZ", "CZ", "PZ", "FC1", "FC2", "CP1", "CP2", "FC5", "FC6",
             "CP5", "CP6"]
BLOCKS = [("shank_L", 32), ("shank_R", 39), ("lower_back", 46), ("wrist_L", 53)]
LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
GYRO_LSB = 131.0            # MPU6050 +-250 dps (assumption, see audit)
SESSION_GAP_MIN = 90.0      # tasks closer than this (minutes) join one session/patient


def load_patient_index(repo):
    """configs/multimodal_fog_patient_index.csv: folder,filename,file_id,size,sha256.
    Maps <file_id prefix> -> (patient, experiment). Rebuilt from the Mendeley public API
    (see docs/multimodal_fog_mapping.md); authoritative over wall-clock grouping."""
    p = os.path.join(repo, "configs", "multimodal_fog_patient_index.csv")
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            folder = (row.get("folder") or "").replace("Filtered Data/", "").strip("/")
            if not folder or not row.get("file_id"):
                continue
            parts = folder.split("/")
            patient = parts[0]                       # 001..012
            experiment = parts[1] if len(parts) > 1 else ""   # OFF_1 / OFF_2 for 008
            out[row["file_id"][:8]] = (patient, experiment)
    return out


def tsec(s):
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def first_last_time(path):
    with open(path, "rb") as f:
        first = f.readline().decode(errors="replace")
        f.seek(max(-4096, -os.path.getsize(path)), 2)
        last = f.read().decode(errors="replace").strip().splitlines()[-1]
    try:
        return tsec(first.split(",")[1]), tsec(last.split(",")[1])
    except Exception:
        return None, None


def parse_file(path):
    eeg, emg, imu, lab, tsecs = [], [], [], [], []
    bad = 0
    with open(path) as f:
        for line in f:
            p = line.rstrip("\n").split(",")
            if len(p) != 61:
                bad += 1
                continue
            try:
                row = [float(x) for x in p[2:]]
            except ValueError:
                bad += 1
                continue
            eeg.append(row[0:25])
            emg.append(row[25:30])
            imu.append(row[30:58])
            lab.append(row[58])
            if len(tsecs) < 4000:
                try:
                    tsecs.append(tsec(p[1]))
                except Exception:
                    pass
    return (np.asarray(eeg, np.float32), np.asarray(emg, np.float32),
            np.asarray(imu, np.float32), np.asarray(lab, np.int8),
            np.asarray(tsecs), bad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true", help="grouping + audit only, no pkl")
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "imu", "multimodal_fog")
    rawd = os.path.join(base, "raw")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)

    files = [f for f in sorted(glob.glob(os.path.join(rawd, "*task_*.txt")))
             if not os.path.basename(f).startswith("._")]
    if not files:
        raise SystemExit(f"no task files under {rawd}")

    # ---- pass 1: wall-clock session grouping (patient recovery)
    meta = []
    for f in files:
        t0, t1 = first_last_time(f)
        meta.append({"file": f, "t0": t0, "t1": t1})
    meta.sort(key=lambda m: (m["t0"] is None, m["t0"]))
    sessions, cur = [], None
    for m in meta:
        if m["t0"] is None:
            sessions.append([m])        # unparseable time: its own group, flagged
            continue
        if cur and cur[-1]["t1"] is not None and \
           0 <= (m["t0"] - cur[-1]["t1"]) / 60.0 <= SESSION_GAP_MIN:
            cur.append(m)
        else:
            cur = [m]
            sessions.append(cur)
    with open(os.path.join(outd, "patient_grouping_report.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["session", "file", "t_start", "t_end", "note"])
        for si, s in enumerate(sessions):
            for m in s:
                w.writerow([f"sess{si:02d}", os.path.basename(m["file"]),
                            m["t0"], m["t1"],
                            "" if m["t0"] is not None else "TIME UNPARSEABLE: review"])
    print(f"{len(files)} files -> {len(sessions)} wall-clock sessions (fallback only)")

    # ---- pass 1b: TRUE patient identity from the Mendeley folder tree
    pindex = load_patient_index(args.repo)
    if not pindex:
        print("WARNING: configs/multimodal_fog_patient_index.csv missing; falling back to "
              "wall-clock sessions, which are NOT patient-safe (see docstring)")
    else:
        n_hit = sum(1 for f in files
                    if os.path.basename(f).split("__")[0] in pindex)
        pats = sorted({pindex[os.path.basename(f).split("__")[0]][0] for f in files
                       if os.path.basename(f).split("__")[0] in pindex})
        print(f"patient index: {n_hit}/{len(files)} files matched, "
              f"{len(pats)} patients {pats}")
        if n_hit < len(files):
            print(f"  {len(files) - n_hit} UNMATCHED file(s) keep their wall-clock group "
                  "and are flagged in the audit; review before use")

    # ---- pass 2: parse, verify, build records
    audit, recs, streams, manifest = [], [], [], []
    for si, s in enumerate(sessions):
        for m in s:
            b = os.path.basename(m["file"])
            hit = pindex.get(b.split("__")[0])
            if hit:
                subj = f"multimodal_fog:p{hit[0]}"
                id_src = "mendeley_folder"
            else:
                subj = f"multimodal_fog:sess{si:02d}"
                id_src = "WALL_CLOCK_FALLBACK"
            eeg, emg, imu, lab, tt, bad = parse_file(m["file"])
            notes = []
            dt = np.median(np.diff(tt)) if len(tt) > 10 else None
            fs = (1.0 / dt) if dt and dt > 0 else None
            if fs is None or not (490 < fs < 510):
                notes.append(f"fs suspect: {fs}")
            if np.nanmax(np.abs(eeg)) > 5000:
                notes.append("EEG amplitude > 5000 (uV attendu)")
            if not set(np.unique(lab)) <= {0, 1}:
                notes.append(f"labels hors {{0,1}}: {np.unique(lab)[:5]}")
            loc_data, scales, active = {}, {}, []
            for name, col in BLOCKS:
                blk = imu[:, col - 32:col - 32 + 7]
                if float(np.max(np.abs(blk[:, :6]))) == 0.0:
                    continue
                active.append(name)
                acc = blk[:, 0:3].astype(np.float64)
                gn = float(np.median(np.linalg.norm(acc, axis=1)))
                if not (2000 < gn < 40000):
                    notes.append(f"{name}: norme gravite atypique {gn:.0f}")
                    gn = 16384.0
                scales[name] = gn
                loc_data[name] = {
                    "acc_x": (acc[:, 0] / gn).astype(np.float32),
                    "acc_y": (acc[:, 1] / gn).astype(np.float32),
                    "acc_z": (acc[:, 2] / gn).astype(np.float32),
                    "gyro_x": blk[:, 3] / GYRO_LSB, "gyro_y": blk[:, 4] / GYRO_LSB,
                    "gyro_z": blk[:, 5] / GYRO_LSB}
            sc = imu[:, 53 - 32 + 6] if "wrist_L" in loc_data else None
            if id_src != "mendeley_folder":
                notes.append("patient identity UNRESOLVED: wall-clock fallback, "
                             "not patient-safe for splits")
            audit.append([b, subj, len(lab), bad,
                          round(fs, 2) if fs else "", "|".join(active),
                          "|".join(f"{k}:{v:.0f}" for k, v in scales.items()),
                          int((lab == 1).sum()), "; ".join(notes)])
            if args.dry or not loc_data:
                continue
            T = len(lab)
            actives = [l for l in LOCATIONS if l in loc_data]
            sig = np.zeros((T, len(actives), 9), np.float32)
            cmask = np.zeros((len(actives), 9), bool)
            for li, l in enumerate(actives):
                for ci, ch in enumerate(["acc_x", "acc_y", "acc_z",
                                         "gyro_x", "gyro_y", "gyro_z"]):
                    sig[:, li, ci] = loc_data[l][ch]
                    cmask[li, ci] = True
            task = b.split("__")[-1][:-4]
            if hit and hit[1]:          # 008 recorded twice: OFF_1 / OFF_2
                task = f"{hit[1]}/{task}"
            recs.append({"signal": sig,
                         "location_ids": np.array([LOC_I[l] for l in actives]),
                         "channel_mask": cmask, "fps": 500.0, "subject_ns": subj,
                         "task": task, "source": "multimodal_fog", "n_frames": T,
                         "label": lab})
            streams.append({"subject_ns": subj, "task": task, "fps": 500.0,
                            "eeg": eeg, "eeg_names": EEG_NAMES, "emg_block": emg,
                            "emg_note": "ordre par patient (README table); col index 2 = EOG",
                            "sc": sc, "label": lab, "file": b})
            manifest.append(["multimodal_fog", subj, task, 500.0, T, "|".join(actives)])
            print(f"  {b}: T={T} blocs={active} FoG={int((lab==1).sum())}")

    with open(os.path.join(outd, "mapping_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "subject_ns", "n_rows", "bad_rows", "fs", "blocs_actifs",
                    "echelle_acc_counts_per_g", "n_fog_samples", "notes"])
        w.writerows(audit)
    if not args.dry:
        pickle.dump(recs, open(os.path.join(outd, "canonical_imu.pkl"), "wb"))
        pickle.dump(streams, open(os.path.join(outd, "streams_eeg_emg.pkl"), "wb"))
        mp = os.path.join(args.repo, "datasets",
                          "_canonical_imu_manifest_multimodal_fog.csv")
        with open(mp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "subject_ns", "task", "fps", "n_frames", "locations"])
            w.writerows(manifest)
        print(f"\n{len(recs)} canonical IMU records ; {len(streams)} paired streams")
        print("merge the manifest rows into datasets/_canonical_imu_manifest.csv "
              "after reviewing the grouping report")
    print("audit -> processed/mapping_audit.csv")


if __name__ == "__main__":
    main()
