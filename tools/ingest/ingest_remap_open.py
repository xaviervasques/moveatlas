# -*- coding: utf-8 -*-
"""Ingest REMAP Open (data.bris, 24 subjects: 12 PD + 12 controls) into the
canonical skeleton contract.

Two activity streams, verified on the real download 2026-08-25:
  Turning/Data/turning_2D3D_skeletons_coarsened/Turning_coarsen_CSV/
      <Pt###_{PD|C}_n_####>/input_2D/keypoints.csv     (T, 34) H36M-17 x 2
      <episode>/input_3D/keypoints3d.csv               (T, 51) H36M-17 x 3
  SitToStand/Data/STS_2D_skeletons_coarsened/<episode>.csv
      (T, 52) = frame index + timestamp(s) + OpenPose BODY_25 x 2; missing
      keypoints are (0,0); the timestamp column yields each episode's fps,
      which is the stated 30 (the source writes the column as frame / 30).
      The turning CSVs have no time column: their records carry the 30 fps
      the deposit readme states. Both streams say so in fps_provenance.
      Identification evidence for both conventions is in
      configs/canonical_skeleton.yaml.

Joint convention: Human3.6M-17 in VideoPose3D order; the identification
evidence is recorded in configs/canonical_skeleton.yaml (h36m17_remap). The 3D
was lifted from the coarsened 2D BY THE SOURCE (VideoPose3D); those records
carry lift_provenance so the pool config can include or exclude them. PD /
control group is a cohort attribute plus an eval-only label; it never enters
pretraining (R1).

Outputs:
  datasets/pose/remap_open/processed/canonical.npz
  datasets/pose/remap_open/processed/remap_ingest_audit.csv
  rows merged into datasets/_canonical_manifest.csv in place of the source's
  earlier rows

Usage: python ingest_remap_open.py [--repo PATH] [--limit N]
"""
import argparse
import csv
import glob
import os

import numpy as np

from build_canonical import CFG, make_record, to_canonical

H36M = CFG["sources"]["h36m17_remap"]["joint_order"]
BODY25 = CFG["sources"]["body25_remap_sts"]["joint_order"]

# Frame rate. The deposit readme.txt (doi:10.5523/bris.21h9f9e30v9cl2fapjggz4q1x7)
# states that the video was captured at 30 frames per second and warns that
# frame timing may be uneven. The turning CSVs have no time column; the
# sit-to-stand time column equals frame / 30 within 3.3e-05 s (checked
# 2026-09-28). Both streams carry the stated rate, marked nominal.
REMAP_FPS = 30.0
FPS_PROVENANCE_TURN = ("30 fps stated by the deposit readme.txt (video captured at 30 "
                       "frames per second, frame timing possibly uneven); the turning "
                       "CSVs carry no time column: nominal, not measured")
FPS_PROVENANCE_STS = ("30 fps stated by the deposit readme.txt; the file time column "
                      "equals frame / 30 and restates that rate: nominal, not a clock")


def load_kp(path, dims):
    a = np.loadtxt(path, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] != 17 * dims:
        raise ValueError(f"{os.path.basename(path)}: {a.shape[1]} columns, "
                         f"expected {17 * dims}")
    kp = a.reshape(a.shape[0], 17, dims)
    # exact (0,0) pairs would be OpenPose-style missings; none were seen in
    # the turning files, but if one appears it must not enter as a real point
    if dims == 2:
        miss = (kp == 0).all(axis=2)
        kp = kp.astype(float)
        kp[miss] = np.nan
    return kp


def load_sts(path):
    """(T,52) -> (kp (T,25,2) with NaN for missing, fps derived from the
    file's timestamp column, which the source writes as frame / 30)."""
    a = np.loadtxt(path, delimiter=",")
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] != 52:
        raise ValueError(f"{os.path.basename(path)}: {a.shape[1]} columns, "
                         f"expected 52")
    t = a[:, 1]
    dt = np.diff(t)
    dt = dt[np.isfinite(dt) & (dt > 0)]
    fps = round(1.0 / float(np.median(dt)), 2) if dt.size else None
    kp = a[:, 2:].reshape(a.shape[0], 25, 2).astype(float)
    kp[(kp == 0).all(axis=2)] = np.nan
    return kp, fps


