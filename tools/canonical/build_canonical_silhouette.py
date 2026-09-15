"""Ingest SAM3 dense-silhouette timeseries into the canonical SILHOUETTE contract.

Contract: configs/canonical_silhouette.yaml. A third pose-family modality, distinct from
the 15-joint skeleton and from the signal contracts. SAM3 gives a body-mask outline (no
reliable joints), so we keep the 64-point resampled contour + 8 shape scalars.

Per recording (one video) we store:
    contour      (T, 64, 2)  float32   normalized silhouette outline
    scalars      (T, 8)      float32   [area, perimeter, solidity, extent,
                                        aspect_ratio, orientation_deg, major_axis, minor_axis]
    detect_mask  (T,)        bool      subject segmented this frame
    scalar_mask  (8,)        bool
    fps, scale, dim=2, modality="silhouette"
    subject_ns, cohort, severity, sequence, source

Normalization (mirrors the 2D pose contract): center on per-frame centroid, flip image-y,
scale by the per-recording median major-axis (person height in px). Size-dependent scalars
(area, perimeter, major/minor axis) are divided by the same scale (area by scale^2).

Env: atlas-mouvement. Usage: python build_canonical_silhouette.py [SAM3_OUTPUTS_DIR]
"""
import os
import re
import csv
import sys
import glob
import pickle
import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))

# default location of the SAM3 outputs the owner produced for koa_pd_nm
DEFAULT_KOA = os.path.join(REPO, "builder_inputs/KOA-PD-NM/outputs")

SCALARS = ["area", "perimeter", "solidity", "extent",
           "aspect_ratio", "orientation_deg", "major_axis", "minor_axis"]
SIZE_DEP = {"area", "perimeter", "major_axis", "minor_axis"}
# source column for each scalar (px-named ones get normalized)
SRC_COL = {"area": "area_px", "perimeter": "perimeter_px", "solidity": "solidity",
           "extent": "extent", "aspect_ratio": "aspect_ratio",
           "orientation_deg": "orientation_deg", "major_axis": "major_axis_px",
           "minor_axis": "minor_axis_px"}
NC = 64  # contour points

COHORT_NAME = {"KOA": "knee_osteoarthritis", "PD": "parkinson", "NM": "healthy"}
SEV_NAME = {"EL": "early", "MD": "moderate", "SV": "severe", "ML": "mild", "NA": "none"}

# <num>_<COH>_<seq>[_<SEV>]_sam3_timeseries.xlsx
FNAME = re.compile(r"(\d+)_([A-Z]+)_(\d+)(?:_([A-Z]+))?_sam3_timeseries\.xlsx$")


def parse_name(basename):
    m = FNAME.match(basename)
    if not m:
        return None
    num, coh, seq, sev = m.groups()
    sev = sev or "NA"
    subject_ns = f"koa_{coh}_{sev}_{num}"       # severity partitions subjects
    return subject_ns, coh, sev, seq


def load_one(path):
    df = pd.read_excel(path)
    T = len(df)
    det = df["patient_detected"].fillna(0).astype(int).values.astype(bool)

    # fps from time_s (native per recording)
    t = df["time_s"].values.astype(float)
    dt = np.median(np.diff(t)) if T > 1 else np.nan
    fps = float(1.0 / dt) if dt and dt > 0 else None

    cx = df["centroid_x"].values.astype(np.float32)
    cy = df["centroid_y"].values.astype(np.float32)

    # per-recording scale = median major-axis over detected frames (person height, px)
    maj = df["major_axis_px"].values.astype(np.float32)
    valid_maj = maj[det & np.isfinite(maj) & (maj > 0)]
    scale = float(np.median(valid_maj)) if valid_maj.size else 1.0
    if not np.isfinite(scale) or scale <= 0:
        scale = 1.0

    # contour (T, 64, 2): center on centroid, flip y, scale
    contour = np.zeros((T, NC, 2), np.float32)
    for i in range(NC):
        cxi = df[f"contour_{i:03d}_x"].values.astype(np.float32)
        cyi = df[f"contour_{i:03d}_y"].values.astype(np.float32)
        contour[:, i, 0] = (cxi - cx) / scale
        contour[:, i, 1] = -(cyi - cy) / scale        # flip image-y -> up positive
    # undetected / non-finite frames -> zero, masked by detect_mask
    bad = ~det | ~np.isfinite(contour).all(axis=(1, 2))
    contour[bad] = 0.0
    detect = det & ~bad

    # scalars (T, 8)
    scalars = np.zeros((T, len(SCALARS)), np.float32)
    for j, name in enumerate(SCALARS):
        col = df[SRC_COL[name]].values.astype(np.float32)
        if name in SIZE_DEP:
            div = scale * scale if name == "area" else scale
            col = col / div
        scalars[:, j] = col
    scalars[~detect] = 0.0
    scalars = np.nan_to_num(scalars, nan=0.0, posinf=0.0, neginf=0.0)

    return contour, scalars, detect, fps, scale, T


