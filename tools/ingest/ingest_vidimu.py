# -*- coding: utf-8 -*-
"""Ingest VIDIMU (healthy daily-activity video pose + synchronized lower-body IMU).

Dataset: VIDIMU (Sci Data 2023, doi 10.1038/s41597-023-02554-9), on disk under
datasets/socle/vidimu/raw/{dataset.zip, analysis.zip, videosmallsize.zip}.
Unzip dataset.zip into raw/ first (raw/dataset/...). Format verified on the real
files 2026-08-22 (this session):

  dataset/videonly/S01..S39            37 subjects, video-derived 3D keypoints only
  dataset/videoandimus/S40..S57        16 subjects, THE PAIRED SET: per trial both
                                       SXX_AYY_TZZ.csv (keypoints) and .raw (IMU),
                                       ~13 paired trials per subject (verified on
                                       real files: 13/13 same-take pairs on S41,
                                       S46, S50), plus .sto and _Npose.csv
                                       (OpenSense derivations, provenance only).
  dataset/videoandimusync/             SMALL trimmed/aligned SUBSET of the same
                                       trials; SKIPPED for pose (duplicates) but
                                       its .raw kept as variant="sync_trimmed"
                                       alignment aids.
    SXX_AYY_TZZ.csv    3D keypoints, 34 named landmarks, header row, mm; no time
                       column. fps recovered from csv/ik_*.mot durations where
                       available, else dataset median (measured 29.42 ~ 30 fps).
    SXX_AYY_TZZ.raw    text stream "QUAT,w,x,y,z,timestamp"; per-sensor rows with
                       DYNAMIC qs* prefixes: lower-body config qs{HIPS,LUL,LLL,
                       RUL,RLL} for gait trials, upper-body config qs{BACK,RUA,
                       RLA,LUA,LLA,...} for arm trials (both observed on disk).
                       ORIENTATION ONLY: no acc/gyro -> NOT the canonical
                       9-channel IMU contract; emitted as the PAIRED ALIGNMENT
                       STREAM for stage B (pose <-> IMU pair of the v2 spec).
    ik_SXX_AYY_TZZ.mot OpenSim joint angles at 50 Hz (derived; provenance only).
Activities (from analysis.zip): A01 walk_forward, A02 walk_backward, A03
walk_along, A04 sit_to_stand, A05 move_right_arm, A06 move_left_arm, A07
drink_right_arm, A08 drink_left_arm, A09 assemble_both_arms, A10 throw_both_arms,
A11 reachup_right_arm, A12 reachup_left_arm, A13 tear_both_arms.

Outputs (datasets/socle/vidimu/processed/):
  canonical.pkl        canonical 15-joint skeleton records (same schema as
                       build_canonical.py: coords/coord_mask/joint_mask/valid_mask/
                       dim/fps/modality/source/subject_ns/take/n_frames/scale)
  streams_pose_imu.pkl paired quaternion streams (subject, activity/trial, per-
                       sensor t + quat arrays, matching csv take when present)
  vidimu_ingest_audit.csv
  ../../_canonical_manifest_vidimu.csv   manifest rows to merge

Subjects are HEALTHY adults (C1 socle). Labels: none (activity code A01..A13 is
kept in `take`). Env: atlas-mouvement (numpy). Usage:
  python ingest_vidimu.py [--repo PATH] [--dry]
"""
import argparse
import csv
import glob
import os
import pickle
import re
import numpy as np

# canonical skeleton (mirrors configs/canonical_skeleton.yaml + build_canonical.py)
CANON = ["pelvis", "neck", "head",
         "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
         "left_wrist", "right_wrist", "left_hip", "right_hip",
         "left_knee", "right_knee", "left_ankle", "right_ankle"]
ROOT_I = CANON.index("pelvis")
REF_A, REF_B = CANON.index("pelvis"), CANON.index("neck")
# VIDIMU landmark -> canonical (all direct except head <- nose proxy)
VIDIMU_MAP = {"pelvis": "pelvis", "neck": "neck", "head": "nose",
              "left_shoulder": "left_shoulder", "right_shoulder": "right_shoulder",
              "left_elbow": "left_elbow", "right_elbow": "right_elbow",
              "left_wrist": "left_wrist", "right_wrist": "right_wrist",
              "left_hip": "left_hip", "right_hip": "right_hip",
              "left_knee": "left_knee", "right_knee": "right_knee",
              "left_ankle": "left_ankle", "right_ankle": "right_ankle"}
