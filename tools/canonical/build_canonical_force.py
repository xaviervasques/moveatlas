"""Ingest plantar-force / VGRF datasets into the canonical force contract.

Contract: configs/canonical_force.yaml. Per sample:
    force        (T, 2, 9)  float32   feet x [8 insole positions + total]; absent -> 0
    sensor_mask  (2, 9)     bool      which positions present per foot
    fps          float
    subject_ns, task, source, label(optional)

gaitpdb: 8 sensors/insole + total per foot (text, 100 Hz).
gaitndd: totals only (wfdb, 300 Hz); insole positions masked.

Env: atlas-mouvement (wfdb). Usage: python build_canonical_force.py
"""
import os
import csv
import glob
import zipfile
import tempfile
import numpy as np

REPO = os.path.dirname(os.path.abspath(__file__))
# record-level declaration for sources whose force is not in newtons
UNCALIBRATED = {"unit": "unknown",
                "calibration": "uncalibrated force-sensitive resistor output"}
# force grid: 8 insole positions (0..7) + total (8), per foot
NPOS = 9


def make_record(footL, footR, maskL, maskR, fps, subject_ns, task, source,
                extra=None):
    T = footL.shape[0]
    force = np.zeros((T, 2, NPOS), np.float32)
    force[:, 0, :] = np.nan_to_num(footL)
    force[:, 1, :] = np.nan_to_num(footR)
    mask = np.stack([maskL, maskR])
    rec = {"force": force, "sensor_mask": mask, "fps": fps,
           "subject_ns": subject_ns, "task": task, "source": source, "n_frames": T}
    if extra:
        rec.update(extra)
    return rec


def save(source, recs, manifest):
    out = os.path.join(REPO, "datasets/imu", source, "processed")
    os.makedirs(out, exist_ok=True)
    # straight to the moveatlas-record/1 container (pickle retired 2026-09-17)
    from moveatlas import records as _records
    _records.save(os.path.join(out, "canonical_force.npz"), recs)
    for r in recs:
        manifest.append([source, r["subject_ns"], r["task"], r["fps"], r["n_frames"]])
    print(f"  {source}: {len(recs)} recordings, "
          f"{len({r['subject_ns'] for r in recs})} subjects")


def ingest_gaitpdb(manifest):
    z = zipfile.ZipFile(os.path.join(
        REPO, "datasets/imu/physionet_gaitpdb/raw/gaitpdb.zip"))
    full = np.ones(NPOS, bool)                       # all 8 positions + total present
    recs = []
    for n in sorted(x for x in z.namelist() if x.endswith(".txt")):
        b = os.path.basename(n)
        if "_" not in b or not b[:2] in ("Ga", "Ju", "Si"):
            continue
        a = np.array([[float(v) for v in ln.split()]
                      for ln in z.read(n).decode().splitlines() if ln.strip()])
        if a.shape[1] < 19:
            continue
        footL = np.concatenate([a[:, 1:9], a[:, 17:18]], axis=1)   # L1..L8 + total_L
        footR = np.concatenate([a[:, 9:17], a[:, 18:19]], axis=1)  # R1..R8 + total_R
        subj, walk = b[:-4].split("_")
        recs.append(make_record(footL, footR, full, full, 100.0,
                                f"gaitpdb:{subj}", b[:-4], "physionet_gaitpdb"))
    save("physionet_gaitpdb", recs, manifest)


def ingest_gaitndd(manifest):
    import wfdb
    z = zipfile.ZipFile(os.path.join(REPO, "datasets/imu/gaitndd/raw/gaitndd.zip"))
    heas = sorted(n for n in z.namelist() if n.endswith(".hea"))
    tmask = np.zeros(NPOS, bool); tmask[8] = True     # total only
    recs = []
    with tempfile.TemporaryDirectory() as td:
        z.extractall(td)
        root = os.path.join(td, os.path.dirname(heas[0])) if "/" in heas[0] else td
        for h in heas:
            rec_name = os.path.basename(h)[:-4]
            try:
                sig, _ = wfdb.rdsamp(os.path.join(root, rec_name))
            except Exception:
                continue
            if sig.shape[1] < 2:
                continue
            footL = np.zeros((sig.shape[0], NPOS)); footL[:, 8] = sig[:, 0]
            footR = np.zeros((sig.shape[0], NPOS)); footR[:, 8] = sig[:, 1]
            # the source's force-sensitive resistors are not calibrated:
            # the values are sensor outputs (about -2 to 1.1), not newtons.
            # Kept as recorded, never rescaled (2026-09-17; the contract's
            # unit N was implied until then).
            recs.append(make_record(footL, footR, tmask, tmask, 300.0,
                                    f"gaitndd:{rec_name}", rec_name, "gaitndd",
                                    extra=UNCALIBRATED))
    save("gaitndd", recs, manifest)


def ingest_weargait_force(manifest):
    """WearGait insole force. The 16 per-foot pressure cells (LPressure1..16) have an
    UNDOCUMENTED cell->anatomy layout, so we do NOT map them to the 8 anatomical
    positions (mis-map risk). We ingest the unambiguous per-foot total (L/R TotalForce)
    as totals-only, exactly like gaitndd. The raw 16-cell arrays are left for later if
    the insole layout is documented."""
    import pandas as pd
    tmask = np.zeros(NPOS, bool); tmask[8] = True     # total only
    recs = []
    for f in glob.glob(os.path.join(
            REPO, "datasets/imu/weargait_pd/raw/**/CSV files/*.csv"), recursive=True):
        b = os.path.basename(f)
        if b.startswith("._") or "Demographic" in b or "Metrics" in b:
            continue
        try:
            df = pd.read_csv(f, low_memory=False)
        except Exception:
            continue
        if "LTotalForce" not in df.columns or "RTotalForce" not in df.columns:
            continue
        lt = pd.to_numeric(df["LTotalForce"], errors="coerce").values
        rt = pd.to_numeric(df["RTotalForce"], errors="coerce").values
        if not (np.isfinite(lt).any() and np.isfinite(rt).any()):
            continue
        T = len(df)
        footL = np.zeros((T, NPOS)); footL[:, 8] = lt
        footR = np.zeros((T, NPOS)); footR[:, 8] = rt
        parts = b[:-4].split("_")
        recs.append(make_record(footL, footR, tmask, tmask, 100.0,
                                f"weargait:{parts[0]}", "_".join(parts[1:]) or "rec",
                                "weargait_pd"))
    save("weargait_pd", recs, manifest)


SOURCES = {"gaitpdb": ingest_gaitpdb, "gaitndd": ingest_gaitndd,
           "weargait": ingest_weargait_force}
HEADER = ["source", "subject_ns", "task", "fps", "n_frames"]


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
    mp = os.path.join(REPO, "datasets/_canonical_force_manifest.csv")
    if args.only and os.path.exists(mp):
        # merge, never clobber the rows of the sources not rebuilt
        with open(mp, newline="") as f:
            old_rows = list(csv.reader(f))[1:]
        manifest, kept = _merge_in_place(old_rows, manifest)
        print(f"merged: kept {kept} rows from other sources")
    with open(mp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "task", "fps", "n_frames"])
        w.writerows(manifest)
    print(f"\ntotal {len(manifest)} recordings -> {mp}")


if __name__ == "__main__":
    main()
