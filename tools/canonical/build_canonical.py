"""Ingest processed datasets into the canonical skeleton contract.

Reads configs/canonical_skeleton.yaml and emits, per sample, a harmonized record:
    coords      (T, 15, 3)  float   canonical joints; z = 0 for 2D sources
    coord_mask  (3,)        bool    which coordinate axes are valid (z False for 2D)
    joint_mask  (15,)       bool    which canonical joints are populated (all True here)
    dim         2 | 3
    fps         float | None
    modality    '2d_pixel' | '3d_meter'
    source, subject_ns, take, n_frames
Normalization (from the YAML): root-center on pelvis, flip image-y to up for 2D,
scale by torso length (pelvis-neck). No 2D->3D lifting, no fps decimation.

This version ingests CARE-PD (3D) and Li/Taati communication+drinking (2D). CODY and
Li/Taati leg_agility (which carries _rst/_act state suffixes) are handled separately.

Env: atlas-mouvement. Usage: python build_canonical.py
Outputs: datasets/pose/<src>/processed/canonical.pkl  +  datasets/_canonical_manifest.csv
"""
import os
import csv
import glob
import json
import pickle
import numpy as np
import yaml

REPO = os.path.dirname(os.path.abspath(__file__))
CFG = yaml.safe_load(open(os.path.join(REPO, "configs", "canonical_skeleton.yaml")))
CANON = CFG["canonical_joints"]
ROOT_I = CANON.index(CFG["root_joint"])
REF_A, REF_B = [CANON.index(j) for j in CFG["reference_segment"]]
LI_TAATI_FPS = 30.0
LI_TAATI_FPS_PROVENANCE = ("30 fps: the video capture rate stated by the data paper (Li et al. "
                           "2018, J NeuroEng Rehabil 15:97, doi:10.1186/s12984-018-0446-z, "
                           "Methods); the paper does not say whether every frame was posed and "
                           "the export has no time field: nominal, not measured")


def resolve(rule, idx, coords):
    if "direct" in rule:
        return coords[:, idx[rule["direct"]], :]
    if "proxy" in rule:
        return coords[:, idx[rule["proxy"]], :]
    if "midpoint" in rule:
        a, b = rule["midpoint"]
        return 0.5 * (coords[:, idx[a], :] + coords[:, idx[b], :])
    raise ValueError(rule)


def to_canonical(source_key, names, coords):
    """coords (T, J, C) in source order -> (T, 15, C) in canonical order."""
    jmap = CFG["sources"][source_key]["joint_map"]
    idx = {n: i for i, n in enumerate(names)}
    T, _, C = coords.shape
    out = np.zeros((T, len(CANON), C), dtype=float)
    for j, cj in enumerate(CANON):
        out[:, j, :] = resolve(jmap[cj], idx, coords)
    return out


def normalize(coords, dim):
    """Root-center, flip image-y to up for 2D, scale by torso length. NaN-aware:
    undetected keypoints (NaN, common in video-derived pose) are handled without
    poisoning the statistics, and reported via a per-frame per-joint validity mask.
    coords (T,15,C) -> (coords_norm, scale, valid_mask (T,15))."""
    c = coords.astype(float).copy()
    valid = ~np.isnan(c).any(axis=-1)                   # (T,15) per-joint detection
    # a frame is usable if its ROOT is detected (root-centering needs it); a single
    # occluded limb must NOT invalidate the whole frame (side-view video has many).
    root_ok = np.isfinite(c[:, ROOT_I, :]).all(axis=-1)  # (T,)
    torso = np.linalg.norm(c[:, REF_A, :] - c[:, REF_B, :], axis=-1)  # (T,)
    good = torso[np.isfinite(torso) & (torso > 1e-6)]
    scale = float(np.median(good)) if good.size else 1.0
    c = c - c[:, ROOT_I:ROOT_I + 1, :]                  # root-center per frame
    if dim == 2:
        c[:, :, 1] = -c[:, :, 1]                        # image y down -> up
    c = c / scale
    valid = valid & root_ok[:, None]                    # joint valid if detected & root ok
    c = np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0)
    return c, scale, valid


