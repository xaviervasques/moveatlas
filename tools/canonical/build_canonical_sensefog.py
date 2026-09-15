# -*- coding: utf-8 -*-
"""Build canonical EEG + EMG records for sensefog (Mendeley c9ckcvjxc7,
CC BY 4.0, 12 PD patients with bilateral STN-DBS; STN Percept LFP +
scalp EEG + leg EMG + APDM motion during sitting/standing/gait with
FOG). WBS 1.4, same contract shape as build_canonical_eeg.py.

Scope of THIS pass (the unambiguous half):
  - scalp EEG: BrainVision (.vhdr/.eeg/.vmrk), 48 10-10 sites, 1000 Hz,
    unit uV explicit in the header (0.1 uV resolution). Reference is
    NOT documented (the SenseFOG-Documentation repo names the amplifier
    but no reference electrode), so every channel is stored
    ref=REF_COMMON_UNKNOWN per C-EEG-1 - recorded, not guessed.
  - leg EMG: the trailing bipolar channels TA_L1/2, GA_L1/2, TA_R1/2,
    GA_R1/2 (tibialis anterior + gastrocnemius, left/right, two
    electrodes each) ride in the same BrainVision file at the same
    1000 Hz / uV; routed to canonical_emg with explicit muscle+side and
    an electrode suffix (the BF1/BF2 policy from the stroke-analog
    scoping: two electrodes on one muscle, both kept, same muscle name).
  - IPG_1/IPG_2 (implantable pulse generator monitor traces) are NOT
    scalp derivations and NOT muscle; kept as aux so nothing is dropped.
  - BrainVision markers ride verbatim as events. NO FOG label array is
    emitted: the .vmrk holds only Moblab/Toggle sync markers, not FOG
    onset/offset annotations, so a per-frame label would be a guess
    (C: better unknown than wrong). FOG labels wait for the motion/mat
    pass that locates the real annotation source.

DEFERRED to later passes (need their own verified readers):
  - STN Percept LFP (ieeg/*.json, Medtronic export) -> canonical
    intracranial; sampling rate and montage read from the JSON, not
    assumed.
  - APDM Opal motion (motion/*.h5, 3 IMUs ankles+L5) -> canonical imu.

Outputs (per-record pkl, C-EEG-6), source id 'sensefog':
  datasets/eeg/sensefog/processed/canonical_eeg/<record_id>.pkl
  datasets/eeg/sensefog/processed/canonical_emg/<record_id>.pkl
  datasets/eeg/sensefog/processed/aux/<record_id>.pkl
  datasets/eeg/sensefog/processed/eeg_ingest_audit.csv
  rows appended to datasets/_canonical_eeg_manifest.csv and
  datasets/_canonical_emg_manifest.csv (merge_manifest dedups by source)

Env: numpy only. Usage: python build_canonical_sensefog.py [--repo PATH]
"""
import argparse
import csv
import os
import pickle
import re
import numpy as np

# reuse the vetted vocabulary + helpers from the EEG builder
from build_canonical_eeg import norm_site, sanitize, write_record

# The trailing bipolar EMG channels, exact header names -> canonical muscle.
# Names are explicit in the BrainVision header; no inference. Electrode index
# is the trailing digit (two electrodes per muscle-side).
EMG_MUSCLES = {"TA": "tibialis_anterior", "GA": "gastrocnemius"}
# Channels that are neither scalp EEG nor muscle EMG: the DBS pulse-generator
# monitor traces. Kept as aux, never forced onto a contract.
AUX_NAMES = {"IPG_1", "IPG_2"}

SESSION_TASK = {
    "ses-sitting": "sitting", "ses-standing": "standing",
    "ses-walk": "walk", "ses-walkws": "walk_with_stops",
    "ses-walkint": "walk_dualtask", "ses-walkint2": "walk_dualtask_2"}


