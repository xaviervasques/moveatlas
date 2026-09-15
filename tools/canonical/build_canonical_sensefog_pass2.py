# -*- coding: utf-8 -*-
"""SenseFOG canonical pass 2 (Mendeley c9ckcvjxc7, CC BY 4.0; documentation
repo github.com/PKlocke/SenseFOG-Documentation, CC BY 4.0). Three tasks,
each refusing rather than guessing (house rule: better unknown than wrong).

Task A - FOG label arrays on the pass-1 EEG + EMG records
  Source: Matlab_scripts/A) Subject Files/sub-XX-datafile.m, the hand-set
  `subjectdata.events_filt.<Session>(i).start/.end/.task` segments (seconds)
  and the manual alignment samples `subjectdata.signalpoint.<Session>.
  EEG_signal / .LFP_signal`.
  Clock of the segment seconds, established from the authors' scripts and
  confirmed empirically (see clock_check rows of pass2_audit.csv):
    * 1.5_Data_Alignment.m line 100 cuts the raw EEG at the first 'M  1'
      marker (the start of the IMU recording, lines 75-76):
          EEG_pre_signal = EEG_File.dat.dataset(:,(sample_M1(1,1):end));
      then, ONLY when EEG_signal > LFP_signal (line 146), cuts EEG_pre_signal
      again by `delay` = EEG_signal - LFP_signal (line 147); otherwise the LFP
      is cut (lines 140-142) and the EEG stays EEG_pre_signal.
    * 1.6_Sub_GrandActivity_Log.m lines 82-88 apply the SAME correction to
      the segment seconds, in the same branch only:
          if subjectdata.signalpoint.(name).EEG_signal > ...LFP_signal == 1
              ...events_filt.(name)(i).start = ...start - (signaldelay/fs_eeg)
      so the segment seconds are expressed on EEG_pre_signal (raw EEG after
      the M1 cut, before the delay cut) = the native IMU clock. Relative to
      the raw EEG the delay cancels in both branches; the only offset is M1.
    * The time vectors are MATLAB 1-based (1.5 line 101: sample k at k/fs),
      so segment time t is EEG_pre sample k = t*1000 (1-based) = raw sample
      k + M1 - 1 (1-based) = raw 0-based frame t*1000 + M1 - 2.
  Codes: 0 unlabelled, 1 Walk, 2 Selected_stop, 3 Freezing_walk,
  4 Freezing_walk_initiation. Only the exact task tokens 1.6 selects with
  ismember() are honoured; the spelling variants 'Selected stop' (sub-15)
  and 'Selected_stop_start' (sub-11) were ignored by the authors' pipeline
  and are refused here (counted). Segments with end <= start are refused.
  Overlaps of different codes are set to 0 and counted.

Task B - APDM Opal .h5 -> canonical imu (moveatlas-record/1 list container)
  Layout read from the file: root attrs CaseIdList / MonitorLabelList
  (index-aligned, as 1.4_Import_HDF.m lines 25-27 read them), per-sensor
  group <CaseId>/Calibrated/{Accelerometers,Gyroscopes,Magnetometers} with
  explicit Units attributes (m/s^2, rad/s, microtesla) and SampleRate.
  Conversions to the contract units are applied ONLY because the units are
  explicit: acc / 9.80665 -> g, gyro * 180/pi -> deg/s, mag * 1 -> uT.
  Locations: 'Lumbar' -> lower_back; 'Left Leg'/'Left Foot' -> ankle_L and
  'Right Leg'/'Right Foot' -> ankle_R per the documentation README line 94
  ("attached to both left and right ankles and lumbar spine (L5)"); the h5
  label is kept verbatim per location. Any other label is refused.

Task C - Percept BrainSenseTimeDomain -> aux streams only (no family)
  Per session one processed/aux/<rid>_lfp.npz: per packet the raw
  TimeDomainData (no unit is declared in the JSON -> unit "unknown", Gain
  recorded), 250 Hz, channel, FirstPacketDateTime, and a per-sample validity
  mask rebuilt from TicksInMses (250 ms ticks; a gap of g ms inserts g/4
  masked samples) cross-checked with GlobalSequences; Stimulation and
  LeadConfiguration ride as metadata.

Outputs: processed/pass2_audit.csv, processed/canonical_imu.npz, aux/*_lfp.npz,
re-saved canonical_eeg/*.npz + canonical_emg/*.npz (labelled sessions only,
every non-label field verified identical), rows of source sensefog in
datasets/_canonical_imu_manifest.csv.
Usage: python build_canonical_sensefog_pass2.py [--repo PATH] [--skip-clock-check]
       or python build_canonical_sensefog.py --pass2
"""
import argparse
import csv
import glob
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moveatlas import records                      # noqa: E402
from moveatlas.frames import IMU_LOCATIONS         # noqa: E402
from build_canonical_eeg import sanitize           # noqa: E402
from build_canonical_sensefog import SESSION_TASK, merge_manifest  # noqa: E402