def pad3(coords2d):
    """(T,15,2) -> (T,15,3) with z=0."""
    T, J, _ = coords2d.shape
    out = np.zeros((T, J, 3))
    out[:, :, :2] = coords2d
    return out


def make_record(source, subject_ns, take, coords_canon, dim, fps):
    coords, scale, valid = normalize(coords_canon, dim)
    if dim == 2:
        coords = pad3(coords)
        coord_mask = np.array([True, True, False])
    else:
        coord_mask = np.array([True, True, True])
    return {
        "coords": coords.astype(np.float32),
        "coord_mask": coord_mask,
        "joint_mask": np.ones(len(CANON), dtype=bool),
        "valid_mask": valid,                            # (T,15) per-frame joint validity
        "dim": dim,
        "fps": fps,
        "modality": "3d_meter" if dim == 3 else "2d_pixel",
        "source": source,
        "subject_ns": subject_ns,
        "take": take,
        "n_frames": int(coords.shape[0]),
        "scale": scale,
    }


def ingest_care_pd(manifest):
    smpl_names = json.load(open(os.path.join(
        REPO, "datasets/pose/care_pd/processed/smpl_joint_names.json")))
    out = []
    for pkl in sorted(glob.glob(os.path.join(
            REPO, "datasets/pose/care_pd/processed/*_positions.pkl"))):
        cohort = os.path.basename(pkl).replace("_positions.pkl", "")
        d = pickle.load(open(pkl, "rb"))
        for subj, takes in d.items():
            for take_id, leaf in takes.items():
                arr = np.asarray(leaf["joints3d"] if isinstance(leaf, dict) else leaf)
                if arr.ndim != 3 or arr.shape[1] != 24:
                    continue
                fps = leaf.get("fps") if isinstance(leaf, dict) else None
                canon = to_canonical("smpl_carepd", smpl_names, arr)
                ns = f"care_pd:{cohort}:{subj}"
                rec = make_record("care_pd", ns, str(take_id), canon, 3, fps)
                out.append(rec)
                manifest.append([rec["source"], ns, str(take_id), 3,
                                 fps if fps else "", rec["n_frames"], "3d_meter"])
    save = os.path.join(REPO, "datasets/pose/care_pd/processed/canonical.pkl")
    pickle.dump(out, open(save, "wb"))
    return len(out)


def ingest_li_taati(manifest):
    out = []
    for task in ("communication", "drinking"):   # leg_agility handled separately
        pkl = os.path.join(REPO, f"datasets/pose/li_taati/processed/{task}_pose.pkl")
        if not os.path.exists(pkl):
            continue
        d = pickle.load(open(pkl, "rb"))
        recs = d if isinstance(d, list) else list(d.values())
        for r in recs:
            coords = np.asarray(r["joints2d"])
            names = list(r["joint_names"])
            canon = to_canonical("li_taati", names, coords)
            ns = f"li_taati:{task}:{r.get('subject')}"
            take = f"{task}_{r.get('take')}"
            rec = make_record("li_taati", ns, take, canon, 2, LI_TAATI_FPS)
            rec["fps_provenance"] = LI_TAATI_FPS_PROVENANCE
            out.append(rec)
            manifest.append([rec["source"], ns, take, 2, LI_TAATI_FPS, rec["n_frames"],
                             "2d_pixel"])
    save = os.path.join(REPO, "datasets/pose/li_taati/processed/canonical.pkl")
    pickle.dump(out, open(save, "wb"))
    return len(out)


CODY_LABELS = ["Dystonia", "Tremor", "Myoclonus", "Chorea", "Tics", "Athetosis",
               "Ballismus", "Stereotypie"]
