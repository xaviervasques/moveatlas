# -*- coding: utf-8 -*-
"""Build canonical EEG records (contract: configs/canonical_eeg.yaml, WBS 1.4).

Additive to the v1 pipeline: new family, per-record pkl storage (C-EEG-6). Design
decisions C-EEG-1..6 in configs/README_canonical_eeg.md. Montage is stored AS
RECORDED, made explicit per channel; no software re-referencing (C-EEG-1).

Sources handled here:
  multimodal_fog   IMPLEMENTED, tested on real samples 2026-08-22. Consumes
                   streams_eeg_emg.pkl (ingest_multimodal_fog.py): 25 named sites,
                   500 Hz, uV amplitude-verified, reference LM (TP9/TP10 mastoid
                   average, read from the bundled README.docx 2026-08-22)
                   (re-read the bundled README.docx for the reference electrode).
  cap_sleep        runs when datasets/eeg/cap_sleep/raw/ has EDF files. The EDF
                   reader below is stdlib+numpy, enforced by the file's own header
                   (units, rates, sizes). WRITTEN 2026-08-22, UNTESTED ON REAL
                   DATA until the rbd,n subset lands: the first run IS the
                   verification (hard assertions, per-file audit, unrecognized
                   labels never land in eeg). Emits, per C-EEG-3:
                     canonical_eeg records   (eeg channels, per fs group)
                     canonical_emg records   (chin EMG -> submentalis, C-EMG-5)
                     aux_streams pkl         (EOG / ECG / resp / other)
  tuh_eeg          same EDF pass once the corpus lands (referential labels
                   'EEG FP1-REF' / '-LE' handled by the same parser).
  seizeit2         BIDS with EDF files (OpenNeuro ds005873), one directory per
                   modality (eeg/ emg/ ecg/ mov/), 125 focal-epilepsy patients.
                   WRITTEN 2026-08-23 on the Paris machine against the ~60 GB
                   already synced; per the HANDOFF 7 plan it reuses read_edf and
                   the BIDS sidecar helpers rather than a new script. Two
                   behind-the-ear EEG channels per run (C-EEG-2: wearable ear
                   sites become EAR_L/EAR_R, never forced onto the 10-20 grid),
                   deltoid EMG -> canonical_emg, ECG + accelerometer/gyroscope
                   -> aux streams. Seizure annotations (events.tsv, ILAE 2017
                   vocabulary) become a per-frame int8 label plus verbatim
                   events; labels are for evaluation, never pretraining.

Outputs:
  datasets/eeg/<set>/processed/canonical_eeg/<record_id>.pkl (+ canonical_emg/, aux/)
  datasets/eeg/<set>/processed/eeg_ingest_audit.csv
  datasets/_canonical_eeg_manifest.csv (+ rows appended to _canonical_emg_manifest.csv)

Env: atlas-mouvement (numpy). Usage: python build_canonical_eeg.py [--repo PATH]
                                     [--only multimodal_fog,cap_sleep,tuh_eeg]
"""
import argparse
import csv
import json
import os
import pickle
import re
import numpy as np

SITES = [
    # 10-20 core
    "FP1", "FP2", "FPZ", "F1", "F2", "F3", "F4", "F7", "F8", "FZ",
    "C3", "C4", "CZ", "T7", "T8", "P3", "P4", "P7", "P8", "PZ",
    "O1", "O2", "OZ",
    # 10-10 extension, all observed in real corpora (OpenNeuro ds004584 63-ch and
    # ds007526 65-ch caps, surveyed 2026-08-22). Added only names actually seen.
    "AF3", "AF4", "AF7", "AF8", "AFZ",
    "F5", "F6", "F9", "F10",
    "FC1", "FC2", "FC3", "FC4", "FC5", "FC6", "FCZ",
    "FT7", "FT8", "FT9", "FT10",
    "C1", "C2", "C5", "C6",
    "CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CPZ",
    "TP7", "TP8", "TP9", "TP10",
    "P1", "P2", "P5", "P6", "P9", "P10",
    "PO3", "PO4", "PO7", "PO8", "POZ",
    "I1", "I2", "IZ", "T9", "T10",
    # ear lobes and mastoids stay distinct on purpose
    "A1", "A2", "M1", "M2", "EAR_L", "EAR_R", "UNKNOWN"]
ALIASES = {"T3": "T7", "T4": "T8", "T5": "P7", "T6": "P8"}
REFS_SPECIAL = ["AVG", "LE", "LM", "REF_COMMON_UNKNOWN"]
FOG_EEG_NAMES = ["FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
                 "F7", "F8", "P7", "P8", "FZ", "CZ", "PZ", "FC1", "FC2", "CP1",
                 "CP2", "FC5", "FC6", "CP5", "CP6"]
AUX_TOKENS = ("SAO2", "SPO2", "PLETH", "RESP", "FLOW", "THOR", "ABD", "POS",
              "SNORE", "HR", "PULSE", "BODY", "TEMP", "PRESS", "MIC", "LIGHT",
              "BATT", "PPG", "CANNULA", "NASAL")


def norm_site(tok):
    t = tok.strip().upper().replace(" ", "")
    t = ALIASES.get(t, t)
    return t if t in SITES else None