def read_brainvision(vhdr_path):
    """Parse a BrainVision header + its binary, next to the .vhdr (the
    internal DataFile= field points at the ORIGINAL name PD01_gehen.eeg,
    which the Mendeley release renamed - so resolve siblings by extension,
    never by the header's stale filename). Returns (meta, names, res,
    units, data[n_samples, n_ch] in native units, markers)."""
    with open(vhdr_path, encoding="utf-8", errors="replace") as f:
        txt = f.read()

    def kv(key):
        m = re.search(rf"^{key}=(.*)$", txt, re.M)
        return m.group(1).strip() if m else None

    n_ch = int(kv("NumberOfChannels"))
    interval_us = float(kv("SamplingInterval"))
    fs = 1e6 / interval_us
    fmt = (kv("BinaryFormat") or "").upper()
    orient = (kv("DataOrientation") or "MULTIPLEXED").upper()
    dtype = {"INT_16": "<i2", "IEEE_FLOAT_32": "<f4",
             "UINT_16": "<u2"}.get(fmt)
    if dtype is None:
        raise ValueError(f"{vhdr_path}: unsupported BinaryFormat {fmt}")
    if orient != "MULTIPLEXED":
        raise ValueError(f"{vhdr_path}: unsupported DataOrientation {orient}")

    names, res, units = [], [], []
    for i in range(1, n_ch + 1):
        line = kv(f"Ch{i}")
        if line is None:
            raise ValueError(f"{vhdr_path}: missing Ch{i}")
        # Name,Ref,Resolution,Unit  (unit field may be omitted -> default uV
        # per the BrainVision spec, but only when Resolution is present)
        parts = line.split(",")
        names.append(parts[0].replace("\\1", ",").strip())
        res.append(float(parts[2]) if len(parts) > 2 and parts[2].strip() else 1.0)
        unit = parts[3].strip() if len(parts) > 3 and parts[3].strip() else "uV"
        units.append(unit.replace("\xb5", "u").replace("μ", "u"))

    base = os.path.splitext(vhdr_path)[0]
    eeg_path = base + ".eeg"
    if not os.path.exists(eeg_path):
        # fall back to any sibling .eeg
        sib = [p for p in os.listdir(os.path.dirname(vhdr_path))
               if p.lower().endswith(".eeg")]
        if len(sib) != 1:
            raise ValueError(f"{vhdr_path}: cannot resolve the .eeg binary")
        eeg_path = os.path.join(os.path.dirname(vhdr_path), sib[0])

    raw = np.fromfile(eeg_path, dtype=dtype)
    if raw.size % n_ch:
        raise ValueError(f"{eeg_path}: {raw.size} samples not divisible by "
                         f"{n_ch} channels")
    data = raw.reshape(-1, n_ch).astype(np.float32)

    markers = []
    vmrk = base + ".vmrk"
    if os.path.exists(vmrk):
        with open(vmrk, encoding="utf-8", errors="replace") as f:
            for ln in f:
                m = re.match(r"Mk\d+=([^,]*),([^,]*),(\d+),", ln)
                if m:
                    markers.append({"type": m.group(1),
                                    "desc": m.group(2).replace("\\1", ","),
                                    "pos": int(m.group(3))})
    meta = {"fs": fs, "n_ch": n_ch}
    return meta, names, res, units, data, markers


def to_uv(vals, unit, res, where):
    u = unit.strip().lower()
    if u in ("uv", "microv", "microvolt", "microvolts"):
        scale = 1.0
    elif u == "mv":
        scale = 1000.0
    elif u == "v":
        scale = 1e6
    else:
        raise ValueError(f"{where}: unit '{unit}' is not a voltage (C-EEG-4)")
    return vals * res * scale, res * scale


def parse_emg(name):
    """'TA_L1' -> ('tibialis_anterior','L','1'); None if not a leg-EMG name."""
    m = re.fullmatch(r"(TA|GA)_([LR])(\d+)", name)
    if not m:
        return None
    return EMG_MUSCLES[m.group(1)], m.group(2), m.group(3)