COCO17 = {"nose", "left_eye", "right_eye", "left_ear", "right_ear",
          "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
          "left_wrist", "right_wrist", "left_hip", "right_hip",
          "left_knee", "right_knee", "left_ankle", "right_ankle"}


def ingest_cody(manifest):
    """Adult cohort from cody_3/01_train_labels_raw. Keypoints are identical across the
    two raters (dd, lc) -> ingest pose ONCE per video; attach each rater's per-frame
    labels separately (labels are for eval/fine-tuning, never pretraining)."""
    import pandas as pd
    base = os.path.join(REPO, "datasets/pose/cody_3/raw/01_train_labels_raw")
    raters = ("dd", "lc")
    patients = set()
    for r in raters:
        for d in glob.glob(os.path.join(base, f"dataset_{r}", "*")):
            b = os.path.basename(d)
            if os.path.isdir(d) and not b.startswith("._"):
                patients.add(b)
    out = []
    for pid in sorted(patients):
        videos = {}   # video filename -> {rater: path}
        for r in raters:
            for f in glob.glob(os.path.join(base, f"dataset_{r}", pid, "*.xlsx")):
                if os.path.basename(f).startswith("._"):
                    continue
                videos.setdefault(os.path.basename(f), {})[r] = f
        for vid, rmap in videos.items():
            dfs = {r: pd.read_excel(p) for r, p in rmap.items()}
            df0 = next(iter(dfs.values()))
            names = [c[:-2] for c in df0.columns if c.endswith("_x") and c[:-2] in COCO17]
            coords = np.stack([df0[[n + "_x", n + "_y"]].values for n in names], axis=1)
            canon = to_canonical("cody_coco17", names, coords)
            ns = f"adult:{pid}"
            take = vid.replace(".xlsx", "")
            rec = make_record("cody", ns, take, canon, 2, 33.3)
            labels = {}
            for r, df in dfs.items():
                present = [l for l in CODY_LABELS if l in df.columns]
                # blank / non-numeric cells = frame not annotated -> -1 (distinct from 0)
                num = df[present].apply(pd.to_numeric, errors="coerce")
                vals = np.nan_to_num(num.values[:rec["n_frames"]].astype(float),
                                     nan=-1.0).astype(np.int8)
                labels[r] = {"names": present, "values": vals}
            rec["labels"] = labels
            out.append(rec)
            manifest.append([rec["source"], ns, take, 2, 33.3, rec["n_frames"],
                             "2d_pixel"])
    save = os.path.join(REPO, "datasets/pose/cody_3/processed/canonical.pkl")
    os.makedirs(os.path.dirname(save), exist_ok=True)
    pickle.dump(out, open(save, "wb"))
    return len(out)


def main():
    raise SystemExit(
        "build_canonical.py refuses to run (2026-09-29): its inputs are .npz now "
        "(care_pd/processed/*_positions.npz, li_taati/processed/*_pose.npz), so it "
        "would ingest 0 care_pd and 0 li_taati records, write empty canonical.pkl "
        "lists beside the .npz containers, re-ingest CODY from the raw xlsx and "
        "rewrite datasets/_canonical_manifest.csv with 51 rows. The records it once "
        "wrote stay as they are (li_taati fps: set_stated_fps.py).")
    manifest = []
    n_care = ingest_care_pd(manifest)
    n_li = ingest_li_taati(manifest)
    n_cody = ingest_cody(manifest)
    print(f"cody: {n_cody} samples")
    with open(os.path.join(REPO, "datasets/_canonical_manifest.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])
        w.writerows(manifest)
    n_subj = len({m[1] for m in manifest})
    print(f"care_pd: {n_care} samples | li_taati: {n_li} samples")
    print(f"total {len(manifest)} canonical samples, {n_subj} namespaced subjects")
    print("-> datasets/pose/{care_pd,li_taati}/processed/canonical.pkl")
    print("-> datasets/_canonical_manifest.csv")


if __name__ == "__main__":
    main()
