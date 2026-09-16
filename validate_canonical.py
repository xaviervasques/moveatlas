# -*- coding: utf-8 -*-
"""Cross-check the canonical manifests against the records they claim to describe.

Written 2026-08-23. The repo had builders and audits but nothing that verified,
after the fact, that a manifest row and the pkl it points at still agree. Every
problem this session surfaced was of that shape: a 0-byte download logged as
complete, a manifest counting 22 patients twice under two ids, a channel table
whose side had been silently lost. This script is the standing check.

It NEVER repairs anything. It reports, and exits non-zero when something is
actually wrong, so it can gate a release build.

Checks, per canonical family (imu, pose/skeleton, eeg, emg, force, silhouette):
  STRUCTURE  every manifest row resolves to a file on disk (for the families
             that store one record per file), and every record on disk appears
             in the manifest (orphans are as bad as dangling rows)
  SHAPE      the pkl loads, and its declared n_frames / channel count match the
             array it carries
  VALUES     no NaN or Inf in the signal, and the signal is not all-zero
  UNITS      the family's declared unit is one the contract allows, and the
             per-family amplitude sanity band is respected (EEG uV, EMG mV,
             IMU acc in g)
  IDENTITY   subject_ns is namespaced by source (source:subject), no subject id
             is shared across two sources (that is how the same patient ends up
             on both sides of a split), and no record id repeats
  SPLITS     reports the subject count per source, which is what a patient-level
             split actually partitions

Usage:
    python validate_canonical.py                 # all families, summary
    python validate_canonical.py --family eeg    # one family
    python validate_canonical.py --full          # open EVERY record (slow)
    python validate_canonical.py --sample 5      # records opened per source
"""
import argparse
import collections
import csv
import glob
import os
import pickle
import random
import re
import sys

import numpy as np

# manifest -> (path column or None if the family stores one big pkl, unit, band)
FAMILIES = {
    "imu": {"manifest": "_canonical_imu_manifest.csv", "path_col": None,
            "unit": "g", "band": (0.05, 32.0), "sig_key": "signal"},
    # the skeleton family predates the per-family naming: its blobs are just
    # canonical.pkl, which is why an earlier version of this script silently
    # validated ZERO pose records while reporting 9761 manifest rows.
    # the skeleton family predates the per-family naming: its blobs are
    # canonical.pkl and its array is "coords", not "signal". An earlier version of
    # this script assumed both and produced 11,836 phantom errors.
    "pose": {"manifest": "_canonical_manifest.csv", "path_col": None,
             "unit": None, "band": None, "sig_key": "coords",
             "pkl_name": "canonical.pkl"},
    # "allowed" is the set the contract permits, not just the canonical target:
    # configs/canonical_emg.yaml says "mV | uV | unknown, canonical target is mV;
    # store what is proven", so a record honestly stored in uV is the contract
    # working, not a deviation to flag.
    "eeg": {"manifest": "_canonical_eeg_manifest.csv", "path_col": "record_path",
            "unit": "uV", "allowed": {"uV"}, "band": (0.5, 20000.0),
            "sig_key": "signal"},
    "emg": {"manifest": "_canonical_emg_manifest.csv", "path_col": "record_path",
            "unit": "mV", "allowed": {"mV", "uV"}, "band": (1e-5, 2000.0),
            "sig_key": "signal"},
    "force": {"manifest": "_canonical_force_manifest.csv", "path_col": None,
              "unit": None, "band": None, "sig_key": "force"},
    # each family names its own array: imu/eeg/emg "signal", skeleton "coords",
    # force "force", silhouette "contour". Assuming one name for all of them was
    # the single biggest source of phantom findings while writing this script.
    "silhouette": {"manifest": "_canonical_silhouette_manifest.csv", "path_col": None,
                   "unit": None, "band": None, "sig_key": "contour"},
}


def _load_container(path):
    """moveatlas-record/1 .npz natively; legacy .pkl through pickle."""
    if path.endswith(".npz"):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from moveatlas import records
        return records.load(path)
    with open(path, "rb") as fh:
        return pickle.load(fh)


