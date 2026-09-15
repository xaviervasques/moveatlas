#!/usr/bin/env python3
"""
Robust mirror of the PADS PhysioNet record (parkinsons-disease-smartwatch),
file by file from SHA256SUMS.txt. The dynamic get-zip endpoint truncates for
this record, so we fetch each file and verify its checksum.

Idempotent: files already present with the correct SHA256 are skipped.
Run inside 'atlas-mouvement':  python pads_mirror.py
"""
import hashlib, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://physionet.org/files/parkinsons-disease-smartwatch/1.0.0/"
RAW = "datasets/imu/pads/raw"
SUMS_URL = BASE + "SHA256SUMS.txt"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(sha, rel):
    out = os.path.join(RAW, rel)
    if os.path.exists(out) and os.path.getsize(out) > 0:
        try:
            if sha256(out) == sha:
                return ("skip", rel)
        except OSError:
            pass
    os.makedirs(os.path.dirname(out), exist_ok=True)
    url = BASE + rel
    for attempt in range(7):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            with open(out, "wb") as f:
                f.write(data)
            if sha256(out) == sha:
                return ("ok", rel)
        except Exception:
            # PhysioNet throttles: back off before retrying
            time.sleep(min(2 ** attempt, 30))
    return ("FAIL", rel)


def main():
    req = urllib.request.Request(SUMS_URL, headers={"User-Agent": "curl/8"})
    lines = urllib.request.urlopen(req, timeout=60).read().decode().splitlines()
    items = []
    for ln in lines:
        parts = ln.strip().split(None, 1)
        if len(parts) == 2:
            items.append((parts[0], parts[1]))
    print(f"{len(items)} files listed", flush=True)

    ok = skip = fail = 0
    fails = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch, s, r) for s, r in items]
        for i, fu in enumerate(as_completed(futs), 1):
            st, rel = fu.result()
            if st == "ok": ok += 1
            elif st == "skip": skip += 1
            else:
                fail += 1; fails.append(rel)
            if i % 1000 == 0:
                print(f"  {i}/{len(items)}  ok={ok} skip={skip} fail={fail}", flush=True)

    print(f"\nDone. ok={ok} skip={skip} fail={fail}", flush=True)
    if fails:
        print("FAILED (first 20):", fails[:20], flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
