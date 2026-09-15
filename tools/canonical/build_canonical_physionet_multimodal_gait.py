# -*- coding: utf-8 -*-
"""Build canonical EEG + EMG + IMU + force records for the PhysioNet
multimodal gait dataset (multimodal-gait-dataset v1.0.0, CC BY 4.0,
59 healthy young adults, treadmill walking at 0.5 / 0.75 / 1.0 m/s).
Source id: physionet_multimodal_gait. Written 2026-09-08.

Everything stored is READ from the dataset (file headers, the bundled
README files, EEG_referencing.m, the PhysioNet record page re-read on
2026-09-08); nothing is guessed. Where a fact is not declared it is
stored as unknown and counted in the audit.

EEG   EEG_Data/EEG.csv/S<id>_<speed>_raw.csv (the RAW export of the
      DSI-Streamer; the .edf twin is a 58 s cut of the same recording
      (29 x 2 s records vs 17960 samples in the csv) with identical
      labels, so the csv is ingested and the edf is not). Header lines
      declare 300 Hz, uV, "Reference location: Pz", "Non-Filtered",
      mains 50/60 Hz, filter delay 40 ms. 18 scalp sites + A1 + A2, all
      recorded against Pz -> 20 eeg channels with ref PZ, stored as
      recorded (the README's "19 scalp channels" counts Pz, which is the
      hardware reference and is not a data column; no software
      re-referencing: EEG_referencing.m documents the authors' linked-ears
      re-reference and Pz reconstruction, which is NOT applied). CM
      (common-mode trace), X1/X2/X3 (unused aux), Trigger, Time_Offset,
      ADC_Status, ADC_Sequence, Event -> aux stream. One file
      (S32_1_raw) carries a corrupted montage line ('?', '???', F6, C2,
      A2 twice, in the csv AND the edf) -> refused, counted.
EMG   EMG_Data/EMG_S<id>_<speed>.csv: 12 named muscles, header
      "<side> <MUSCLE>: EMG k->MAV [Volts]" -> mean-absolute-value
      ENVELOPE (signal_kind envelope), Volts -> mV (unit_scale 1000).
      Rate is not declared anywhere; it is MEASURED from the file's own
      X [s] column (dt 62.3077 ms, jitter < 1e-13 s, i.e. 16.049 Hz)
      and stored with that provenance.
IMU   IMU_Data/IMU.tar.gz: Xsens MVN Awinda 2023 export, 17 sensors,
      60 Hz (record page). Only Sensor_Free_Acceleration.csv is a
      sensor signal with a declared unit ("[m/s2]" on the record page)
      -> acc_xyz in g with acc_content linear_no_gravity (the pads
      precedent). Sensor_Magnetic_Field is "[a.u.]" -> not uT, refused
      (kept in aux). No sensor angular velocity is exported (segment
      angular velocity is a model output) -> gyro absent. Sensor ->
      grid mapping in IMU_SENSOR_MAP below; the upper-limb sensors go
      to aux because the record does not say where on the arm they sit.
FORCE FP_Data/FP_S<id>_<speed>.csv: Bertec split-belt treadmill, 1000 Hz
      (record page), block "1:" = left leg, "2:" = right leg (README +
      record page). Fz -> per-foot total (totals-only, like gaitndd);
      Fx/Fy/Mx/My/Mz/COPx/COPy -> aux. Force UNIT is declared nowhere
      (page, README, header) -> unit "unknown", with the body-weight
      consistency check noted, never promoted to N.

subject-info.csv carries a full DOB: it is never read into any record
or output (only Subject, GENDER, Age are loaded; see load_subjects).

Outputs (moveatlas-record/1 .npz containers, no pickle):
  datasets/eeg/physionet_multimodal_gait/processed/canonical_eeg/<rid>.npz
  .../processed/canonical_emg/<rid>.npz
  .../processed/canonical_imu.npz      (one list)
  .../processed/canonical_force.npz    (one list)
  .../processed/aux/<rid>__<family>.npz
  .../processed/ingest_audit.csv
  rows merged (by source) into datasets/_canonical_{eeg,emg,imu,force}_manifest.csv

Usage: python build_canonical_physionet_multimodal_gait.py [--repo PATH]
       [--only eeg,emg,imu,force]
"""
import argparse
import csv
import io
import os
import re
import tarfile

import numpy as np
import pandas as pd

from build_canonical_eeg import norm_site, sanitize
from build_canonical_emg import MUSCLES
from moveatlas import records
from moveatlas.frames import IMU_LOCATIONS

SOURCE = "physionet_multimodal_gait"
REL = os.path.join("datasets", "eeg", "physionet_multimodal_gait")
G = 9.80665

# speed token in the file names -> task id
TASKS = {"0.5": "walk_0.50ms", "0.75": "walk_0.75ms", "1": "walk_1.00ms"}

# ---------------------------------------------------------------- EEG facts
# The 24 data columns of the DSI-24 csv, verbatim (176 of 177 files agree;
# the odd one is refused). Everything not a scalp/ear site is aux.
EEG_COLUMNS = ["P3", "C3", "F3", "Fz", "F4", "C4", "P4", "Cz", "CM", "A1",
               "Fp1", "Fp2", "T3", "T5", "O1", "O2", "X3", "X2", "F7", "F8",
               "X1", "A2", "T6", "T4"]
