# -*- coding: utf-8 -*-
"""Ingest the Goodwin SMM accelerometry (UbiComp 2014) into the
canonical IMU contract. INTERNAL-ONLY (no data licence exists; owner GO
2026-09-01 with that standing restriction; mmasd precedent).

Source layout (verified on disk 2026-09-01):
  raw/data/Study1/URI-<subj>-<MM-DD-YY>/MITes_XX_RawCorrectedData_<Loc>.RAW_DATA.csv
  raw/data/Study2/<subj>-<YYYY-MM-DD>/Wocket_XX_RawCorrectedData_<Loc>.csv
  columns: epoch_ms, raw_x, raw_y, raw_z (no header). Annotations per
  session as Annotator*Stereotypy.annotation.xml (datetime intervals:
  Rock / Flap / Flap-Rock / Good Data).

UNITS, established by MEASUREMENT (sixmwt calm-window method):
- MITes: the instruction doc declares 0-512 counts spanning +/-2g, but
  the calm-window gravity reads 64.3 counts (median over files, range
  60-81), i.e. 0-512 spans +/-4g. THE MEASUREMENT WINS and the
  declaration discrepancy is recorded (semg S01/S21 precedent).
  Scale: g = (count - 256) / 64.
- Wockets: declared 0-1023 spanning +/-4g (128 counts/g); measured
  calm gravity is 98.3 counts (range 91-110), consistent with known
  per-device Wockets calibration spread. Scale is measured PER FILE
  from that file's own calm-window gravity (accepted band 80-120
  counts/g, refused outside), factor recorded in the audit.

SAMPLING: per-row epoch-ms timestamps are jittery; fps = 1/median(dt)
measured per file; jitter p95 recorded. Signals are stored at native
irregular sampling with their measured nominal fps (the contract's
native-rate rule; no resampling).

SUBJECTS: the same six people appear in Study1 (URI-001..006, 2008)
and Study2 (001..006, 2010-2011) three years apart (the paper's own
design); URI- is stripped so one person = one subject_ns across both
studies and can never straddle a split. Study is kept in the task.

ANNOTATIONS: parsed verbatim to processed/annotations/<session>.csv
(label, start_dt, stop_dt, annotator). They are wall-clock datetimes
while sensor rows are epoch-ms; the observed offset is NOT a clean
timezone shift, so no alignment is fabricated here: aligning is a
label-use step with its own verification. Labels are eval-only (R1).

Outputs (datasets/imu/goodwin_smm/processed/):
  canonical_imu.pkl, goodwin_ingest_audit.csv, annotations/*.csv,
  ../../_canonical_imu_manifest_goodwin_smm.csv

Usage: python ingest_goodwin_smm.py [--repo PATH] [--dry]
"""
import argparse
import csv
import glob
import os
import pickle
import re
import xml.etree.ElementTree as ET

import numpy as np

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R",
             "thigh_L", "thigh_R", "shank_L", "shank_R", "ankle_L",
             "ankle_R", "foot_L", "foot_R", "pocket"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
LOC_MAP = {"trunk": "trunk", "torso": "trunk",
           "left-wrist": "wrist_L", "right-wrist": "wrist_R"}
MITES_CENTER, MITES_PER_G = 256.0, 64.0
WOCKET_CENTER = 512.0
WOCKET_BAND = (80.0, 120.0)


