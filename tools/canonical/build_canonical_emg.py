# -*- coding: utf-8 -*-
"""Build canonical EMG records (contract: configs/canonical_emg.yaml, WBS 1.3).

Additive to the v1 pipeline: new family, per-record pkl storage (C-EMG-6), nothing
in pose/imu/force/silhouette changes. Design decisions C-EMG-1..6 are in
configs/README_canonical_emg.md; unresolved channel identity is a STATUS, never a
guess (C-EMG-1).

Sources handled here:
  multimodal_fog     IMPLEMENTED, tested on real samples 2026-08-22. Consumes
                     datasets/imu/multimodal_fog/processed/streams_eeg_emg.pkl
                     (produced by ingest_multimodal_fog.py). 5-column block:
                     block index 2 is IO/EOG (verified, weakest amplitude); the
                     other 4 are EMG+ECG in a per-patient order that stays
                     unresolved_emg_ecc until configs/multimodal_fog_channel_order.csv
                     is filled (session -> patient-ID correspondence).
  semg_walking       runs when datasets/emg/physionet_semg_walking/raw/ has WFDB
                     records; needs the wfdb package (pip install wfdb). The .hea
                     headers are self-describing (sig_name, units, fs) and are
                     enforced at run time. FIRST REAL RUN IS THE VERIFICATION:
                     the script prints the observed channel table; unrecognized
                     names route to kind aux and are flagged, never guessed.
  gait120            IMPLEMENTED 2026-08-28. The MCOS lock (barriers case 4)
                     fell to the mat-io package, which decodes the MATLAB
                     'table' objects scipy cannot: S###/EMG/RawData.mat inside
                     the raw zips, 12 named right-leg muscles at 2000 Hz
                     (EMGs_info.fs, enforced), 7 tasks x up to 5 trials.
                     Raw signal only (ProcessedData envelopes are derivatives).
                     Needs: pip install mat-io.
  cap_sleep chin EMG is emitted by build_canonical_eeg.py (same EDF pass, C-EEG-3).

Outputs:
  datasets/<fam>/<set>/processed/canonical_emg/<record_id>.pkl
  datasets/<fam>/<set>/processed/emg_ingest_audit.csv
  datasets/_canonical_emg_manifest.csv        (rewritten per source section)

Env: atlas-mouvement (numpy). Usage: python build_canonical_emg.py [--repo PATH]
                                     [--only multimodal_fog,semg_walking]
"""
import argparse
import csv
import os
import pickle
import numpy as np

MUSCLES = ["tibialis_anterior", "gastrocnemius", "gastrocnemius_lateralis",
           "gastrocnemius_medialis",
           "soleus", "soleus_medialis", "soleus_lateralis",
           "peroneus_longus", "peroneus_brevis",
           "rectus_femoris", "vastus_lateralis",
           "vastus_medialis", "biceps_femoris", "semitendinosus", "hamstrings", "gluteus_medius",
           "erector_spinae", "rectus_abdominis", "deltoid_anterior", "deltoid_medius",
           "deltoid_posterior", "biceps_brachii", "triceps_brachii",
           "flexor_carpi_radialis", "extensor_carpi_radialis", "extensor_carpi_ulnaris",
           "flexor_digitorum", "extensor_digitorum", "first_dorsal_interosseous",
           "abductor_pollicis_brevis", "sternocleidomastoideus", "trapezius_superior",
           "splenius_capitis", "levator_scapulae", "masseter", "orbicularis_oculi",
           "submentalis", "forearm_array", "unknown"]