def ingest_koa(src_dir, manifest):
    files = sorted(glob.glob(os.path.join(src_dir, "P*", "*_sam3_timeseries.xlsx")))
    files = [f for f in files if not os.path.basename(f).startswith("._")]
    recs = []
    for f in files:
        meta = parse_name(os.path.basename(f))
        if meta is None:
            print(f"  SKIP unparsed: {os.path.basename(f)}")
            continue
        subject_ns, coh, sev, seq = meta
        contour, scalars, detect, fps, scale, T = load_one(f)
        recs.append({
            "contour": contour, "scalars": scalars, "detect_mask": detect,
            "scalar_mask": np.ones(len(SCALARS), bool),
            "fps": fps, "scale": scale, "dim": 2, "modality": "silhouette",
            "subject_ns": subject_ns, "cohort": COHORT_NAME.get(coh, coh),
            "severity": SEV_NAME.get(sev, sev), "sequence": seq,
            "source": "koa_pd_nm", "n_frames": T,
        })
    save("koa_pd_nm", recs, manifest)
    return recs


# ------------------------------------------------------------- CODY external
CODY_ROOT = os.path.join(REPO, "datasets/pose/cody_3/raw/06_external_sam3_outputs")
CODY_LABELS = os.path.join(REPO, "datasets/pose/cody_3/raw/dataset_inference.xlsx")
RATERS = ["LC", "DD", "MCJ", "CH", "TW"]
PHENOMS = ["Dystonia", "Tremor", "Chorea", "Athetosis", "Myoclonus", "Ballismus",
           "Stereotypies", "Tics"]


def load_cody_labels():
    """dataset_inference.xlsx -> {(dataset_num, subject): (5 raters, 8 phenoms) int8}.
    5 rater blocks of 8 phenomenologies; only a few external subjects are rated."""
    if not os.path.exists(CODY_LABELS):
        return {}
    df = pd.read_excel(CODY_LABELS, header=None)
    # row 0 = rater names, row 1 = phenom names, rows 2.. = subjects
    out = {}
    cur_ds = None
    for _, row in df.iloc[2:].iterrows():
        ds = row[0]
        if isinstance(ds, str) and ds.strip():
            cur_ds = ds.strip().replace("Dataset_", "")
        subj = row[1]
        if not (isinstance(subj, str) and subj.strip()):
            continue
        vals = pd.to_numeric(row[2:2 + len(RATERS) * len(PHENOMS)],
                             errors="coerce").values
        out[(cur_ds, subj.strip())] = vals.reshape(len(RATERS), len(PHENOMS)).astype(
            np.int8)
    return out


def ingest_cody_external(manifest):
    labels = load_cody_labels()
    files = sorted(f for f in glob.glob(
        os.path.join(CODY_ROOT, "dataset_*", "P*", "*_sam3_timeseries.xlsx"))
        if not os.path.basename(f).startswith("._"))
    recs = []
    for f in files:
        parts = f.split(os.sep)
        ds = parts[-3].replace("dataset_", "")          # "1" / "2" / "3"
        subj = parts[-2]                                 # "P28"
        subject_ns = f"cody_ext_ds{ds}_{subj}"           # leakage-safe per dataset
        rec_id = os.path.basename(f).replace("_sam3_timeseries.xlsx", "")
        contour, scalars, detect, fps, scale, T = load_one(f)
        rec = {
            "contour": contour, "scalars": scalars, "detect_mask": detect,
            "scalar_mask": np.ones(len(SCALARS), bool),
            "fps": fps, "scale": scale, "dim": 2, "modality": "silhouette",
            "subject_ns": subject_ns, "cohort": "hyperkinetic_external",
            "severity": "", "sequence": rec_id,
            "source": "cody_external", "n_frames": T,
        }
        lab = labels.get((ds, subj))
        if lab is not None:
            rec["labels"] = lab            # (5 raters, 8 phenoms), eval only
            rec["label_raters"] = RATERS
            rec["label_phenoms"] = PHENOMS
        recs.append(rec)
    save("cody_external", recs, manifest, out_folder="cody_3")
    n_lab = sum("labels" in r for r in recs)
    print(f"    ({n_lab} recordings carry multi-rater phenomenology labels)")
    return recs


def save(source, recs, manifest, out_folder=None):
    out = os.path.join(REPO, "datasets/pose", out_folder or source, "processed")
    os.makedirs(out, exist_ok=True)
    pickle.dump(recs, open(os.path.join(out, "canonical_silhouette.pkl"), "wb"))
    for r in recs:
        manifest.append([source, r["subject_ns"], r["cohort"], r["severity"],
                         r["sequence"], round(r["fps"], 2) if r["fps"] else "",
                         r["n_frames"], int(r["detect_mask"].sum()),
                         round(r["scale"], 1)])
    print(f"  {source}: {len(recs)} recordings, "
          f"{len({r['subject_ns'] for r in recs})} subjects")


def main():
    koa_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_KOA
    manifest = []
    print(f"koa_pd_nm SAM3 source: {koa_dir}")
    ingest_koa(koa_dir, manifest)
    print("CODY external SAM3 source:", CODY_ROOT)
    ingest_cody_external(manifest)
    mp = os.path.join(REPO, "datasets/_canonical_silhouette_manifest.csv")
    with open(mp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "subject_ns", "cohort", "severity", "sequence",
                    "fps", "n_frames", "n_detected", "scale_px"])
        w.writerows(manifest)
    print(f"\ntotal {len(manifest)} recordings -> {mp}")


if __name__ == "__main__":
    main()
