"""Ingest NTU RGB+D 120 skeletons into the canonical skeleton (healthy base).

Reads the .skeleton text files directly from the two raw zips (no extraction), parses
the primary body's 25 Kinect v2 joints per frame (3D meters), maps 25 -> canonical 15
via the ntu_kinect25 mapping in configs/canonical_skeleton.yaml, normalizes, and writes
one shard pickle per camera setup (memory-bounded) plus a manifest.

Applies the two missing-skeleton exclusion lists. Healthy base: pretraining only, no
labels. Env: atlas-mouvement. Usage: python build_canonical_ntu.py
"""
import os
import re
import csv
import zipfile
import pickle
import numpy as np
from build_canonical import to_canonical, make_record, CFG

REPO = os.path.dirname(os.path.abspath(__file__))
NTU = os.path.join(REPO, "datasets/socle/ntu_rgbd")
RAW = os.path.join(NTU, "raw")
OUT = os.path.join(NTU, "processed", "canonical")
JOINT_ORDER = CFG["sources"]["ntu_kinect25"]["joint_order"]   # 25 Kinect names
FPS = 30.0


def load_exclusions():
    s = set()
    for f in ("NTU_RGBD_samples_with_missing_skeletons.txt",
              "NTU_RGBD120_samples_with_missing_skeletons.txt"):
        p = os.path.join(RAW, f)
        if os.path.exists(p):
            for line in open(p):
                t = line.strip()
                if t and not t.startswith(("#", "This", "NTU")):
                    s.add(t)
    return s


def parse_skeleton(text):
    """Return (T,25,3) of the primary body, or None if no body ever tracked."""
    lines = text.splitlines()
    i = 0
    nframes = int(lines[i]); i += 1
    frames = []
    for _ in range(nframes):
        nb = int(lines[i]); i += 1
        first = None
        for b in range(nb):
            i += 1                       # body info line
            nj = int(lines[i]); i += 1
            joints = []
            for _j in range(nj):
                v = lines[i].split(); i += 1
                joints.append((float(v[0]), float(v[1]), float(v[2])))
            if b == 0:
                first = joints
        frames.append(first)
    valid = [f for f in frames if f is not None]
    if not valid:
        return None
    fill = valid[0]
    arr = np.array([f if f is not None else fill for f in frames], dtype=float)
    return arr                            # (T,25,3)


def main():
    os.makedirs(OUT, exist_ok=True)
    excl = load_exclusions()
    print(f"exclusions: {len(excl)} samples")
    zips = [os.path.join(RAW, z) for z in
            ("nturgbd_skeletons_s001_to_s017.zip",
             "nturgbd_skeletons_s018_to_s032.zip")]
    manifest_path = os.path.join(NTU, "processed", "canonical_manifest.csv")
    mf = open(manifest_path, "w", newline="")
    mw = csv.writer(mf)
    mw.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])

    total, skipped, bad = 0, 0, 0
    for zp in zips:
        zf = zipfile.ZipFile(zp)
        entries = [n for n in zf.namelist() if n.endswith(".skeleton")]
        # group by setup S###
        setups = {}
        for n in entries:
            m = re.search(r"(S\d{3})", os.path.basename(n))
            setups.setdefault(m.group(1), []).append(n)
        for setup in sorted(setups):
            shard = []
            for n in setups[setup]:
                code = os.path.basename(n).replace(".skeleton", "")
                if code in excl:
                    skipped += 1
                    continue
                try:
                    arr = parse_skeleton(zf.read(n).decode())
                    if arr is None or arr.shape[1] != 25:
                        bad += 1
                        continue
                    canon = to_canonical("ntu_kinect25", JOINT_ORDER, arr)
                    pid = re.search(r"P(\d{3})", code).group(1)
                    rec = make_record("ntu", f"ntu:P{pid}", code, canon, 3, FPS)
                    shard.append(rec)
                    mw.writerow([rec["source"], rec["subject_ns"], code, 3, FPS,
                                 rec["n_frames"], "3d_meter"])
                    total += 1
                except Exception:
                    bad += 1
            if shard:
                pickle.dump(shard, open(os.path.join(OUT, f"ntu_{setup}.pkl"), "wb"))
            print(f"  {setup}: {len(shard)} samples (running total {total})", flush=True)
    mf.close()
    print(f"\nNTU canonical: {total} samples, {skipped} excluded, {bad} bad")
    print(f"-> {OUT}/ntu_S###.pkl  +  {manifest_path}")


if __name__ == "__main__":
    main()