ACTIVITIES = {"A01": "walk_forward", "A02": "walk_backward", "A03": "walk_along",
              "A04": "sit_to_stand", "A05": "move_right_arm", "A06": "move_left_arm",
              "A07": "drink_right_arm", "A08": "drink_left_arm",
              "A09": "assemble_both_arms", "A10": "throw_both_arms",
              "A11": "reachup_right_arm", "A12": "reachup_left_arm",
              "A13": "tear_both_arms"}
SENSOR_RE = re.compile(r"^(qs\w+),")


def normalize(coords):
    """Root-center, scale by median torso length; NaN-aware (build_canonical.py)."""
    c = coords.astype(float).copy()
    valid = ~np.isnan(c).any(axis=-1)
    root_ok = np.isfinite(c[:, ROOT_I, :]).all(axis=-1)
    torso = np.linalg.norm(c[:, REF_A, :] - c[:, REF_B, :], axis=-1)
    good = torso[np.isfinite(torso) & (torso > 1e-6)]
    scale = float(np.median(good)) if good.size else 1.0
    c = c - c[:, ROOT_I:ROOT_I + 1, :]
    c = c / scale
    valid = valid & root_ok[:, None]
    return np.nan_to_num(c, nan=0.0).astype(np.float32), scale, valid


def read_csv_pose(path):
    with open(path) as f:
        header = [h.strip() for h in f.readline().rstrip("\n").split(",")]
        rows = [line.rstrip("\n").split(",") for line in f if line.strip()]
    arr = np.asarray(rows, dtype=float)
    names = sorted({h[:-2] for h in header if h.endswith("_x")})
    idx = {h: i for i, h in enumerate(header)}
    T = arr.shape[0]
    out = np.full((T, len(CANON), 3), np.nan)
    for j, cj in enumerate(CANON):
        src = VIDIMU_MAP[cj]
        if src not in names:
            raise SystemExit(f"{path}: missing landmark {src}; refusing to guess")
        for k, ax in enumerate(("_x", "_y", "_z")):
            out[:, j, k] = arr[:, idx[src + ax]]
    return out


def read_raw_quat(path):
    sens = {}
    with open(path, errors="replace") as f:
        for line in f:
            p = line.rstrip("\r\n").split(",")
            if len(p) == 6 and p[0].startswith("qs"):
                try:
                    q = [float(x) for x in p[1:5]]
                    t = float(p[5])
                except ValueError:
                    continue
                d = sens.setdefault(p[0], {"t": [], "q": []})
                d["q"].append(q)
                d["t"].append(t)
    return {s: {"t": np.asarray(d["t"]), "quat": np.asarray(d["q"], np.float32)}
            for s, d in sens.items() if d["t"]}