def build_sensefog(repo, audit, manifest, emg_manifest):
    root = os.path.join(repo, "datasets", "eeg", "sensefog", "raw",
                        "SenseFOG-main")
    if not os.path.isdir(root):
        print(f"sensefog: SKIP (missing {root})")
        return 0
    base = os.path.join(repo, "datasets", "eeg", "sensefog")
    eeg_dir = os.path.join(base, "processed", "canonical_eeg")
    emg_dir = os.path.join(base, "processed", "canonical_emg")
    aux_dir = os.path.join(base, "processed", "aux")
    n_eeg = 0
    for subj_d in sorted(os.listdir(root)):
        sp = os.path.join(root, subj_d)
        if not (os.path.isdir(sp) and subj_d.startswith("sub-")):
            continue
        subject_ns = f"sensefog:{subj_d}"
        for ses_d in sorted(os.listdir(sp)):
            vdir = os.path.join(sp, ses_d, "eeg")
            if not os.path.isdir(vdir):
                continue
            vhdrs = [p for p in os.listdir(vdir) if p.lower().endswith(".vhdr")]
            if not vhdrs:
                continue
            task = SESSION_TASK.get(ses_d, sanitize(ses_d))
            vhdr = os.path.join(vdir, vhdrs[0])
            try:
                meta, names, res, units, data, markers = read_brainvision(vhdr)
            except ValueError as e:
                audit.append(["sensefog", os.path.relpath(vhdr, repo),
                              subject_ns, task, "", "", "", "", f"READ FAIL: {e}"])
                print(f"  {subj_d}/{ses_d}: READ FAIL {e}")
                continue
            fs = meta["fs"]
            n = data.shape[0]

            eeg_cols, eeg_chan = [], []
            emg_groups = {}   # (muscle, side) -> list of (col, electrode)
            aux_cols, aux_chan = [], []
            unrec = []
            for j, nm in enumerate(names):
                emg = parse_emg(nm)
                if emg:
                    emg_groups.setdefault((emg[0], emg[1]), []).append((j, emg[2]))
                    continue
                if nm in AUX_NAMES:
                    aux_cols.append(j)
                    aux_chan.append({"label": nm, "kind": "aux"})
                    continue
                site = norm_site(nm)
                if site:
                    eeg_cols.append(j)
                    eeg_chan.append({"site": site, "ref": "REF_COMMON_UNKNOWN",
                                     "kind": "eeg"})
                    continue
                unrec.append(nm)

            events = [{"onset_s": m["pos"] / fs, "type": m["type"],
                       "desc": m["desc"]} for m in markers]

            # --- EEG record
            if eeg_cols:
                sig = np.empty((n, len(eeg_cols)), np.float32)
                scale_uv = None
                for k, j in enumerate(eeg_cols):
                    sig[:, k], sc = to_uv(data[:, j], units[j], res[j],
                                          f"sensefog {subj_d}/{ses_d} {names[j]}")
                    scale_uv = sc
                p99 = float(np.nanpercentile(np.abs(sig), 99))
                notes = [f"p99={p99:.0f}uV"]
                if p99 > 1000:
                    notes.append("p99>1000uV review")
                rec = {"signal": sig, "channels": eeg_chan, "fps": float(fs),
                       "unit": "uV", "unit_scale": float(scale_uv),
                       "signal_kind": "as_recorded",
                       "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
                       "subject_ns": subject_ns, "task": task, "source": "sensefog",
                       "n_frames": int(n), "label": None, "events": events}
                _, path = write_record(eeg_dir, rec)
                manifest.append(["sensefog", subject_ns, task, float(fs), int(n),
                                 len(eeg_chan),
                                 "|".join(c["site"] for c in eeg_chan),
                                 os.path.relpath(path, repo)])
                n_eeg += 1
            else:
                p99 = 0.0
                notes = ["no EEG channels"]

            # --- EMG record (all leg muscles in one record, channel-tagged)
            if emg_groups:
                cols, chans = [], []
                for (muscle, side), electrodes in sorted(emg_groups.items()):
                    for j, elec in sorted(electrodes, key=lambda t: t[1]):
                        cols.append(j)
                        chans.append({"kind": "emg", "muscle": muscle,
                                      "side": side, "electrode": elec,
                                      "placement": names[j], "resolved": True})
                emg_sig = np.empty((n, len(cols)), np.float32)
                emg_scale = None
                for k, j in enumerate(cols):
                    emg_sig[:, k], emg_scale = to_uv(
                        data[:, j], units[j], res[j],
                        f"sensefog {subj_d}/{ses_d} {names[j]}")
                erec = {"signal": emg_sig, "channels": chans, "fps": float(fs),
                        "unit": "uV", "unit_scale": float(emg_scale),
                        "signal_kind": "as_recorded",
                        "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
                        "subject_ns": subject_ns, "task": task,
                        "source": "sensefog", "n_frames": int(n),
                        "label": None, "events": events}
                _, ep = write_record(emg_dir, erec)
                emg_manifest.append(["sensefog", subject_ns, task, float(fs),
                                     int(n), len(chans),
                                     "|".join(f"{c['muscle']}_{c['side']}{c['electrode']}"
                                              for c in chans),
                                     os.path.relpath(ep, repo)])

            # --- aux (IPG monitor)
            if aux_cols:
                arec = {"streams": [{"label": names[j], "kind": "aux",
                                     "signal": data[:, j].copy(),
                                     "unit": units[j], "fs": float(fs)}
                                    for j in aux_cols],
                        "subject_ns": subject_ns, "task": task,
                        "source": "sensefog", "n_frames": int(n)}
                write_record(aux_dir, arec)

            audit.append(["sensefog", os.path.relpath(vhdr, repo), subject_ns,
                          task, int(n), len(eeg_chan), round(fs, 1),
                          f"eeg={len(eeg_chan)} emg_ch={sum(len(v) for v in emg_groups.values())} "
                          f"aux={len(aux_cols)} events={len(events)}",
                          ("unrecognized: " + ",".join(unrec)) if unrec
                          else "; ".join(notes)])
            print(f"  {subj_d}/{ses_d} [{task}]: EEG {len(eeg_chan)}ch "
                  f"EMG {sum(len(v) for v in emg_groups.values())}ch "
                  f"aux {len(aux_cols)} events {len(events)}"
                  + (f"  UNREC {unrec}" if unrec else ""))
    print(f"sensefog: {n_eeg} canonical EEG records "
          "(ref REF_COMMON_UNKNOWN - not documented at source)")
    return n_eeg


