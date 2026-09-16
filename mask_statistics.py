# -*- coding: utf-8 -*-
"""Validity-mask statistics across the harmonized corpus: how much of
each record is USABLE signal, per dataset and family.

The Technical Validation companion the resource paper promised. Per
family the usability metric is the family's own honesty mechanism:
  pose        mean of valid_mask (per-frame, per-joint validity)
  silhouette  mean of detect_mask (per-frame detection)
  imu         mean of sample_valid over present locations when the
              record carries it, else finite fraction over channels
              the channel_mask declares present
  force       finite fraction over sensors the sensor_mask declares
  eeg         1 - bad_channels/n_channels (declared-bad channels) and
              finite fraction
  emg         finite fraction (the family has no mask by design; unit
              honesty lives in the unit field)

SAMPLING, stated openly: a dataset with more records than the cap
(default 150) is sampled with a fixed seed and flagged sampled=yes in
the output; small datasets are exhaustive. Shard directories load at
most 40 shards per dataset (fixed-seed choice). Exact full-corpus
numbers can be produced by --cap 0 (hours of IO).

Outputs: docs/mask_statistics.csv and
site/source/_generated/mask_stats.html (per-family tables).

Usage: python mask_statistics.py [--repo PATH] [--cap N]
"""
import argparse
import csv
import glob
import os
import pickle
import random

import numpy as np

FAMS = ["pose", "imu", "emg", "eeg", "force", "silhouette"]

# record-level source names that differ from registry ids
SOURCE_ALIAS = {
    "semg_walking": "physionet_semg_walking",
    "cervical_motion": "cervical_motion_multiplanar",
    "modys": "modys_video", "ntu": "ntu_rgbd", "cody": "cody_1",
    "cody_external": "cody_3", "cap_sleep_chin": "cap_sleep",
    "seizeit2_emg": "seizeit2", "weargait": "weargait_pd",
}


def rec_family(rec):
    if "coords" in rec:
        return "pose"
    if "contour" in rec:
        return "silhouette"
    if "force" in rec:
        return "force"
    if "signal" in rec:
        sig = rec["signal"]
        if "channel_mask" in rec:
            return "imu"
        if rec.get("unit") == "uV" and "channels" in rec and \
                isinstance(rec["channels"], list) and rec["channels"] \
                and isinstance(rec["channels"][0], dict) and \
                "site" in rec["channels"][0]:
            return "eeg"
        return "emg"
    return None


def usability(rec, fam):
    try:
        if fam == "pose":
            return float(np.mean(rec["valid_mask"]))
        if fam == "silhouette":
            return float(np.mean(rec["detect_mask"]))
        if fam == "imu":
            if "sample_valid" in rec:
                return float(np.mean(rec["sample_valid"]))
            sig, cm = rec["signal"], rec["channel_mask"]
            vals = sig[:, cm]
            return float(np.mean(np.isfinite(vals))) if vals.size else 0.0
        if fam == "force":
            sig, sm = rec["force"], rec["sensor_mask"]
            vals = sig[:, sm]
            return float(np.mean(np.isfinite(vals))) if vals.size else 0.0
        if fam == "eeg":
            n = len(rec.get("channels") or [])
            bad = len(rec.get("bad_channels") or [])
            declared = 1.0 - (bad / n if n else 0.0)
            finite = float(np.mean(np.isfinite(rec["signal"])))
            return min(declared, finite)
        if fam == "emg":
            return float(np.mean(np.isfinite(rec["signal"])))
    except Exception:
        return None
    return None


def _containers(pattern_dir, names):
    """Record containers in a directory: the .npz (moveatlas-record/1)
    when present, else the legacy .pkl - never both for one stem."""
    out = {}
    for suf in (".pkl", ".npz"):
        for p in glob.glob(os.path.join(pattern_dir, "*" + suf)):
            stem = p[:-4]
            if os.path.basename(p).startswith("._"):
                continue
            if names is None or os.path.basename(p) in names:
                if suf == ".npz" or stem not in out:
                    out[stem] = p
    return sorted(out.values())


def _load_container(p):
    if p.endswith(".npz"):
        from moveatlas import records
        return records.load(p)
    with open(p, "rb") as f:
        return pickle.load(f)