def _take(path, full, sample):
    """The records of a list container to check: all of them (--full) or a
    fixed-seed sample, read ONE AT A TIME from an .npz so a container
    larger than memory (weargait_pd, ~7 GB decompressed) can be checked
    on an 8 GB machine. random.sample picks by position, so sampling
    range(n) chooses exactly the records sampling the list did."""
    if not path.endswith(".npz"):
        blob = _load_container(path)
        if not isinstance(blob, list):
            return
        take = blob if full else random.Random(0).sample(blob, min(sample, len(blob)))
        yield from take
        return
    import json as _json
    import zipfile as _zipfile
    from moveatlas import records as _records
    with _zipfile.ZipFile(path) as zf:
        header = _json.loads(zf.read("meta.json"))
        if header.get("kind") != "list":
            return
        metas = header["records"]
        idx = range(len(metas)) if full else \
            random.Random(0).sample(range(len(metas)), min(sample, len(metas)))
        for i in idx:
            yield _records._assemble(zf, metas[i], f"r{i:06d}/")


def _containers_in(d):
    """Record containers of a shard directory: .npz preferred, a legacy
    .pkl only when no .npz sibling exists; AppleDouble ghosts skipped."""
    out = {}
    for suf in (".pkl", ".npz"):
        for p in sorted(glob.glob(os.path.join(d, "*" + suf))):
            if os.path.basename(p).startswith("._"):
                continue
            if suf == ".npz" or p[:-4] not in out:
                out[p[:-4]] = p
    return [out[k] for k in sorted(out)]


class Report:
    def __init__(self):
        self.errors, self.warnings, self.info = [], [], []

    def error(self, fam, msg):
        self.errors.append(f"[{fam}] {msg}")

    def warn(self, fam, msg):
        self.warnings.append(f"[{fam}] {msg}")

    def note(self, msg):
        self.info.append(msg)


def load_manifest(repo, name):
    p = os.path.join(repo, "datasets", name)
    if not os.path.exists(p):
        return None, p
    with open(p, newline="") as f:
        return list(csv.DictReader(f)), p