EEG_DIAG = ["Trigger", "Time_Offset", "ADC_Status", "ADC_Sequence", "Event"]
EEG_RAIL_UV = 9830.1      # observed extreme (max and -min) in 30+ files, see build_eeg
EEG_AUX_KIND = {"CM": "common_mode", "X1": "aux_unused", "X2": "aux_unused",
                "X3": "aux_unused", "Trigger": "trigger",
                "Time_Offset": "diagnostic", "ADC_Status": "diagnostic",
                "ADC_Sequence": "diagnostic", "Event": "event"}

# ---------------------------------------------------------------- EMG facts
# README.txt and the csv headers agree on these 12 names; each maps onto the
# corpus vocabulary (build_canonical_emg.MUSCLES) by its FULL name. Any
# header not in this table is refused, never guessed.
EMG_MUSCLES = {"TIBIALIS ANTERIOR": "tibialis_anterior",
               "VASTUS LATERALIS": "vastus_lateralis",
               "RECTUS FEMORIS": "rectus_femoris",
               "GASTROCNEMIUS MEDIAL HEAD": "gastrocnemius_medialis",
               "SEMITENDINOSUS": "semitendinosus",
               "GASTROCNEMIUS LATERAL HEAD": "gastrocnemius_lateralis"}
EMG_SIDES = {"R": "R", "L": "L"}
EMG_HEADER_RE = re.compile(r"^([LR]) (.+?): EMG (\d+)->MAV \[(.+)\]$")

# ---------------------------------------------------------------- IMU facts
# MVN Awinda 17-sensor set (the Sensor_* csv files list all 23 MVN segments;
# the 6 without a physical sensor - L5, L3, T12, Neck, Right/Left Toe - are
# all-zero columns and are treated as absent). Mapping onto the 14-location
# grid (moveatlas/frames.py IMU_LOCATIONS). The record page and README name
# the sensors by MVN segment only, so:
#   Head -> head, T8 -> trunk, Upper Leg -> thigh, Lower Leg -> shank,
#   Foot -> foot are the segment's own name;
#   Pelvis -> lower_back is the one judgment call (the grid has no pelvis
#   slot; the pelvis sensor of a full-body suit is worn posteriorly and
#   lower_back is the slot every other lumbar/sacral sensor of the corpus
#   uses) - flagged on every record (sensor_map) and in the datacard;
#   Shoulder / Upper Arm / Forearm / Hand carry no statement of where on
#   the arm they sit, so they are NOT forced onto wrist_L/R: aux.
IMU_SENSOR_MAP = {"Head": "head", "T8": "trunk", "Pelvis": "lower_back",
                  "Right Upper Leg": "thigh_R", "Left Upper Leg": "thigh_L",
                  "Right Lower Leg": "shank_R", "Left Lower Leg": "shank_L",
                  "Right Foot": "foot_R", "Left Foot": "foot_L"}
IMU_AUX_SENSORS = ["Right Shoulder", "Left Shoulder", "Right Upper Arm",
                   "Left Upper Arm", "Right Forearm", "Left Forearm",
                   "Right Hand", "Left Hand"]
IMU_NO_SENSOR = ["L5", "L3", "T12", "Neck", "Right Toe", "Left Toe"]
IMU_FPS = 60.0            # "The system operates at a sampling frequency of
                          # 60 Hz" (record page); cross-checked below against
                          # the frame count of the 60 s recording window
LOC_I = {l: i for i, l in enumerate(IMU_LOCATIONS)}

# -------------------------------------------------------------- force facts
FP_HEADER = ["1:Timestamp", "1:Sync", "1:Aux", "1:Fx", "1:Fy", "1:Fz",
             "1:Mx", "1:My", "1:Mz", "1:COPx", "1:COPy",
             "2:Timestamp", "2:Sync", "2:Aux", "2:Fx", "2:Fy", "2:Fz",
             "2:Mx", "2:My", "2:Mz", "2:COPx", "2:COPy"]
FP_FPS = 1000.0           # "All force and COP data were sampled at a high
                          # frequency of 1000 Hz" (record page); the file's
                          # own Timestamp columns are all zero
NPOS = 9                  # 8 insole positions + total (configs/canonical_force.yaml)


# ------------------------------------------------------------------ helpers
def parse_name(stem, prefix):
    """'EMG_S10_0.75' / 'S10_0.75_raw' / 'IMU_S10_0.5' -> ('S10', '0.75')."""
    s = stem
    if prefix and s.startswith(prefix):
        s = s[len(prefix):]
    if s.endswith("_raw"):
        s = s[:-4]
    m = re.fullmatch(r"(S\d+)_(0\.5|0\.75|1)", s)
    return (m.group(1), m.group(2)) if m else (None, None)


def load_subjects(path):
    """Per-subject age and sex ONLY. The file also carries a full date of
    birth and 18 anthropometrics; the DOB column is never read (the row
    dict is reduced to the three fields before anything is kept) and the
    summary rows at the bottom (Average, Median, ...) are skipped."""
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sid = (row.get("Subject") or "").strip()
            if not re.fullmatch(r"S\d+", sid):
                continue
            sex = (row.get("GENDER") or "").strip().upper() or None
            try:
                age = int(float(row.get("Age", "")))
            except ValueError:
                age = None
            out[sid] = {"age": age, "sex": sex if sex in ("M", "F") else None}
    return out