def iter_records(repo, cap_shards=40):
    # cap_shards=0 disables BOTH sampling points (the exhaustive --cap 0
    # promise of the module docstring; before 2026-09-02 these two caps
    # were hardcoded and --cap 0 silently kept sampling)
    rnd = random.Random(0)
    seen_paths = set()
    # per-record families (eeg/emg canonical_eeg dirs and friends)
    for d in glob.glob(os.path.join(repo, "datasets", "*", "*",
                                    "processed", "canonical_e*g")):
        pkls = _containers(d, None)
        # the pre-2026-09-02 code yielded sampled=True unconditionally
        # here, so every per-record eeg/emg dataset showed Sampled=yes
        # even on an exhaustive pass
        e_sampled = bool(cap_shards) and len(pkls) > 400
        if e_sampled:
            pkls = rnd.sample(pkls, 400)
        for p in pkls:
            if p in seen_paths:
                continue
            seen_paths.add(p)
            try:
                rec = _load_container(p)
                if isinstance(rec, dict):
                    yield rec, e_sampled
            except Exception:
                continue
    # shard dirs (one container per subject, list inside)
    for d in glob.glob(os.path.join(repo, "datasets", "*", "*",
                                    "processed", "canonical")):
        shards = _containers(d, None)
        sampled = bool(cap_shards) and len(shards) > cap_shards
        if sampled:
            shards = rnd.sample(shards, cap_shards)
        for p in shards:
            try:
                blob = _load_container(p)
            except Exception:
                continue
            if isinstance(blob, list):
                for rec in blob:
                    if isinstance(rec, dict):
                        yield rec, sampled
    # one-big-container families
    big = {"canonical", "canonical_imu", "canonical_force", "canonical_emg",
           "canonical_silhouette", "canonical_eeg"}
    for root, _, files in os.walk(os.path.join(repo, "datasets")):
        stems = {}
        for fn in files:
            if fn.startswith("._") or not fn.endswith((".pkl", ".npz")):
                continue
            if fn[:-4] in big:
                # .npz wins over a lingering .pkl of the same stem
                if fn.endswith(".npz") or fn[:-4] not in stems:
                    stems[fn[:-4]] = fn
        for fn in sorted(stems.values()):
                p = os.path.join(root, fn)
                if p in seen_paths:
                    continue
                seen_paths.add(p)
                try:
                    blob = _load_container(p)
                except Exception:
                    continue
                if isinstance(blob, list):
                    for rec in blob:
                        if isinstance(rec, dict):
                            yield rec, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--cap", type=int, default=150,
                    help="per-source record cap (0 = exhaustive)")
    ap.add_argument("--containers", default=None,
                    help="comma list of container paths (relative to the "
                         "repo): measure only these, exhaustively and one "
                         "record at a time, and replace only their "
                         "(family, dataset) rows in docs/mask_statistics.csv")
    args = ap.parse_args()
    rnd = random.Random(0)
    per = {}
    if args.containers:
        from moveatlas import records as _records
        args.cap = 0

        def _only():
            for rel in args.containers.split(","):
                for rec in _records.iter_load(os.path.join(args.repo, rel.strip())):
                    if isinstance(rec, dict):
                        yield rec, False
        stream = _only()
    else:
        stream = iter_records(args.repo, cap_shards=(0 if args.cap == 0 else 40))
    for rec, shard_sampled in stream:
        fam = rec_family(rec)
        if not fam:
            continue
        src = rec.get("source") or "?"
        src = SOURCE_ALIAS.get(src, src)
        key = (fam, src)
        st = per.setdefault(key, {"vals": [], "n_seen": 0,
                                  "sampled": shard_sampled})
        st["n_seen"] += 1
        st["sampled"] = st["sampled"] or shard_sampled
        if args.cap and len(st["vals"]) >= args.cap:
            # reservoir: keep a fixed-seed uniform sample
            j = rnd.randrange(st["n_seen"])
            if j < args.cap:
                u = usability(rec, fam)
                if u is not None:
                    st["vals"][j] = u
            st["sampled"] = True
            continue
        u = usability(rec, fam)
        if u is not None:
            st["vals"].append(u)

    rows = []
    for (fam, src), st in sorted(per.items()):
        v = np.array(st["vals"])
        if not len(v):
            continue
        rows.append([fam, src, st["n_seen"], len(v),
                     "yes" if st["sampled"] or
                     (args.cap and st["n_seen"] > args.cap) else "no",
                     round(float(v.mean()), 4),
                     round(float(np.median(v)), 4),
                     round(float(np.percentile(v, 10)), 4),
                     round(float((v >= 0.999).mean()), 4)])
    out = os.path.join(args.repo, "docs", "mask_statistics.csv")
    if args.containers and os.path.exists(out):
        # merge: the measured (family, dataset) rows replace theirs in place
        with open(out, newline="", encoding="utf-8") as f:
            old = list(csv.reader(f))[1:]
        new = {(r[0], r[1]): r for r in rows}
        merged = [new.pop((r[0], r[1]), r) for r in old if r]
        merged += list(new.values())
        rows = [[r[0], r[1], int(r[2]), int(r[3]), r[4], float(r[5]),
                 float(r[6]), float(r[7]), float(r[8])] for r in merged]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["family", "source", "n_records_seen", "n_measured",
                    "sampled", "usable_mean", "usable_median",
                    "usable_p10", "fully_usable_frac"])
        w.writerows(rows)
    print(f"{out}: {len(rows)} (family, dataset) rows")

    gen = os.path.join(args.repo, "site", "source", "_generated")
    os.makedirs(gen, exist_ok=True)
    html = ["<div style=\"overflow-x:auto\">",
            "<table class=\"table\"><thead><tr><th>Family</th>"
            "<th>Dataset</th><th>Records seen</th><th>Measured</th>"
            "<th>Sampled</th><th>Usable mean</th><th>median</th>"
            "<th>p10</th><th>fully usable</th></tr></thead><tbody>"]
    for r in rows:
        pct = lambda x: f"{x * 100:.1f}%"  # noqa: E731
        html.append(
            f"<tr><td><span class=\"ma-fam ma-{r[0]}\">{r[0]}</span>"
            f"</td><td><b>{r[1]}</b></td><td>{r[2]:,}</td>"
            f"<td>{r[3]:,}</td><td>{r[4]}</td><td><b>{pct(r[5])}</b>"
            f"</td><td>{pct(r[6])}</td><td>{pct(r[7])}</td>"
            f"<td>{pct(r[8])}</td></tr>")
    html.append("</tbody></table></div>")
    with open(os.path.join(gen, "mask_stats.html"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(html))
    print("mask_stats.html written")


if __name__ == "__main__":
    main()
