# -*- coding: utf-8 -*-
"""Fetch the Rat 7M video articles (the mocap core landed 2026-09-01;
this completes the collection). All 8 collection articles verified
CC BY 4.0 via the figshare API on 2026-09-01. Idempotent, sha256
journaled.

Usage: python fetch_rat7m_videos.py [--repo PATH]
"""
import argparse
import hashlib
import json
import os
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (moveatlas-fetch)"}
# the 7 video articles of collection 5295370 (13739233 = mocap, done)
VIDEO_ARTICLES = [13751023, 13753417, 13759336, 13764208, 13767502,
                  13769833, 13770565]


def gj(u):
    with urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=120) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "MOVEATLAS_REPO", os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    dsdir = os.path.join(args.repo, "datasets", "animal", "rat7m")
    for aid in VIDEO_ARTICLES:
        art = gj(f"https://api.figshare.com/v2/articles/{aid}")
        lic = art.get("license", {}).get("name", "?")
        print(f"[{aid}] {art['title'][:60]} | licence {lic} | "
              f"{len(art['files'])} file(s)", flush=True)
        for fobj in art["files"]:
            dest = os.path.join(dsdir, "raw", "videos", fobj["name"])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(dest) and \
                    os.path.getsize(dest) == fobj["size"]:
                print(f"  = {fobj['name']}", flush=True)
                continue
            h = hashlib.sha256()
            n = 0
            with urllib.request.urlopen(urllib.request.Request(
                    fobj["download_url"], headers=UA),
                    timeout=1200) as r, open(dest, "wb") as f:
                while True:
                    c = r.read(1 << 20)
                    if not c:
                        break
                    h.update(c)
                    f.write(c)
                    n += len(c)
            with open(os.path.join(dsdir, "downloads.sha256"), "a",
                      encoding="utf-8", newline="\n") as jf:
                jf.write(f"{h.hexdigest()}  videos/{fobj['name']}  "
                         f"{n}\n")
            print(f"  + {fobj['name']} {n:,} B", flush=True)
    print("rat7m videos done.")


if __name__ == "__main__":
    main()
