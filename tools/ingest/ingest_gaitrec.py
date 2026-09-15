# -*- coding: utf-8 -*-
"""Ingest GaitRec (figshare c.4788012, 2084 patients + 211 controls, bilateral
GRF on an instrumented walkway) into the canonical force contract.

FORMAT, verified on the real files 2026-08-27: wide CSVs, one ROW per stance
trial (SUBJECT_ID, SESSION_ID, TRIAL_ID, then sample columns), one file per
component x side. RAW files carry the native 250 Hz stance in Newtons with
NaN padding on the right; PRO files are the authors' time-normalized,
body-weight-normalized derivatives and are NOT ingested (no-resampling
policy; derived products stay in raw/). GRF_metadata.csv: per-session class
label (HC / H hip / K knee / A ankle / C calcaneus), demographics, affected
side, and the authors' own TRAIN / TRAIN_BALANCED / TEST partition flags.

Mapping (canonical_force.yaml, gaitndd precedent totals_only): the VERTICAL
component becomes the per-foot total, insole positions masked; AP and ML
force plus COP go to a per-subject aux shard, nothing discarded. Class
labels are eval-only; the authors' partition flags ride along as attributes
but OUR splits remain patient-level by subject_ns.

Outputs:
  datasets/imu/gaitrec/processed/canonical/<subject>.pkl  (list of records)
  datasets/imu/gaitrec/processed/aux/<subject>.pkl
  datasets/imu/gaitrec/processed/gaitrec_ingest_audit.csv
  rows merged into datasets/_canonical_force_manifest.csv (dedup by source)

Usage: python ingest_gaitrec.py [--repo PATH] [--limit N]
"""
import argparse
import collections
import csv
import os
import pickle

import numpy as np

FPS = 250.0                    # GaitRec RAW rate per the data descriptor
NPOS = 9                       # 8 insole positions + total (contract layout)
COMPONENTS = ["F_V", "F_AP", "F_ML", "COP_AP", "COP_ML"]


def load_component(path):
    """Wide CSV -> dict[(subj, sess, trial)] = float32 array (trailing NaN
    trimmed). Streams line by line: six 250 MB files must not be pandas'd
    at once."""
    out = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            key = (int(float(row[0])), int(float(row[1])), int(float(row[2])))
            # empty trailing cells are the CSV's NaN padding
            a = np.array([v if v.strip() else "nan" for v in row[3:]],
                         dtype=np.float32)
            n = np.flatnonzero(np.isfinite(a))
            out[key] = a[:n[-1] + 1] if n.size else a[:0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--limit", type=int, default=0, help="first N subjects")
    args = ap.parse_args()
    rawd = os.path.join(args.repo, "datasets", "imu", "gaitrec", "raw")
    outd = os.path.join(args.repo, "datasets", "imu", "gaitrec", "processed")
    shard_dir = os.path.join(outd, "canonical")
    aux_dir = os.path.join(outd, "aux")
    os.makedirs(shard_dir, exist_ok=True)
    os.makedirs(aux_dir, exist_ok=True)

    meta = {}
    with open(os.path.join(rawd, "GRF_metadata.csv"), newline="",
              encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            meta[int(float(row["SESSION_ID"]))] = row

    data = {}
    for comp in COMPONENTS:
        for side in ("left", "right"):
            p = os.path.join(rawd, f"GRF_{comp}_RAW_{side}.csv")
            if not os.path.exists(p):
                print(f"  (absent: {os.path.basename(p)}; its stream will be "
                      "missing from aux)" if comp != "F_V" else
                      f"REFUSED TO RUN: {p} is required")
                if comp == "F_V":
                    raise SystemExit(1)
                continue
            print(f"  loading {os.path.basename(p)}", flush=True)
            data[(comp, side)] = load_component(p)

    keys = sorted(set(data[("F_V", "left")]) | set(data[("F_V", "right")]))
    by_subj = collections.defaultdict(list)
    for k in keys:
        by_subj[k[0]].append(k)
    subjects = sorted(by_subj)
    if args.limit:
        subjects = subjects[:args.limit]
    print(f"gaitrec: {len(keys)} trials, {len(subjects)} subjects")

    manifest, audit = [], []
    n_rec = 0
    classes = collections.Counter()
    for si, subj in enumerate(subjects, 1):
        ns = f"gaitrec:{subj}"
        recs, aux = [], []
        for key in by_subj[subj]:
            _, sess, trial = key
            vl = data[("F_V", "left")].get(key, np.zeros(0, np.float32))
            vr = data[("F_V", "right")].get(key, np.zeros(0, np.float32))
            T = max(vl.shape[0], vr.shape[0])
            if T < FPS * 0.2:
                audit.append([subj, sess, trial, T, "SKIPPED: under 0.2 s"])
                continue
            force = np.zeros((T, 2, NPOS), np.float32)
            mask = np.zeros((2, NPOS), bool)
            for fi, v in ((0, vl), (1, vr)):
                if v.size:
                    force[:v.shape[0], fi, 8] = np.nan_to_num(v)
                    mask[fi, 8] = True
            m = meta.get(sess, {})
            cls = (m.get("CLASS_LABEL") or "unknown").strip()
            classes[cls] += 1
            rec = {"force": force, "sensor_mask": mask, "fps": FPS,
                   "subject_ns": ns, "task": f"s{sess}_t{trial}",
                   "source": "gaitrec", "n_frames": int(T),
                   "label": cls,
                   "label_def": "CLASS_LABEL: HC healthy, H hip, K knee, "
                                "A ankle, C calcaneus; eval only",
                   "affected_side": (m.get("AFFECTED_SIDE") or "").strip(),
                   "authors_partition": {
                       "train": m.get("TRAIN"),
                       "train_balanced": m.get("TRAIN_BALANCED"),
                       "test": m.get("TEST")}}
            recs.append(rec)
            streams = {}
            for comp in COMPONENTS[1:]:
                for side in ("left", "right"):
                    v = data.get((comp, side), {}).get(key)
                    if v is not None and v.size:
                        streams[f"{comp}_{side}"] = v
            if streams:
                aux.append({"task": rec["task"], "fps": FPS,
                            "streams": streams})
            manifest.append(["gaitrec", ns, rec["task"], FPS, int(T)])
            n_rec += 1
        if recs:
            with open(os.path.join(shard_dir, f"{subj}.pkl"), "wb") as f:
                pickle.dump(recs, f)
        if aux:
            with open(os.path.join(aux_dir, f"{subj}.pkl"), "wb") as f:
                pickle.dump({"subject_ns": ns, "trials": aux,
                             "note": "AP/ML force (N) and COP (raw units) "
                                     "per stance; the vertical component is "
                                     "canonical"}, f)
        if si % 200 == 0:
            print(f"  [{si}/{len(subjects)}] {n_rec} records", flush=True)

    with open(os.path.join(outd, "gaitrec_ingest_audit.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject", "session", "trial", "n_frames", "notes"])
        w.writerows(audit)
    mp = os.path.join(args.repo, "datasets", "_canonical_force_manifest.csv")
    with open(mp, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f)]
    head, body = rows[0], [r for r in rows[1:] if r and r[0] != "gaitrec"]
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(body + manifest)
    print(f"\n{n_rec} canonical force records / {len(subjects)} subjects; "
          f"classes: {dict(classes)}")
    print(f"manifest: {len(body) + len(manifest)} rows")


if __name__ == "__main__":
    main()