def classify_label(raw_label):
    """EDF/TUH/sleep channel label -> (kind, payload). Never guesses:
    kind eeg only when the label parses onto the site vocabulary."""
    lab = raw_label.strip()
    U = lab.upper()
    if "ANNOTATION" in U:
        return "annotations", None
    if any(t in U for t in ("CHIN", "MENT", "SUBM")):
        return "emg_chin", lab
    if U.startswith("EMG") or " EMG" in U or U.endswith("EMG"):
        return "emg_other", lab
    if any(t in U for t in ("EOG", "LOC", "ROC", "E1-", "E2-")) and "EEG" not in U:
        return "eog", lab
    if any(t in U for t in ("ECG", "EKG")):
        return "ecg", lab
    if any(t in U for t in AUX_TOKENS):
        return "aux", lab
    # VREF / CMS / DRL are the amplifier's own reference and driven-ground traces
    # (EGI and BioSemi caps). They are not scalp derivations, so they never enter
    # the EEG contract; kept as aux so nothing is thrown away.
    if U in ("VREF", "REF", "CMS", "DRL"):
        return "aux", lab
    # --- CAP sleep (Ospedale Maggiore, Parma): Italian labels. VERIFIED 2026-08-22
    # against the PhysioNet capslpdb description ("at least 3 EEG channels (F3 or
    # F4, C3 or C4 and O1 or O2, referred to A1 or A2), EOG (2 channels), EMG of
    # the submentalis muscle, bilateral anterior tibial EMG, respiration signals
    # (airflow, abdominal and thoracic effort and SaO2) and EKG") and against the
    # header labels of all 108 records, read over HTTP Range.
    if any(t in U for t in ("MILO", "MILOIOID", "MYLOHYOID")):
        return "emg_chin", lab          # milohioideo = submental muscle
    if U.startswith("TIB") or " TIB" in U:
        return "emg_other", lab         # tibiale anteriore, bilateral
    if "DELTOID" in U:
        return "emg_other", lab
    if any(t in U for t in ("TORACE", "TORACIC", "ADDOME", "ADDDOME", "FLUSSO",
                            "TERMISTORE", "CANULA", "CANNULA")):
        return "aux", lab               # respiration: effort, airflow, thermistor
    body = re.sub(r"^EEG[\s_]*", "", lab, flags=re.I).strip()
    if "-" in body:
        a, b = body.split("-", 1)
        sa = norm_site(a)
        bu = b.strip().upper()
        if sa and bu in ("REF", "CREF"):
            return "eeg", (sa, "REF_COMMON_UNKNOWN")
        if sa and bu == "LE":
            return "eeg", (sa, "LE")
        if sa and bu in ("AVG", "AV", "AR"):
            return "eeg", (sa, "AVG")
        sb = norm_site(b)
        if sa and sb:
            return "eeg", (sa, sb)
        return "unrecognized", lab
    s = norm_site(body)
    if s:
        return "eeg", (s, "REF_COMMON_UNKNOWN")
    # CAP writes the earlobe-referenced derivations without a separator: F3A2,
    # C4A1, O1A2. Split only when BOTH halves are vocabulary sites and the
    # reference half is an earlobe/mastoid, so this cannot swallow other labels.
    m = re.fullmatch(r"([A-Za-z]+\d?)(A[12]|M[12])", body.replace(" ", ""),
                     flags=re.I)
    if m:
        sa, sb = norm_site(m.group(1)), norm_site(m.group(2))
        if sa and sb:
            return "eeg", (sa, sb)
    return "unrecognized", lab


# ------------------------------------------------------------------ EDF reader
def read_edf(path):
    """Minimal EDF/EDF+ reader, stdlib+numpy, enforced by the file's own header.
    Returns (header_dict, list of per-signal dicts with 'signal' float32 arrays).
    Refuses discontinuous EDF+D files."""
    with open(path, "rb") as f:
        h = f.read(256)
        if len(h) < 256:
            raise ValueError("truncated EDF header")
        reserved = h[192:236].decode("ascii", "replace").strip()
        if reserved.startswith("EDF+D"):
            raise ValueError("EDF+D (discontinuous) not supported; review this file")
        n_records = int(h[236:244].decode().strip())
        rec_dur = float(h[244:252].decode().strip())
        ns = int(h[252:256].decode().strip())
        if not (0 < ns < 512):
            raise ValueError(f"implausible signal count {ns}")

        def field(width):
            raw = f.read(width * ns)
            return [raw[i * width:(i + 1) * width].decode("ascii", "replace").strip()
                    for i in range(ns)]
        labels = field(16); field(80)                       # transducer unused
        phys_dim = field(8)
        phys_min = [float(x) for x in field(8)]
        phys_max = [float(x) for x in field(8)]
        dig_min = [int(float(x)) for x in field(8)]
        dig_max = [int(float(x)) for x in field(8)]
        prefilter = field(80)
        spr = [int(x) for x in field(8)]                    # samples per record
        field(32)
        data = np.frombuffer(f.read(), dtype="<i2")
    per_rec = sum(spr)
    if n_records < 0:                                       # EDF allows -1
        n_records = data.size // per_rec
    if data.size < n_records * per_rec:
        raise ValueError(f"data area short: {data.size} < {n_records}x{per_rec}")
    data = data[:n_records * per_rec].reshape(n_records, per_rec)
    sigs, off = [], 0
    for i in range(ns):
        chunk = data[:, off:off + spr[i]].reshape(-1).astype(np.float32)
        off += spr[i]
        if dig_max[i] == dig_min[i]:
            raise ValueError(f"signal {labels[i]}: dig_max == dig_min")
        gain = (phys_max[i] - phys_min[i]) / (dig_max[i] - dig_min[i])
        sigs.append({"label": labels[i], "unit": phys_dim[i],
                     "prefilter": prefilter[i],
                     "fs": spr[i] / rec_dur if rec_dur > 0 else float("nan"),
                     "signal": (chunk - dig_min[i]) * gain + phys_min[i]})
    return {"n_records": n_records, "record_duration": rec_dur}, sigs


def to_uv(sig, unit, where):
    u = unit.strip().lower().replace("\xb5", "u").replace("μ", "u")
    if u in ("uv", "microv", "microvolt", "microvolts"):
        return sig, 1.0
    if u == "mv":
        return sig * 1000.0, 1000.0
    if u == "v":
        return sig * 1e6, 1e6
    raise ValueError(f"{where}: unit '{unit}' is not a voltage; refusing (C-EEG-4)")


