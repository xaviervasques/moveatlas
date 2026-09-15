# -*- coding: utf-8 -*-
"""Canonical-EMG ingestion of drummer_tremor_model (RDG doi:10.57745/THHWP2).

Expert drummers replicating physiological-tremor frequencies (4.6-8.7 Hz
unilateral): full-body mocap + 7-per-leg surface EMG at 2000 Hz, one C3D
per subject x tempo. This recipe ingests the RAW EMG layer only
(Voltage.EMG1..16), mapped to muscles through the deposit's own
TAB1_Analog_channels.tab (per-drummer electrode table, NA electrodes
skipped, never guessed). The C3D header declares 'V' but the values sit
at uV scale: per the units policy the signal is stored AS-RECORDED with
unit unknown and the contradiction flagged (ds007526 precedent). The in-file processed variants (bandpass/rectified/normaMVC)
are deliberately NOT ingested: canonical keeps signal_kind raw.

Output: processed/canonical_emg/*.pkl (one per trial) + per-source
rewrite of datasets/_canonical_emg_manifest.csv + an ingest audit.
Context lane record: healthy expert drummers, a mechanistic model of
physiological tremor (A2 context, C2) - never a patient cohort.

Usage: python build_canonical_drummer.py
"""
import csv
import glob
import os
import pickle
import re

import numpy as np
import ezc3d

REPO = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(REPO, "datasets", "imu", "drummer_tremor_model")
RAW = os.path.join(DS, "raw")
OUT = os.path.join(DS, "processed", "canonical_emg")
MANIFEST = os.path.join(REPO, "datasets", "_canonical_emg_manifest.csv")
SOURCE = "drummer_tremor_model"

MUSCLES = ["erector_spinae", "rectus_abdominis", "tensor_fascia_latae",
           "semitendinosus", "gluteus_medius", "rectus_femoris",
           "soleus", "tibialis_anterior"]


def sanitize(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def load_mapping():
    """TAB1: per-drummer EMG channel number per muscle x side (NA = no
    electrode). Returns {subject int -> [(muscle, side, channel int)]}."""
    path = os.path.join(RAW, "TAB1_Analog_channels.tab")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";"))
    mapping = {}
    for row in rows[2:]:
        m = re.match(r"Drummer (\d+)", row[0] or "")
        if not m:
            continue
        subj = int(m.group(1))
        chans = []
        for i, muscle in enumerate(MUSCLES):
            for j, side in enumerate(("L", "R")):
                cell = (row[1 + 2 * i + j] or "").strip()
                if cell and cell.upper() != "NA":
                    chans.append((muscle, side, int(cell)))
        mapping[subj] = chans
    return mapping


def main():
    mapping = load_mapping()
    os.makedirs(OUT, exist_ok=True)
    audit_rows, manifest_new = [], []
    files = sorted(glob.glob(os.path.join(RAW, "S*_*bpm_*.c3d")))
    for path in files:
        name = os.path.basename(path)
        m = re.match(r"S(\d+)_(\d+)bpm", name)
        subj, bpm = int(m.group(1)), int(m.group(2))
        chans = mapping.get(subj)
        if not chans:
            audit_rows.append([name, "REFUSED", "no TAB1 mapping row"])
            continue
        c = ezc3d.c3d(path)
        labels = c["parameters"]["ANALOG"]["LABELS"]["value"]
        rate = float(c["parameters"]["ANALOG"]["RATE"]["value"][0])
        analogs = c["data"]["analogs"][0]  # (channels, samples)
        idx, channels = [], []
        missing = []
        for muscle, side, n in chans:
            lab = f"Voltage.EMG{n}"
            if lab in labels:
                idx.append(labels.index(lab))
                channels.append({
                    "kind": "emg", "muscle": muscle, "side": side,
                    "placement": (f"electrode {lab} per the deposit's "
                                  "TAB1_Analog_channels.tab (drummer-"
                                  "specific table)"),
                    "resolved": True})
            else:
                missing.append(lab)
        if not idx:
            audit_rows.append([name, "REFUSED", "no mapped EMG channels"])
            continue
        # The C3D header declares 'V' but the values contradict it
        # (p99 up to 7e5 after a V->mV conversion; plausible only if
        # the true unit is uV). Units policy: NEVER rescale on a
        # guess - store as-recorded, unit unknown, flagged.
        sig = analogs[idx].T.astype(np.float32)
        rec = {
            "source": SOURCE,
            "subject_ns": f"drummer:S{subj:02d}",
            "task": f"drumming_{bpm}bpm",
            "signal": sig,
            "channels": channels,
            "fps": rate,
            "n_frames": sig.shape[0],
            "unit": "unknown",
            "unit_scale": 1.0,
            "signal_kind": "raw",
            "filters": ("none (raw Voltage.EMG channels; the file's "
                        "bandpass/rectified/normaMVC variants are not "
                        "ingested)"),
            "gait_events": None,
        }
        rid = sanitize(f"{SOURCE}__{rec['subject_ns']}__{rec['task']}")
        out = os.path.join(OUT, rid + ".pkl")
        with open(out, "wb") as f:
            pickle.dump(rec, f)
        kinds = "emg"
        manifest_new.append([SOURCE, rec["subject_ns"], rec["task"],
                             rec["fps"], rec["n_frames"], len(channels),
                             kinds, os.path.relpath(out, REPO)])
        audit_rows.append([name, "OK_UNIT_FLAGGED",
                           f"{len(channels)} muscles; header says V but "
                           "values are uV-scale: stored as-recorded, "
                           "unit unknown (units policy)"])
    # per-source manifest rewrite (idempotent)
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f)]
    head, body = rows[0], [r for r in rows[1:] if r and r[0] != SOURCE]
    with open(MANIFEST, "w", newline="\n", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(body + manifest_new)
    audit = os.path.join(DS, "processed", "emg_ingest_audit.csv")
    with open(audit, "w", newline="\n", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "status", "note"])
        w.writerows(audit_rows)
    ok = sum(1 for r in audit_rows if r[1].startswith("OK"))
    print(f"{ok}/{len(files)} trials -> canonical EMG records; "
          f"manifest rows: {len(manifest_new)}; audit: {audit}")


if __name__ == "__main__":
    main()