def subject_fields(subjects, sid):
    s = subjects.get(sid, {"age": None, "sex": None})
    return {"age": s["age"], "sex": s["sex"],
            "demographics_note": "age (years) and sex from subject-info.csv; "
                                 "the file's date of birth is not carried "
                                 "(direct identifier), anthropometrics not "
                                 "carried"}


def write_aux(auxdir, rid, family, streams, subject_ns, task, n):
    os.makedirs(auxdir, exist_ok=True)
    rec = {"streams": streams, "subject_ns": subject_ns, "task": task,
           "source": SOURCE, "family": family, "n_frames": int(n)}
    records.save(os.path.join(auxdir, f"{rid}__{family}.npz"), rec)


def relp(path, repo):
    return os.path.relpath(path, repo).replace("\\", "/")


# ---------------------------------------------------------------------- EEG
def read_eeg_header(path):
    """The 15 header lines ('# key =,value,,,') then the column line."""
    hdr = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [f.readline().rstrip("\r\n") for _ in range(16)]
    for ln in lines[:15]:
        body = ln.lstrip("#").strip()
        k, _, v = body.partition(",")
        hdr[k.strip().rstrip("=").rstrip(":").strip()] = v.strip(",").strip()
    cols = [c.strip() for c in lines[15].split(",")]
    return hdr, cols


def read_eeg_data(path, cols):
    return pd.read_csv(path, skiprows=16, header=None, names=cols,
                       dtype={"Comments": str}, keep_default_na=False,
                       low_memory=False)