def merge_manifest(path, header, new_rows):
    if not new_rows:
        return
    old = []
    if os.path.exists(path):
        with open(path, newline="") as f:
            old = [r for r in csv.reader(f)][1:]
        old = [r for r in old if r and r[0] not in {m[0] for m in new_rows}]
    # csv.writer defaults to \r\n whatever the file's newline; force LF so
    # the shared manifests do not churn between the Mac and the PC (H19 s3b)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(old + new_rows)
    print(f"manifest: {path} ({len(old) + len(new_rows)} rows)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--pass2", action="store_true",
                    help="run pass 2 only (FOG labels, APDM imu, Percept LFP aux; "
                         "build_canonical_sensefog_pass2.py) on the pass-1 outputs")
    ap.add_argument("--skip-clock-check", action="store_true")
    args = ap.parse_args()
    if args.pass2:
        from build_canonical_sensefog_pass2 import run as run_pass2
        run_pass2(args.repo, args.skip_clock_check)
        return
    audit, manifest, emg_manifest = [], [], []
    total = build_sensefog(args.repo, audit, manifest, emg_manifest)

    ap_ = os.path.join(args.repo, "datasets", "eeg", "sensefog", "processed",
                       "eeg_ingest_audit.csv")
    os.makedirs(os.path.dirname(ap_), exist_ok=True)
    with open(ap_, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source", "file", "subject_ns", "task", "n_frames",
                    "n_eeg_channels", "fs", "routing", "notes"])
        w.writerows(audit)
    merge_manifest(os.path.join(args.repo, "datasets", "_canonical_eeg_manifest.csv"),
                   ["source", "subject_ns", "task", "fps", "n_frames",
                    "n_channels", "sites", "record_path"], manifest)
    merge_manifest(os.path.join(args.repo, "datasets", "_canonical_emg_manifest.csv"),
                   ["source", "subject_ns", "task", "fps", "n_frames",
                    "n_channels", "kinds", "record_path"], emg_manifest)
    print(f"total: {total} canonical EEG records")


if __name__ == "__main__":
    main()