def sanitize(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def write_record(outdir, rec, suffix=""):
    # moveatlas-record/1 container (moveatlas/records.py) since 2026-09-08:
    # no pickle on disk; the manifest row points at the .npz
    from moveatlas import records as _records
    os.makedirs(outdir, exist_ok=True)
    rid = sanitize(f"{rec['source']}__{rec['subject_ns']}__{rec['task']}") + suffix
    path = os.path.join(outdir, rid + ".npz")
    _records.save(path, rec)
    return rid, path


def eeg_manifest_row(rec, path, repo):
    sites = "|".join(c["site"] for c in rec["channels"])
    return [rec["source"], rec["subject_ns"], rec["task"], rec["fps"],
            rec["n_frames"], len(rec["channels"]), sites,
            os.path.relpath(path, repo)]


# ---------------------------------------------------------------- multimodal_fog
def build_multimodal_fog(repo, audit, manifest, emg_manifest):
    src = os.path.join(repo, "datasets", "imu", "multimodal_fog", "processed",
                       "streams_eeg_emg.pkl")
    if not os.path.exists(src):
        print(f"multimodal_fog: SKIP (missing {src}; run ingest_multimodal_fog.py)")
        return 0
    streams = pickle.load(open(src, "rb"))
    outdir = os.path.join(repo, "datasets", "imu", "multimodal_fog", "processed",
                          "canonical_eeg")
    n = 0
    for s in streams:
        eeg = np.asarray(s["eeg"], np.float32)
        names = list(s["eeg_names"])
        if names != FOG_EEG_NAMES or eeg.shape[1] != 25:
            raise SystemExit(f"{s['file']}: EEG names/shape drifted from the verified "
                             "mapping; refusing to guess")
        notes = []
        p99 = float(np.nanpercentile(np.abs(eeg), 99))
        if p99 > 1000:
            notes.append(f"p99 amplitude {p99:.0f} uV, review")
        channels = [{"site": nm, "ref": "LM", "kind": "eeg"} for nm in names]
        rec = {"signal": eeg, "channels": channels, "fps": float(s["fps"]),
               "unit": "uV", "unit_scale": 1.0,
               "filters": {"hp_hz": 0.5, "lp_hz": 100.0, "notch_hz": 50.0},
               "subject_ns": s["subject_ns"], "task": s["task"],
               "source": "multimodal_fog", "n_frames": int(eeg.shape[0]),
               "label": np.asarray(s["label"], np.int8)}
        rid, path = write_record(outdir, rec)
        manifest.append(eeg_manifest_row(rec, path, repo))
        audit.append(["multimodal_fog", s["file"], s["subject_ns"], s["task"],
                      eeg.shape[0], 25, round(float(s["fps"]), 1),
                      f"p99={p99:.0f}uV", "; ".join(notes)])
        n += 1
    print(f"multimodal_fog: {n} canonical EEG records "
          "(ref LM = TP9/TP10 mastoid average, from the bundled README)")
    return n


# ------------------------------------------------------------- EDF sets (CAP, TUH)
def build_edf_set(repo, setname, audit, manifest, emg_manifest):
    base = os.path.join(repo, "datasets", "eeg", setname)
    rawd = os.path.join(base, "raw")
    edfs = []
    for root, _, files in os.walk(rawd) if os.path.isdir(rawd) else []:
        edfs += [os.path.join(root, f) for f in files
                 if f.lower().endswith((".edf", ".rec")) and not f.startswith("._")]
    if not edfs:
        print(f"{setname}: SKIP (no EDF under raw/)")
        return 0
    print(f"{setname} FIRST-RUN VERIFICATION: this reader has not seen this corpus "
          "before; watch the audit and the unrecognized-label column")
    n = 0
    for path in sorted(edfs):
        b = os.path.basename(path)
        subj = f"{setname}:{sanitize(os.path.splitext(b)[0])}"
        ok, expected, actual = edf_is_complete(path)
        if not ok:
            print(f"  {b}: SKIP, still incomplete "
                  f"({actual / 1e6:.0f} of {expected / 1e6:.0f} MB)")
            continue
        try:
            hdr, sigs = read_edf(path)
        except ValueError as e:
            audit.append([setname, b, subj, "", "", "", "", "", f"READ FAIL: {e}"])
            print(f"  {b}: READ FAIL {e}")
            continue
        # 3 of the 38 CAP rbd,n records (n13, n14, n15) declare NO physical
        # dimension for ANY channel. Their ranges (+-156.25, 10-bit) look like
        # microvolts and the rest of the same corpus does say uV, but looking like
        # is not saying so: C-EEG-4 forbids inferring a unit, so the whole record
        # is refused rather than ingested at a guessed scale. If the owner decides
        # the scale is certain, add an explicit per-record override here; do not
        # relax the rule globally.
        if not any((sg.get("unit") or "").strip() for sg in sigs):
            audit.append([setname, b, subj, "", "", "", "",
                          "REFUSED: no unit declared", "the EDF header declares an "
                          "empty physical dimension for every channel; refusing to "
                          "infer one (C-EEG-4)"])
            print(f"  {b}: REFUSED, the header declares no unit for any channel")
            continue
        # A single unusable channel must not kill the run either: everything below
        # is contained per file rather than aborting the whole corpus.
        try:
            groups, routed = {}, {"eeg": 0, "emg_chin": 0, "eog": 0, "ecg": 0,
                                  "aux": 0, "emg_other": 0, "unrecognized": 0}
            aux_streams, unrec_labels, notes_unitless = [], [], []
            for sg in sigs:
                kind, payload = classify_label(sg["label"])
                if kind == "annotations":
                    continue
                if kind == "eeg":
                    site, ref = payload
                    sig_uv, _ = to_uv(sg["signal"], sg["unit"], f"{b}:{sg['label']}")
                    groups.setdefault(round(sg["fs"], 3), []).append(
                        {"site": site, "ref": ref, "signal": sig_uv,
                         "prefilter": sg["prefilter"]})
                    routed["eeg"] += 1
                elif kind == "emg_chin":
                    # A chin channel with no declared unit (CAP n13-n15 carry
                    # CHIN1 with an EMPTY unit) must not cost the whole recording:
                    # the EEG in the same file is perfectly usable. The channel is
                    # kept as an aux stream, flagged, and simply does not become a
                    # canonical EMG record. Still no unit guessing (C-EEG-4).
                    try:
                        sig_uv, _ = to_uv(sg["signal"], sg["unit"],
                                          f"{b}:{sg['label']}")
                    except ValueError as e:
                        aux_streams.append({"label": sg["label"], "kind": "emg_chin",
                                            "unit": sg["unit"], "fs": sg["fs"],
                                            "signal": sg["signal"]})
                        routed["aux"] += 1
                        notes_unitless.append(str(e).split(":")[-1].strip())
                        continue
                    emg_rec = {"signal": sig_uv[:, None].astype(np.float32),
                               "channels": [{"kind": "emg", "muscle": "submentalis",
                                             "side": "midline", "placement": sg["label"],
                                             "resolved": True}],
                               "fps": float(sg["fs"]), "unit": "uV", "unit_scale": 1.0,
                               "signal_kind": "as_recorded",
                               "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
                               "subject_ns": subj, "task": "sleep",
                               "source": setname + "_chin",
                               "n_frames": int(sig_uv.shape[0]), "label": None}
                    _, p = write_record(os.path.join(base, "processed", "canonical_emg"),
                                        emg_rec)
                    kinds = "emg"
                    emg_manifest.append([emg_rec["source"], subj, "sleep", emg_rec["fps"],
                                         emg_rec["n_frames"], 1, kinds,
                                         os.path.relpath(p, repo)])
                    routed["emg_chin"] += 1
                else:
                    aux_streams.append({"label": sg["label"], "kind": kind,
                                        "unit": sg["unit"], "fs": sg["fs"],
                                        "signal": sg["signal"]})
                    routed[kind] += 1
                    if kind == "unrecognized":
                        unrec_labels.append(sg["label"].strip())
            for fi, (fs, chans) in enumerate(sorted(groups.items())):
                T = min(c["signal"].shape[0] for c in chans)
                sig = np.stack([c["signal"][:T] for c in chans], axis=1)
                rec = {"signal": sig,
                       "channels": [{"site": c["site"], "ref": c["ref"], "kind": "eeg"}
                                    for c in chans],
                       "fps": float(fs), "unit": "uV", "unit_scale": 1.0,
                       "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None,
                                   "prefilter_verbatim": chans[0]["prefilter"]},
                       "subject_ns": subj, "task": "sleep" if setname == "cap_sleep"
                       else "clinical", "source": setname, "n_frames": int(T),
                       "label": None}
                suffix = f"__fs{fi}" if len(groups) > 1 else ""
                _, p = write_record(os.path.join(base, "processed", "canonical_eeg"),
                                    rec, suffix)
                manifest.append(eeg_manifest_row(rec, p, repo))
                n += 1
            if aux_streams:
                auxd = os.path.join(base, "processed", "aux")
                os.makedirs(auxd, exist_ok=True)
                with open(os.path.join(auxd, sanitize(subj) + "_aux.pkl"), "wb") as f:
                    pickle.dump({"subject_ns": subj, "streams": aux_streams}, f)
            audit.append([setname, b, subj,
                          "sleep" if setname == "cap_sleep" else "clinical",
                          hdr["n_records"], routed["eeg"],
                          "|".join(sorted({str(round(fs, 1)) for fs in groups})),
                          f"chin={routed['emg_chin']} eog={routed['eog']} "
                          f"ecg={routed['ecg']} aux={routed['aux']} "
                          f"emg_other={routed['emg_other']}",
                          "; ".join(
                              ([f"UNRECOGNIZED={routed['unrecognized']}: "
                                + "|".join(sorted(set(unrec_labels)))]
                               if routed["unrecognized"] else [])
                              + ([f"{len(notes_unitless)} channel(s) kept as aux "
                                  "for want of a declared unit: "
                                  + "|".join(sorted(set(notes_unitless)))]
                                 if notes_unitless else []))])
        except (ValueError, KeyError) as e:
            audit.append([setname, b, subj, "", "", "", "", "", f"BUILD FAIL: {e}"])
            print(f"  {b}: BUILD FAIL {e}")
            continue
        print(f"  {b}: eeg_ch={routed['eeg']} fs_groups={len(groups)} "
              f"unrecognized={routed['unrecognized']}")
    return n



