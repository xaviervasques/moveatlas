"""Ingest Motion-X++ into the canonical skeleton (healthy 3D base).

Uses the motion_generation/new_joint/*.zip subsets: each clip is a (T, 52, 3) array
whose first 22 joints are the SMPL body skeleton (verified: hip/shoulder symmetry,
plausible bone lengths, y-up meters). We take [:, :22, :] and reuse the SMPL joint_map
(smpl_carepd) to produce canonical (T, 15, 3), 3D. Sharded per subset.

Healthy base: pretraining only, no labels, no subject index (clips come from mixed
sources; namespaced per clip). Env: atlas-mouvement. Usage: python build_canonical_motionx.py
"""
import os
import io
import csv
import glob
import json
import zipfile
import pickle
import numpy as np
from build_canonical import to_canonical, make_record, REPO

MX = os.path.join(REPO, "datasets/socle/motion_x/raw/motion_x_plusplus/"
                        "motion/motion_generation/new_joint")
OUT = os.path.join(REPO, "datasets/socle/motion_x/processed/canonical")
FPS = 30.0
# first 22 SMPL joint names (= HumanML3D body order); reuse CARE-PD's SMPL joint names
SMPL22 = json.load(open(os.path.join(
    REPO, "datasets/pose/care_pd/processed/smpl_joint_names.json")))[:22]


def main():
    os.makedirs(OUT, exist_ok=True)
    mf = open(os.path.join(REPO, "datasets/socle/motion_x/processed",
                           "canonical_manifest.csv"), "w", newline="")
    mw = csv.writer(mf)
    mw.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])
    total, bad = 0, 0
    for zp in sorted(glob.glob(os.path.join(MX, "*.zip"))):
        subset = os.path.basename(zp).replace(".zip", "")
        zf = zipfile.ZipFile(zp)
        shard = []
        for n in zf.namelist():
            if not n.endswith(".npy"):
                continue
            clip = os.path.basename(n).replace(".npy", "")
            try:
                arr = np.load(io.BytesIO(zf.read(n)), allow_pickle=True)
                if arr.ndim != 3 or arr.shape[1] < 22:
                    bad += 1
                    continue
                canon = to_canonical("smpl_carepd", SMPL22, arr[:, :22, :])
                ns = f"motionx:{subset}:{clip}"
                rec = make_record("motion_x", ns, clip, canon, 3, FPS)
                shard.append(rec)
                mw.writerow([rec["source"], ns, clip, 3, FPS, rec["n_frames"],
                             "3d_meter"])
                total += 1
            except Exception:
                bad += 1
        if shard:
            pickle.dump(shard, open(os.path.join(OUT, f"motionx_{subset}.pkl"), "wb"))
        print(f"  {subset}: {len(shard)} clips (running total {total})", flush=True)
    mf.close()
    print(f"\nMotion-X canonical: {total} samples, {bad} bad -> {OUT}/")


if __name__ == "__main__":
    main()