def calm_gravity(nrm, fs, window_s=1.0, quietest_frac=0.05):
    w = max(4, int(window_s * fs))
    m = (len(nrm) // w) * w
    if m < w * 4:
        return float(np.median(nrm))
    win = nrm[:m].reshape(-1, w)
    k = max(1, int(len(win) * quietest_frac))
    calm = win[np.argsort(win.std(axis=1))[:k]]
    return float(np.median(calm))


def parse_annotations(session_dir, outdir, session):
    rows = []
    for xml in sorted(glob.glob(os.path.join(
            session_dir, "Annotator*Stereotypy.annotation.xml"))):
        annotator = os.path.basename(xml).split("Stereotypy")[0]
        try:
            root = ET.parse(xml).getroot()
        except ET.ParseError as e:
            rows.append([annotator, "PARSE_ERROR", str(e), ""])
            continue
        for ann in root.iter("ANNOTATION"):
            label = (ann.findtext("LABEL") or "").strip()
            rows.append([annotator, label,
                         (ann.findtext("START_DT") or "").strip(),
                         (ann.findtext("STOP_DT") or "").strip()])
    if rows:
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, session + ".csv"), "w",
                  newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["annotator", "label", "start_dt", "stop_dt"])
            w.writerows(rows)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    base = os.path.join(args.repo, "datasets", "imu", "goodwin_smm")
    outd = os.path.join(base, "processed")
    annd = os.path.join(outd, "annotations")
    os.makedirs(outd, exist_ok=True)

    recs, manifest, audit = [], [], []
    for study, pattern, center in (
            ("study1", "Study1/*/MITes_*RawCorrectedData_*.csv", MITES_CENTER),
            ("study2", "Study2/*/Wocket_*RawCorrectedData_*.csv",
             WOCKET_CENTER)):
        files = sorted(glob.glob(os.path.join(
            base, "raw", "data", pattern.replace("/", os.sep))))
        print(f"{study}: {len(files)} sensor files")
        seen_sessions = set()
        for path in files:
            session = os.path.basename(os.path.dirname(path))
            fname = os.path.basename(path)
            m = re.match(r"(?:URI-)?(\d+)", session)
            subj = f"goodwin_smm:{int(m.group(1)):03d}" if m else None
            locm = re.search(r"RawCorrectedData_([A-Za-z-]+?)(?:\.RAW_DATA)?\.csv$",
                             fname)
            loc = LOC_MAP.get((locm.group(1) or "").lower()) if locm else None
            notes = []
            if not subj or not loc:
                audit.append([study, session, fname, "", "", "", "",
                              "SKIP: subject or location unparsed"])
                continue
            if session not in seen_sessions:
                seen_sessions.add(session)
                n_ann = parse_annotations(os.path.dirname(path), annd,
                                          session)
                if n_ann == 0:
                    notes.append("no annotation intervals in session")
            try:
                rows = np.loadtxt(path, delimiter=",")
            except Exception as e:
                audit.append([study, session, fname, subj, "", "", "",
                              f"UNREADABLE: {e}"])
                continue
            if rows.ndim != 2 or rows.shape[1] != 4 or len(rows) < 600:
                audit.append([study, session, fname, subj, "", "", "",
                              f"REFUSED: shape {rows.shape}, expected "
                              "(T>=600, 4)"])
                continue
            t_ms, xyz = rows[:, 0], rows[:, 1:4]
            dt = np.diff(t_ms)
            dt = dt[(dt > 0) & (dt < 1000)]
            if len(dt) < 100:
                audit.append([study, session, fname, subj, "", "", "",
                              "REFUSED: unusable timestamps"])
                continue
            fs = 1000.0 / float(np.median(dt))
            jitter_p95 = float(np.percentile(dt, 95))
            v = xyz - center
            nrm = np.linalg.norm(v, axis=1)
            gcalm = calm_gravity(nrm, fs)
            if study == "study1":
                per_g = MITES_PER_G
                if not (0.85 <= gcalm / per_g <= 1.15):
                    notes.append(f"calm gravity {gcalm:.1f} counts vs the "
                                 f"study-level {per_g}/g: outside 15%, "
                                 "KEPT with flag")
            else:
                per_g = gcalm
                if not (WOCKET_BAND[0] <= per_g <= WOCKET_BAND[1]):
                    audit.append([study, session, fname, subj,
                                  f"{fs:.2f}", f"{gcalm:.1f}", "",
                                  "REFUSED: per-file gravity "
                                  f"{gcalm:.1f} counts/g outside "
                                  f"{WOCKET_BAND}; calibration "
                                  "undetermined, not guessed"])
                    print(f"  {session}/{fname}: REFUSED "
                          f"(gravity {gcalm:.1f})")
                    continue
            acc_g = v / per_g
            T = len(acc_g)
            sig = np.zeros((T, 1, 9), np.float32)
            sig[:, 0, 0:3] = acc_g
            cmask = np.zeros((1, 9), bool)
            cmask[0, :3] = True
            task = f"smm_{study}_{session}"
            recs.append({"signal": sig,
                         "location_ids": np.array([LOC_I[loc]]),
                         "channel_mask": cmask, "fps": fs,
                         "subject_ns": subj, "task": task,
                         "source": "goodwin_smm", "n_frames": int(T),
                         "acc_content": "with_gravity",
                         "t_epoch_ms_first": float(t_ms[0]),
                         "t_epoch_ms_last": float(t_ms[-1]),
                         "counts_per_g": float(per_g)})
            manifest.append(["goodwin_smm", subj, task,
                             round(fs, 3), int(T), loc])
            audit.append([study, session, fname, subj, f"{fs:.2f}",
                          f"{gcalm:.1f}", f"{per_g:.1f}",
                          f"dur={T / fs / 60:.1f}min loc={loc} "
                          f"jitter_p95={jitter_p95:.0f}ms "
                          + ("; ".join(notes) if notes else "ok")])
        print(f"  {study}: sessions={len(seen_sessions)}")

    print(f"{len(recs)} canonical IMU records / "
          f"{len({r['subject_ns'] for r in recs})} subjects")
    if not args.dry:
        with open(os.path.join(outd, "canonical_imu.pkl"), "wb") as f:
            pickle.dump(recs, f)
        mp = os.path.join(args.repo, "datasets",
                          "_canonical_imu_manifest_goodwin_smm.csv")
        with open(mp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["source", "subject_ns", "task", "fps",
                        "n_frames", "locations"])
            w.writerows(manifest)
        ap_ = os.path.join(outd, "goodwin_ingest_audit.csv")
        with open(ap_, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["study", "session", "file", "subject_ns", "fs",
                        "calm_gravity_counts", "counts_per_g", "notes"])
            w.writerows(audit)
        print(f"wrote {mp}")


if __name__ == "__main__":
    main()