def edf_is_complete(path):
    """Is this EDF fully on disk? Returns (ok, expected_bytes, actual_bytes).

    Ingestion often runs while a download is still in flight (the CAP subset takes
    hours). A partial file would surface as a READ FAIL and pollute the audit with
    a failure that is really just "not finished yet", so the size implied by the
    header is checked first and short files are SKIPPED rather than failed.
    """
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            h = f.read(256)
            if len(h) < 256:
                return False, 0, size
            ns = int(h[252:256].decode("ascii", "replace").strip())
            n_records = int(h[236:244].decode("ascii", "replace").strip())
            hdr_bytes = 256 + 256 * ns
            rest = f.read(256 * ns)
            if len(rest) < 256 * ns:
                return False, hdr_bytes, size
            # Per-signal header fields, in order and each ns-wide:
            #   label 16, transducer 80, dim 8, phys min 8, phys max 8,
            #   dig min 8, dig max 8, prefilter 80, SAMPLES-PER-RECORD 8, reserved 32
            # so samples-per-record starts at ns*216, NOT in the reserved tail.
            off = ns * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80)
            spr = [int(rest[off + 8 * i: off + 8 * (i + 1)].decode(
                "ascii", "replace").strip() or 0) for i in range(ns)]
            if sum(spr) == 0:
                return True, 0, size          # cannot tell; let the reader decide
        if n_records < 0:
            return True, size, size          # EDF allows -1: length not declared
        expected = hdr_bytes + n_records * sum(spr) * 2
        return size >= expected, expected, size
    except Exception:
        return True, 0, 0                    # let the real reader report the problem


