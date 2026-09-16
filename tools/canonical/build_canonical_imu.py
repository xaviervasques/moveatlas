"""Ingest body-worn inertial datasets into the canonical IMU contract.

Contract: configs/canonical_imu.yaml. Per sample we store the ACTIVE sensor locations
only (compact), plus the masks that place them into the logical (T,14,9) grid:
    signal        (T, n_active, 9)  float32   [acc_xyz, gyro_xyz, mag_xyz]
    location_ids  (n_active,)       int       indices into the 14 canonical locations
    channel_mask  (n_active, 9)     bool      channels present per active location
    fps           float                       native rate of this sample
    subject_ns, task, source, label (optional, eval only)
Units converted to canonical: acc -> g, gyro -> deg/s, mag -> uT.

Env: atlas-mouvement. Usage: python build_canonical_imu.py
"""
import os
import csv
import glob
import zipfile
import gzip
import pickle
import io
import numpy as np

REPO = os.path.dirname(os.path.abspath(__file__))

LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R", "thigh_L", "thigh_R",
             "shank_L", "shank_R", "ankle_L", "ankle_R", "foot_L", "foot_R", "pocket"]
CHANNELS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z",
            "mag_x", "mag_y", "mag_z"]
LOC_I = {n: i for i, n in enumerate(LOCATIONS)}
CH_I = {n: i for i, n in enumerate(CHANNELS)}
G = 9.80665
# magnetometers exported by Xsens software are normalized to the local
# field strength (|B| ~ 1), not in uT; converting would need the field at
# the recording site, which the sources do not give, so the values stay
# as recorded and the record says so
MAG_NORMALIZED = "normalized (source units, |B| ~ 1 at the recording site)"


def make_record(loc_data, fps, subject_ns, task, source, label=None, extra=None):
    """loc_data: {location_name: {channel_name: np.array(T,)}}. Same T across all.

    VALIDITY, added 2026-08-23. This used to mark every channel it was handed as
    PRESENT, whatever the values were. fog_star exposed the cost: 23 of its 106
    records carried NaN in channels channel_mask called valid, in several cases a
    sensor dead for the whole recording, and the contract tells consumers to trust
    that mask. Three rules now hold for every source:

      - a channel with no finite sample anywhere is an ABSENT sensor: masked off
        and zeroed, which is what the contract means by absent
      - a location left with no valid channel at all is dropped from the record
        rather than carried as an empty slot
      - a channel that is mostly fine but drops out for a stretch stays present,
        its non-finite samples are zeroed, and the record gains sample_valid
        (T, L) so the dropout is explicit and excludable instead of silently
        looking like a limb that stopped moving

    The signal array is therefore guaranteed finite, and nothing is inferred.

    A fourth rule, added 2026-09-17: a channel whose finite samples are all
    exactly zero is an ABSENT sensor too (clinical_gait_multipatho RIL_12
    ships a head sensor written as zeros for five whole trials); no real
    accelerometer, gyroscope or magnetometer reads exactly zero throughout.
    `extra` adds record-level keys (e.g. mag_unit where the source's
    magnetometer is not in the contract unit).
    """
    active = [l for l in LOCATIONS if l in loc_data]
    T = len(next(iter(next(iter(loc_data.values())).values())))
    sig = np.zeros((T, len(active), 9), np.float32)
    cmask = np.zeros((len(active), 9), bool)
    for li, loc in enumerate(active):
        for ch, arr in loc_data[loc].items():
            sig[:, li, CH_I[ch]] = arr
            cmask[li, CH_I[ch]] = True

    finite = np.isfinite(sig)
    dead = cmask & ~finite.any(axis=0)          # (L, 9) channel never finite
    dead |= cmask & ~np.any(finite & (sig != 0), axis=0)   # all exact zeros
    if dead.any():
        cmask = cmask & ~dead
    keep = [li for li in range(len(active)) if cmask[li].any()]
    if len(keep) != len(active):
        active = [active[li] for li in keep]
        sig, cmask = sig[:, keep], cmask[keep]
        finite = np.isfinite(sig)
    # per-sample validity over the channels that remain present
    present = np.broadcast_to(cmask[None], sig.shape)
    sample_valid = np.all(finite | ~present, axis=2)          # (T, L)
    sig = np.where(finite, sig, 0.0).astype(np.float32)       # guarantee finite

    rec = {"signal": sig, "location_ids": np.array([LOC_I[l] for l in active]),
           "channel_mask": cmask, "sample_valid": sample_valid,
           "fps": fps, "subject_ns": subject_ns,
           "task": task, "source": source, "n_frames": T}
    if not sample_valid.all():
        rec["dropout_fraction"] = float(1.0 - sample_valid.mean())
    if label is not None:
        rec["label"] = np.asarray(label)
    if extra:
        rec.update(extra)
    return rec