# semg_walking .hea sig_name aliases -> muscle. EXTENDED AT THE FIRST REAL RUN
# (2026-08-22, all 31 records read): the headers use "<sensor> <side> <site>",
# e.g. "semg LT TIB.A", "baso RT FOOT", "gonio LT KNEE". Observed vocabulary is
# closed: sensors {semg, baso, gonio}, sides {LT, RT}, EMG sites
# {TIB.A, LAT.G, REC.F, HAM, LAT.V}. Unrecognized names are NOT ingested as emg
# (kind aux + audit flag).
SEMG_ALIASES = {
    "TIB.A": "tibialis_anterior", "TA": "tibialis_anterior",
    "LAT.G": "gastrocnemius_lateralis", "LGS": "gastrocnemius_lateralis",
    "GL": "gastrocnemius_lateralis", "MED.G": "gastrocnemius_medialis",
    "MGS": "gastrocnemius_medialis", "GM": "gastrocnemius_medialis",
    "SOL": "soleus", "PL": "peroneus_longus",
    "REC.F": "rectus_femoris", "RF": "rectus_femoris",
    "LAT.V": "vastus_lateralis", "VL": "vastus_lateralis",
    "MED.V": "vastus_medialis", "VM": "vastus_medialis",
    "HAM": "hamstrings",          # head not specified by the header, see contract
    "BF": "biceps_femoris", "ST": "semitendinosus",
}
SEMG_SIDES = {"LT": "L", "L": "L", "LEFT": "L",
              "RT": "R", "R": "R", "RIGHT": "R"}
# non-EMG sensors carried in the same record: basographic footswitch, goniometer
SEMG_AUX_SENSORS = ("BASO", "GONIO", "ELGON", "FOOTSW", "FSW", "ANGLE")


def parse_semg_channel(name):
    """'semg LT TIB.A' -> ('emg', 'tibialis_anterior', 'L').
    'baso RT FOOT' / 'gonio LT KNEE' -> ('aux', None, None).
    Anything else -> (None, None, None): flagged, never guessed."""
    toks = str(name).upper().replace("_", " ").replace("-", " ").split()
    if not toks:
        return None, None, None
    sensor = toks[0]
    if sensor in SEMG_AUX_SENSORS:
        return "aux", None, None
    if sensor not in ("SEMG", "EMG"):
        return None, None, None
    side = None
    rest = toks[1:]
    if rest and rest[0] in SEMG_SIDES:
        side = SEMG_SIDES[rest[0]]
        rest = rest[1:]
    site = " ".join(rest)
    if site not in SEMG_ALIASES:
        return None, None, None
    return "emg", SEMG_ALIASES[site], side


