"""Ingest AMASS into the canonical skeleton (healthy 3D base).

Runs the SMPL+H body model (human_body_prior + the AMASS SMPL+H model in
body_models/smplh) forward on each motion's parameters to get 3D joint positions,
takes the 22 SMPL body joints, converts AMASS z-up -> y-up (to match the other 3D
sources), maps SMPL 22 -> canonical 15, normalizes (root-center on pelvis, scale by
torso), and shards per sub-dataset. Native fps is kept per sample (no decimation).

MUST run in the `smpl` conda env (torch, smplx, human_body_prior). Uses Apple MPS if
available. Usage: ~/miniconda3/envs/smpl/bin/python build_canonical_amass.py
"""
import os
import io
import csv
import glob
import tarfile
import pickle
import numpy as np
import torch

# smplx's lbs dropped the `dtype` kwarg that human_body_prior still passes; drop it.
import human_body_prior.body_model.body_model as hbm
_orig_lbs = hbm.lbs
hbm.lbs = lambda *a, **k: (k.pop("dtype", None), _orig_lbs(*a, **k))[1]
from human_body_prior.body_model.body_model import BodyModel

REPO = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(REPO, "datasets/socle/amass/raw")
OUT = os.path.join(REPO, "datasets/socle/amass/processed/canonical")
WORK = os.path.join(REPO, "temporary/amass_work")
# CPU is robust and, for this small-batch LBS, nearly as fast as MPS (whose padding op
# is slow and, over a very long run, deadlocks). Force CPU to avoid the MPS hang.
DEV = "cpu"
CHUNK = 4000                       # frames per forward pass

# canonical 15 <- SMPL 22 joint indices (SMPL order verified)
SEL = [0, 12, 15, 16, 17, 18, 19, 20, 21, 1, 2, 4, 5, 7, 8]
ROOT_I, NECK_I = 0, 1              # positions of pelvis, neck in canonical order


def load_models():
    return {g: BodyModel(bm_path=os.path.join(REPO, f"body_models/smplh/{g}/model.npz"),
                         model_type="smplh", num_betas=16, batch_size=1).to(DEV)
            for g in ("male", "female", "neutral")}


def joints_for(npz, models):
    poses = npz["poses"]
    if poses.ndim != 2 or poses.shape[1] < 156:
        return None, None
    T = poses.shape[0]
    g = npz["gender"].item()
    g = g.decode() if isinstance(g, bytes) else str(g)
    g = g if g in models else "neutral"
    bm = models[g]
    betas = np.zeros((16,), np.float32)
    b = npz["betas"][:16]
    betas[:len(b)] = b
    trans = npz["trans"].astype(np.float32)
    fps = float(npz["mocap_framerate"]) if "mocap_framerate" in npz else None
    out = []
    for s in range(0, T, CHUNK):
        e = min(s + CHUNK, T)
        p = torch.tensor(poses[s:e, :156], dtype=torch.float32, device=DEV)
        tr = torch.tensor(trans[s:e], dtype=torch.float32, device=DEV)
        be = torch.tensor(betas, device=DEV).unsqueeze(0).repeat(e - s, 1)
        with torch.no_grad():
            body = bm(root_orient=p[:, :3], pose_body=p[:, 3:66],
                      pose_hand=p[:, 66:156], trans=tr, betas=be)
        out.append(body.Jtr[:, :22].cpu().numpy())
    J = np.concatenate(out, 0)                       # (T,22,3) z-up
    J = np.stack([J[..., 0], J[..., 2], -J[..., 1]], -1)   # z-up -> y-up
    return J, fps


def normalize(canon):
    c = canon.astype(float) - canon[:, ROOT_I:ROOT_I + 1, :]
    torso = np.linalg.norm(c[:, NECK_I] - c[:, ROOT_I], axis=-1)
    good = torso[np.isfinite(torso) & (torso > 1e-6)]
    scale = float(np.median(good)) if good.size else 1.0
    return (c / scale).astype(np.float32), scale


def make_record(ns, take, canon, fps):
    coords, scale = normalize(canon)
    return {"coords": coords, "coord_mask": np.array([True, True, True]),
            "joint_mask": np.ones(15, bool), "valid_mask": np.ones(coords.shape[:2], bool),
            "dim": 3, "fps": fps, "modality": "3d_meter", "source": "amass",
            "subject_ns": ns, "take": take, "n_frames": int(coords.shape[0]),
            "scale": scale}


def main():
    os.makedirs(OUT, exist_ok=True)
    models = load_models()
    print("device:", DEV)
    mf = open(os.path.join(REPO, "datasets/socle/amass/processed",
                           "canonical_manifest.csv"), "w", newline="")
    mw = csv.writer(mf)
    mw.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])
    total, bad = 0, 0
    for tb in sorted(glob.glob(os.path.join(RAW, "*.tar.bz2"))):
        sub = os.path.basename(tb).replace(".tar.bz2", "")
        if os.path.exists(os.path.join(OUT, f"amass_{sub}.pkl")):
            print(f"  {sub}: shard exists, skip (resume)", flush=True)
            continue
        wd = os.path.join(WORK, sub)
        os.makedirs(wd, exist_ok=True)
        with tarfile.open(tb, "r:bz2") as t:
            t.extractall(wd)
        shard = []
        for f in glob.glob(os.path.join(wd, "**", "*.npz"), recursive=True):
            b = os.path.basename(f)
            if b.startswith("._") or "shape" in b.lower() or "neutral" in b.lower():
                continue
            try:
                npz = np.load(f, allow_pickle=True)
                if "poses" not in npz:
                    continue
                J, fps = joints_for(npz, models)
                if J is None:
                    bad += 1
                    continue
                canon = J[:, SEL, :]
                rel = os.path.relpath(f, wd)
                ns = f"amass:{sub}:{os.path.dirname(rel).replace(os.sep, '_')}"
                rec = make_record(ns, rel.replace(os.sep, "/"), canon, fps)
                shard.append(rec)
                mw.writerow([rec["source"], ns, rec["take"], 3, fps or "",
                             rec["n_frames"], "3d_meter"])
                total += 1
            except Exception:
                bad += 1
        if shard:
            pickle.dump(shard, open(os.path.join(OUT, f"amass_{sub}.pkl"), "wb"))
        # reclaim disk: drop the extracted params for this sub-dataset
        os.system(f'rm -rf "{wd}"')
        print(f"  {sub}: {len(shard)} motions (running total {total})", flush=True)
    mf.close()
    # rebuild the FULL manifest from every shard on disk (incl. skipped/resumed ones)
    allrows = []
    for sp in sorted(glob.glob(os.path.join(OUT, "amass_*.pkl"))):
        for r in pickle.load(open(sp, "rb")):
            allrows.append([r["source"], r["subject_ns"], r["take"], 3,
                            r["fps"] or "", r["n_frames"], "3d_meter"])
    with open(os.path.join(REPO, "datasets/socle/amass/processed",
                           "canonical_manifest.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])
        w.writerows(allrows)
    print(f"\nAMASS canonical: {len(allrows)} motions total "
          f"({len(glob.glob(os.path.join(OUT, 'amass_*.pkl')))} shards), {bad} bad")


if __name__ == "__main__":
    main()
