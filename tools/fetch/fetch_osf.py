# -*- coding: utf-8 -*-
"""Fetch an OSF project's osfstorage tree into a dataset's raw/ dir.

House discipline: recursive folder walk via the OSF v2 API, every file
verified against the SERVER's own sha256 (OSF publishes per-file
hashes), journaled in downloads.sha256, idempotent. The project's
license file (if any) is downloaded like any other file - read it and
date the datacard. Stdlib only.

Usage:
  python fetch_osf.py <node> <dataset_dir>
  python fetch_osf.py mp5ha datasets/imu/osf_tremor_amplitude
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (moveatlas-fetch)"}


def gj(url):
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.load(r)


def sha256_of(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


FAILED_BRANCHES = []


def walk(url, prefix=""):
    """Yield (relpath, size, sha256, download_url) for every file. A
    branch whose listing 5xx's is SKIPPED and recorded (honest partial
    beats a retry storm; rerun later - the journal makes it cheap)."""
    while url:
        try:
            d = gj(url)
        except urllib.error.HTTPError as e:
            FAILED_BRANCHES.append((prefix or "/", e.code))
            print(f"  ! listing failed under '{prefix or '/'}' "
                  f"(HTTP {e.code}) - branch skipped")
            return
        for it in d["data"]:
            a = it["attributes"]
            if a["kind"] == "folder":
                sub = it["relationships"]["files"]["links"]["related"]["href"]
                yield from walk(sub, prefix + a["name"] + "/")
            else:
                yield (prefix + a["name"], a.get("size") or 0,
                       (a.get("extra", {}).get("hashes", {})
                        .get("sha256") or "").lower(),
                       it["links"]["download"])
        url = d.get("links", {}).get("next")


def main():
    node, dsdir = sys.argv[1], sys.argv[2]
    raw = os.path.join(dsdir, "raw")
    os.makedirs(raw, exist_ok=True)
    journal = os.path.join(dsdir, "downloads.sha256")
    done = set()
    if os.path.exists(journal):
        with open(journal) as f:
            done = {ln.split("  ")[1] for ln in f if "  " in ln}
    root = f"https://api.osf.io/v2/nodes/{node}/files/osfstorage/"
    n, total = 0, 0
    for rel, size, want, dl in walk(root):
        dest = os.path.join(raw, rel)
        if rel in done and os.path.exists(dest):
            print(f"  = {rel}")
            continue
        print(f"  + {rel} ({size/1e6:.2f} MB)")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        with urllib.request.urlopen(urllib.request.Request(
                dl, headers=UA), timeout=600) as r, open(tmp, "wb") as out:
            for b in iter(lambda: r.read(1 << 22), b""):
                out.write(b)
        got = sha256_of(tmp)
        if want and got != want:
            os.remove(tmp)
            sys.exit(f"SHA256 MISMATCH on {rel}")
        os.replace(tmp, dest)
        with open(journal, "a") as j:
            j.write(f"{got}  {rel}  {size}\n")
        n += 1
        total += size
    print(f"done: {n} new files, {total/1e6:.1f} MB, server-sha256 "
          f"verified, journal {journal}")
    if FAILED_BRANCHES:
        print("INCOMPLETE - skipped branches (rerun later):",
              FAILED_BRANCHES)
        sys.exit(3)


if __name__ == "__main__":
    main()