# ------------------------------------------------------------------- BIDS EEG
def _tsv(path):
    """BIDS tsv -> list of dicts. utf-8-sig: several OpenNeuro files carry a BOM."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def build_bids_eeg(repo, setname, reldir, audit, manifest, emg_manifest):
    """EEGLAB .set recordings laid out as BIDS (OpenNeuro).

    Everything that matters is DECLARED by the dataset and is read, never
    guessed: the reference comes from eeg.json EEGReference, units and
    per-channel filters from channels.tsv, the sampling rate from the file
    itself (cross-checked against eeg.json). Channels marked status=bad are kept
    but flagged, because dropping them silently would change the montage.
    subject_ns is the BIDS subject, so every task of one person shares a subject
    and cannot straddle a split; the BIDS task label becomes the task.
    """
    base = os.path.join(repo, "datasets", reldir)
    rawd = os.path.join(base, "raw")
    sets = []
    for root, _, files in os.walk(rawd) if os.path.isdir(rawd) else []:
        sets += [os.path.join(root, f) for f in files
                 if (f.endswith("_eeg.set") or f.endswith("_eeg.bdf"))
                 and not f.startswith("._")]
    if not sets:
        print(f"{setname}: SKIP (no BIDS *_eeg.set/.bdf under raw/)")
        return 0
    try:
        import mne
    except ImportError:
        raise SystemExit(f"{setname}: the mne package is required to read EEGLAB "
                         ".set / BioSemi .bdf files (pip install mne); "
                         "hand-rolling that reader is a mis-map risk, refused")
    mne.set_log_level("ERROR")
    outdir = os.path.join(base, "processed", "canonical_eeg")
    n = 0
    print(f"{setname}: {len(sets)} BIDS recordings")
    for path in sorted(sets):
        b = os.path.basename(path)
        stem = b[:-len("_eeg.set")]        # same length for _eeg.bdf
        subj_id = stem.split("_")[0]
        task = "unknown"
        ses = ""
        for part in stem.split("_"):
            if part.startswith("task-"):
                task = part[len("task-"):]
            if part.startswith("ses-"):
                ses = part[len("ses-"):]
        # the BIDS session is state-bearing (ds002778: ses-on / ses-off
        # medication, ses-hc for controls); it rides in the task label so
        # ON and OFF recordings stay distinct while subject_ns keeps the
        # person whole across sessions (split safety)
        if ses:
            task = f"{task}_ses-{ses}"
        meta = _json(os.path.join(os.path.dirname(path), stem + "_eeg.json"))
        chan_rows = _tsv(os.path.join(os.path.dirname(path), stem + "_channels.tsv"))
        by_name = {(r.get("name") or "").strip(): r for r in chan_rows}
        notes = []
        try:
            if path.endswith(".bdf"):
                raw = mne.io.read_raw_bdf(path, preload=True, verbose="ERROR")
            else:
                raw = mne.io.read_raw_eeglab(path, preload=True,
                                             verbose="ERROR")
        except Exception as e:
            notes.append(f"UNREADABLE: {e}")
            audit.append([setname, b, f"{setname}:{subj_id}", task, 0, 0, "", "",
                          "; ".join(notes)])
            print(f"  {b}: FAILED to read ({e})")
            continue
        fs = float(raw.info["sfreq"])
        declared = meta.get("SamplingFrequency")
        if declared and abs(float(declared) - fs) > 0.5:
            notes.append(f"sfreq {fs} disagrees with eeg.json {declared}")
        # reference, as declared by the dataset
        ref_raw = str(meta.get("EEGReference", "") or "").strip()
        ref = norm_site(ref_raw) or ("AVG" if ref_raw.lower() in
                                     ("average", "avg", "common average")
                                     else "REF_COMMON_UNKNOWN")
        if ref_raw and ref == "REF_COMMON_UNKNOWN" and ref_raw.lower() not in ("n/a", ""):
            notes.append(f"EEGReference {ref_raw!r} not a vocabulary site")
        data = raw.get_data()                      # mne returns volts
        routed = {"eeg": 0, "emg_chin": 0, "eog": 0, "ecg": 0, "aux": 0,
                  "emg_other": 0, "unrecognized": 0}
        unrec_labels, bad_kept = [], []
        chans, sigs, aux_streams = [], [], []
        for ci, name in enumerate(raw.ch_names):
            row = by_name.get(name, {})
            kind, payload = classify_label(name)
            unit = (row.get("units") or "").strip()
            x = data[ci] * 1e6                     # V -> uV
            if unit and unit.replace("\u00b5", "u").lower() not in ("uv", "µv", "n/a", ""):
                notes.append(f"{name}: channels.tsv says units {unit!r}, "
                             "mne was trusted for scaling")
            if (row.get("status") or "").strip().lower() == "bad":
                bad_kept.append(name)
            if kind == "eeg":
                site, _ = payload
                chans.append({"site": site, "ref": ref, "kind": "eeg",
                              "bad": name in bad_kept})
                sigs.append(x.astype(np.float32))
                routed["eeg"] += 1
            else:
                aux_streams.append({"label": name, "kind": kind, "unit": "uV",
                                    "fs": fs, "signal": x.astype(np.float32)})
                routed[kind] += 1
                if kind == "unrecognized":
                    unrec_labels.append(name)
        if bad_kept:
            notes.append(f"{len(bad_kept)} channel(s) flagged status=bad in "
                         "channels.tsv, KEPT and marked: " + "|".join(bad_kept[:8]))
        # amplitude plausibility, NEVER a silent rescale. Scalp EEG sits in the
        # tens of uV. ds007526 stores values whose p99 is ~5e4 uV after the
        # standard EEGLAB uV convention that mne applies and that the dataset's
        # own channels.tsv declares, i.e. about 1000x too large. The declaration
        # is carried through faithfully and the record is FLAGGED; the true scale
        # is a question for the authors, not something to guess here.
        if sigs:
            stack = np.stack(sigs, axis=1)
            # DC-coupled recordings (channels.tsv declares low_cutoff 0.0,
            # e.g. BioSemi .bdf in ds002778) carry physical electrode
            # offsets of tens of mV: the amplitude that must be plausible
            # is the AC component, so the test demeans per channel THERE
            # ONLY. The stored data keeps its offsets untouched.
            lo_vals = {(row.get("low_cutoff") or "").strip()
                       for row in chan_rows}
            dc_coupled = lo_vals and all(
                v in ("0", "0.0") for v in lo_vals
                if v and v.lower() != "n/a")
            test = (stack - stack.mean(axis=0, keepdims=True)
                    if dc_coupled and lo_vals != {""} else stack)
            p99 = float(np.percentile(np.abs(test), 99))
            if not (0.5 <= p99 <= 500.0):
                notes.append(f"AMPLITUDE IMPLAUSIBLE: p99 {p99:.4g} uV against a "
                             "scalp-EEG range of roughly 0.5-500 uV; the source "
                             "declares uV, the values disagree by about "
                             f"{p99 / 50.0:.0f}x. NOT rescaled, scale UNRESOLVED")
            elif dc_coupled:
                notes.append("DC-coupled recording (declared low_cutoff 0.0): "
                             "amplitude plausibility measured on the demeaned "
                             "signal; raw DC offsets preserved in the data")
        if not chans:
            notes.append("no EEG channel parsed onto the site vocabulary")
            audit.append([setname, b, f"{setname}:{subj_id}", task, 0, 0,
                          str(round(fs, 1)), "", "; ".join(notes)])
            continue
        lo = {(row.get("low_cutoff") or "").strip() for row in chan_rows}
        hi = {(row.get("high_cutoff") or "").strip() for row in chan_rows}
        def _one(v):
            v = {x for x in v if x and x.lower() != "n/a"}
            try:
                return float(next(iter(v))) if len(v) == 1 else None
            except ValueError:
                return None
        rec = {"signal": np.stack(sigs, axis=1),
               "channels": [{"site": c["site"], "ref": c["ref"], "kind": "eeg"}
                            for c in chans],
               "bad_channels": [c["site"] for c in chans if c["bad"]],
               "fps": fs, "unit": "uV", "unit_scale": 1.0,
               "filters": {"hp_hz": _one(lo), "lp_hz": _one(hi), "notch_hz": None,
                           "prefilter_verbatim": meta.get("SoftwareFilters")},
               "subject_ns": f"{setname}:{subj_id}", "task": task,
               "source": setname, "n_frames": int(len(sigs[0])), "label": None}
        _, outp = write_record(outdir, rec)
        manifest.append(eeg_manifest_row(rec, outp, repo))
        if aux_streams:
            auxd = os.path.join(base, "processed", "aux")
            os.makedirs(auxd, exist_ok=True)
            with open(os.path.join(auxd, sanitize(stem) + "_aux.pkl"), "wb") as f:
                pickle.dump({"subject_ns": rec["subject_ns"], "task": task,
                             "streams": aux_streams}, f)
        audit.append([setname, b, rec["subject_ns"], task, rec["n_frames"],
                      routed["eeg"], str(round(fs, 1)),
                      f"ref={ref} eog={routed['eog']} ecg={routed['ecg']} "
                      f"aux={routed['aux']} unrec={routed['unrecognized']}",
                      "; ".join(notes) + (("; UNRECOGNIZED: "
                        + "|".join(sorted(set(unrec_labels)))) if unrec_labels else "")])
        n += 1
        if n % 25 == 0:
            print(f"  {n}/{len(sets)} done", flush=True)
    print(f"{setname}: {n} canonical EEG records")
    return n


# ----------------------------------------------------------------- seizeit2
# SensorDot channel labels, surveyed across every synced subject 2026-08-23:
# exactly three EEG label sets exist ('BTEleft SD'+'CROSStop SD',
# 'BTEright SD'+'CROSStop SD', 'BTEleft SD'+'BTEright SD'), matching the README's
# montage rules (same-side pair over the suspected hemisphere plus one cross-head
# channel; bilateral pair when generalized onset was suspected). Encoding per
# C-EEG-2/C-EEG-7: a same-side behind-the-ear derivation is (EAR_X, EAR_X), both
# electrodes on one mastoid; the cross-head channel is (EAR_L, EAR_R). Nothing is
# mapped onto the 10-20 grid because nothing was recorded there.
SEIZEIT2_EEG = {"BTELEFT SD": ("EAR_L", "EAR_L"),
                "BTERIGHT SD": ("EAR_R", "EAR_R"),
                "CROSSTOP SD": ("EAR_L", "EAR_R")}


def _seizeit2_label_array(events, fps, n_frames):
    """events.tsv rows -> per-frame int8: 0 background, 1 seizure (eventType
    sz*), 2 impedance check (impd, likely artifactual). Rows typed bckg are the
    annotators' explicit background and stay 0."""
    lab = np.zeros(n_frames, np.int8)
    for ev in events:
        et = (ev.get("eventType") or "").strip()
        code = 1 if et.startswith("sz") else 2 if et == "impd" else 0
        if not code:
            continue
        try:
            a = int(float(ev["onset"]) * fps)
            b = int((float(ev["onset"]) + float(ev["duration"])) * fps)
        except (KeyError, TypeError, ValueError):
            continue
        a, b = max(a, 0), min(b, n_frames)
        if a >= b:
            continue
        if code == 1:
            lab[a:b] = 1
        else:
            seg = lab[a:b]          # a seizure inside an impedance window
            seg[seg != 1] = 2       # stays a seizure
    return lab