def acc3(x, y, z):
    return {"acc_x": x, "acc_y": y, "acc_z": z}


def save(source, recs, manifest):
    """Write the records straight to the moveatlas-record/1 container
    (canonical_imu.npz; the pickle step is retired, 2026-09-17). `recs`
    may be a generator: records are written one at a time, which is how
    weargait_pd (about 7 GB in memory) builds on an 8 GB machine."""
    from moveatlas import records as _records
    out = os.path.join(REPO, "datasets/imu", source, "processed")
    os.makedirs(out, exist_ok=True)
    rows, subjects = [], set()

    def stream():
        for r in recs:
            rows.append([source, r["subject_ns"], r["task"], round(r["fps"], 2)
                         if r["fps"] else "", r["n_frames"],
                         "|".join(LOCATIONS[i] for i in r["location_ids"])])
            subjects.add(r["subject_ns"])
            yield r
    _records.save(os.path.join(out, "canonical_imu.npz"), stream())
    manifest.extend(rows)
    print(f"  {source}: {len(rows)} recordings, {len(subjects)} subjects")


# ---------------------------------------------------------------- daphnet
def ingest_daphnet(manifest):
    z = zipfile.ZipFile(glob.glob(os.path.join(
        REPO, "datasets/imu/daphnet/raw/*.zip"))[0])
    recs = []
    for n in sorted(x for x in z.namelist() if x.endswith(".txt") and "/S" in "/" + x):
        base = os.path.basename(n)
        if not (base[0] == "S" and "R" in base):
            continue
        a = np.array([[float(v) for v in ln.split()]
                      for ln in z.read(n).decode().splitlines() if ln.strip()])
        if a.size == 0:
            continue
        g = a[:, 1:10] / 1000.0                     # mg -> g; ankle, thigh, trunk
        loc = {"ankle_L": acc3(g[:, 0], g[:, 1], g[:, 2]),
               "thigh_L": acc3(g[:, 3], g[:, 4], g[:, 5]),
               "trunk": acc3(g[:, 6], g[:, 7], g[:, 8])}
        subj = base[:3]                             # S01
        recs.append(make_record(loc, 64.0, f"daphnet:{subj}", base[:-4],
                                "daphnet", a[:, 10]))
    save("daphnet", recs, manifest)


# ---------------------------------------------------------------- kaggle_fog
def ingest_kaggle_fog(manifest):
    import pandas as pd
    base = os.path.join(REPO, "datasets/imu/kaggle_fog/raw/extracted")
    # Id -> Subject from metadata
    id2subj = {}
    for m in ("tdcsfog_metadata.csv", "defog_metadata.csv"):
        p = os.path.join(base, m)
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                id2subj[r["Id"]] = r.get("Subject", r["Id"])
    recs = []
    for proto, fps, unit in (("tdcsfog", 128.0, G), ("defog", 100.0, 1.0)):
        for f in glob.glob(os.path.join(base, "**", proto, "*.csv"), recursive=True):
            rid = os.path.basename(f)[:-4]
            df = pd.read_csv(f)
            if not {"AccV", "AccML", "AccAP"} <= set(df.columns):
                continue
            av, aml, aap = (df["AccV"].values / unit, df["AccML"].values / unit,
                            df["AccAP"].values / unit)
            loc = {"lower_back": {"acc_z": av, "acc_x": aml, "acc_y": aap}}
            subj = id2subj.get(rid, rid)
            recs.append(make_record(loc, fps, f"kaggle_fog:{subj}", f"{proto}_{rid}",
                                    "kaggle_fog"))
    save("kaggle_fog", recs, manifest)