def build_eeg(repo, subjects, audit, manifest):
    rawd = os.path.join(repo, REL, "raw", "Dataset", "EEG_Data", "EEG.csv")
    outdir = os.path.join(repo, REL, "processed", "canonical_eeg")
    auxdir = os.path.join(repo, REL, "processed", "aux")
    files = sorted(p for p in os.listdir(rawd) if p.endswith(".csv"))
    n = 0
    for fn in files:
        sid, speed = parse_name(fn[:-4], "")
        if sid is None:
            audit.append([fn, "", "", "eeg", "", "", "", "refused",
                          "file name does not parse as S<id>_<speed>_raw"])
            continue
        subject_ns, task = f"{SOURCE}:{sid}", TASKS[speed]
        try:
            hdr, cols = read_eeg_header(os.path.join(rawd, fn))
        except Exception as e:
            audit.append([fn, subject_ns, task, "eeg", "", "", "", "refused",
                          f"READ FAIL (header): {e}"])
            continue
        notes = []
        # --- declarations, enforced BEFORE the data is parsed
        fs = float(hdr.get("Sample_Frequency_(Hz)", "nan"))
        unit = hdr.get("Sensor_Data_Units", "")
        ref = hdr.get("Reference location", "")
        if not (fs == 300.0 and unit == "uV" and norm_site(ref) == "PZ"):
            audit.append([fn, subject_ns, task, "eeg", "", fs, unit,
                          "refused", f"header declares fs={fs} unit={unit!r} "
                          f"ref={ref!r}; expected 300/uV/Pz"])
            continue
        data_cols = cols[1:25]
        if data_cols != EEG_COLUMNS:
            audit.append([fn, subject_ns, task, "eeg", "", fs, unit,
                          "refused", "montage line differs from the DSI-24 "
                          "layout of the other 176 files (channel identity "
                          "uncertain: '?' / '???' labels, A2 twice, F6, C2; "
                          "the .edf twin carries the same labels): "
                          + ",".join(data_cols)])
            continue
        try:
            df = read_eeg_data(os.path.join(rawd, fn), cols)
        except Exception as e:
            audit.append([fn, subject_ns, task, "eeg", "", fs, unit, "refused",
                          f"READ FAIL: {e}"])
            continue
        t = df["Time"].to_numpy(float)
        dt = np.diff(t)
        med = float(np.median(dt)) if dt.size else float("nan")
        if abs(med * fs - 1.0) > 0.02:
            notes.append(f"Time column median dt {med * 1000:.3f} ms disagrees "
                         f"with the declared {fs} Hz")
        gaps = int(np.sum(np.abs(dt * fs - 1.0) > 0.5)) if dt.size else 0
        if gaps:
            notes.append(f"{gaps} Time step(s) off by >50% of a sample "
                         "(kept as recorded, no repair)")
        # --- eeg channels: every scalp/ear site, recorded against Pz
        sig_cols, chans, aux_streams = [], [], []
        for c in data_cols:
            site = norm_site(c) if c not in EEG_AUX_KIND else None
            if site:
                sig_cols.append(c)
                chans.append({"site": site, "ref": "PZ", "kind": "eeg",
                              "placement": c})
            else:
                aux_streams.append({"label": c, "kind": EEG_AUX_KIND.get(c, "aux"),
                                    "unit": unit if c in ("CM", "X1", "X2", "X3")
                                    else "", "fs": fs,
                                    "signal": df[c].to_numpy(np.float32)})
        for c in EEG_DIAG:
            if c in df:
                aux_streams.append({"label": c, "kind": EEG_AUX_KIND[c],
                                    "unit": "", "fs": fs,
                                    "signal": df[c].to_numpy(np.float32)})
        if "Comments" in df:
            cm = df["Comments"].astype(str).str.strip()
            nz = cm[cm != ""]
            if len(nz):
                aux_streams.append({"label": "Comments", "kind": "text",
                                    "unit": "", "fs": fs,
                                    "signal": np.zeros(0, np.float32),
                                    "entries": [[int(i), str(v)] for i, v
                                                in nz.items()][:1000]})
                notes.append(f"{len(nz)} non-empty Comments cell(s) kept in aux")
        sig = df[sig_cols].to_numpy(np.float32)
        if not np.isfinite(sig).all():
            audit.append([fn, subject_ns, task, "eeg", len(df), fs, unit,
                          "refused", "non-finite EEG samples"])
            continue
        p99 = float(np.percentile(np.abs(sig), 99))
        # Saturation flag (honesty mechanism, nothing is altered): the exact
        # extreme +/-9830.1 uV recurs across dozens of files and whole
        # channels sit on it (dry electrodes with poor contact, mostly Cz).
        # The header declares no range, so the rail is OBSERVED, not declared.
        railed = np.mean(np.abs(sig) >= EEG_RAIL_UV - 0.5, axis=0)
        railed_ch = [chans[i]["site"] for i in np.where(railed > 0.5)[0]]
        if railed_ch:
            notes.append("railed >50%: " + "|".join(
                f"{chans[i]['site']}({railed[i] * 100:.0f}%)"
                for i in np.where(railed > 0.5)[0]))
        rec = {"signal": sig, "channels": chans, "fps": fs, "unit": "uV",
               "railed_channels": railed_ch,
               "railed_fraction": [round(float(x), 4) for x in railed],
               "railed_note": f"fraction of samples per channel at |x| >= "
                              f"{EEG_RAIL_UV} uV, the exact extreme observed "
                              "across the corpus (ADC rail; not declared in "
                              "the header); railed_channels lists sites above "
                              "50%; values are stored as recorded",
               "unit_scale": 1.0, "signal_kind": "as_recorded",
               "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None,
                           "prefilter_verbatim": hdr.get("Filter"),
                           "filter_delay_ms": float(hdr.get("Filter_Delay_(ms)", "nan")),
                           "mains_hz": float(hdr.get("Mains_Frequency_(Hz)", "nan"))},
               "reference_note": "hardware reference Pz (csv header 'Reference "
                                 "location: Pz', EEG_referencing.m, record "
                                 "page); A1/A2 are data channels against Pz; "
                                 "the authors' linked-ears re-reference is "
                                 "NOT applied",
               "headset": hdr.get("Headset_Name", "").split(" SN:")[0],
               "subject_ns": subject_ns, "task": task, "source": SOURCE,
               "n_frames": int(sig.shape[0]), "label": None}
        rec.update(subject_fields(subjects, sid))
        rid = sanitize(f"{SOURCE}__{subject_ns}__{task}")
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, rid + ".npz")
        records.save(path, rec)
        write_aux(auxdir, rid, "eeg", aux_streams, subject_ns, task, sig.shape[0])
        manifest.append([SOURCE, subject_ns, task, fs, rec["n_frames"],
                         len(chans), "|".join(c["site"] for c in chans),
                         relp(path, repo)])
        audit.append([fn, subject_ns, task, "eeg", rec["n_frames"], fs, "uV",
                      f"eeg={len(chans)} aux={len(aux_streams)}",
                      "; ".join([f"p99={p99:.0f}uV", f"ref=PZ",
                                 f"mains={hdr.get('Mains_Frequency_(Hz)')}Hz"]
                                + notes)])
        n += 1
    print(f"eeg: {n} records from {len(files)} csv files")
    return n