def build_seizeit2(repo, audit, manifest, emg_manifest):
    base = os.path.join(repo, "datasets", "eeg", "seizeit2")
    rawd = os.path.join(base, "raw")
    eeg_edfs = []
    for root, _, files in os.walk(rawd) if os.path.isdir(rawd) else []:
        eeg_edfs += [os.path.join(root, f) for f in files
                     if f.endswith("_eeg.edf") and not f.startswith("._")]
    if not eeg_edfs:
        print("seizeit2: SKIP (no BIDS *_eeg.edf under raw/)")
        return 0
    outdir = os.path.join(base, "processed", "canonical_eeg")
    print(f"seizeit2: {len(eeg_edfs)} BIDS EDF runs on disk (sync may still be "
          "in flight; incomplete files are skipped, rerun after it finishes)")
    n = 0
    for path in sorted(eeg_edfs):
        b = os.path.basename(path)
        stem = b[:-len("_eeg.edf")]              # sub-001_ses-01_task-x_run-01
        parts = dict(p.split("-", 1) for p in stem.split("_") if "-" in p)
        subj = f"seizeit2:{parts.get('sub', '?')}"
        task = parts.get("task", "unknown")
        suffix = f"__ses{parts.get('ses', '?')}_run{parts.get('run', '?')}"
        eegdir = os.path.dirname(path)
        moddir = os.path.dirname(eegdir)         # .../sub-XXX/ses-YY
        ok, expected, actual = edf_is_complete(path)
        if not ok:
            print(f"  {b}: SKIP, still incomplete "
                  f"({actual / 1e6:.0f} of {expected / 1e6:.0f} MB)")
            continue
        ev_path = os.path.join(eegdir, stem + "_events.tsv")
        if not os.path.exists(ev_path):
            # the annotation file may simply not have synced yet; a run ingested
            # without its seizure labels would look "label-free" forever, so wait
            print(f"  {b}: SKIP, events.tsv not on disk yet")
            continue
        try:
            hdr, sigs = read_edf(path)
        except ValueError as e:
            audit.append(["seizeit2", b, subj, task, "", "", "", "",
                          f"READ FAIL: {e}"])
            print(f"  {b}: READ FAIL {e}")
            continue
        meta = _json(os.path.join(eegdir, stem + "_eeg.json"))
        events = _tsv(ev_path)
        notes = []
        chans, cols = [], []
        fs = None
        for sg in sigs:
            lab = sg["label"].strip().upper()
            if "ANNOTATION" in lab:
                continue
            pair = SEIZEIT2_EEG.get(lab)
            if pair is None:
                # never guess a montage: an unexpected label parks the whole run
                audit.append(["seizeit2", b, subj, task, "", "", "", "",
                              f"REFUSED: unexpected EEG label {sg['label']!r}"])
                chans = []
                break
            sig_uv, _ = to_uv(sg["signal"], sg["unit"], f"{b}:{sg['label']}")
            if fs is None:
                fs = sg["fs"]
            elif abs(sg["fs"] - fs) > 1e-6:
                audit.append(["seizeit2", b, subj, task, "", "", "", "",
                              f"REFUSED: mixed EEG rates {fs} vs {sg['fs']}"])
                chans = []
                break
            chans.append({"site": pair[0], "ref": pair[1], "kind": "eeg",
                          "placement": sg["label"].strip()})
            cols.append(sig_uv)
        if not chans:
            continue
        declared = meta.get("SamplingFrequency")
        if declared and abs(float(declared) - fs) > 0.5:
            notes.append(f"sfreq {fs} disagrees with eeg.json {declared}")
        T = min(c.shape[0] for c in cols)
        sig = np.stack([c[:T] for c in cols], axis=1)
        label = _seizeit2_label_array(events, fs, T)
        n_sz = sum(1 for ev in events
                   if (ev.get("eventType") or "").startswith("sz"))
        rec = {"signal": sig, "channels": chans, "fps": float(fs),
               "unit": "uV", "unit_scale": 1.0,
               "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None,
                           "prefilter_verbatim": sigs[0]["prefilter"]},
               "subject_ns": subj, "task": task, "source": "seizeit2",
               "n_frames": int(T), "label": label,
               "label_def": {0: "background", 1: "seizure (eventType sz*)",
                             2: "impedance check (impd), likely artifactual"},
               "events": events,
               "montage": meta.get("EEGMontage"),
               "placement_scheme": meta.get("EEGPlacementScheme")}
        _, p = write_record(outdir, rec, suffix)
        manifest.append(eeg_manifest_row(rec, p, repo))
        n += 1
        # ---- deltoid EMG, same run, own canonical family (C-EEG-3 pattern)
        emg_path = os.path.join(moddir, "emg", stem + "_emg.edf")
        emg_ok = os.path.exists(emg_path) and edf_is_complete(emg_path)[0]
        if emg_ok:
            try:
                _, esigs = read_edf(emg_path)
                for sg in esigs:
                    if "ANNOTATION" in sg["label"].upper():
                        continue
                    sig_uv, _ = to_uv(sg["signal"], sg["unit"],
                                      f"{b}:{sg['label']}")
                    emg_rec = {"signal": sig_uv[:, None].astype(np.float32),
                               "channels": [{"kind": "emg", "muscle": "deltoid",
                                             "side": "left",
                                             "placement": sg["label"].strip(),
                                             "resolved": True}],
                               "fps": float(sg["fs"]), "unit": "uV",
                               "unit_scale": 1.0, "signal_kind": "as_recorded",
                               "filters": {"hp_hz": None, "lp_hz": None,
                                           "notch_hz": None},
                               "subject_ns": subj, "task": task,
                               "source": "seizeit2_emg",
                               "n_frames": int(sig_uv.shape[0]),
                               "label": _seizeit2_label_array(
                                   events, sg["fs"], int(sig_uv.shape[0])),
                               "label_def": rec["label_def"]}
                    _, ep = write_record(os.path.join(base, "processed",
                                                      "canonical_emg"),
                                         emg_rec, suffix)
                    emg_manifest.append([emg_rec["source"], subj, task,
                                         emg_rec["fps"], emg_rec["n_frames"], 1,
                                         "emg", os.path.relpath(ep, repo)])
            except ValueError as e:
                notes.append(f"EMG file unusable: {e}")
        else:
            notes.append("no complete EMG file for this run")
        # ---- ECG and movement (acc+gyro) stay aux, as recorded
        aux_streams = []
        for mod, kind in (("ecg", "ecg"), ("mov", "imu")):
            mp = os.path.join(moddir, mod, stem + f"_{mod}.edf")
            if not (os.path.exists(mp) and edf_is_complete(mp)[0]):
                notes.append(f"no complete {mod} file for this run")
                continue
            try:
                _, msigs = read_edf(mp)
            except ValueError as e:
                notes.append(f"{mod} file unusable: {e}")
                continue
            for sg in msigs:
                if "ANNOTATION" in sg["label"].upper():
                    continue
                aux_streams.append({"label": sg["label"], "kind": kind,
                                    "unit": sg["unit"], "fs": sg["fs"],
                                    "signal": sg["signal"]})
        if aux_streams:
            # the EDF headers of the mov files declare 'g' for the gyroscope
            # axes too; kept verbatim (aux is as-recorded), noted here once
            auxd = os.path.join(base, "processed", "aux")
            os.makedirs(auxd, exist_ok=True)
            with open(os.path.join(auxd, sanitize(subj + suffix) + "_aux.pkl"),
                      "wb") as f:
                pickle.dump({"subject_ns": subj, "task": task,
                             "streams": aux_streams}, f)
        audit.append(["seizeit2", b, subj, task, T, len(chans),
                      str(round(fs, 1)),
                      f"montage={meta.get('EEGMontage')} sz_events={n_sz} "
                      f"emg={'yes' if emg_ok else 'no'} aux={len(aux_streams)}",
                      "; ".join(notes)])
        if n % 50 == 0:
            print(f"  {n} runs done (last {b})", flush=True)
    print(f"seizeit2: {n} canonical EEG records")
    return n


