# -*- coding: utf-8 -*-
"""Ingest tremordb: PhysioNet "Effect of Deep Brain Stimulation on Parkinsonian
Tremor" (rest tremor VELOCITY by laser Doppler, 100 Hz).

RE-EXAMINED 2026-08-22 (was SKIPPED in v1 for "opaque channel names"). The .hea
comment blocks document everything; verified on the real files this session:
  - Each record group r{...}{h|l} bundles 8 subjects (h = high-, l = low-amplitude
    tremor cohort); one TEXT file per subject, one float per line, values already
    in physical units (mm/s or m/s per the .hea table), 100 Hz.
  - .rit / .let = RIGHT / LEFT hand recording.
  - Subject prefix g/v/s = DBS target GPi / Vim / STN. 16 subjects total.
  - Conditions encoded in the group name and stated in each .hea comment:
    ron/rof = rest tremor, medication ON/OFF (DBS state per .hea comment);
    ren/ref = DBS ON groups; r15/30/45/60of = 15..60 min after DBS switched OFF
    (washout timeline). The ingester TRUSTS the .hea comment line "CONDITION: ..."
    and stores it verbatim; the group code is kept as `task`.

This is LASER VELOCITY, not accel/gyro: it does NOT fit the canonical 9-channel
IMU contract. It is ingested as an AUX time-series asset (like voice/keystroke):
one record per (subject, group): signal (T,1) float32 mm/s (m/s converted), fps
100, side L/R, DBS target, condition verbatim, cohort h/l. Value: A1 tremor
severity dynamics under DBS on/off + washout, per target.

Outputs (datasets/imu/tremordb/processed/):   [physical location unchanged, rule 1]
  tremordb_velocity.pkl        list of records
  tremordb_subject_table.csv   subject x condition inventory
  tremordb_ingest_audit.csv
Env: atlas-mouvement (numpy). Usage: python ingest_tremordb.py [--repo PATH]
Raw expected at datasets/imu/tremordb/raw/ (zip unzipped, folder
effect-of-deep-brain-stimulation-on-parkinsonian-tremor-1.0.0/).
"""
import argparse
import csv
import glob
import os
import pickle
import re
import numpy as np

TARGET = {"g": "GPi", "v": "Vim", "s": "STN"}
ROW = re.compile(r"#\s+(\w+)\s+(\S+\.(let|rit))\s+([\d.]+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "imu", "tremordb")
    roots = glob.glob(os.path.join(base, "raw", "*effect-of-deep-brain*")) or \
        glob.glob(os.path.join(base, "raw"))
    root = roots[0]
    heas = sorted(glob.glob(os.path.join(root, "*", "*.hea")))
    if not heas:
        raise SystemExit(f"no .hea under {root}; unzip tremordb.zip first")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)
    recs, audit, table = [], [], []
    for hea in heas:
        gdir = os.path.dirname(hea)
        group = os.path.basename(gdir)                       # e.g. ronl, r15ofh
        txt = open(hea, errors="replace").read()
        cond = re.search(r"#\s*(?:REST TREMOR|.*?TREMOR).*?CONDITION:\s*([^\n]+)", txt)
        cond = cond.group(1).strip() if cond else ""
        cohort = {"h": "high_amplitude", "l": "low_amplitude"}.get(group[-1], "?")
        for m in ROW.finditer(txt):
            subj, fn, ext, rng, unit, laser, rate, nsamp = m.groups()
            path = os.path.join(gdir, fn)
            notes = []
            if not os.path.exists(path):
                audit.append([group, fn, subj, "MISSING FILE", ""])
                continue
            vals = np.asarray(open(path).read().split(), dtype=float)
            if len(vals) != int(nsamp):
                notes.append(f"n={len(vals)} != header {nsamp}")
            u = unit.strip().lower()
            if u == "m/s":
                sig, out_unit = vals * 1000.0, "mm/s"
            elif u == "mm/s":
                sig, out_unit = vals, "mm/s"
            else:
                sig, out_unit = vals, u
                notes.append(f"unit '{unit}' kept as is")
            fs = float(rate)
            if fs != 100.0:
                notes.append(f"rate {fs}")
            side = "R" if ext == "rit" else "L"
            ns = f"tremordb:{subj}"
            recs.append({"signal": sig.astype(np.float32)[:, None],
                         "unit": out_unit, "kind": "laser_doppler_velocity",
                         "fps": fs, "subject_ns": ns, "task": group,
                         "condition_verbatim": cond, "cohort": cohort,
                         "side": side, "dbs_target": TARGET.get(subj[0], "?"),
                         "range_V": float(rng), "laser_setting": laser,
                         "source": "tremordb", "n_frames": int(len(sig))})
            table.append([ns, TARGET.get(subj[0], "?"), cohort, group, cond, side,
                          len(sig), round(float(np.median(np.abs(sig))), 3)])
            audit.append([group, fn, subj,
                          f"T={len(sig)} unit={out_unit} med|v|="
                          f"{np.median(np.abs(sig)):.3f}", "; ".join(notes)])
    pickle.dump(recs, open(os.path.join(outd, "tremordb_velocity.pkl"), "wb"))
    with open(os.path.join(outd, "tremordb_subject_table.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_ns", "dbs_target", "cohort", "group", "condition",
                    "side", "n_samples", "median_abs_mm_s"])
        w.writerows(table)
    with open(os.path.join(outd, "tremordb_ingest_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "file", "subject", "result", "notes"])
        w.writerows(audit)
    subs = {r["subject_ns"] for r in recs}
    print(f"{len(recs)} velocity records / {len(subs)} subjects / "
          f"{len(heas)} condition groups")
    print("-> processed/tremordb_velocity.pkl + subject table + audit")


if __name__ == "__main__":
    main()