def check_record(rec, cfg, fam, label, rep):
    """Shape, value and unit checks on one loaded record."""
    sig = rec.get(cfg["sig_key"])
    if sig is None:
        rep.error(fam, f"{label}: record has no '{cfg['sig_key']}' array")
        return
    sig = np.asarray(sig)
    n_declared = rec.get("n_frames")
    if n_declared is not None and int(n_declared) != sig.shape[0]:
        rep.error(fam, f"{label}: n_frames says {n_declared} but the array has "
                       f"{sig.shape[0]} rows")
    chans = rec.get("channels")
    if isinstance(chans, list) and sig.ndim == 2 and len(chans) != sig.shape[1]:
        rep.error(fam, f"{label}: {len(chans)} channel entries but the array has "
                       f"{sig.shape[1]} columns")
    if sig.size == 0:
        rep.error(fam, f"{label}: empty signal")
        return
    finite = np.isfinite(sig)
    if not finite.all():
        n_bad = int((~finite).sum())
        mask = rec.get("channel_mask")
        in_valid = None
        if mask is not None and sig.ndim == 3:
            m = np.asarray(mask)
            if m.shape == sig.shape[1:]:
                in_valid = int(((~finite) & np.broadcast_to(m[None], sig.shape)).sum())
        if in_valid:
            # the dangerous case: a consumer that trusts channel_mask trains on NaN
            rep.error(fam, f"{label}: {in_valid} non-finite sample(s) sit in channels "
                           f"channel_mask marks PRESENT (of {n_bad} non-finite total)")
        else:
            rep.warn(fam, f"{label}: {n_bad} non-finite sample(s), all in channels "
                          "the mask already marks absent")
    vals = sig[finite]
    if vals.size == 0 or float(np.abs(vals).max()) == 0.0:
        # a record that is empty AND says so through its own validity mask is
        # honest bookkeeping (a pose extraction that found nothing), not corruption
        declared_empty = False
        for k in ("valid_mask", "detect_mask", "channel_mask", "sensor_mask"):
            m = rec.get(k)
            if m is not None and int(np.asarray(m).sum()) == 0:
                declared_empty = True
                break
        if declared_empty:
            rep.warn(fam, f"{label}: empty record, and its {k} correctly says so "
                          "(no usable data, excluded by any mask-aware consumer)")
        else:
            rep.error(fam, f"{label}: all-zero {cfg['sig_key']} and NO mask marks it "
                           "absent, so a consumer would read it as real data")
        return
    unit = rec.get("unit")
    # configs/canonical_emg.yaml: "convert only when the source documents its unit;
    # otherwise keep values as-recorded with unit unknown and flag in the audit".
    # So a unit like uV_assumed or unknown is the contract working as designed, not
    # a mismatch to complain about; it just means the band must be read in THAT unit.
    assumed = bool(unit) and (unit.endswith("_assumed") or unit == "unknown")
    base_unit = unit.replace("_assumed", "") if assumed else unit
    allowed = cfg.get("allowed") or ({cfg["unit"]} if cfg["unit"] else set())
    if cfg["unit"] and unit and not assumed and unit not in allowed:
        rep.warn(fam, f"{label}: unit {unit!r} is not one the contract allows "
                      f"({'/'.join(sorted(allowed))})")
    if not cfg["band"]:
        return
    lo, hi = cfg["band"]
    factor = {("uV", "mV"): 1000.0, ("mV", "uV"): 0.001}.get((base_unit, cfg["unit"]))
    if factor:
        lo, hi = lo * factor, hi * factor    # judge the band in the record's own unit
    elif assumed:
        if base_unit not in (cfg["unit"], "unknown", None):
            return
    elif not (unit in allowed or unit is None):
        return
    # Amplitude has to be judged PER CHANNEL KIND. An IMU record carries acc in g
    # AND gyro in deg/s in the same array, and an EMG record carries footswitch and
    # goniometer traces beside the muscles. Pooling them makes every record look
    # like an outlier: the first run of this script "found" 289 g and 29,000 mV,
    # which was this bug and not the data.
    if fam == "imu" and sig.ndim == 3 and sig.shape[2] >= 6:
        acc = sig[:, :, 0:3]
        gyro = sig[:, :, 3:6]
        mask = rec.get("channel_mask")
        if mask is not None:
            mask = np.asarray(mask)
            if mask.shape[:1] == sig.shape[1:2]:
                keep = mask[:, 0:3].any(axis=1)
                if keep.any():
                    acc, gyro = acc[:, keep], gyro[:, keep]
        # a source that removed gravity at the sensor (CoreMotion userAcceleration,
        # e.g. pads) legitimately rests near 0 g; the record declares this, so read
        # the declaration instead of calling a still wrist an outlier.
        acc_band = (0.0005, hi) if rec.get("acc_content") == "linear_no_gravity" \
            else (lo, hi)
        for name, arr, band in (("acc", acc, acc_band),
                                ("gyro", gyro, (0.01, 4000.0))):
            a = arr[np.isfinite(arr)]
            a = a[a != 0]
            if a.size == 0:
                continue
            p99 = float(np.percentile(np.abs(a), 99))
            if not (band[0] <= p99 <= band[1]):
                rep.warn(fam, f"{label}: {name} p99 = {p99:.4g}, outside "
                              f"{band[0]}-{band[1]}")
        return
    if isinstance(chans, list) and sig.ndim == 2 and len(chans) == sig.shape[1]:
        idx = [i for i, c in enumerate(chans)
               if isinstance(c, dict) and c.get("kind") in (None, "emg", "eeg")]
        if idx:
            vals = sig[:, idx]
            vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return
    p99 = float(np.percentile(np.abs(vals), 99))
    if not (lo <= p99 <= hi):
        rep.warn(fam, f"{label}: p99 |value| = {p99:.4g} {cfg['unit']}, outside "
                      f"the plausibility band {lo}-{hi}")