FS_EEG = 1000.0                                    # 1.5_Data_Alignment.m line 41
# session folder -> the struct field name of the subject files
# (1.5_Data_Alignment.m lines 128-133)
SESSION_KEY = {"ses-sitting": "Sit", "ses-standing": "Stand", "ses-walk": "Walk",
               "ses-walkws": "WalkWS", "ses-walkint": "WalkINT",
               "ses-walkint2": "WalkINT_new"}
TASK_SESSION = {v: k for k, v in SESSION_TASK.items()}
LABEL_CODES = {"0": "unlabelled", "1": "Walk", "2": "Selected_stop",
               "3": "Freezing_walk", "4": "Freezing_walk_initiation"}
TASK_CODE = {v: int(k) for k, v in LABEL_CODES.items() if k != "0"}
DOC_REPO = os.path.join("datasets", "eeg", "sensefog", "raw", "_doc_repo")
SUBJECT_FILES = os.path.join(DOC_REPO, "Matlab_scripts", "A) Subject Files")
RAW = os.path.join("datasets", "eeg", "sensefog", "raw", "SenseFOG-main")
G0 = 9.80665                                       # configs/canonical_imu.yaml: m/s2 -> /9.80665
H5_LOCATION = {"Lumbar": "lower_back", "Left Leg": "ankle_L", "Left Foot": "ankle_L",
               "Right Leg": "ankle_R", "Right Foot": "ankle_R"}
TICK_MS = 250                                      # Percept BrainSense TD packet period


# ----------------------------------------------------------------- subject files
def parse_subject_file(path):
    """Regex parser for the MATLAB assignments of sub-XX-datafile.m. Comments
    (%) are stripped first so commented-out segments never enter."""
    body = "\n".join(ln.split("%")[0] for ln in
                     open(path, encoding="utf-8", errors="replace"))
    sp = {}
    for s, k, v in re.findall(
            r"subjectdata\.signalpoint\.(\w+)\.(EEG_signal|LFP_signal)"
            r"\s*=\s*([-+\d.eE]+)\s*;", body):
        sp.setdefault(s, {})[k] = int(float(v))
    segs = {}
    for s, i, k, v in re.findall(
            r"subjectdata\.events_filt\.(\w+)\((\d+)\)\.(start|end|task)"
            r"\s*=\s*('[^']*'|[-+\d.eE]+)\s*;", body):
        d = segs.setdefault(s, {}).setdefault(int(i), {"index": int(i)})
        d[k] = v.strip("'") if k == "task" else float(v)
    # any events_filt assignment the regex did not catch is a refusal of the
    # whole file (nothing guessed)
    other = [ln.strip() for ln in body.splitlines()
             if "events_filt" in ln and "=" in ln and "struct" not in ln
             and not re.search(r"events_filt\.\w+\(\d+\)\.(start|end|task)\s*=", ln)]
    if other:
        raise ValueError(f"{os.path.basename(path)}: unparsed events_filt lines {other}")
    for s in sp:
        e, l = sp[s].get("EEG_signal"), sp[s].get("LFP_signal")
        if e is None or l is None:
            raise ValueError(f"{os.path.basename(path)}: incomplete signalpoint {s}")
        # the datafile's own rule (sub-XX-datafile.m lines 23-27): delay = |EEG - LFP|
        sp[s]["delay"] = abs(e - l)
        sp[s]["cut"] = "EEG" if e > l else "LFP"
    return {"signalpoint": sp,
            "segments": {s: [v[i] for i in sorted(v)] for s, v in segs.items()}}


def load_subject_files(repo):
    out = {}
    for p in sorted(glob.glob(os.path.join(repo, SUBJECT_FILES, "sub-*-datafile.m"))):
        sub = re.match(r"(sub-\d+)-datafile\.m", os.path.basename(p)).group(1)
        out[sub] = parse_subject_file(p)
    return out


def classify_segments(segs):
    """Split a session's segments into (accepted, refused-with-reason)."""
    ok, bad = [], []
    for s in segs:
        if not {"start", "end", "task"} <= set(s):
            bad.append((s, "incomplete (missing start/end/task)"))
        elif s["task"] not in TASK_CODE:
            bad.append((s, f"task token {s['task']!r} is not one of "
                           f"{sorted(TASK_CODE)} (1.6 ismember would not select it)"))
        elif not (s["end"] > s["start"]):
            bad.append((s, f"end {s['end']} <= start {s['start']}"))
        else:
            ok.append(s)
    return ok, bad


