# -*- coding: utf-8 -*-
"""Download a DANDI dandiset via the public API (no CLI dependency).

Usage: python fetch_dandi.py <dandiset_id> <dest_dir> [--version V]
Lists assets of the most recent published version (fallback: draft),
downloads each with size-skip idempotence, journals sha256.
"""
import argparse
import hashlib
import json
import os
import urllib.request

API = "https://api.dandiarchive.org/api"
UA = {"User-Agent": "Mozilla/5.0 (moveatlas-fetch)"}


def get_json(url):
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dandiset")
    ap.add_argument("dest")
    ap.add_argument("--version")
    args = ap.parse_args()
    ver = args.version
    if not ver:
        info = get_json(f"{API}/dandisets/{args.dandiset}/")
        pub = info.get("most_recent_published_version")
        ver = (pub or info.get("draft_version"))["version"]
    print(f"dandiset {args.dandiset} version {ver}")
    url = (f"{API}/dandisets/{args.dandiset}/versions/{ver}/assets/"
           f"?page_size=100")
    n_done = n_skip = 0
    journal = os.path.join(args.dest, "..", "downloads.sha256")
    while url:
        page = get_json(url)
        for a in page["results"]:
            path = a["path"]
            size = a["size"]
            dest = os.path.join(args.dest, path.replace("/", os.sep))
            if os.path.exists(dest) and os.path.getsize(dest) == size:
                n_skip += 1
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            dl = (f"{API}/assets/{a['asset_id']}/download/")
            h = hashlib.sha256()
            with urllib.request.urlopen(urllib.request.Request(
                    dl, headers=UA), timeout=600) as r, \
                    open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    h.update(chunk)
                    f.write(chunk)
            with open(journal, "a", encoding="utf-8",
                      newline="\n") as jf:
                jf.write(f"{h.hexdigest()}  {path}  {size}\n")
            n_done += 1
            print(f"  + {path} {size:,} B")
        url = page.get("next")
    print(f"done: {n_done} downloaded, {n_skip} already present")


if __name__ == "__main__":
    main()