# ---------------------------------------------------------------- hd_accel
def ingest_hd_accel(manifest):
    import pandas as pd
    recs = []
    for f in sorted(glob.glob(os.path.join(REPO, "datasets/imu/hd_accel_jnet/raw/*.csv"))):
        b = os.path.basename(f)
        if b.startswith("._") or "metadata" in b:
            continue
        df = pd.read_csv(f)
        if not {"x", "y", "z"} <= set(df.columns):
            continue
        loc = {"wrist_L": acc3(df["x"].values, df["y"].values, df["z"].values)}
        lab = df["label"].values if "label" in df.columns else None
        # the deposit (zenodo 14384260) states GENEActiv at 100 Hz; the
        # CSVs carry no time column (fps was None until 2026-09-17)
        recs.append(make_record(loc, 100.0, f"hd_accel:{b[:-4]}", b[:-4],
                                "hd_accel_jnet", lab))
    save("hd_accel_jnet", recs, manifest)


def acc_to_g(a):
    """Auto-detect accel unit: |acc| ~1 => already g; ~9.8 => m/s^2."""
    m = np.nanmedian(np.linalg.norm(a, axis=1))
    return a / G if m > 5 else a


def deg(x):
    return np.rad2deg(x)


# ---------------------------------------------------------------- fog_star
def ingest_fog_star(manifest):
    import pandas as pd
    df = pd.read_csv(os.path.join(REPO, "datasets/imu/fog_star/raw/sensor_data.csv"))
    locmap = {"ankleL": "ankle_L", "ankleR": "ankle_R", "back": "lower_back",
              "wrist": "wrist_L"}
    recs = []
    for (subj, sess, task), g in df.groupby(["subjectID", "sessionID", "taskID"]):
        loc = {}
        for src, dst in locmap.items():
            acc = acc_to_g(g[[f"{src}_acc_x", f"{src}_acc_y", f"{src}_acc_z"]].values)
            gy = g[[f"{src}_gyro_x", f"{src}_gyro_y", f"{src}_gyro_z"]].values
            loc[dst] = {"acc_x": acc[:, 0], "acc_y": acc[:, 1], "acc_z": acc[:, 2],
                        "gyro_x": gy[:, 0], "gyro_y": gy[:, 1], "gyro_z": gy[:, 2]}
        lab = g["fog"].values if "fog" in g else None
        recs.append(make_record(loc, 60.0, f"fog_star:{subj}", f"s{sess}_t{task}",
                                "fog_star", lab))
    save("fog_star", recs, manifest)