def episode_id(name):
    """Pt204_C_n_350 -> (subject 'Pt204', group, 'n_350')."""
    parts = name.split("_")
    if len(parts) < 4 or parts[1] not in ("PD", "C"):
        return None
    return parts[0], ("pd" if parts[1] == "PD" else "control"), "_".join(parts[2:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="first N episodes per task")
    args = ap.parse_args()
    R = args.repo
    root = None
    for cand in glob.glob(os.path.join(R, "datasets", "pose", "remap_open",
                                       "raw", "*")):
        if os.path.isdir(os.path.join(cand, "Turning")):
            root = cand
            break
    if root is None:
        raise SystemExit("REMAP root with Turning/ not found under raw/")

    out, manifest, audit = [], [], []

    # ---------------------------------------------------------------- turning
    turn_dir = os.path.join(root, "Turning", "Data",
                            "turning_2D3D_skeletons_coarsened",
                            "Turning_coarsen_CSV")
    eps = sorted(d for d in os.listdir(turn_dir)
                 if os.path.isdir(os.path.join(turn_dir, d))
                 and not d.startswith("._"))
    if args.limit:
        eps = eps[:args.limit]
    print(f"turning: {len(eps)} episodes")
    for e in eps:
        ident = episode_id(e)
        if ident is None:
            audit.append(["turning", e, "", "", "SKIPPED: unparseable name"])
            continue
        subj, group, ep = ident
        ns = f"remap_open:{subj}"
        for dims, sub, suffix in ((2, os.path.join("input_2D", "keypoints.csv"),
                                   "2d"),
                                  (3, os.path.join("input_3D", "keypoints3d.csv"),
                                   "3d")):
            p = os.path.join(turn_dir, e, sub)
            if not os.path.exists(p):
                audit.append(["turning", e, dims, "", "missing file"])
                continue
            try:
                kp = load_kp(p, dims)
            except ValueError as err:
                audit.append(["turning", e, dims, "", f"REFUSED: {err}"])
                continue
            canon = to_canonical("h36m17_remap", H36M, kp)
            rec = make_record("remap_open", ns, f"turn_{ep}_{suffix}",
                              canon, dims, REMAP_FPS)
            rec["group"] = group
            rec["label"] = np.int8(1 if group == "pd" else 0)
            rec["fps_provenance"] = FPS_PROVENANCE_TURN
            if dims == 3:
                rec["lift_provenance"] = "videopose3d_by_source"
            out.append(rec)
            manifest.append(["remap_open", ns, rec["take"], dims, REMAP_FPS,
                             rec["n_frames"], rec["modality"]])
            audit.append(["turning", e, dims, rec["n_frames"], group])

    # ------------------------------------------------------------ sit-to-stand
    sts_dir = os.path.join(root, "SitToStand", "Data",
                           "STS_2D_skeletons_coarsened")
    csvs = sorted(f for f in os.listdir(sts_dir)
                  if f.endswith(".csv") and not f.startswith("._"))
    if args.limit:
        csvs = csvs[:args.limit]
    print(f"sit-to-stand: {len(csvs)} episodes")
    for f in csvs:
        ident = episode_id(f[:-4])
        if ident is None:
            audit.append(["sts", f, "", "", "SKIPPED: unparseable name"])
            continue
        subj, group, ep = ident
        ns = f"remap_open:{subj}"
        try:
            kp, fps = load_sts(os.path.join(sts_dir, f))
        except ValueError as err:
            audit.append(["sts", f, 2, "", f"REFUSED: {err}"])
            continue
        canon = to_canonical("body25_remap_sts", BODY25, kp)
        rec = make_record("remap_open", ns, f"sts_{ep}", canon, 2, fps)
        rec["group"] = group
        rec["label"] = np.int8(1 if group == "pd" else 0)
        rec["fps_provenance"] = FPS_PROVENANCE_STS
        out.append(rec)
        manifest.append(["remap_open", ns, rec["take"], 2, fps or "",
                         rec["n_frames"], rec["modality"]])
        audit.append(["sts", f, 2, rec["n_frames"], f"{group}, fps={fps}"])

    procd = os.path.join(R, "datasets", "pose", "remap_open", "processed")
    os.makedirs(procd, exist_ok=True)
    from moveatlas import records as _records
    _records.save(os.path.join(procd, "canonical.npz"), out)
    with open(os.path.join(procd, "remap_ingest_audit.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["task", "episode", "dim", "n_frames", "notes"])
        w.writerows(audit)

    mp = os.path.join(R, "datasets", "_canonical_manifest.csv")
    with open(mp, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f)]
    # the source's rows are replaced where they stood, every other row keeps
    # its place (the logic of build_canonical_force._merge_in_place)
    head, merged, placed = rows[0], [], False
    for r in rows[1:]:
        if not r:
            continue
        if r[0] == "remap_open":
            if not placed:
                merged.extend(manifest)
                placed = True
            continue
        merged.append(r)
    if not placed:
        merged.extend(manifest)
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(merged)
    subs = {m[1] for m in manifest}
    groups = {}
    for r in out:
        groups.setdefault(r["group"], set()).add(r["subject_ns"])
    print(f"\n{len(out)} canonical records / {len(subs)} subjects "
          f"({len(groups.get('pd', ()))} PD, {len(groups.get('control', ()))} "
          f"controls); manifest now {len(merged)} rows")


if __name__ == "__main__":
    main()