def sanitize(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def write_record(outdir, rec):
    os.makedirs(outdir, exist_ok=True)
    rid = sanitize(f"{rec['source']}__{rec['subject_ns']}__{rec['task']}")
    path = os.path.join(outdir, rid + ".pkl")
    with open(path, "wb") as f:
        pickle.dump(rec, f)
    return rid, path


def manifest_row(rec, rid, path, repo):
    kinds = "|".join(sorted({c["kind"] for c in rec["channels"]}))
    return [rec["source"], rec["subject_ns"], rec["task"], rec["fps"],
            rec["n_frames"], len(rec["channels"]), kinds,
            os.path.relpath(path, repo).replace("\\", "/")]


# ---------------------------------------------------------------- multimodal_fog
def load_channel_order(repo):
    """configs/multimodal_fog_channel_order.csv:
    subject_ns,experiment,block_index,kind,muscle,side.
    Key is (subject_ns, experiment, block_index); an empty experiment matches any task.
    The experiment column exists because patient 008 was recorded twice with DIFFERENT
    5-column orders (README table rows 008-1 and 008-2), while subject_ns is the patient.
    Empty template = hook not yet filled = stay unresolved (C-EMG-1)."""
    p = os.path.join(repo, "configs", "multimodal_fog_channel_order.csv")
    table = {}
    if os.path.exists(p):
        with open(p, newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("subject_ns"):
                    continue
                key = (row["subject_ns"].strip(), (row.get("experiment") or "").strip(),
                       int(row["block_index"]))
                mu = row.get("muscle", "unknown").strip() or "unknown"
                if mu not in MUSCLES:
                    raise SystemExit(f"channel_order: unknown muscle '{mu}' (vocabulary "
                                     f"is versioned; extend the contract, not the CSV)")
                table[key] = (row["kind"].strip(), mu, (row.get("side") or "unknown").strip())
    return table


def order_lookup(order, subject_ns, task, i):
    """Exact (subject, experiment, block) first, then the experiment-agnostic row.
    task is 'task_n' or '<experiment>/task_n' (008)."""
    exp = task.split("/")[0] if "/" in task else ""
    for key in ((subject_ns, exp, i), (subject_ns, "", i)):
        if key in order:
            return order[key]
    return None


def build_multimodal_fog(repo, audit, manifest):
    src = os.path.join(repo, "datasets", "imu", "multimodal_fog", "processed",
                       "streams_eeg_emg.pkl")
    if not os.path.exists(src):
        print("multimodal_fog: SKIP (run ingest_multimodal_fog.py first; "
              f"missing {src})")
        return 0
    streams = pickle.load(open(src, "rb"))
    order = load_channel_order(repo)
    outdir = os.path.join(repo, "datasets", "imu", "multimodal_fog", "processed",
                          "canonical_emg")
    n = 0
    for s in streams:
        blk = np.asarray(s["emg_block"], np.float32)
        if blk.ndim != 2 or blk.shape[1] != 5:
            raise SystemExit(f"multimodal_fog {s['file']}: EMG block shape {blk.shape}, "
                             "expected (T, 5); refusing to guess")
        notes = []
        # verify the one certain identity: block index 2 = IO/EOG, weakest amplitude
        amp = np.nanmax(np.abs(blk), axis=0)
        if int(np.argmin(amp)) != 2:
            notes.append(f"EOG check: min-amplitude column is {int(np.argmin(amp))}, "
                         "not 2 (README says IO at index 2); review this file")
        channels = []
        for i in range(5):
            got = order_lookup(order, s["subject_ns"], s["task"], i)
            if i == 2 and got is None:
                channels.append({"kind": "eog", "muscle": None, "side": "midline",
                                 "placement": "IO (infraorbital), block index 2",
                                 "resolved": True})
            elif got is not None:
                kind, mu, side = got
                channels.append({"kind": kind, "muscle": mu if kind == "emg" else None,
                                 "side": side, "placement": f"block index {i}, "
                                 "README per-patient table", "resolved": True})
            else:
                channels.append({"kind": "unresolved_emg_ecg", "muscle": "unknown",
                                 "side": "unknown",
                                 "placement": f"block index {i}, order pending "
                                 "session->patient-ID correspondence",
                                 "resolved": False})
        rec = {"signal": blk, "channels": channels, "fps": float(s["fps"]),
               "unit": "uV_assumed", "unit_scale": 1.0, "signal_kind": "bandpassed",
               "filters": {"hp_hz": 10.0, "lp_hz": 500.0, "notch_hz": 50.0},
               "subject_ns": s["subject_ns"], "task": s["task"],
               "source": "multimodal_fog", "n_frames": int(blk.shape[0]),
               "label": np.asarray(s["label"], np.int8)}
        rid, path = write_record(outdir, rec)
        manifest.append(manifest_row(rec, rid, path, repo))
        resolved = sum(1 for c in channels if c["resolved"])
        audit.append(["multimodal_fog", s["file"], rec["subject_ns"], rec["task"],
                      blk.shape[0], 5, resolved,
                      "|".join(f"{a:.0f}" for a in amp), "; ".join(notes)])
        n += 1
    print(f"multimodal_fog: {n} canonical EMG records "
          f"({'order table applied' if order else 'unresolved order, C-EMG-1'})")
    return n


# ---------------------------------------------------------------- semg_walking
def build_semg_walking(repo, audit, manifest):
    rawd = os.path.join(repo, "datasets", "emg", "physionet_semg_walking", "raw")
    heas = []
    for root, _, files in os.walk(rawd) if os.path.isdir(rawd) else []:
        heas += [os.path.join(root, f) for f in files
                 if f.endswith(".hea") and not f.startswith("._")]
    if not heas:
        print("semg_walking: SKIP (no WFDB records under raw/; "
              "fetch_p2_lot.py --only semg_walking first)")
        return 0
    try:
        import wfdb
    except ImportError:
        raise SystemExit("semg_walking: wfdb package required (pip install wfdb); "
                         "hand-rolling a 212 reader is a mis-map risk, refused")
    outdir = os.path.join(repo, "datasets", "emg", "physionet_semg_walking",
                          "processed", "canonical_emg")
    n = 0
    print("semg_walking FIRST-RUN VERIFICATION: observed channel table below; "
          "extend SEMG_ALIASES if any EMG channel shows as aux")
    for hea in sorted(heas):
        rec_name = hea[:-4]
        r = wfdb.rdrecord(rec_name)
        sig = np.asarray(r.p_signal, np.float32)
        fs = float(r.fs)
        if not (500 <= fs <= 4000):
            raise SystemExit(f"{rec_name}: fs {fs} outside sanity range; header says "
                             f"{r.fs}; stop and read the record docs")
        channels, keep, unit_notes = [], [], []
        for ci, (name, unit) in enumerate(zip(r.sig_name, r.units)):
            u = (unit or "").lower()
            kind, mu, side = parse_semg_channel(name)
            if kind == "emg":
                if u not in ("mv", "uv", "v"):
                    raise SystemExit(f"{rec_name} ch {name}: unit '{unit}' not a "
                                     "voltage; refusing to ingest as emg")
                scale = {"uv": 0.001, "mv": 1.0, "v": 1000.0}[u]   # -> mV
                channels.append({"kind": "emg", "muscle": mu,
                                 "side": side or "unknown", "placement": name,
                                 "unit_in_header": unit,
                                 "resolved": side is not None})
                keep.append((ci, scale))
            elif kind == "aux":
                channels.append({"kind": "aux", "muscle": None, "side": None,
                                 "placement": name, "unit_in_header": unit,
                                 "resolved": True})
                keep.append((ci, 1.0))     # aux keeps its own header unit
            else:
                channels.append({"kind": "aux", "muscle": None, "side": None,
                                 "placement": name + " [UNRECOGNIZED, review]",
                                 "unit_in_header": unit, "resolved": False})
                keep.append((ci, 1.0))
            print(f"  {os.path.basename(rec_name)} ch{ci} '{name}' [{unit}] -> "
                  f"{channels[-1]['kind']}/{channels[-1].get('muscle')}")
        out = np.stack([sig[:, ci] * sc for ci, sc in keep], axis=1)
        # amplitude plausibility, NEVER a silent rescale (C-EMG-1 spirit): surface
        # EMG sits around 0.1 mV. Verified 2026-08-22 over all 31 records: S01 and
        # S21 declare mV in their .hea while their values are ~1000x the other 29
        # records, i.e. the header unit is wrong and the data is really uV. Such
        # records are FLAGGED here and left unscaled for a human decision.
        emg_idx = [k for k, c in enumerate(channels) if c["kind"] == "emg"]
        if emg_idx:
            p99 = float(np.nanpercentile(np.abs(out[:, emg_idx]), 99))
            if not (0.005 <= p99 <= 2.0):
                unit_notes.append(
                    f"EMG p99 {p99:.4g} mV is outside the physiological range "
                    f"0.005-2 mV for header unit '{r.units[emg_idx[0]]}': suspect "
                    "header unit, NOT rescaled, review before use")
        subj = "semg_walking:" + sanitize(os.path.basename(rec_name))
        rec = {"signal": out, "channels": channels, "fps": fs, "unit": "mV",
               "unit_scale": 1.0, "signal_kind": "raw_per_header",
               "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
               "subject_ns": subj, "task": "walk", "source": "semg_walking",
               "n_frames": int(out.shape[0]), "label": None}
        rid, path = write_record(outdir, rec)
        manifest.append(manifest_row(rec, rid, path, repo))
        emg_amp = "|".join(f"{a:.4g}" for a in
                           np.nanmax(np.abs(out), axis=0)) if out.size else ""
        audit.append(["semg_walking", os.path.basename(rec_name), subj, "walk",
                      out.shape[0], len(channels),
                      sum(1 for c in channels if c["resolved"]), emg_amp,
                      "; ".join(unit_notes)])
        n += 1
    flagged = sum(1 for a in audit if a[0] == "semg_walking" and a[8])
    print(f"semg_walking: {n} canonical EMG records"
          + (f"; {flagged} FLAGGED for suspect header unit "
             "(see emg_ingest_audit.csv)" if flagged else ""))
    return n


# -------------------------------------------------------------------- ninapro
# Electrode layout, from the Ninapro documentation (DB pages read 2026-08-25 and
# Atzori et al. 2014, 10.1038/sdata.2014.53): eight electrodes equally spaced
# around the forearm at the radio-humeral joint, then the main activity spots of
# flexor digitorum and extensor digitorum, and for DB2 additionally biceps and
# triceps, IN THAT LISTING ORDER. Channels 1-8 are therefore the untargeted ring
# (muscle forearm_array); the targeted spots get their named muscles. Side is
# not distributed per subject and stays unknown.
NINAPRO_MUSCLES = {
    "db1": ["forearm_array"] * 8 + ["flexor_digitorum", "extensor_digitorum"],
    "db2": ["forearm_array"] * 8 + ["flexor_digitorum", "extensor_digitorum",
                                    "biceps_brachii", "triceps_brachii"],
}
# Sampling rates are stated by the DB pages ("sampled at a rate of 2 kHz" for
# DB2; 100 Hz MyoBock RMS for DB1) and cross-checked below against recording
# duration: exercise files must land in the plausible 5-40 min band.
NINAPRO_FS = {"db1": 100.0, "db2": 2000.0}


def build_ninapro(repo, audit, manifest):
    import io
    import zipfile
    try:
        import scipy.io as sio
    except ImportError:
        raise SystemExit("ninapro: scipy required to read the .mat files")
    rawd = os.path.join(repo, "datasets", "emg", "ninapro", "raw")
    zips = sorted(f for f in (os.listdir(rawd) if os.path.isdir(rawd) else [])
                  if f.lower().endswith(".zip") and not f.startswith("._"))
    if not zips:
        print("ninapro: SKIP (no zips under raw/)")
        return 0
    base = os.path.join(repo, "datasets", "emg", "ninapro")
    outdir = os.path.join(base, "processed", "canonical_emg")
    auxdir = os.path.join(base, "processed", "aux")
    os.makedirs(auxdir, exist_ok=True)
    n = 0
    for zf in zips:
        db = zf.split("_")[0].lower()                    # DB1_s3.zip -> db1
        if db not in NINAPRO_MUSCLES:
            audit.append(["ninapro", zf, "", "", "", "", "",
                          "", f"SKIPPED: unknown database prefix {db!r}"])
            continue
        muscles = NINAPRO_MUSCLES[db]
        fs = NINAPRO_FS[db]
        z = zipfile.ZipFile(os.path.join(rawd, zf))
        mats = sorted(x for x in z.namelist() if x.lower().endswith(".mat"))
        for mat_name in mats:
            m = sio.loadmat(io.BytesIO(z.read(mat_name)))
            emg = np.asarray(m.get("emg"), np.float32)
            if emg.ndim != 2 or emg.shape[1] != len(muscles):
                audit.append(["ninapro", f"{zf}:{mat_name}", "", "", "", "", "",
                              "", f"REFUSED: emg shape {getattr(emg, 'shape', None)}, "
                              f"expected (T, {len(muscles)}) for {db}"])
                continue
            subj = int(np.asarray(m["subject"]).ravel()[0])
            ex = int(np.asarray(m["exercise"]).ravel()[0])
            ns = f"ninapro:{db}_s{subj}"
            task = f"{db}_E{ex}"
            notes = []
            dur_min = emg.shape[0] / fs / 60
            if not (5 <= dur_min <= 40):
                notes.append(f"duration {dur_min:.1f} min at the documented "
                             f"{fs:g} Hz is outside 5-40 min: rate suspect")
            if db == "db2":
                sig = emg * 1000.0                       # V (Delsys) -> mV
                unit, skind = "mV", "raw_per_docs"
                p99 = float(np.nanpercentile(np.abs(sig), 99))
                if not (0.005 <= p99 <= 2.0):
                    notes.append(f"EMG p99 {p99:.4g} mV outside the "
                                 "physiological 0.005-2 mV band for V->mV: "
                                 "scale suspect, review")
            else:
                # DB1 ships the MyoBock RMS envelope; no unit is declared
                # anywhere, so none is invented (C-EMG-1)
                sig = emg
                unit, skind = "unknown", "rms_envelope_as_recorded"
            channels = [{"kind": "emg", "muscle": mu, "side": "unknown",
                         "placement": f"{db} electrode {i + 1} "
                         "(ring of 8 then targeted spots, per the Ninapro docs)",
                         "resolved": mu != "forearm_array"}
                        for i, mu in enumerate(muscles)]
            label = np.asarray(m.get("restimulus"), np.int16).ravel() \
                if m.get("restimulus") is not None else None
            rec = {"signal": sig, "channels": channels, "fps": fs,
                   "unit": unit, "unit_scale": 1.0, "signal_kind": skind,
                   "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
                   "subject_ns": ns, "task": task, "source": "ninapro",
                   "n_frames": int(sig.shape[0]), "label": label,
                   "label_def": "restimulus: refined movement id per the "
                                "Ninapro exercise tables, 0 = rest; eval only"}
            rid, path = write_record(outdir, rec)
            manifest.append(manifest_row(rec, rid, path, repo))
            aux = {}
            for k in ("glove", "acc", "inclin"):
                if m.get(k) is not None:
                    aux[k] = np.asarray(m[k], np.float32)
            if aux:
                with open(os.path.join(auxdir, rid + "_aux.pkl"), "wb") as f:
                    pickle.dump({"subject_ns": ns, "task": task, "fps": fs,
                                 "streams": aux,
                                 "note": "glove: 22 Cyberglove channels, "
                                         "uncalibrated units; acc: 3 axes per "
                                         "electrode; inclin: 2 inclinometer "
                                         "channels (DB2)"}, f)
            audit.append(["ninapro", f"{zf}:{os.path.basename(mat_name)}", ns,
                          task, sig.shape[0], len(channels),
                          sum(1 for c in channels if c["resolved"]),
                          f"p99={float(np.nanpercentile(np.abs(sig), 99)):.4g}{unit}",
                          "; ".join(notes)])
            n += 1
        if n and n % 30 == 0:
            print(f"  ninapro: {n} records so far ({zf})", flush=True)
    print(f"ninapro: {n} canonical EMG records")
    return n


# ---------------------------------------------------------------- gait120
# Column names verbatim from the source tables, including the source's own
# 'GastrocnemuisMedialis' misspelling: mapped explicitly, never fuzzy-matched.
GAIT120_MUSCLES = {
    "VastusLateralis": "vastus_lateralis",
    "RectusFemoris": "rectus_femoris",
    "VastusMedialis": "vastus_medialis",
    "TibialisAnterior": "tibialis_anterior",
    "BicepsFemoris": "biceps_femoris",
    "Semitendinosus": "semitendinosus",
    "GastrocnemuisMedialis": "gastrocnemius_medialis",   # sic in the source
    "GastrocnemiusMedialis": "gastrocnemius_medialis",
    "GastrocnemiusLateralis": "gastrocnemius_lateralis",
    "SoleusMedialis": "soleus_medialis",
    "SoleusLateralis": "soleus_lateralis",
    "PeroneusLongus": "peroneus_longus",
    "PeroneusBrevis": "peroneus_brevis",
}
GAIT120_TASKS = {"LevelWalking": "level_walking", "StairAscent": "stair_ascent",
                 "StairDescent": "stair_descent", "SlopeAscent": "slope_ascent",
                 "SlopeDescent": "slope_descent", "SitToStand": "sit_to_stand",
                 "StandToSit": "stand_to_sit"}


def _g120_unwrap(v):
    import numpy as _np
    while isinstance(v, _np.ndarray) and v.dtype == object and v.size == 1:
        v = v.item()
    return v


def build_gait120(repo, audit, manifest):
    import re
    import zipfile
    import tempfile
    try:
        from matio import load_from_mat
    except ImportError:
        raise SystemExit("gait120: mat-io package required (pip install mat-io); "
                         "the EMG tables are MCOS objects nothing else decodes")
    import pandas as pd
    rawd = os.path.join(repo, "datasets", "emg", "gait120", "raw")
    zips = sorted(f for f in (os.listdir(rawd) if os.path.isdir(rawd) else [])
                  if f.lower().endswith(".zip") and not f.startswith("._"))
    if not zips:
        print("gait120: SKIP (no zips under raw/)")
        return 0
    outdir = os.path.join(repo, "datasets", "emg", "gait120", "processed",
                          "canonical_emg")
    n = 0
    for zf_name in zips:
        z = zipfile.ZipFile(os.path.join(rawd, zf_name))
        mats = sorted(nm for nm in z.namelist()
                      if re.fullmatch(r"S\d+/EMG/RawData\.mat", nm))
        for nm in mats:
            subj = nm.split("/")[0]
            subject_ns = f"gait120:{subj}"
            with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as t:
                t.write(z.read(nm))
                p = t.name
            try:
                m = load_from_mat(p)
            except Exception as e:
                audit.append(["gait120", nm, subject_ns, "", "", "", "", "",
                              f"READ FAIL: {e}"])
                os.unlink(p)
                continue
            finally:
                if os.path.exists(p):
                    os.unlink(p)
            fs = float(np.asarray(_g120_unwrap(
                m["EMGs_info"][0, 0]["fs"])).ravel()[0])
            if abs(fs - 2000.0) > 1e-6:
                audit.append(["gait120", nm, subject_ns, "", "", "", "", "",
                              f"REFUSED: EMGs_info.fs {fs} != 2000"])
                continue
            for src_task, task_slug in GAIT120_TASKS.items():
                if src_task not in m:
                    audit.append(["gait120", nm, subject_ns, task_slug,
                                  "", "", "", "", "MISSING TASK"])
                    continue
                block = m[src_task][0, 0]
                for tf in block.dtype.names:
                    if not tf.startswith("Trial"):
                        continue
                    trial = _g120_unwrap(block[tf])
                    if not (hasattr(trial, "dtype") and trial.dtype.names
                            and "EMGs_raw" in trial.dtype.names):
                        continue        # absent trial slots serialize empty
                    tr = trial[0, 0] if trial.shape == (1, 1) else trial
                    df = _g120_unwrap(tr["EMGs_raw"])
                    if not isinstance(df, pd.DataFrame):
                        audit.append(["gait120", nm, subject_ns,
                                      f"{task_slug}_{tf.lower()}", "", "", "",
                                      "", "REFUSED: EMGs_raw is not a decoded "
                                      "table"])
                        continue
                    unknown = [c for c in df.columns
                               if c not in GAIT120_MUSCLES]
                    if unknown:
                        audit.append(["gait120", nm, subject_ns,
                                      f"{task_slug}_{tf.lower()}", "", "", "",
                                      "", f"REFUSED: unmapped columns "
                                      f"{unknown[:4]}; extend the explicit map"])
                        continue
                    # source documents volts; the contract's canonical unit
                    # is mV and sanctions conversion exactly when the source
                    # documents its unit, so V -> mV here (x1000)
                    sig = df.to_numpy(dtype=np.float32) * 1000.0
                    if not np.any(sig):
                        # an absent trial serialized as a zero block; the
                        # source's own AvailableTrialIdx still counts it
                        # (observed on S058 slope_ascent trial05)
                        audit.append(["gait120", nm, subject_ns,
                                      f"{task_slug}_{tf.lower()}",
                                      sig.shape[0], sig.shape[1], "", "",
                                      "REFUSED: all-zero signal (absent "
                                      "trial serialized as zeros)"])
                        continue
                    channels = [{"kind": "emg",
                                 "muscle": GAIT120_MUSCLES[c], "side": "R",
                                 "placement": f"{c} (right leg, data "
                                 "descriptor PMC12177048)",
                                 "resolved": True} for c in df.columns]
                    events = {}
                    if "TotalFrame" in trial.dtype.names:
                        v = np.asarray(_g120_unwrap(tr["TotalFrame"])).ravel()
                        events["total_frame_100hz"] = v.tolist()
                    steps = []
                    for sf in trial.dtype.names:
                        if sf.startswith("Step"):
                            st = _g120_unwrap(tr[sf])
                            if hasattr(st, "dtype") and st.dtype.names and \
                                    "TargetFrame" in st.dtype.names:
                                w = np.asarray(_g120_unwrap(
                                    st[0, 0]["TargetFrame"] if st.shape == (1, 1)
                                    else st["TargetFrame"])).ravel()
                                steps.append(w.tolist())
                    if steps:
                        events["step_target_frames_100hz"] = steps
                    # unit documented: "Surface EMG signals were recorded in
                    # volts" (data descriptor, PMC12177048); stored as mV
                    rec = {"signal": sig, "channels": channels, "fps": fs,
                           "unit": "mV", "unit_scale": 1000.0,
                           "signal_kind": "raw", "filters": None,
                           "subject_ns": subject_ns,
                           "task": f"{task_slug}_{tf.lower()}",
                           "source": "gait120",
                           "n_frames": int(sig.shape[0]),
                           "gait_events": events}
                    rid, path = write_record(outdir, rec)
                    manifest.append(manifest_row(rec, rid, path, repo))
                    amp = np.nanmax(np.abs(sig), axis=0)
                    audit.append(["gait120", nm, subject_ns, rec["task"],
                                  sig.shape[0], sig.shape[1], len(channels),
                                  "|".join(f"{a:.2e}" for a in amp[:4]),
                                  f"steps={len(steps)}"])
                    n += 1
            print(f"gait120 {subj}: done ({n} records so far)", flush=True)
    print(f"gait120: {n} canonical EMG records (raw 2000 Hz, 12 right-leg "
          "muscles; MVC calibration and processed envelopes not emitted)")
    return n


BUILDERS = {"multimodal_fog": build_multimodal_fog,
            "semg_walking": build_semg_walking,
            "ninapro": build_ninapro,
            "gait120": build_gait120}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--only", default=None,
                    help="comma list among: " + ",".join(BUILDERS))
    args = ap.parse_args()
    todo = list(BUILDERS) if not args.only else [s.strip() for s in args.only.split(",")]
    audit, manifest = [], []
    total = 0
    for s in todo:
        if s not in BUILDERS:
            raise SystemExit(f"unknown source '{s}'; known: {', '.join(BUILDERS)}")
        total += BUILDERS[s](args.repo, audit, manifest)
    for base, per_set in (("imu/multimodal_fog", "multimodal_fog"),
                          ("emg/physionet_semg_walking", "semg_walking"),
                          ("emg/ninapro", "ninapro"),
                          ("emg/gait120", "gait120")):
        rows = [a for a in audit if a[0] == per_set]
        if rows:
            p = os.path.join(args.repo, "datasets", base, "processed",
                             "emg_ingest_audit.csv")
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["source", "file", "subject_ns", "task", "n_frames",
                            "n_channels", "n_resolved", "max_abs_per_channel", "notes"])
                w.writerows(rows)
    if manifest:
        mp = os.path.join(args.repo, "datasets", "_canonical_emg_manifest.csv")
        old = []
        if os.path.exists(mp):
            with open(mp, newline="") as f:
                old = [r for r in csv.reader(f)][1:]
            old = [r for r in old if r and r[0] not in {m[0] for m in manifest}]
        with open(mp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "subject_ns", "task", "fps", "n_frames",
                        "n_channels", "kinds", "record_path"])
            w.writerows(old + manifest)
        print(f"manifest: {mp} ({len(old) + len(manifest)} rows)")
    print(f"total: {total} canonical EMG records")


if __name__ == "__main__":
    main()