# ---------------------------------------------------------------- clinical_gait
def ingest_clinical_gait(manifest):
    import pandas as pd
    z = zipfile.ZipFile(os.path.join(
        REPO, "datasets/imu/clinical_gait_multipatho/raw/dataset.zip"))
    LOC = {"RF": "foot_R", "LF": "foot_L", "LB": "lower_back", "HE": "head"}
    trials = {}
    for n in z.namelist():
        b = os.path.basename(n)
        if not b.endswith(".txt") or "_raw_data_" not in b:
            continue
        stem, loc = b[:-4].rsplit("_raw_data_", 1)
        if loc in LOC:
            trials.setdefault(stem, {})[loc] = n
    recs = []
    for stem, files in sorted(trials.items()):
        loc_data, Ts = {}, []
        parsed = {}
        for loc, n in files.items():
            d = pd.read_csv(io.BytesIO(z.read(n)), sep="\t")
            parsed[loc] = d
            Ts.append(len(d))
        T = min(Ts)
        for loc, d in parsed.items():
            acc = acc_to_g(d[["Acc_X", "Acc_Y", "Acc_Z"]].values[:T])
            gy = deg(d[["Gyr_X", "Gyr_Y", "Gyr_Z"]].values[:T])
            mg = d[["Mag_X", "Mag_Y", "Mag_Z"]].values[:T]
            loc_data[LOC[loc]] = {
                "acc_x": acc[:, 0], "acc_y": acc[:, 1], "acc_z": acc[:, 2],
                "gyro_x": gy[:, 0], "gyro_y": gy[:, 1], "gyro_z": gy[:, 2],
                "mag_x": mg[:, 0], "mag_y": mg[:, 1], "mag_z": mg[:, 2]}
        parts = stem.split("_")
        subj = "_".join(parts[:2])                  # pathology_subject e.g. HS_70
        recs.append(make_record(loc_data, 100.0, f"clinical_gait:{subj}", stem,
                                "clinical_gait_multipatho",
                                extra={"mag_unit": MAG_NORMALIZED}))
    save("clinical_gait_multipatho", recs, manifest)


# ---------------------------------------------------------------- fog_turning
def ingest_fog_turning(manifest):
    z = zipfile.ZipFile(glob.glob(os.path.join(
        REPO, "datasets/pose/fog_turning_filho/raw/*.zip"))[0])
    recs = []
    for n in sorted(x for x in z.namelist() if x.endswith(".txt")):
        ls = [l for l in z.read(n).decode("latin-1").splitlines() if l.strip()]
        a = np.array([[float(v) for v in l.split("\t")] for l in ls[1:]
                      if len(l.split("\t")) >= 7])
        if a.size == 0:
            continue
        # cols: Frame, Time, ACC ML/AP/SI [g], GYR ML/AP [deg/s]
        loc = {"lower_back": {"acc_x": a[:, 2], "acc_y": a[:, 3], "acc_z": a[:, 4],
                              "gyro_x": a[:, 5], "gyro_y": a[:, 6]}}
        subj = os.path.basename(n).split("_")[0]
        recs.append(make_record(loc, 128.0, f"fog_turning:{subj}",
                                os.path.basename(n)[:-4], "fog_turning_filho"))
    save("fog_turning_filho", recs, manifest)