# ---------------------------------------------------------------------- EMG
def build_emg(repo, subjects, audit, manifest):
    rawd = os.path.join(repo, REL, "raw", "Dataset", "EMG_Data")
    outdir = os.path.join(repo, REL, "processed", "canonical_emg")
    files = sorted(p for p in os.listdir(rawd) if p.endswith(".csv"))
    n = 0
    for fn in files:
        sid, speed = parse_name(fn[:-4], "EMG_")
        if sid is None:
            audit.append([fn, "", "", "emg", "", "", "", "refused",
                          "file name does not parse"])
            continue
        subject_ns, task = f"{SOURCE}:{sid}", TASKS[speed]
        try:
            df = pd.read_csv(os.path.join(rawd, fn))
        except Exception as e:
            audit.append([fn, subject_ns, task, "emg", "", "", "", "refused",
                          f"READ FAIL: {e}"])
            continue
        cols = list(df.columns)
        if cols[0] != "X [s]":
            audit.append([fn, subject_ns, task, "emg", len(df), "", "",
                          "refused", f"first column {cols[0]!r} is not the "
                          "timestamp"])
            continue
        chans, keep, refused = [], [], []
        for c in cols[1:]:
            m = EMG_HEADER_RE.match(c.strip())
            if not m or m.group(2) not in EMG_MUSCLES or m.group(4) != "Volts":
                refused.append(c)
                continue
            muscle = EMG_MUSCLES[m.group(2)]
            assert muscle in MUSCLES, muscle
            chans.append({"kind": "emg", "muscle": muscle,
                          "side": EMG_SIDES[m.group(1)], "placement": c.strip(),
                          "electrode": m.group(3), "unit_in_header": m.group(4),
                          "resolved": True})
            keep.append(c)
        if not chans:
            audit.append([fn, subject_ns, task, "emg", len(df), "", "",
                          "refused", "no channel header matched the README "
                          "muscle list: " + "|".join(refused)])
            continue
        t = df["X [s]"].to_numpy(float)
        dt = np.diff(t)
        if dt.size < 2 or not (dt > 0).all():
            audit.append([fn, subject_ns, task, "emg", len(df), "", "",
                          "refused", "timestamp column not strictly increasing"])
            continue
        med = float(np.median(dt))
        jitter = float(np.abs(dt - med).max())
        fs = 1.0 / med
        notes = []
        if jitter > 0.01 * med:
            notes.append(f"timestamp jitter {jitter * 1000:.3f} ms")
        sig = df[keep].to_numpy(np.float64) * 1000.0          # V -> mV
        if not np.isfinite(sig).all():
            audit.append([fn, subject_ns, task, "emg", len(df), fs, "mV",
                          "refused", "non-finite samples"])
            continue
        if (sig < 0).any():
            notes.append(f"{int((sig < 0).sum())} negative sample(s) in a MAV "
                         "envelope, kept as recorded")
        sig = sig.astype(np.float32)
        p99 = float(np.percentile(sig, 99))
        rec = {"signal": sig, "channels": chans, "fps": float(fs),
               "fps_provenance": "measured from the file's X [s] column "
                                 f"(median dt {med * 1000:.4f} ms, max jitter "
                                 f"{jitter:.2e} s); not declared by the source",
               "unit": "mV", "unit_scale": 1000.0,
               "signal_kind": "envelope",
               "envelope_kind": "MAV (mean absolute value) as exported by the "
                                "source (header 'EMG k->MAV [Volts]', README "
                                "'mean absolute value, volts'); window not "
                                "declared; the raw EMG is not distributed",
               "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
               "system": "Delsys Trigno Wireless EMG (record page)",
               "subject_ns": subject_ns, "task": task, "source": SOURCE,
               "n_frames": int(sig.shape[0]), "label": None}
        rec.update(subject_fields(subjects, sid))
        rid = sanitize(f"{SOURCE}__{subject_ns}__{task}")
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, rid + ".npz")
        records.save(path, rec)
        manifest.append([SOURCE, subject_ns, task, float(fs), rec["n_frames"],
                         len(chans), "emg", relp(path, repo)])
        audit.append([fn, subject_ns, task, "emg", rec["n_frames"],
                      round(fs, 4), "mV (V x1000)",
                      f"emg={len(chans)} refused_ch={len(refused)}",
                      "; ".join([f"p99={p99:.4f}mV", "envelope=MAV"] + notes
                                + ([f"refused channels: " + "|".join(refused)]
                                   if refused else []))])
        n += 1
    print(f"emg: {n} records from {len(files)} csv files")
    return n


