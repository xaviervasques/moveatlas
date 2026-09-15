"""Ingest MODYS-video (DeepLabCut stick-figure 2D pose) into the canonical skeleton.

Chorea/dystonia (dyskinetic cerebral palsy), side-view lying protocol. Reads the DLC
csv per clip (bodypart x,y,likelihood), builds (T,14,2), maps to canonical 15 via the
modys_dlc mapping, uses DLC likelihood as the per-joint validity mask, normalizes.

Env: atlas-mouvement. Usage: python build_canonical_modys.py
"""
import os
import io
import csv
import glob
import zipfile
import pickle
import numpy as np
import pandas as pd
from build_canonical import to_canonical, make_record, REPO, CFG

ZIP = glob.glob(os.path.join(
    REPO, "datasets/pose/modys_video/raw/data_stickfigure*.zip"))[0]
OUT = os.path.join(REPO, "datasets/pose/modys_video/processed")
CONF = 0.5   # DLC likelihood below this -> joint marked invalid


def main():
    os.makedirs(OUT, exist_ok=True)
    zf = zipfile.ZipFile(ZIP)
    out, manifest = [], []
    for n in sorted(x for x in zf.namelist() if x.endswith(".csv")):
        df = pd.read_csv(io.StringIO(zf.read(n).decode()), header=[1, 2], index_col=0)
        bodyparts = list(dict.fromkeys(c[0] for c in df.columns))  # ordered unique
        coords = np.stack([df[(bp, "x")].values for bp in bodyparts]
                          + [df[(bp, "y")].values for bp in bodyparts], axis=-1)
        coords = coords.reshape(len(df), 2, len(bodyparts)).transpose(0, 2, 1)  # (T,14,2)
        like = np.stack([df[(bp, "likelihood")].values for bp in bodyparts], -1)  # (T,14)
        # low-confidence -> NaN so normalize/mask handles them
        c = coords.copy()
        c[like < CONF] = np.nan
        canon = to_canonical("modys_dlc", bodyparts, c)
        subj = os.path.basename(n).split("_")[0]           # 001, 002, ...
        rec = make_record("modys", f"modys:{subj}", os.path.basename(n)[:-4],
                          canon, 2, None)
        out.append(rec)
        manifest.append([rec["source"], rec["subject_ns"], rec["take"], 2, "",
                         rec["n_frames"], "2d_pixel"])
    pickle.dump(out, open(os.path.join(OUT, "canonical.pkl"), "wb"))
    with open(os.path.join(OUT, "canonical_manifest.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])
        w.writerows(manifest)
    print(f"MODYS canonical: {len(out)} clips, {len({m[1] for m in manifest})} subjects "
          f"-> {OUT}/canonical.pkl")


if __name__ == "__main__":
    main()
