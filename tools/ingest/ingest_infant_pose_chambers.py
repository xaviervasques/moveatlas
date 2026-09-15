# -*- coding: utf-8 -*-
"""Ingest the Chambers infant pose estimates into the canonical pose
contract. CC BY 4.0 (figshare API, confirmed at fetch 2026-09-01).

Two cohorts, verified on the real files:
- YouTube normative set: pose_estimates_youtube_dataset.csv, 85 videos,
  long format (video, bp, frame, x, y, fps, ...), COCO-18 part names,
  meta_data_youtube_dataset.csv gives age_in_weeks + infant_id.
- Clinical set: pose_estimates_clinical_dataset.csv, 19 videos of the
  CHOP evaluation subset (infant, session, trial columns; same long
  format shifted by two columns), meta_data_clinical_dataset.csv gives
  sex, chronological/corrected age and BINS risk scores.

Joint mapping mirrors the cody_coco17 conventions in
configs/canonical_skeleton.yaml (chambers_coco18 entry): pelvis =
midpoint of the hips, neck DIRECT (COCO-18 has it), head = proxy nose,
eyes and ears dropped. Coordinates are image pixels, y down; dim 2;
coords slot 2 is zero with coord_mask [1,1,0]. Missing detections are
empty/NaN cells -> valid_mask False; pelvis needs both hips, neck its
own detection.

Cohort namespaces are DISJOINT ON PURPOSE (yt/cl prefixes): the
YouTube infants and the clinical infants are different children.
BINS risk and ages ride as record attributes, labels eval-only (R1).

Outputs (datasets/pose/infant_pose_chambers/processed/):
  canonical.pkl, chambers_ingest_audit.csv,
  ../../_canonical_manifest_infant_pose_chambers.csv

Usage: python ingest_infant_pose_chambers.py [--repo PATH] [--dry]
"""
import argparse
import csv
import os
import pickle

import numpy as np
import pandas as pd

CANON = ["pelvis", "neck", "head", "left_shoulder", "right_shoulder",
         "left_elbow", "right_elbow", "left_wrist", "right_wrist",
         "left_hip", "right_hip", "left_knee", "right_knee",
         "left_ankle", "right_ankle"]
DIRECT = {"neck": "Neck", "head": "Nose",
          "left_shoulder": "LShoulder", "right_shoulder": "RShoulder",
          "left_elbow": "LElbow", "right_elbow": "RElbow",
          "left_wrist": "LWrist", "right_wrist": "RWrist",
          "left_hip": "LHip", "right_hip": "RHip",
          "left_knee": "LKnee", "right_knee": "RKnee",
          "left_ankle": "LAnkle", "right_ankle": "RAnkle"}