def mot_duration(path):
    try:
        last = None
        with open(path) as f:
            for line in f:
                if line[:1].isdigit() or line[:1] == "-":
                    last = line.split("\t")[0]
        return float(last) if last else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "socle", "vidimu")
    rawroot = None
    for cand in (os.path.join(base, "raw", "dataset"),
                 os.path.join(base, "raw", "dataset", "dataset")):
        if os.path.isdir(cand):
            rawroot = cand
            break
    if rawroot is None:
        raise SystemExit("unzip raw/dataset.zip first (expected raw/dataset/...)")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)

    # pass 1: fps calibration from trials having both csv and ik mot
    ratios = []
    sync = os.path.join(rawroot, "videoandimusync")
    for csvf in glob.glob(os.path.join(sync, "S*", "S*_A*_T*.csv")):
        b = os.path.basename(csvf)
        if b.startswith("._"):
            continue
        mot = os.path.join(os.path.dirname(csvf), "ik_" + b[:-4] + ".mot")
        if os.path.exists(mot):
            dur = mot_duration(mot)
            if dur and dur > 2:
                n = sum(1 for _ in open(csvf)) - 1
                ratios.append(n / dur)
    fps_est = float(np.median(ratios)) if ratios else 30.0
    fps_note = f"fps median over {len(ratios)} csv/mot pairs = {fps_est:.2f}"
    print(fps_note)

    def act_of(take):
        m = re.search(r"_(A\d\d)_", take + "_")
        return ACTIVITIES.get(m.group(1), "?") if m else "?"

    # pose sources: videonly + videoandimus (full set). videoandimusync csv only
    # when the same take is absent from videoandimus (it is a trimmed duplicate).
    pose_files, seen_takes = [], set()
    for subset in ("videonly", "videoandimus"):
        for csvf in sorted(glob.glob(os.path.join(rawroot, subset, "S*",
                                                  "S*_A*_T*.csv"))):
            b = os.path.basename(csvf)
            if b.startswith("._") or b.endswith("_Npose.csv"):
                continue
            pose_files.append((subset, csvf))
            seen_takes.add(b[:-4])
    for csvf in sorted(glob.glob(os.path.join(rawroot, "videoandimusync", "S*",
                                              "S*_A*_T*.csv"))):
        b = os.path.basename(csvf)
        if b.startswith("._") or b.endswith("_Npose.csv"):
            continue
        if b[:-4] in seen_takes:
            continue                       # trimmed duplicate, skip for pose
        pose_files.append(("videoandimusync", csvf))

    recs, streams, manifest, audit = [], [], [], []
    for subset, csvf in pose_files:
        b = os.path.basename(csvf)
        sid = b.split("_")[0]
        ns = f"vidimu:{sid}"
        take = b[:-4]
        try:
            coords = read_csv_pose(csvf)
        except SystemExit:
            raise
        except Exception as e:
            audit.append([subset, b, ns, "CSV FAIL", str(e)])
            continue
        cn, scale, valid = normalize(coords)
        recs.append({"coords": cn, "coord_mask": np.array([True] * 3),
                     "joint_mask": np.ones(len(CANON), bool),
                     "valid_mask": valid, "dim": 3, "fps": fps_est,
                     "modality": "3d_meter", "source": "vidimu",
                     "subject_ns": ns, "take": take, "activity": act_of(take),
                     "n_frames": int(cn.shape[0]), "scale": scale})
        manifest.append(["vidimu", ns, take, 3, round(fps_est, 2),
                         cn.shape[0], "3d_meter"])
        audit.append([subset, b, ns, f"T={cn.shape[0]}",
                      f"valid={valid.mean():.3f} scale={scale:.1f}"])

    # IMU quaternion streams: videoandimus = the full paired set (variant "full");
    # videoandimusync raws kept as trimmed/aligned variants.
    for subset, variant in (("videoandimus", "full"),
                            ("videoandimusync", "sync_trimmed")):
        for rawf in sorted(glob.glob(os.path.join(rawroot, subset, "S*",
                                                  "S*_A*_T*.raw"))):
            b = os.path.basename(rawf)
            if b.startswith("._"):
                continue
            sid = b.split("_")[0]
            ns = f"vidimu:{sid}"
            take = b[:-4]
            sens = read_raw_quat(rawf)
            if not sens:
                audit.append([subset, b, ns, "RAW EMPTY", ""])
                continue
            rates = {}
            for s, d in sens.items():
                dt = np.median(np.diff(d["t"])) if len(d["t"]) > 10 else None
                rates[s] = round(1.0 / dt, 1) if dt and dt > 0 else None
            paired = os.path.exists(os.path.join(os.path.dirname(rawf),
                                                 take + ".csv"))
            streams.append({"subject_ns": ns, "take": take, "variant": variant,
                            "activity": act_of(take), "sensors": sens,
                            "rates_hz": rates, "paired_with_pose_csv": paired,
                            "note": "orientation quaternions only (no acc/gyro);"
                                    " stage B alignment asset, not the IMU contract"})
            audit.append([subset, b, ns,
                          f"sensors={sorted(sens)} rates={rates}",
                          f"variant={variant} paired_csv={paired}"])

    with open(os.path.join(outd, "vidimu_ingest_audit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subset", "file", "subject_ns", "result", "notes"])
        w.writerow(["-", "-", "-", "CALIBRATION", fps_note])
        w.writerows(audit)
    if not args.dry:
        pickle.dump(recs, open(os.path.join(outd, "canonical.pkl"), "wb"))
        pickle.dump(streams, open(os.path.join(outd, "streams_pose_imu.pkl"), "wb"))
        mp = os.path.join(args.repo, "datasets", "_canonical_manifest_vidimu.csv")
        with open(mp, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames",
                        "modality"])
            w.writerows(manifest)
    n_subj = len({r["subject_ns"] for r in recs})
    print(f"{len(recs)} pose records / {n_subj} subjects ; "
          f"{len(streams)} IMU quaternion streams "
          f"({sum(1 for s in streams if s['paired_with_pose_csv'])} paired with pose)")
    print("merge _canonical_manifest_vidimu.csv into datasets/_canonical_manifest.csv "
          "after review; audit -> processed/vidimu_ingest_audit.csv")


if __name__ == "__main__":
    main()