# ----------------------------------------------------------------------- vmrk
def first_m1_sample(vmrk_path):
    """1-based position of the first 'M  1' (Moblab) marker, the sample the
    authors cut the EEG at (1.5 lines 78-80: strcmp('M  1'), sample_M1(1))."""
    with open(vmrk_path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            m = re.match(r"Mk\d+=([^,]*),([^,]*),(\d+),", ln)
            if m and m.group(2) == "M  1":
                return int(m.group(3))
    return None


def session_dir(repo, subj, ses):
    return os.path.join(repo, RAW, subj, ses)


def vmrk_of(repo, subj, ses):
    c = glob.glob(os.path.join(session_dir(repo, subj, ses), "eeg", "*.vmrk"))
    return c[0] if len(c) == 1 else None


# --------------------------------------------------------------------- Task A
def label_array(n, segments, m1, fs=FS_EEG):
    """int8 label on the raw EEG frame axis. Segment time t -> 0-based frame
    round(t*fs) + m1 - 2 (derivation in the module docstring). Returns the
    array, per-code frame counts, clipped-frame count, conflict-frame count."""
    lab = np.zeros(n, np.int8)
    conflict = np.zeros(n, bool)
    clipped = 0
    for s in segments:
        code = TASK_CODE[s["task"]]
        i0 = int(round(s["start"] * fs)) + m1 - 2
        i1 = int(round(s["end"] * fs)) + m1 - 2           # inclusive (MATLAB start:stop)
        j0, j1 = max(i0, 0), min(i1, n - 1)
        clipped += (j0 - i0) + (i1 - j1)
        if j1 < j0:
            clipped += 0
            continue
        region = lab[j0:j1 + 1]
        conflict[j0:j1 + 1] |= (region != 0) & (region != code)
        region[:] = code
    lab[conflict] = 0
    counts = {k: int((lab == int(k)).sum()) for k in LABEL_CODES if k != "0"}
    return lab, counts, clipped, int(conflict.sum())


def task_a(repo, subject_files, audit):
    base = os.path.join(repo, "datasets", "eeg", "sensefog", "processed")
    n_lab = n_none = 0
    for fam in ("canonical_eeg", "canonical_emg"):
        for path in sorted(glob.glob(os.path.join(base, fam, "*.npz"))):
            rec = records.load(path)
            # idempotent: a record labelled by an earlier pass-2 run is relabelled
            # from scratch, so the identity check below sees pass-1 fields only
            rec = {k: v for k, v in rec.items()
                   if k not in ("label_codes", "label_source", "label_note")}
            subj = rec["subject_ns"].split(":", 1)[1]
            ses = TASK_SESSION[rec["task"]]
            key = SESSION_KEY[ses]
            rid = os.path.basename(path)[:-4]
            sf = subject_files.get(subj)
            if sf is None:
                audit.append(["A", rec["subject_ns"], ses, rid, "label None",
                              0, 0, "no subject file in the documentation repo"])
                n_none += 1
                continue
            segs = sf["segments"].get(key, [])
            ok, bad = classify_segments(segs)
            for s, why in bad:
                audit.append(["A", rec["subject_ns"], ses, rid, "segment refused", 0, 1,
                              f"{key}({s['index']}) {s}: {why}"])
            if not ok:
                audit.append(["A", rec["subject_ns"], ses, rid, "label None", 0, len(bad),
                              "no events_filt segments for this session"
                              if not segs else "every segment refused"])
                n_none += 1
                continue
            vmrk = vmrk_of(repo, subj, ses)
            m1 = first_m1_sample(vmrk) if vmrk else None
            if m1 is None:
                audit.append(["A", rec["subject_ns"], ses, rid, "label None", 0, len(ok),
                              "no 'M  1' marker in the .vmrk: the M1 cut of 1.5 line 100 "
                              "cannot be applied"])
                n_none += 1
                continue
            sp = sf["signalpoint"].get(key, {})
            n = int(rec["n_frames"])
            lab, counts, clipped, conflicts = label_array(n, ok, m1)
            rec2 = dict(rec)
            rec2["label"] = lab
            rec2["label_codes"] = dict(LABEL_CODES)
            rec2["label_source"] = (f"SenseFOG-Documentation {subj}-datafile.m, CC BY 4.0, "
                                    f"alignment sample {m1}")
            rec2["label_note"] = (
                "events_filt seconds are on the EEG-after-M1-cut clock "
                "(1.5_Data_Alignment.m line 100; 1.6_Sub_GrandActivity_Log.m "
                "lines 82-88); frame = round(t*1000) + M1 - 2 with M1 the "
                "1-based .vmrk position of the first 'M  1' marker; the EEG/LFP "
                f"delay ({sp.get('delay')} samples, {sp.get('cut')} cut) cancels "
                "on the raw EEG frame; conflicting overlaps set to 0")
            records.save(path, rec2)
            back = records.load(path)
            same = all(records.equal({k: rec[k]}, {k: back[k]}) for k in rec
                       if k != "label") and set(back) - set(rec) == {
                           "label_codes", "label_source", "label_note"} \
                and np.array_equal(back["label"], lab) and back["label"].dtype == np.int8
            if not same:
                raise RuntimeError(f"{rid}: re-saved record differs beyond the label fields")
            n_lab += 1
            audit.append(["A", rec["subject_ns"], ses, rid, "labelled", len(ok), len(bad),
                          f"M1={m1} delay={sp.get('delay')} cut={sp.get('cut')} "
                          f"frames Walk={counts['1']} Selected_stop={counts['2']} "
                          f"Freezing_walk={counts['3']} Freezing_walk_initiation={counts['4']} "
                          f"unlabelled={int((lab == 0).sum())} clipped={clipped} "
                          f"conflict={conflicts} of n={n}; non-label fields verified identical"])
            print(f"  A {rid}: {len(ok)} segments, M1={m1}, "
                  f"FOG frames={counts['3'] + counts['4']}, conflicts={conflicts}")
    # subject-file sessions that have no pass-1 record at all
    have = {(os.path.basename(p)[:-4]) for p in
            glob.glob(os.path.join(base, "canonical_eeg", "*.npz"))}
    for subj, sf in sorted(subject_files.items()):
        for key, segs in sf["segments"].items():
            ses = {v: k for k, v in SESSION_KEY.items()}[key]
            rid = sanitize(f"sensefog__sensefog:{subj}__{SESSION_TASK[ses]}")
            if rid not in have:
                audit.append(["A", f"sensefog:{subj}", ses, rid, "no pass-1 record",
                              0, len(segs), "session has no BrainVision EEG in the "
                              "deposit (derived .mat only); segments not placed"])
    return n_lab, n_none


# ------------------------------------------------------- clock check (evidence)
def clock_check(repo, subject_files, audit):
    """Evidence for the clock rule: the authors' reviewed heel-strike times
    (motion/*_gaitfilt_cor.mat, GaitEvents.rf_events/lf_events.Heelstrike_Loc
    + Heelstrike_Peak, used by 1.6 on the aligned clock) must land on the
    native h5 sagittal gyro (deg/s) when shifted by +delay/1000 in the
    EEG-cut branch and by 0 in the LFP-cut branch. Median |gyro - peak| is
    reported for shifts 0, +delay and -delay. Also counts heel strikes that
    fall inside Walk vs Freezing_walk segments under the native-clock reading
    of events_filt (HS + delay) versus the aligned reading (HS unshifted)."""
    try:
        import h5py
        import scipy.io as sio
    except ImportError as e:
        audit.append(["clock_check", "", "", "", "skipped", 0, 0, str(e)])
        return
    for p in sorted(glob.glob(os.path.join(repo, RAW, "sub-*", "ses-*", "motion",
                                           "*_gaitfilt_cor.mat"))):
        d = os.path.dirname(p)
        ses = os.path.basename(os.path.dirname(d))
        subj = os.path.basename(os.path.dirname(os.path.dirname(d)))
        h5s = glob.glob(os.path.join(d, "*.h5"))
        sf = subject_files.get(subj)
        key = SESSION_KEY[ses]
        if not h5s or sf is None or key not in sf["signalpoint"]:
            audit.append(["clock_check", f"sensefog:{subj}", ses, "", "skipped", 0, 0,
                          "no raw h5 or no signalpoint for this session"])
            continue
        sp = sf["signalpoint"][key]
        delay = sp["delay"] / FS_EEG if sp["cut"] == "EEG" else 0.0
        f = h5py.File(h5s[0], "r")
        cases = [c.decode() for c in f.attrs["CaseIdList"]]
        labs = [c.decode() for c in f.attrs["MonitorLabelList"]]
        lab = dict(zip(cases, labs))
        ge = sio.loadmat(p, squeeze_me=True, struct_as_record=False)["GaitEvents"]
        segs_ok, _ = classify_segments(sf["segments"].get(key, []))
        parts = []
        for side, fld in (("R", "rf_events"), ("L", "lf_events")):
            gid = next((c for c in cases if lab[c].startswith("Right" if side == "R" else "Left")), None)
            if gid is None:
                continue
            ev = np.atleast_1d(getattr(ge, fld))
            hs = np.array([e.Heelstrike_Loc for e in ev], float)
            pk = np.array([e.Heelstrike_Peak for e in ev], float)
            gy = np.degrees(f[gid]["Calibrated/Gyroscopes"][:, 1])
            fs = float(f[gid].attrs["SampleRate"])
            t = np.arange(1, len(gy) + 1) / fs        # MATLAB 1-based time vector
            errs = {}
            for name, sh in (("0", 0.0), ("+delay", delay), ("-delay", -delay)):
                v = np.interp(hs + sh, t, gy, left=np.nan, right=np.nan)
                errs[name] = float(np.nanmedian(np.abs(v - pk)))
            walk = [(s["start"], s["end"]) for s in segs_ok if s["task"] == "Walk"]
            fog = [(s["start"], s["end"]) for s in segs_ok if s["task"] == "Freezing_walk"]

            def inside(times, wins):
                return int(sum(any(a <= x <= b for a, b in wins) for x in times))
            parts.append(
                f"{side}={gid}({lab[gid]}) n_HS={len(hs)} |peak|med={np.median(np.abs(pk)):.0f} "
                f"err@0={errs['0']:.1f} err@+delay={errs['+delay']:.1f} "
                f"err@-delay={errs['-delay']:.1f}; HS in Walk/FOG native "
                f"{inside(hs + delay, walk)}/{inside(hs + delay, fog)} aligned "
                f"{inside(hs, walk)}/{inside(hs, fog)}")
        audit.append(["clock_check", f"sensefog:{subj}", ses, "", "evidence", 0, 0,
                      f"delay_s={delay:.3f} cut={sp['cut']}; " + " | ".join(parts)])
        print(f"  clock {subj}/{ses} delay={delay:.3f}s: " + " | ".join(parts))


# --------------------------------------------------------------------- Task B
def task_b(repo, subject_files, audit, manifest):
    try:
        import h5py
    except ImportError as e:
        audit.append(["B", "", "", "", "deferred", 0, 0, f"h5py not importable: {e}"])
        print("  B deferred: h5py missing")
        return []
    recs = []
    for h5 in sorted(glob.glob(os.path.join(repo, RAW, "sub-*", "ses-*", "motion", "*.h5"))):
        d = os.path.dirname(h5)
        ses = os.path.basename(os.path.dirname(d))
        subj = os.path.basename(os.path.dirname(os.path.dirname(d)))
        subject_ns = f"sensefog:{subj}"
        task = SESSION_TASK.get(ses, sanitize(ses))
        rid = sanitize(f"sensefog__{subject_ns}__{task}")
        rel = os.path.relpath(h5, repo).replace("\\", "/")
        f = h5py.File(h5, "r")
        cases = [c.decode() for c in f.attrs["CaseIdList"]]
        labs = [c.decode() for c in f.attrs["MonitorLabelList"]]
        if len(cases) != len(labs):
            audit.append(["B", subject_ns, ses, rid, "refused", 0, 1,
                          f"{rel}: CaseIdList/MonitorLabelList lengths differ"])
            continue
        placement, refused = [], []
        for cid, lb in zip(cases, labs):
            loc = H5_LOCATION.get(lb)
            if loc is None:
                refused.append(f"{cid} label {lb!r} has no grid slot")
            elif cid not in f:
                refused.append(f"{cid} ({lb}) listed but no group in the file")
            else:
                placement.append({"location": loc, "location_id": IMU_LOCATIONS.index(loc),
                                  "case_id": cid, "h5_label": lb})
        for r in refused:
            audit.append(["B", subject_ns, ses, rid, "location refused", 0, 1, r])
        if not placement:
            audit.append(["B", subject_ns, ses, rid, "refused", 0, 1, "no usable sensor"])
            continue
        if len({p["location"] for p in placement}) != len(placement):
            audit.append(["B", subject_ns, ses, rid, "refused", 0, 1,
                          "two sensors map onto one grid slot"])
            continue
        placement.sort(key=lambda p: p["location_id"])
        # sampling rate and co-sampling
        rates = {int(f[p["case_id"]].attrs["SampleRate"]) for p in placement}
        lens = {f[p["case_id"]]["Calibrated/Accelerometers"].shape[0] for p in placement}
        if len(rates) != 1 or len(lens) != 1:
            audit.append(["B", subject_ns, ses, rid, "refused", 0, 1,
                          f"sensors not co-sampled: rates {rates} lengths {lens}"])
            continue
        fs, n = float(rates.pop()), int(lens.pop())
        sig = np.zeros((n, len(placement), 9), np.float32)
        cmask = np.zeros((len(placement), 9), bool)
        units_seen, glitches, nan_rows = {}, [], 0
        for li, p in enumerate(placement):
            g = f[p["case_id"]]
            blocks = (("Accelerometers", "AccelerometersEnabled", 0, {"m/s^2": 1.0 / G0}),
                      ("Gyroscopes", "GyroscopesEnabled", 3, {"rad/s": 180.0 / math.pi}),
                      ("Magnetometers", "MagnetometersEnabled", 6, {"microtesla": 1.0}))
            for name, flag, c0, conv in blocks:
                if int(g.attrs.get(flag, 1)) != 1 or f"Calibrated/{name}" not in g:
                    continue                          # channel absent -> mask stays False
                ds = g[f"Calibrated/{name}"]
                unit = ds.attrs["Units"].decode() if "Units" in ds.attrs else None
                if unit not in conv:
                    audit.append(["B", subject_ns, ses, rid, "channel refused", 0, 1,
                                  f"{p['case_id']} {name}: unit {unit!r} not explicit/known"])
                    continue
                x = ds[:].astype(np.float64) * conv[unit]
                bad = ~np.isfinite(x).all(axis=1)
                nan_rows += int(bad.sum())
                x[bad] = 0.0
                sig[:, li, c0:c0 + 3] = x
                cmask[li, c0:c0 + 3] = True
                units_seen[name] = unit
                p[f"{name.lower()}_unit_in_file"] = unit
                if "Gravity" in ds.attrs:
                    p["gravity_attr"] = float(ds.attrs["Gravity"])
                if "Range" in ds.attrs:
                    p[f"{name.lower()}_range"] = ds.attrs["Range"].decode()
            t = g["Time"][:].astype(np.int64)
            dt = np.diff(t)
            odd = np.where((dt < 7812) | (dt > 7813))[0]
            if odd.size:
                glitches.append(f"{p['case_id']}: {odd.size} Time steps outside 7812-7813 us "
                                f"at {odd[:4].tolist()} (net {int(dt[odd].sum() - 7812.5 * odd.size)} us)")
        finite = np.isfinite(sig)                      # NaN rows were zeroed above
        sample_valid = np.ones((n, len(placement)), bool)
        for li, p in enumerate(placement):
            g = f[p["case_id"]]
            for name, c0 in (("Accelerometers", 0), ("Gyroscopes", 3), ("Magnetometers", 6)):
                if cmask[li, c0] and f"Calibrated/{name}" in g:
                    raw = g[f"Calibrated/{name}"][:]
                    sample_valid[:, li] &= np.isfinite(raw).all(axis=1)
        # events copy: the segment seconds are on the native IMU clock
        key = SESSION_KEY[ses]
        sf = subject_files.get(subj)
        events, ev_note = [], ""
        if sf is not None and sf["segments"].get(key):
            ok, bad = classify_segments(sf["segments"][key])
            events = [{"onset_s": s["start"], "offset_s": s["end"], "task": s["task"],
                       "code": TASK_CODE[s["task"]]} for s in ok]
            ev_note = (f"{len(ok)} events_filt segments of {subj}-datafile.m ({key}), "
                       f"{len(bad)} refused (see pass2_audit.csv); seconds verbatim on "
                       "the native IMU clock (= EEG after the M1 cut; 1.6 lines 82-88): "
                       "the authors' 1-based time vector puts sample k at k/1000 s")
        elif sf is None:
            ev_note = "no subject file in the documentation repo"
        else:
            ev_note = "no events_filt segments for this session"
        vmrk = vmrk_of(repo, subj, ses)
        m1 = first_m1_sample(vmrk) if vmrk else None
        rec = {"signal": sig, "location_ids": np.array([p["location_id"] for p in placement],
                                                       np.int64),
               "channel_mask": cmask, "fps": fs, "subject_ns": subject_ns, "task": task,
               "source": "sensefog", "n_frames": n, "label": None,
               "units": {"acc": "g", "gyro": "deg_per_s", "mag": "uT"},
               "unit_factors": {"acc": f"m/s^2 / {G0} (unit explicit in the h5)",
                                "gyro": "rad/s * 180/pi (unit explicit in the h5)",
                                "mag": "microtesla * 1 (unit explicit in the h5)"},
               "placement": placement,
               "placement_source": "h5 root attrs CaseIdList/MonitorLabelList (index-aligned, "
                                   "1.4_Import_HDF.m lines 25-27); ankle per the "
                                   "SenseFOG-Documentation README line 94",
               "sensor": "APDM Opal, Calibrated group, wireless streaming",
               "raw_file": rel, "events": events, "events_note": ev_note,
               "eeg_m1_sample": m1,
               "clock_note": "sample 0 = the EEG 'M  1' marker (1.5_Data_Alignment.m "
                             "lines 75-76 and 100); no resampling"}
        if not sample_valid.all():
            rec["sample_valid"] = sample_valid
            rec["dropout_fraction"] = float(1.0 - sample_valid.mean())
        if glitches:
            rec["time_column_note"] = ("; ".join(glitches) + "; sample counts identical "
                                       "across sensors, samples kept co-indexed as in 1.4")
        recs.append(rec)
        manifest.append(["sensefog", subject_ns, task, fs, n,
                         "|".join(p["location"] for p in placement)])
        audit.append(["B", subject_ns, ses, rid, "imu record", len(placement), len(refused),
                      f"fs={fs:g} n={n} locations={[p['location'] for p in placement]} "
                      f"labels={[p['h5_label'] for p in placement]} units={units_seen} "
                      f"nan_rows_zeroed={nan_rows} events={len(events)} "
                      f"time_glitches={len(glitches)} M1={m1}"])
        print(f"  B {rid}: {n} @ {fs:g} Hz, {[p['h5_label'] for p in placement]}, "
              f"events {len(events)}, nan rows {nan_rows}")
    return recs


# --------------------------------------------------------------------- Task C
def rebuild_axis(pk):
    """Samples + validity mask on a 250 Hz axis rebuilt from TicksInMses:
    packets are concatenated in order; a tick gap of g ms (> 250) inserts
    g/4 masked samples. GlobalSequences (0-255, skipping one value every
    fourth packet by design) are cross-checked: a jump beyond that pattern
    without a tick gap is reported. Returns (signal, valid, stats)."""
    seq = np.array([int(x) for x in pk["GlobalSequences"].split(",") if x != ""])
    siz = np.array([int(x) for x in pk["GlobalPacketSizes"].split(",") if x != ""])
    tic = np.array([int(x) for x in pk["TicksInMses"].split(",") if x != ""])
    x = np.asarray(pk["TimeDomainData"], np.float32)
    stats = {"n_packets": int(len(tic)), "n_samples_raw": int(x.size),
             "sizes_sum_matches": bool(siz.sum() == x.size),
             "n_lost_ticks": 0, "n_masked_samples": 0, "size_anomalies": [],
             "tick_anomalies": [], "seq_anomalies": [], "wrap_events": 0}
    if not (len(seq) == len(siz) == len(tic)) or siz.sum() != x.size:
        stats["refused"] = "sequence/size/tick lists or sample count inconsistent"
        return None, None, stats
    out, val = [], []
    pos = 0
    for k in range(len(tic)):
        if k:
            gap = int(tic[k] - tic[k - 1])
            ds = int((seq[k] - seq[k - 1]) % 256)
            if gap < 0 or gap % TICK_MS:
                stats["tick_anomalies"].append((k, gap))
            elif gap > TICK_MS:
                lost = gap // TICK_MS - 1
                fill = (gap - TICK_MS) * 250 // 1000            # 62.5 samples per lost tick
                stats["n_lost_ticks"] += lost
                stats["n_masked_samples"] += fill
                out.append(np.zeros(fill, np.float32))
                val.append(np.zeros(fill, bool))
                if ds not in (lost + 1, lost + 2):
                    stats["seq_anomalies"].append((k, ds, lost))
            elif ds not in (1, 2):
                stats["seq_anomalies"].append((k, ds, 0))
            if seq[k] < seq[k - 1]:
                stats["wrap_events"] += 1
        s = int(siz[k])
        if s not in (62, 63):
            stats["size_anomalies"].append((k, s))
        out.append(x[pos:pos + s])
        val.append(np.ones(s, bool))
        pos += s
    sig, v = np.concatenate(out), np.concatenate(val)
    stats["n_samples_axis"] = int(sig.size)
    stats["masked_fraction"] = float(1.0 - v.mean())
    stats["tick_span_s"] = float((tic[-1] - tic[0] + TICK_MS) / 1000.0)
    return sig, v, stats


def task_c(repo, audit):
    aux_dir = os.path.join(repo, "datasets", "eeg", "sensefog", "processed", "aux")
    os.makedirs(aux_dir, exist_ok=True)
    n_files = 0
    for js in sorted(glob.glob(os.path.join(repo, RAW, "sub-*", "ses-*", "ieeg", "*.json"))):
        d = os.path.dirname(js)
        ses = os.path.basename(os.path.dirname(d))
        subj = os.path.basename(os.path.dirname(os.path.dirname(d)))
        subject_ns = f"sensefog:{subj}"
        task = SESSION_TASK.get(ses, sanitize(ses))
        rid = sanitize(f"sensefog__{subject_ns}__{task}")
        rel = os.path.relpath(js, repo).replace("\\", "/")
        dd = json.load(open(js, encoding="utf-8"))
        td = dd.get("BrainSenseTimeDomain") or []
        if not td:
            audit.append(["C", subject_ns, ses, rid, "no BrainSenseTimeDomain", 0, 1,
                          f"{rel}: keys {sorted(dd)[:8]}..."])
            continue
        streams, refused = [], 0
        for k, pk in enumerate(td):
            sig, v, st = rebuild_axis(pk)
            if sig is None:
                refused += 1
                audit.append(["C", subject_ns, ses, rid, "packet refused", 0, 1,
                              f"packet {k} {pk.get('Channel')}: {st['refused']}"])
                continue
            fs = float(pk.get("SampleRateInHz"))
            streams.append({"label": pk.get("Channel"), "kind": "lfp_bipolar_stn",
                            "signal": sig, "valid": v, "fs": fs,
                            "unit": "unknown", "gain": pk.get("Gain"),
                            "unit_note": "TimeDomainData verbatim; the JSON declares no "
                                         "unit for it, Gain recorded as shipped",
                            "first_packet_datetime": pk.get("FirstPacketDateTime"),
                            "pass": pk.get("Pass"), "n_frames": int(sig.size),
                            "tick_ms_first": int(pk["TicksInMses"].split(",")[0]),
                            "axis_note": "250 ms ticks (TicksInMses); lost ticks masked "
                                         "(valid=False, signal 0); packets concatenated "
                                         "verbatim, so packet sizes outside 62/63 shift "
                                         "the axis against the tick clock (see stats)",
                            "stats": st})
            audit.append(["C", subject_ns, ses, rid, "lfp stream", 1, 0,
                          f"{pk.get('Channel')} fs={fs:g} gain={pk.get('Gain')} "
                          f"packets={st['n_packets']} samples={st['n_samples_raw']} "
                          f"axis={st['n_samples_axis']} span_s={st['tick_span_s']:.2f} "
                          f"lost_ticks={st['n_lost_ticks']} masked={st['n_masked_samples']} "
                          f"masked_fraction={st['masked_fraction']:.5f} "
                          f"size_anomalies={st['size_anomalies']} "
                          f"tick_anomalies={st['tick_anomalies']} "
                          f"seq_anomalies={st['seq_anomalies']} wraps={st['wrap_events']}"])
        if not streams:
            continue
        rec = {"streams": streams, "subject_ns": subject_ns, "task": task,
               "source": "sensefog", "kind": "percept_brainsense_timedomain",
               "raw_file": rel, "session_date": dd.get("SessionDate"),
               "stimulation": dd.get("Stimulation"),
               "lead_configuration": dd.get("LeadConfiguration"),
               "device": (dd.get("DeviceInformation") or {}).get("Initial", {}).get("Neurostimulator"),
               "n_streams": len(streams),
               "note": "aux only, no canonical family (intracranial contract is a "
                       "post-paper owner decision); not aligned to the EEG - the "
                       "alignment samples live in the subject files (LFP_signal is on "
                       "the 1000 Hz resampled LFP of 1.3_Import_JSON.m)"}
        path = os.path.join(aux_dir, rid + "_lfp.npz")
        records.save(path, rec)
        n_files += 1
        print(f"  C {rid}: {len(streams)} streams, masked "
              f"{[round(s['stats']['masked_fraction'], 5) for s in streams]}")
    return n_files


# ----------------------------------------------------------------------- main
def run(repo, skip_clock_check=False):
    base = os.path.join(repo, "datasets", "eeg", "sensefog", "processed")
    os.makedirs(base, exist_ok=True)
    audit = []
    subject_files = load_subject_files(repo)
    print(f"subject files: {sorted(subject_files)}")
    if not skip_clock_check:
        clock_check(repo, subject_files, audit)
    n_lab, n_none = task_a(repo, subject_files, audit)
    manifest = []
    recs = task_b(repo, subject_files, audit, manifest)
    if recs:
        out = os.path.join(base, "canonical_imu.npz")
        records.save(out, recs)
        back = records.load(out)
        if not records.equal(recs, back):
            raise RuntimeError("canonical_imu.npz round trip failed")
        merge_manifest(os.path.join(repo, "datasets", "_canonical_imu_manifest.csv"),
                       ["source", "subject_ns", "task", "fps", "n_frames", "locations"],
                       manifest)
    n_lfp = task_c(repo, audit)
    with open(os.path.join(base, "pass2_audit.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["task", "subject_ns", "session", "record", "status", "n_ok",
                    "n_refused", "detail"])
        w.writerows(audit)
    print(f"pass 2: A labelled {n_lab} records (label None kept on {n_none}); "
          f"B {len(recs)} imu records; C {n_lfp} lfp aux files; "
          f"audit rows {len(audit)}")
    return audit


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--skip-clock-check", action="store_true")
    args = ap.parse_args(argv)
    run(args.repo, args.skip_clock_check)


if __name__ == "__main__":
    main()
