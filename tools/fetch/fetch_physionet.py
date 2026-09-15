# -*- coding: utf-8 -*-
"""Fetch an open-access PhysioNet record into a dataset's raw/ dir, file by
file from the record's own SHA256SUMS.txt (pads_mirror.py generalized -
the dynamic get-zip endpoint truncates on large records, and the
per-file route is the one that carries the server's hashes).

House discipline: every file verified against the SERVER's sha256,
journaled in downloads.sha256 (sha256  path  bytes, LF). Idempotent: a
file already present whose hash matches is skipped. PhysioNet throttles
scripted clients: 4 workers, exponential back-off, no retry storm. The
licence is read by the caller from the record page (PhysioNet publishes
no DataCite rights) and written on the datacard.

Usage:
  python fetch_physionet.py <slug> <version> <dataset_dir>
  python fetch_physionet.py multimodal-gait-dataset 1.0.0 datasets/eeg/physionet_multimodal_gait
"""
import hashlib
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = {"User-Agent": "Mozilla/5.0 (moveatlas-fetch)"}


def sha256_of(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def fetch(base, raw, sha, rel):
    out = os.path.join(raw, *rel.split("/"))
    if os.path.exists(out) and os.path.getsize(out) > 0:
        try:
            if sha256_of(out) == sha:
                return "skip", rel, os.path.getsize(out)
        except OSError:
            pass
    os.makedirs(os.path.dirname(out), exist_ok=True)
    url = base + urllib.request.quote(rel)
    tmp = out + ".part"
    for attempt in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=300) as r, open(tmp, "wb") as f:
                for b in iter(lambda: r.read(1 << 22), b""):
                    f.write(b)
            if sha256_of(tmp) == sha:
                os.replace(tmp, out)
                return "ok", rel, os.path.getsize(out)
            os.remove(tmp)
            return "MISMATCH", rel, 0
        except Exception:
            time.sleep(min(2 ** attempt, 30))
    return "FAIL", rel, 0


def main():
    slug, version, dsdir = sys.argv[1], sys.argv[2], sys.argv[3]
    base = f"https://physionet.org/files/{slug}/{version}/"
    raw = os.path.join(dsdir, "raw")
    os.makedirs(raw, exist_ok=True)
    sums = urllib.request.urlopen(urllib.request.Request(
        base + "SHA256SUMS.txt", headers=UA), timeout=60).read().decode()
    items = [ln.split(None, 1) for ln in sums.splitlines() if ln.strip()]
    items = [(s, r.strip()) for s, r in items if r.strip()]
    print(f"{slug} {version}: {len(items)} files listed in SHA256SUMS.txt", flush=True)
    # keep the server's own hash list next to the data as evidence
    with open(os.path.join(dsdir, "SHA256SUMS.txt"), "w", newline="\n") as f:
        f.write(sums)

    journal = os.path.join(dsdir, "downloads.sha256")
    done = set()
    if os.path.exists(journal):
        with open(journal) as f:
            done = {ln.split()[1] for ln in f if ln.strip()}

    sha_of = {r: s for s, r in items}
    ok = skip = bad = 0
    fails = []
    with ThreadPoolExecutor(max_workers=4) as ex, \
            open(journal, "a", newline="\n") as j:
        futs = [ex.submit(fetch, base, raw, s, r) for s, r in items]
        for i, fu in enumerate(as_completed(futs), 1):
            st, rel, size = fu.result()
            if st in ("ok", "skip"):
                if st == "ok":
                    ok += 1
                else:
                    skip += 1
                if rel not in done:
                    j.write(f"{sha_of[rel]}  {rel}  {size}\n")
                    j.flush()
            else:
                bad += 1
                fails.append((st, rel))
            if i % 50 == 0 or i == len(items):
                print(f"  {i}/{len(items)}  ok={ok} skip={skip} bad={bad}", flush=True)
    print(f"done: ok={ok} skip={skip} bad={bad}; server-sha256 verified, "
          f"journaled in {journal}", flush=True)
    if fails:
        print("FAILED (first 20):", fails[:20], flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