# -------------------------------------------------------------------- force
def build_force(repo, subjects, audit, manifest):
    rawd = os.path.join(repo, REL, "raw", "Dataset", "FP_Data")
    auxdir = os.path.join(repo, REL, "processed", "aux")
    files = sorted(p for p in os.listdir(rawd) if p.endswith(".csv"))
    recs = []
    for fn in files:
        sid, speed = parse_name(fn[:-4], "FP_")
        if sid is None:
            audit.append([fn, "", "", "force", "", "", "", "refused",
                          "file name does not parse"])
            continue
        subject_ns, task = f"{SOURCE}:{sid}", TASKS[speed]
        with open(os.path.join(rawd, fn), encoding="utf-8", errors="replace") as f:
            first = f.readline().strip()
        notes = []
        if first.split(",") == FP_HEADER:
            skip = 1
        elif first.startswith("1:"):
            audit.append([fn, subject_ns, task, "force", "", "", "", "refused",
                          f"header differs from the documented layout: {first[:120]}"])
            continue
        else:
            if len(first.split(",")) != 22:
                audit.append([fn, subject_ns, task, "force", "", "", "",
                              "refused", "no header line and not 22 columns"])
                continue
            skip = 0
            notes.append("no header line in this file; the 22-column layout "
                         "of the 170 headed files is applied (same order, "
                         "1: left / 2: right)")
        try:
            a = np.loadtxt(os.path.join(rawd, fn), delimiter=",", skiprows=skip,
                           dtype=np.float64)
        except Exception as e:
            audit.append([fn, subject_ns, task, "force", "", "", "", "refused",
                          f"READ FAIL: {e}"])
            continue
        if a.ndim != 2 or a.shape[1] != 22:
            audit.append([fn, subject_ns, task, "force", "", "", "", "refused",
                          f"shape {a.shape}, expected 22 columns"])
            continue
        if not np.isfinite(a).all():
            audit.append([fn, subject_ns, task, "force", a.shape[0], "", "",
                          "refused", "non-finite samples"])
            continue
        T = a.shape[0]
        col = {h: i for i, h in enumerate(FP_HEADER)}
        for k in ("1:Timestamp", "1:Sync", "2:Timestamp", "2:Sync"):
            if np.any(a[:, col[k]] != 0):
                notes.append(f"{k} column is not all zero (kept in aux)")
        force = np.zeros((T, 2, NPOS), np.float32)
        force[:, 0, 8] = a[:, col["1:Fz"]]            # left leg (README, page)
        force[:, 1, 8] = a[:, col["2:Fz"]]            # right leg
        mask = np.zeros((2, NPOS), bool)
        mask[:, 8] = True
        fz_sum_med = float(np.median(force[:, 0, 8] + force[:, 1, 8]))
        rec = {"force": force, "sensor_mask": mask, "fps": FP_FPS,
               "fps_provenance": "1000 Hz declared on the PhysioNet record "
                                 "page ('All force and COP data were sampled "
                                 "at a high frequency of 1000 Hz'); the "
                                 "file's Timestamp/Sync columns are all zero",
               "unit": "unknown",
               "unit_note": "no unit is declared for the force columns (record "
                            "page, README, header); values are stored as "
                            "exported. Consistency only: the median Fz sum of "
                            f"this record is {fz_sum_med:.0f}, of the order of "
                            "the subject's body weight in newtons; NOT promoted "
                            "to N",
               "component": "Fz (vertical) per belt of the Bertec split-belt "
                            "instrumented treadmill; block '1:' = left leg, "
                            "'2:' = right leg (FP_Data/README.txt and the "
                            "record page); Fx/Fy/Mx/My/Mz/COPx/COPy in aux",
               "subject_ns": subject_ns, "task": task, "source": SOURCE,
               "n_frames": int(T)}
        rec.update(subject_fields(subjects, sid))
        rid = sanitize(f"{SOURCE}__{subject_ns}__{task}")
        streams = []
        for side, blk in (("left", "1:"), ("right", "2:")):
            for k in ("Fx", "Fy", "Mx", "My", "Mz", "COPx", "COPy",
                      "Timestamp", "Sync", "Aux"):
                streams.append({"label": f"{blk}{k}", "kind": f"force_plate_{side}",
                                "unit": "unknown", "fs": FP_FPS,
                                "signal": a[:, col[f"{blk}{k}"]].astype(np.float32)})
        write_aux(auxdir, rid, "force", streams, subject_ns, task, T)
        recs.append(rec)
        manifest.append([SOURCE, subject_ns, task, FP_FPS, int(T)])
        audit.append([fn, subject_ns, task, "force", int(T), FP_FPS, "unknown",
                      "totals_only(Fz L/R) aux=20",
                      "; ".join([f"median Fz sum={fz_sum_med:.0f}",
                                 f"Fz p99 L={np.percentile(force[:, 0, 8], 99):.0f} "
                                 f"R={np.percentile(force[:, 1, 8], 99):.0f}"]
                                + notes)])
    out = os.path.join(repo, REL, "processed", "canonical_force.npz")
    if recs:
        records.save(out, recs)
    print(f"force: {len(recs)} records from {len(files)} csv files -> {out}")
    return len(recs)


# ---------------------------------------------------------------------- IMU
def _sensor_blocks(header):
    """'Frame,Pelvis x,Pelvis y,Pelvis z,L5 x,...' -> {segment: [ix, iy, iz]}"""
    blocks = {}
    for i, h in enumerate(header):
        m = re.fullmatch(r"(.+) ([xyz])", h.strip())
        if m:
            blocks.setdefault(m.group(1), {})[m.group(2)] = i
    return {k: [v["x"], v["y"], v["z"]] for k, v in blocks.items()
            if set(v) == {"x", "y", "z"}}