def build_records(df, meta_attrs, ns_prefix, source, take_of, audit):
    recs, manifest = [], []
    for take, g in df.groupby("take", sort=True):
        fps_vals = g["fps"].dropna().unique()
        fps = float(fps_vals[0]) if len(fps_vals) else None
        frames = np.sort(g["frame"].unique())
        T = int(frames.max()) + 1
        idx = {bp: sub.set_index("frame")[["x", "y"]]
               for bp, sub in g.groupby("bp")}
        coords = np.zeros((T, 15, 3), np.float32)
        valid = np.zeros((T, 15), bool)

        def series(bp):
            out = np.full((T, 2), np.nan, np.float32)
            if bp in idx:
                sub = idx[bp]
                fr = sub.index.to_numpy().astype(int)
                keep = (fr >= 0) & (fr < T)
                out[fr[keep]] = sub[["x", "y"]].to_numpy(
                    np.float32)[keep]
            return out

        for j, name in enumerate(CANON):
            if name == "pelvis":
                lh, rh = series("LHip"), series("RHip")
                xy = (lh + rh) / 2.0
                ok = ~np.isnan(lh).any(1) & ~np.isnan(rh).any(1)
            else:
                xy = series(DIRECT[name])
                ok = ~np.isnan(xy).any(1)
            coords[ok, j, 0:2] = xy[ok]
            valid[:, j] = ok
        det = valid.any(axis=1)
        if det.sum() < 30:
            audit.append([source, take, "", 0, "",
                          f"REFUSED: only {int(det.sum())} frames with "
                          "any detection"])
            continue
        both = valid[:, CANON.index("pelvis")] & \
            valid[:, CANON.index("neck")]
        scale = float(np.median(np.linalg.norm(
            coords[both, CANON.index("pelvis"), :2]
            - coords[both, CANON.index("neck"), :2], axis=1))) \
            if both.sum() >= 10 else None
        ns = ns_prefix(take)
        rec = {"coords": coords, "valid_mask": valid,
               "coord_mask": np.array([True, True, False]),
               "joint_mask": np.ones(15, bool), "dim": 2, "fps": fps,
               "modality": "2d_pixel", "source": source,
               "subject_ns": ns, "take": take_of(take),
               "n_frames": T, "scale": scale}
        rec.update(meta_attrs.get(take, {}))
        recs.append(rec)
        manifest.append([source, ns, take_of(take), 2,
                         round(fps, 3) if fps else "", T, "2d_pixel"])
        audit.append([source, take, ns, T,
                      f"{fps:.2f}" if fps else "",
                      f"valid_frac={valid.mean():.3f} scale={scale and round(scale, 1)} "
                      + " ".join(f"{k}={v}" for k, v in
                                 meta_attrs.get(take, {}).items())])
    return recs, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "pose",
                        "infant_pose_chambers")
    rawd = os.path.join(base, "raw")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)
    recs, manifest, audit = [], [], []

    # ------------------------------------------------ YouTube normative
    yt = pd.read_csv(os.path.join(
        rawd, "pose_estimates_youtube_dataset.csv"))
    yt = yt.rename(columns={"video": "take"})[
        ["take", "bp", "frame", "x", "y", "fps"]]
    yt["take"] = yt["take"].astype(str)
    meta = pd.read_csv(os.path.join(
        rawd, "meta_data_youtube_dataset.csv"))
    infant_of = {str(r["video"]): int(r["infant_id"])
                 for _, r in meta.iterrows()}
    age_of = {str(r["video"]): {"age_weeks": float(r["age_in_weeks"])}
              for _, r in meta.iterrows()}
    r1, m1 = build_records(
        yt.rename(columns={"take": "take"}), age_of,
        lambda t: f"infant_pose_chambers:yt{infant_of.get(t, t)}",
        "infant_pose_chambers", lambda t: t, audit)
    recs += r1
    manifest += m1
    print(f"youtube: {len(r1)} records")

    # --------------------------------------------------- clinical CHOP
    cl = pd.read_csv(os.path.join(
        rawd, "pose_estimates_clinical_dataset.csv"))
    cl["take"] = (cl["video"].astype(str) + "__s"
                  + cl["session"].astype(str) + "_t"
                  + cl["trial"].astype(str))
    infant_cl = {r["take"]: int(r["infant"])
                 for _, r in cl[["take", "infant"]].drop_duplicates()
                 .iterrows()}
    clm = pd.read_csv(os.path.join(
        rawd, "meta_data_clinical_dataset.csv"))
    bins_of = {}
    for _, r in clm.iterrows():
        key = (int(r["Infant"]), int(r["Session"]))
        bins_of[key] = {
            "sex_male1": r.get("Sex [Male=1,Female=0]"),
            "chron_age_months": r.get("Chronological age (Months)"),
            "bins_score": r.get("Chronological BINS score"),
            "bins_risk": r.get("Risk (Chronological Age)")}
    meta_cl = {}
    for take, sub in cl.groupby("take"):
        key = (int(sub["infant"].iloc[0]), int(sub["session"].iloc[0]))
        if key in bins_of:
            meta_cl[take] = {k: v for k, v in bins_of[key].items()
                             if pd.notna(v)}
    r2, m2 = build_records(
        cl[["take", "bp", "frame", "x", "y", "fps"]], meta_cl,
        lambda t: f"infant_pose_chambers:cl{infant_cl.get(t, t)}",
        "infant_pose_chambers", lambda t: t, audit)
    recs += r2
    manifest += m2
    print(f"clinical: {len(r2)} records")

    subs = {r["subject_ns"] for r in recs}
    print(f"{len(recs)} canonical pose records / {len(subs)} subjects")
    if not args.dry:
        with open(os.path.join(outd, "canonical.pkl"), "wb") as f:
            pickle.dump(recs, f)
        mp = os.path.join(args.repo, "datasets",
                          "_canonical_manifest_infant_pose_chambers.csv")
        with open(mp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["source", "subject_ns", "take", "dim", "fps",
                        "n_frames", "modality"])
            w.writerows(manifest)
        with open(os.path.join(outd, "chambers_ingest_audit.csv"), "w",
                  newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["source", "take", "subject_ns", "n_frames",
                        "fps", "notes"])
            w.writerows(audit)
        print(f"wrote {mp}")


if __name__ == "__main__":
    main()