def validate_family(repo, fam, cfg, args, rep):
    rows, mpath = load_manifest(repo, cfg["manifest"])
    if rows is None:
        rep.note(f"{fam:11s} no manifest at {os.path.relpath(mpath, repo)} (skipped)")
        return
    if not rows:
        rep.warn(fam, "manifest is empty")
        return

    by_source = collections.Counter(r.get("source", "?") for r in rows)
    subs_by_source = collections.defaultdict(set)
    for r in rows:
        subs_by_source[r.get("source", "?")].add(r.get("subject_ns", ""))
    rep.note(f"{fam:11s} {len(rows):6d} rows  {len(by_source):2d} sources  "
             f"{sum(len(v) for v in subs_by_source.values()):5d} subjects")

    # IDENTITY: subject_ns must be namespaced, and never shared across sources
    owner = {}
    for r in rows:
        src, ns = r.get("source", "?"), (r.get("subject_ns") or "").strip()
        if not ns:
            rep.error(fam, f"{src}: a row has an empty subject_ns")
            continue
        if ":" not in ns:
            rep.warn(fam, f"{src}: subject_ns {ns!r} is not namespaced as source:subject")
        prev = owner.setdefault(ns, src)
        if prev != src:
            rep.error(fam, f"subject_ns {ns!r} is claimed by BOTH {prev!r} and "
                           f"{src!r}: one patient could land on both sides of a split")

    # STRUCTURE: per-record families must have every row on disk, and no orphans
    pc = cfg["path_col"]
    if pc:
        if pc not in rows[0]:
            rep.error(fam, f"manifest has no {pc!r} column")
            return
        # moveatlas-record/1 migration: a manifest row naming x.pkl is
        # satisfied by x.npz on disk (and the reverse); stems are compared
        def _stem(p):
            p = os.path.normpath(p)
            return p[:-4] if p.endswith((".pkl", ".npz")) else p

        def _resolve(ap):
            if os.path.exists(ap):
                return ap
            if ap.endswith(".pkl") and os.path.exists(ap[:-4] + ".npz"):
                return ap[:-4] + ".npz"
            if ap.endswith(".npz") and os.path.exists(ap[:-4] + ".pkl"):
                return ap[:-4] + ".pkl"
            return None

        listed = set()
        missing = 0
        for r in rows:
            rel = (r.get(pc) or "").strip()
            ap = os.path.join(repo, rel)
            listed.add(_stem(ap))
            if _resolve(ap) is None:
                missing += 1
                if missing <= 5:
                    rep.error(fam, f"manifest points at a missing file: {rel}")
        if missing > 5:
            rep.error(fam, f"...and {missing - 5} more missing file(s)")
        on_disk = set()
        for root, _, files in os.walk(os.path.join(repo, "datasets")):
            if os.path.basename(root) != f"canonical_{fam}":
                continue
            for f in files:
                if f.endswith((".pkl", ".npz")) and not f.startswith("._"):
                    on_disk.add(_stem(os.path.join(root, f)))
        orphans = on_disk - listed
        if orphans:
            rep.error(fam, f"{len(orphans)} record file(s) on disk are NOT in the "
                           f"manifest, e.g. "
                           f"{os.path.relpath(sorted(orphans)[0], repo)}")

        # SHAPE / VALUES on a sample (or everything with --full)
        pool = [r for r in rows if _resolve(os.path.join(repo, r.get(pc, "")))]
        chosen = []
        rnd = random.Random(0)
        for src in sorted(by_source):
            cand = [r for r in pool if r.get("source") == src]
            chosen += cand if args.full else rnd.sample(cand, min(args.sample, len(cand)))
        for r in chosen:
            ap = _resolve(os.path.join(repo, r[pc]))
            try:
                rec = _load_container(ap)
            except Exception as e:
                rep.error(fam, f"{os.path.basename(ap)}: cannot unpickle ({e})")
                continue
            check_record(rec, cfg, fam, os.path.basename(ap), rep)
        rep.note(f"{'':11s} opened {len(chosen)} record(s)")
    else:
        # families stored as one pkl per dataset: locate and sample them.
        # THREE layouts exist in this repo and all three must be covered:
        #   canonical_<fam>.pkl        one list per dataset (most sources)
        #   canonical.pkl              the skeleton family's older name
        #   processed/canonical/*.pkl  SHARDED, used by the socle sets. Missing
        #     this one left amass, motion_x and ntu_rgbd unchecked even after
        #     their 157,058 records entered the central manifest.
        opened = 0
        shard_dirs = sorted(glob.glob(os.path.join(repo, "datasets", "*", "*",
                                                   "processed", "canonical")))
        for d in shard_dirs:
            for sh in _containers_in(d):
                try:
                    blob = _load_container(sh)
                except Exception as e:
                    rep.error(fam, f"{os.path.relpath(sh, repo)}: cannot unpickle ({e})")
                    continue
                if not isinstance(blob, list):
                    continue
                if not blob or not isinstance(blob[0], dict) \
                        or cfg["sig_key"] not in blob[0]:
                    continue                      # shard of another family
                rnd = random.Random(0)
                take = blob if args.full else rnd.sample(blob, min(args.sample, len(blob)))
                for rec in take:
                    check_record(rec, cfg, fam,
                                 f"{os.path.basename(d)}/{rec.get('subject_ns', '?')}", rep)
                    opened += 1
        want_stem = cfg.get("pkl_name", f"canonical_{fam}.pkl")[:-4]
        for root, _, files in os.walk(os.path.join(repo, "datasets")):
            names = set(files)
            for f in files:
                if f.startswith("._") or not f.endswith((".pkl", ".npz")) \
                        or f[:-4] != want_stem:
                    continue
                if f.endswith(".pkl") and f[:-4] + ".npz" in names:
                    continue          # superseded by its .npz sibling
                ap = os.path.join(root, f)
                try:
                    for rec in _take(ap, args.full, args.sample):
                        if isinstance(rec, dict):
                            check_record(rec, cfg, fam,
                                         f"{os.path.basename(root)}/"
                                         f"{rec.get('subject_ns', '?')}", rep)
                            opened += 1
                except Exception as e:
                    rep.error(fam, f"{os.path.relpath(ap, repo)}: cannot read ({e})")
                    continue
        rep.note(f"{'':11s} opened {opened} record(s) from per-dataset pkl files")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--family", default=None, help="comma list: " + ",".join(FAMILIES))
    ap.add_argument("--sample", type=int, default=3,
                    help="records opened per source (default 3)")
    ap.add_argument("--full", action="store_true", help="open every record (slow)")
    args = ap.parse_args()

    fams = list(FAMILIES) if not args.family else [f.strip() for f in args.family.split(",")]
    rep = Report()
    print("canonical validation\n" + "=" * 66)
    for fam in fams:
        if fam not in FAMILIES:
            raise SystemExit(f"unknown family {fam!r}; known: {', '.join(FAMILIES)}")
        validate_family(args.repo, fam, FAMILIES[fam], args, rep)

    for line in rep.info:
        print("  " + line)
    print("-" * 66)

    def show(title, items):
        """Group by the SHAPE of the message, so 226 copies of one naming quirk
        cannot bury the single line that actually matters."""
        if not items:
            return
        groups = collections.OrderedDict()
        for it in items:
            # strip record ids and numbers to get the message shape
            key = re.sub(r"\d+(?:\.\d+)?(?:e[+-]\d+)?", "N", it)
            key = re.sub(r"'[^']*'", "'X'", key)
            groups.setdefault(key, []).append(it)
        print(f"{title} ({len(items)} in {len(groups)} kind(s)):")
        for key, its in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print(f"  x{len(its):<5d} {its[0]}")
            if len(its) > 1:
                print(f"         ...{len(its) - 1} more of this kind, e.g. {its[-1]}")

    show("WARNINGS", rep.warnings)
    if rep.errors:
        show("ERRORS", rep.errors)
        print("\nFAILED")
        return 1
    print(f"OK: {len(rep.warnings)} warning(s), no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
