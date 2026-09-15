# -*- coding: utf-8 -*-
"""Fetch the public CODY derived release from Zenodo -> datasets/pose/cody_3/.

The CODY Zenodo deposit (concept DOI 10.5281/zenodo.22232609, CC BY 4.0,
published 2026-09-01, 15.4 GB) is the publishable derived subset of the
in-house CODY cohorts: dataset_0 labels + merged kinematics + SAM3
timeseries (the 25 canonical adults) and datasets_1_2_3 SAM3 timeseries +
results (the 2 adult, 12 pediatric and 20 real-world eval cohorts). Raw
patient video is NOT in the deposit and never leaves the owner's machine.

RUN from the repo root on a machine with network:
    python fetch_cody_zenodo.py --list
    python fetch_cody_zenodo.py                 # everything, resume-safe
    python fetch_cody_zenodo.py --only README.md,MD5SUMS.txt

Stdlib only. The concept DOI resolves to the LATEST version via the Zenodo
API; files verify against the md5 checksums the API reports, a sha256
journal is written next to the files (downloads.sha256), and partial
downloads resume via Range. Destination: datasets/pose/cody_3/zenodo_release/
(the deposit's dataset_0..3 numbering matches cody_3's internal numbering,
NOT the repo ids cody_1..3).
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request

CONCEPT_RECID = "22232609"
API = "https://zenodo.org/api/records/" + CONCEPT_RECID
REPO = os.environ.get("MOVEATLAS_REPO") or os.environ.get("KINEFM_REPO", ".")
DEST = os.path.join(REPO, "datasets", "pose", "cody_3", "zenodo_release")
JOURNAL = os.path.join(DEST, "downloads.sha256")
CHUNK = 1 << 22


def api_files():
    """The latest version's file list: [(name, size, md5, url)]."""
    with urllib.request.urlopen(API) as r:
        rec = json.load(r)
    out = []
    for f in rec["files"]:
        md5 = f["checksum"].split(":", 1)[-1].lower()
        out.append((f["key"], f["size"], md5,
                    f["links"]["self"]))
    return rec["id"], sorted(out)


def hash_file(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def fetch(name, size, md5, url):
    os.makedirs(DEST, exist_ok=True)
    path = os.path.join(DEST, name)
    have = os.path.getsize(path) if os.path.exists(path) else 0
    if have == size and hash_file(path, "md5") == md5:
        print(f"  OK (already verified) {name}")
        return True
    req = urllib.request.Request(url)
    mode = "wb"
    if 0 < have < size:
        req.add_header("Range", f"bytes={have}-")
        mode = "ab"
        print(f"  resuming {name} at {have:,} / {size:,}")
    else:
        print(f"  downloading {name} ({size:,} bytes)")
    with urllib.request.urlopen(req) as r, open(path, mode) as f:
        for block in iter(lambda: r.read(CHUNK), b""):
            f.write(block)
    if hash_file(path, "md5") != md5:
        print(f"  MD5 MISMATCH {name}: delete and rerun", file=sys.stderr)
        return False
    with open(JOURNAL, "a", encoding="utf-8", newline="\n") as j:
        j.write(f"{hash_file(path, 'sha256')}  {name}\n")
    print(f"  verified {name}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", help="comma-separated file names")
    a = ap.parse_args()
    recid, files = api_files()
    print(f"CODY deposit: latest version is record {recid} "
          f"({len(files)} files)")
    if a.list:
        for name, size, md5, _ in files:
            print(f"  {size:>14,}  md5:{md5}  {name}")
        return 0
    wanted = set(a.only.split(",")) if a.only else None
    ok = True
    for name, size, md5, url in files:
        if wanted and name not in wanted:
            continue
        ok = fetch(name, size, md5, url) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