# ---------------------------------------------------------------- capture24
def ingest_capture24(manifest, win=3000, n_win=20):
    """Healthy free-living wrist accel; window into 30 s (100 Hz) and subsample."""
    import gzip
    z = zipfile.ZipFile(os.path.join(REPO, "datasets/socle/capture24/raw/capture24.zip"))
    recs = []
    for n in sorted(x for x in z.namelist() if x.endswith(".csv.gz")):
        subj = os.path.basename(n).split(".")[0]
        buf = io.TextIOWrapper(gzip.open(io.BytesIO(z.read(n))))
        buf.readline()                                    # header
        rows = []
        for i, line in enumerate(buf):
            if i >= win * n_win:
                break
            p = line.split(",")
            rows.append((float(p[1]), float(p[2]), float(p[3])))
        a = np.array(rows)
        for w in range(min(n_win, len(a) // win)):
            seg = a[w * win:(w + 1) * win]
            loc = {"wrist_L": acc3(seg[:, 0], seg[:, 1], seg[:, 2])}
            recs.append(make_record(loc, 100.0, f"capture24:{subj}", f"w{w}",
                                    "capture24"))
    save("capture24", recs, manifest)


# ---------------------------------------------------------------- imu_inthewild
def ingest_imu_inthewild(manifest, max_sessions=30):
    z = zipfile.ZipFile(os.path.join(
        REPO, "datasets/imu/imu_inthewild_iprognosis/raw",
        "i-PROGNOSIS_DS2.10_Sub1_IMUdataPhonecalls.zip"))
    data = pickle.loads(z.read("tremor_dataset.pickle"))
    recs = []
    for e in data:
        subj = e["subject_id"]
        for si, s in enumerate(e["sessions"][:max_sessions]):
            a = np.asarray(s)
            if a.ndim != 2 or a.shape[1] < 4 or a.shape[0] < 10:
                continue
            # column 0 is a phone timestamp in NANOSECONDS: a session spans
            # at most 75 s by the deposit's description, and the spans read
            # 75.0e9 (checked 2026-09-17; the rate used to be computed as if
            # the stamps were seconds, 2e-7 Hz). Phones sample irregularly:
            # fps is the median rate of the session, 99-1000 Hz across phones.
            ts = a[:, 0]
            dt = np.median(np.diff(ts))
            fps = float(1e9 / dt) if dt > 0 else None
            acc = acc_to_g(a[:, 1:4])
            loc = {"pocket": acc3(acc[:, 0], acc[:, 1], acc[:, 2])}
            recs.append(make_record(loc, fps, f"imu_inthewild:{subj}", f"sess{si}",
                                    "imu_inthewild_iprognosis"))
    save("imu_inthewild_iprognosis", recs, manifest)


# ---------------------------------------------------------------- monipar
def ingest_monipar(manifest):
    from scipy.io import loadmat
    d = loadmat(os.path.join(REPO, "datasets/imu/monipar/raw/MONIPAR_PD_SUPERVISED.mat"),
                squeeze_me=True, struct_as_record=False)
    cells = d["SUPERVISED_RAWDATA"]          # (6,8) cell array of (T,5)
    recs = []
    for i in range(cells.shape[0]):
        for j in range(cells.shape[1]):
            c = np.asarray(cells[i, j])
            if c.ndim != 2 or c.shape[1] < 4 or c.shape[0] < 10:
                continue
            t = c[:, 0]
            dt = np.median(np.diff(t))            # time in ms
            fps = float(1000.0 / dt) if dt > 1e-6 else None
            acc = acc_to_g(c[:, 1:4])
            loc = {"wrist_L": acc3(acc[:, 0], acc[:, 1], acc[:, 2])}
            lab = c[:, 4] if c.shape[1] >= 5 else None
            recs.append(make_record(loc, fps, f"monipar:sup_r{i}c{j}", f"r{i}c{j}",
                                    "monipar", lab))
    save("monipar", recs, manifest)


# ---------------------------------------------------------------- weargait (CSV)
WEARGAIT_LOCMAP = {"Forehead": "head", "Xiphoid": "trunk", "LowerBack": "lower_back",
                   "L_Wrist": "wrist_L", "R_Wrist": "wrist_R",
                   "L_MidLatThigh": "thigh_L", "R_MidLatThigh": "thigh_R",
                   "L_LatShank": "shank_L", "R_LatShank": "shank_R",
                   "L_Ankle": "ankle_L", "R_Ankle": "ankle_R",
                   "L_DorsalFoot": "foot_L", "R_DorsalFoot": "foot_R"}
WEARGAIT_SUF = {"acc_x": "Acc_X", "acc_y": "Acc_Y", "acc_z": "Acc_Z",
                "gyro_x": "Gyr_X", "gyro_y": "Gyr_Y", "gyro_z": "Gyr_Z",
                "mag_x": "Mag_X", "mag_y": "Mag_Y", "mag_z": "Mag_Z"}


def _weargait_files():
    """The per-trial CSVs, sorted (deterministic record order; the order
    of the 2026-09-08 container followed the ingestion volume's listing)."""
    out = []
    for f in glob.glob(os.path.join(
            REPO, "datasets/imu/weargait_pd/raw/**/CSV files/*.csv"), recursive=True):
        b = os.path.basename(f)
        if b.startswith("._") or "Demographic" in b or "Metrics" in b:
            continue
        out.append(f)
    return sorted(out)


def _weargait_record(f):
    import pandas as pd
    b = os.path.basename(f)
    try:
        df = pd.read_csv(f, low_memory=False)
    except Exception:
        return None
    cols = set(df.columns)
    loc = {}
    for pre, dst in WEARGAIT_LOCMAP.items():
        if f"{pre}_Acc_X" not in cols:
            continue
        d = {}
        for ch, suf in WEARGAIT_SUF.items():
            c = f"{pre}_{suf}"
            if c in cols:
                # missing samples stay NaN so make_record marks them in
                # sample_valid (2026-09-17: they were zeroed here, which hid
                # dropouts and, with more than half a trace missing, pulled
                # the median under the m/s2 test: 20 traces were stored in
                # m/s2 under the unit g)
                d[ch] = pd.to_numeric(df[c], errors="coerce").values.astype(float)
        acc = acc_to_g(np.stack([d["acc_x"], d["acc_y"], d["acc_z"]], -1))
        d["acc_x"], d["acc_y"], d["acc_z"] = acc[:, 0], acc[:, 1], acc[:, 2]
        # Xsens exports: gyroscope in rad/s (an ankle's p99 read ~4, i.e.
        # ~250 deg/s; it was stored as deg/s until 2026-09-17), magnetometer
        # normalized to the local field (declared in mag_unit)
        for k in ("gyro_x", "gyro_y", "gyro_z"):
            if k in d:
                d[k] = deg(d[k])
        loc[dst] = d
    if not loc:
        return None
    parts = b[:-4].split("_")
    return make_record(loc, 100.0, f"weargait:{parts[0]}",
                       "_".join(parts[1:]) or "rec", "weargait_pd",
                       extra={"mag_unit": MAG_NORMALIZED})


def ingest_weargait(manifest):
    def stream():
        for f in _weargait_files():
            rec = _weargait_record(f)
            if rec is not None:
                yield rec
    save("weargait_pd", stream(), manifest)


SOURCES = {"weargait": ingest_weargait, "monipar": ingest_monipar,
           "daphnet": ingest_daphnet, "kaggle_fog": ingest_kaggle_fog,
           "hd_accel": ingest_hd_accel, "fog_star": ingest_fog_star,
           "clinical_gait": ingest_clinical_gait, "fog_turning": ingest_fog_turning,
           "capture24": ingest_capture24, "imu_inthewild": ingest_imu_inthewild}
HEADER = ["source", "subject_ns", "task", "fps", "n_frames", "locations"]


def _merge_in_place(old_rows, new_rows):
    """The rebuilt sources' rows replace theirs where they stood (the first
    old row of each source); the other sources' rows are kept untouched."""
    by_src = {}
    for r in new_rows:
        by_src.setdefault(str(r[0]), []).append(r)
    out, done, kept = [], set(), 0
    for r in old_rows:
        if not r:
            continue
        s = r[0]
        if s in by_src:
            if s not in done:
                out.extend(by_src[s]); done.add(s)
            continue
        out.append(r); kept += 1
    for s, rows in by_src.items():
        if s not in done:
            out.extend(rows)
    return out, kept


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None,
                    help="comma list among: " + ",".join(SOURCES))
    args = ap.parse_args()
    todo = list(SOURCES) if not args.only else [x.strip() for x in args.only.split(",")]
    for t in todo:
        if t not in SOURCES:
            raise SystemExit(f"unknown source {t!r}; known: {', '.join(SOURCES)}")

    manifest = []
    for t in todo:
        SOURCES[t](manifest)

    mp = os.path.join(REPO, "datasets/_canonical_imu_manifest.csv")
    if args.only and os.path.exists(mp):
        # MERGE, never clobber: the central manifest also carries sources ingested
        # by other scripts (pads, sixmwt_lifespan, multimodal_fog). Rewriting it
        # wholesale from a partial run would silently delete them.
        with open(mp, newline="") as f:
            rows = list(csv.reader(f))
        head, old_rows = rows[0], rows[1:]
        manifest, kept = _merge_in_place(old_rows, manifest)
        print(f"merged: kept {kept} rows from other sources")
    with open(mp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(manifest)
    print(f"\ntotal {len(manifest)} recordings -> {mp}")


if __name__ == "__main__":
    main()