def build_imu(repo, subjects, audit, manifest):
    tgz = os.path.join(repo, REL, "raw", "Dataset", "IMU_Data", "IMU.tar.gz")
    auxdir = os.path.join(repo, REL, "processed", "aux")
    if not os.path.exists(tgz):
        print(f"imu: SKIP (missing {tgz})")
        return 0
    wanted = {"Sensor_Free_Acceleration.csv": "acc",
              "Sensor_Magnetic_Field.csv": "mag"}
    per_folder = {}
    print("imu: streaming IMU.tar.gz (3.9 GB, sequential gzip; minutes)")
    with tarfile.open(tgz, "r|gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            parts = m.name.replace("\\", "/").split("/")
            if len(parts) < 2 or parts[-1] not in wanted:
                continue
            folder = parts[-2]
            f = tf.extractfile(m)
            per_folder.setdefault(folder, {})[wanted[parts[-1]]] = f.read()
    recs = []
    n_folders = 0
    for folder in sorted(per_folder):
        n_folders += 1
        sid, speed = parse_name(folder, "IMU_")
        if sid is None:
            audit.append([folder, "", "", "imu", "", "", "", "refused",
                          "folder name does not parse"])
            continue
        subject_ns, task = f"{SOURCE}:{sid}", TASKS[speed]
        raw = per_folder[folder]
        if "acc" not in raw:
            audit.append([folder, subject_ns, task, "imu", "", "", "", "refused",
                          "no Sensor_Free_Acceleration.csv in the folder"])
            continue
        if not raw["acc"].strip():
            audit.append([folder, subject_ns, task, "imu", "", "", "", "refused",
                          f"Sensor_Free_Acceleration.csv is EMPTY in the archive "
                          f"({len(raw['acc'])} bytes); nothing to ingest"])
            continue
        try:
            df = pd.read_csv(io.BytesIO(raw["acc"]))
        except Exception as e:
            audit.append([folder, subject_ns, task, "imu", "", "", "", "refused",
                          f"READ FAIL: {e}"])
            continue
        blocks = _sensor_blocks(list(df.columns))
        A = df.to_numpy(np.float64)
        T = A.shape[0]
        notes = []
        frames = A[:, 0]
        if not np.array_equal(frames, np.arange(T)):
            notes.append("Frame column is not 0..T-1 (kept as is)")
        expected = set(IMU_SENSOR_MAP) | set(IMU_AUX_SENSORS) | set(IMU_NO_SENSOR)
        unknown = sorted(set(blocks) - expected)
        if unknown:
            audit.append([folder, subject_ns, task, "imu", T, IMU_FPS, "", "refused",
                          "unexpected segment column(s), montage drift: "
                          + "|".join(unknown)])
            continue
        # sensor presence is what the data says: an all-zero triplet is a
        # segment without a physical sensor (the 6 MVN model-only segments)
        present = {seg: bool(np.any(A[:, ix] != 0)) for seg, ix in blocks.items()}
        ghost = [s for s in IMU_NO_SENSOR if present.get(s)]
        if ghost:
            notes.append("non-sensor segment(s) carry data: " + "|".join(ghost))
        missing = [s for s in list(IMU_SENSOR_MAP) + IMU_AUX_SENSORS
                   if s in blocks and not present[s]]
        if missing:
            notes.append("sensor(s) all-zero, treated as absent: " + "|".join(missing))
        active = [(seg, loc) for seg, loc in IMU_SENSOR_MAP.items()
                  if seg in blocks and present[seg]]
        active.sort(key=lambda t: LOC_I[t[1]])
        if not active:
            audit.append([folder, subject_ns, task, "imu", T, IMU_FPS, "", "refused",
                          "no mapped sensor carries data"])
            continue
        sig = np.zeros((T, len(active), 9), np.float32)
        cmask = np.zeros((len(active), 9), bool)
        for li, (seg, loc) in enumerate(active):
            sig[:, li, 0:3] = A[:, blocks[seg]] / G                 # m/s2 -> g
            cmask[li, 0:3] = True
        if not np.isfinite(sig).all():
            audit.append([folder, subject_ns, task, "imu", T, IMU_FPS, "g", "refused",
                          "non-finite samples"])
            continue
        dur = T / IMU_FPS
        if not (50.0 <= dur <= 80.0):
            notes.append(f"{T} frames = {dur:.1f} s at 60 Hz, outside the "
                         "~60 s recording window; rate cross-check FAILED")
        rec = {"signal": sig,
               "location_ids": np.array([LOC_I[loc] for _, loc in active], np.int64),
               "channel_mask": cmask, "fps": IMU_FPS,
               "fps_provenance": "60 Hz declared on the PhysioNet record page "
                                 "('The system operates at a sampling frequency "
                                 f"of 60 Hz'); cross-check: {T} frames = "
                                 f"{dur:.1f} s for the 60 s middle-minute window",
               "acc_content": "linear_no_gravity",
               "acc_unit_source": "MVN 'Sensor Free Acceleration ... in [m/s2]' "
                                  "(record page), divided by 9.80665 -> g",
               "acc_frame_note": "MVN free acceleration is the sensor "
                                 "acceleration with gravity removed; the "
                                 "reference frame is not stated by the dataset "
                                 "(MVN convention: global frame), NOT the "
                                 "sensor frame",
               "gyro_note": "absent: the export carries no sensor angular "
                            "velocity (Segment_Angular_Velocity is a model "
                            "output, not ingested)",
               "mag_note": "absent: Sensor_Magnetic_Field is exported in "
                           "[a.u.], not uT; kept in aux as recorded",
               "sensor_map": {seg: loc for seg, loc in active},
               "sensor_map_note": "MVN segment name -> grid slot; Pelvis -> "
                                  "lower_back is a judgment call (no pelvis "
                                  "slot in the grid); arm sensors are in aux "
                                  "(no statement of their position on the arm)",
               "system": "Xsens MVN Awinda, 17 sensors, MVN 2023 export "
                         "(General_Information.csv)",
               "subject_ns": subject_ns, "task": task, "source": SOURCE,
               "n_frames": int(T)}
        rec.update(subject_fields(subjects, sid))
        recs.append(rec)
        manifest.append([SOURCE, subject_ns, task, IMU_FPS, int(T),
                         "|".join(loc for _, loc in active)])
        # --- aux: unmapped arm sensors (free acc, m/s2 as exported) + magnetic
        # field (a.u.) of every sensor that carries data
        streams = []
        for seg in IMU_AUX_SENSORS:
            if seg in blocks and present[seg]:
                for k, ax in enumerate("xyz"):
                    streams.append({"label": f"{seg} free_acc_{ax}",
                                    "kind": "imu_free_acc_unmapped",
                                    "unit": "m/s2", "fs": IMU_FPS,
                                    "signal": A[:, blocks[seg][k]].astype(np.float32)})
        n_mag = 0
        if "mag" in raw:
            try:
                dm = pd.read_csv(io.BytesIO(raw["mag"]))
                mb = _sensor_blocks(list(dm.columns))
                M = dm.to_numpy(np.float64)
                if M.shape[0] != T:
                    notes.append(f"magnetic field file has {M.shape[0]} frames "
                                 f"vs {T}; not kept")
                else:
                    for seg, ix in mb.items():
                        if np.any(M[:, ix] != 0):
                            for k, ax in enumerate("xyz"):
                                streams.append({"label": f"{seg} mag_{ax}",
                                                "kind": "imu_mag_au",
                                                "unit": "a.u.", "fs": IMU_FPS,
                                                "signal": M[:, ix[k]].astype(np.float32)})
                            n_mag += 1
            except Exception as e:
                notes.append(f"magnetic field file unreadable: {e}")
        rid = sanitize(f"{SOURCE}__{subject_ns}__{task}")
        write_aux(auxdir, rid, "imu", streams, subject_ns, task, T)
        p99 = float(np.percentile(np.abs(sig[:, :, 0:3]), 99))
        audit.append([folder, subject_ns, task, "imu", int(T), IMU_FPS,
                      "g (m/s2 / 9.80665), free acc",
                      f"locations={len(active)} aux_sensors="
                      f"{sum(1 for s in IMU_AUX_SENSORS if s in blocks and present[s])} "
                      f"mag_au_sensors={n_mag}",
                      "; ".join([f"acc p99={p99:.3f}g",
                                 "|".join(f"{s}->{l}" for s, l in active)] + notes)])
        if len(recs) % 25 == 0:
            print(f"  {len(recs)} imu records", flush=True)
    out = os.path.join(repo, REL, "processed", "canonical_imu.npz")
    if recs:
        records.save(out, recs)
    print(f"imu: {len(recs)} records from {n_folders} folders -> {out}")
    return len(recs)


# ----------------------------------------------------------------- manifests
def merge_manifest(path, header, new_rows):
    """Replace every row of this SOURCE, keep the others, LF line ends."""
    old = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if rows and rows[0] != header:
            raise SystemExit(f"{path}: header {rows[0]} != expected {header}")
        old = [r for r in rows[1:] if r and r[0] != SOURCE]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(old + new_rows)
    print(f"manifest: {os.path.basename(path)} ({len(old)} kept + "
          f"{len(new_rows)} {SOURCE} rows)")


HEADERS = {
    "eeg": ["source", "subject_ns", "task", "fps", "n_frames", "n_channels",
            "sites", "record_path"],
    "emg": ["source", "subject_ns", "task", "fps", "n_frames", "n_channels",
            "kinds", "record_path"],
    "imu": ["source", "subject_ns", "task", "fps", "n_frames", "locations"],
    "force": ["source", "subject_ns", "task", "fps", "n_frames"]}
BUILDERS = {"eeg": build_eeg, "emg": build_emg, "imu": build_imu,
            "force": build_force}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--only", default=None, help="comma list among eeg,emg,imu,force")
    args = ap.parse_args()
    fams = list(BUILDERS) if not args.only else [s.strip() for s in args.only.split(",")]
    subjects = load_subjects(os.path.join(args.repo, REL, "raw", "Dataset",
                                          "subject-info.csv"))
    print(f"subjects: {len(subjects)} (age + sex only; DOB never read)")
    audit_path = os.path.join(args.repo, REL, "processed", "ingest_audit.csv")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    # a partial run (--only) keeps the audit rows of the other families
    audit = []
    if os.path.exists(audit_path) and args.only:
        with open(audit_path, newline="", encoding="utf-8") as f:
            audit = [r for r in list(csv.reader(f))[1:] if r and r[3] not in fams]
    manifests = {f: [] for f in fams}
    for fam in fams:
        if fam not in BUILDERS:
            raise SystemExit(f"unknown family {fam!r}")
        BUILDERS[fam](args.repo, subjects, audit, manifests[fam])
    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "subject_ns", "task", "family", "n_frames", "fs",
                    "unit", "routing", "notes"])
        w.writerows(sorted(audit, key=lambda r: (r[3], r[0])))
    for fam in fams:
        merge_manifest(os.path.join(args.repo, "datasets",
                                    f"_canonical_{fam}_manifest.csv"),
                       HEADERS[fam], manifests[fam])
    for fam in fams:
        rows = manifests[fam]
        hrs = sum(float(r[4]) / float(r[3]) for r in rows) / 3600.0 if rows else 0.0
        subs = len({r[1] for r in rows})
        refused = sum(1 for r in audit if r[3] == fam and r[7] == "refused")
        print(f"{fam:6s} {len(rows):4d} records  {subs:3d} subjects  "
              f"{hrs:6.2f} h  refused files {refused}")


if __name__ == "__main__":
    main()