BUILDERS = {"multimodal_fog": build_multimodal_fog,
            "seizeit2": build_seizeit2,
            "cap_sleep": lambda r, a, m, em: build_edf_set(r, "cap_sleep", a, m, em),
            "tuh_eeg": lambda r, a, m, em: build_edf_set(r, "tuh_eeg", a, m, em),
            "pd_rest_eeg_ds004584": lambda r, a, m, em: build_bids_eeg(
                r, "pd_rest_eeg_ds004584", "eeg/pd_rest_eeg_ds004584", a, m, em),
            "pd_walking_eeg_ds007526": lambda r, a, m, em: build_bids_eeg(
                r, "pd_walking_eeg_ds007526", "eeg/pd_walking_eeg_ds007526", a, m, em),
            "pd_rest_eeg_onoff_ds002778": lambda r, a, m, em: build_bids_eeg(
                r, "pd_rest_eeg_onoff_ds002778",
                "eeg/pd_rest_eeg_onoff_ds002778", a, m, em)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--only", default=None,
                    help="comma list among: " + ",".join(BUILDERS))
    args = ap.parse_args()
    todo = list(BUILDERS) if not args.only else [s.strip() for s in args.only.split(",")]
    audit, manifest, emg_manifest = [], [], []
    total = 0
    for s in todo:
        if s not in BUILDERS:
            raise SystemExit(f"unknown source '{s}'; known: {', '.join(BUILDERS)}")
        total += BUILDERS[s](args.repo, audit, manifest, emg_manifest)
    by_dir = {"multimodal_fog": "imu/multimodal_fog", "cap_sleep": "eeg/cap_sleep",
              "tuh_eeg": "eeg/tuh_eeg", "seizeit2": "eeg/seizeit2",
              "pd_rest_eeg_ds004584": "eeg/pd_rest_eeg_ds004584",
              "pd_walking_eeg_ds007526": "eeg/pd_walking_eeg_ds007526",
              "pd_rest_eeg_onoff_ds002778": "eeg/pd_rest_eeg_onoff_ds002778"}
    for src, rel in by_dir.items():
        rows = [a for a in audit if a[0] == src]
        if rows:
            p = os.path.join(args.repo, "datasets", rel, "processed",
                             "eeg_ingest_audit.csv")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["source", "file", "subject_ns", "task",
                            "n_records_or_frames", "n_eeg_channels", "fs_groups",
                            "routing", "notes"])
                w.writerows(rows)
    def merge_manifest(path, header, new_rows):
        if not new_rows:
            return
        old = []
        if os.path.exists(path):
            with open(path, newline="") as f:
                old = [r for r in csv.reader(f)][1:]
            old = [r for r in old if r and r[0] not in {m[0] for m in new_rows}]
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(old + new_rows)
        print(f"manifest: {path} ({len(old) + len(new_rows)} rows)")
    merge_manifest(os.path.join(args.repo, "datasets", "_canonical_eeg_manifest.csv"),
                   ["source", "subject_ns", "task", "fps", "n_frames", "n_channels",
                    "sites", "record_path"], manifest)
    merge_manifest(os.path.join(args.repo, "datasets", "_canonical_emg_manifest.csv"),
                   ["source", "subject_ns", "task", "fps", "n_frames", "n_channels",
                    "kinds", "record_path"], emg_manifest)
    print(f"total: {total} canonical EEG records")


if __name__ == "__main__":
    main()
