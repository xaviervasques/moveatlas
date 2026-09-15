# -*- coding: utf-8 -*-
"""Migrate every canonical record container from pickle to the
moveatlas-record/1 .npz container (moveatlas/records.py), verifying the
round trip before anything is trusted.

Walks datasets/**/processed/ for *.pkl (skipping AppleDouble ._ files),
writes the .npz sibling, reads it back and checks records.equal() against
the pickle content (array dtype/shape/values incl. NaN, metadata after
JSON normalization). A container that fails verification keeps its .pkl
and is listed; nothing is deleted unless --delete-pkl is given AND the
sibling verified. Idempotent: an existing .npz that verifies is skipped
(fast path: skip re-verification with --trust-existing).

Journal: _paris_logs/npz_conversion_<date>.csv
        (path, status, n_records, pkl_bytes, npz_bytes, seconds, note)
Usage:  python convert_records_to_npz.py [--repo PATH] [--workers 4]
                                         [--only-under datasets/eeg]
                                         [--delete-pkl] [--trust-existing]
"""
import argparse
import csv
import datetime as dt
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moveatlas import records  # noqa: E402


def find_pickles(root, only_under=None):
    base = os.path.join(root, only_under) if only_under else \
        os.path.join(root, "datasets")
    out = []
    for d, _, files in os.walk(base):
        if os.sep + "processed" not in d + os.sep:
            continue
        for f in files:
            if f.endswith(".pkl") and not f.startswith("._"):
                out.append(os.path.join(d, f))
    return sorted(out)


def convert_one(pkl, delete, trust_existing):
    t0 = time.time()
    npz = pkl[:-4] + ".npz"
    try:
        with open(pkl, "rb") as f:
            obj = pickle.load(f)
        if not isinstance(obj, (dict, list)):
            return pkl, "SKIP_NOT_RECORD", 0, os.path.getsize(pkl), 0, \
                time.time() - t0, type(obj).__name__
        if isinstance(obj, list) and not all(isinstance(r, dict) for r in obj):
            return pkl, "SKIP_NOT_RECORD", 0, os.path.getsize(pkl), 0, \
                time.time() - t0, "list of non-dicts"
        n = 1 if isinstance(obj, dict) else len(obj)
        if os.path.exists(npz):
            if trust_existing:
                status = "EXISTS"
            else:
                status = "EXISTS_VERIFIED" if records.equal(records.load(npz), obj) \
                    else "EXISTS_MISMATCH"
        else:
            records.save(npz, obj)
            status = "OK" if records.equal(records.load(npz), obj) else "MISMATCH"
            if status == "MISMATCH":
                os.remove(npz)
        note = ""
        if delete and status in ("OK", "EXISTS_VERIFIED"):
            os.remove(pkl)
            note = "pkl deleted"
        return pkl, status, n, os.path.getsize(pkl) if os.path.exists(pkl) else 0, \
            os.path.getsize(npz) if os.path.exists(npz) else 0, \
            time.time() - t0, note
    except Exception as e:  # keep the pkl, report
        if os.path.exists(npz + ".part"):
            os.remove(npz + ".part")
        return pkl, "ERROR", 0, os.path.getsize(pkl), 0, time.time() - t0, \
            f"{type(e).__name__}: {str(e)[:160]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only-under", default=None)
    ap.add_argument("--delete-pkl", action="store_true")
    ap.add_argument("--trust-existing", action="store_true")
    ap.add_argument("--rewrite-manifests", action="store_true",
                    help="point record_path columns of the per-record "
                         "manifests (eeg, emg) at the .npz where it exists; "
                         "no conversion pass")
    a = ap.parse_args()

    if a.rewrite_manifests:
        for name in ("_canonical_eeg_manifest.csv", "_canonical_emg_manifest.csv"):
            p = os.path.join(a.repo, "datasets", name)
            if not os.path.exists(p):
                continue
            with open(p, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            head, body = rows[0], rows[1:]
            col = head.index("record_path")
            n = 0
            for r in body:
                rp = r[col]
                if rp.endswith(".pkl") and os.path.exists(
                        os.path.join(a.repo, rp[:-4] + ".npz")):
                    r[col] = rp[:-4] + ".npz"
                    n += 1
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(head)
                w.writerows(body)
            print(f"{name}: {n} record_path rows now .npz "
                  f"({sum(1 for r in body if r[col].endswith('.pkl'))} still .pkl)")
        return

    pkls = find_pickles(a.repo, a.only_under)
    total = sum(os.path.getsize(p) for p in pkls)
    print(f"{len(pkls)} pickle containers, {total/1e9:.1f} GB", flush=True)
    stamp = dt.date.today().isoformat()
    jpath = os.path.join(a.repo, "_paris_logs", f"npz_conversion_{stamp}.csv")
    os.makedirs(os.path.dirname(jpath), exist_ok=True)
    counts = {}
    done_bytes = 0
    t0 = time.time()
    with open(jpath, "a", newline="", encoding="utf-8") as jf, \
            ProcessPoolExecutor(max_workers=a.workers) as ex:
        w = csv.writer(jf, lineterminator="\n")
        if jf.tell() == 0:
            w.writerow(["path", "status", "n_records", "pkl_bytes",
                        "npz_bytes", "seconds", "note"])
        futs = {ex.submit(convert_one, p, a.delete_pkl, a.trust_existing): p
                for p in pkls}
        for i, fu in enumerate(as_completed(futs), 1):
            path, status, n, pb, nb, sec, note = fu.result()
            w.writerow([os.path.relpath(path, a.repo), status, n, pb, nb,
                        f"{sec:.1f}", note])
            jf.flush()
            counts[status] = counts.get(status, 0) + 1
            done_bytes += pb
            if status not in ("OK", "EXISTS", "EXISTS_VERIFIED"):
                print(f"  {status}: {os.path.relpath(path, a.repo)} {note}",
                      flush=True)
            if i % 50 == 0 or i == len(pkls):
                el = time.time() - t0
                print(f"  {i}/{len(pkls)} {done_bytes/1e9:.1f} GB "
                      f"{el/60:.1f} min {counts}", flush=True)
    print(f"done: {counts}; journal {jpath}", flush=True)
    bad = sum(v for k, v in counts.items()
              if k in ("MISMATCH", "EXISTS_MISMATCH", "ERROR"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
