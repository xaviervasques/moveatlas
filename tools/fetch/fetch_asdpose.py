# -*- coding: utf-8 -*-
"""Fetch the ASDPose/ASDMotion skeleton datasets from their Google
Drive distribution (the two links published in the Dinstein-Lab
ASDMotion README).

Drive mechanics: large files answer the uc endpoint with an HTML
interstitial ("can't scan for viruses"); the real download needs the
confirm token + uuid from that form, replayed against
drive.usercontent.google.com. Small files stream directly.

House discipline: sha256 journaled (Drive publishes no hashes, so the
journal records OUR digest of what landed - the reproducibility
anchor). Licence caveat lives on the datacard: the repo's MIT covers
CODE; the DATA terms are the JAMA data-sharing statement (read before
any redistribution decision). Stdlib only.

Usage: python fetch_asdpose.py
"""
import hashlib
import html.parser
import os
import re
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
DSDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "datasets", "pose", "asdpose")
FILES = {
    "asdmotion_dataset_no_annotations.zip":
        "1MiNIhlf4mL-vRW1ub2TP3nCYzfMW0bYt",
    "asdmotion_annotated_training.zip":
        "13t1tO4ZxTKmQG-w6fTy3hHQy8gX1bopl",
}


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r:
        ctype = r.headers.get("Content-Type", "")
        if "text/html" in ctype:
            body = r.read(1 << 20).decode("utf-8", errors="replace")
            action = re.search(r'action="([^"]+)"', body)
            fields = dict(re.findall(
                r'name="([^"]+)"\s+value="([^"]*)"', body))
            if not action or "confirm" not in body:
                sys.exit(f"unexpected interstitial for {dest} "
                         "(no confirm form) - browser route needed")
            q = urllib.parse.urlencode(fields)
            return fetch(action.group(1) + "?" + q, dest)
        h = hashlib.sha256()
        n = 0
        with open(dest + ".part", "wb") as out:
            for b in iter(lambda: r.read(1 << 22), b""):
                out.write(b)
                h.update(b)
                n += len(b)
        os.replace(dest + ".part", dest)
        return h.hexdigest(), n


def main():
    raw = os.path.join(DSDIR, "raw")
    os.makedirs(raw, exist_ok=True)
    journal = os.path.join(DSDIR, "downloads.sha256")
    done = set()
    if os.path.exists(journal):
        with open(journal) as f:
            done = {ln.split("  ")[1] for ln in f if "  " in ln}
    for name, fid in FILES.items():
        dest = os.path.join(raw, name)
        if name in done and os.path.exists(dest):
            print(f"  = {name}")
            continue
        print(f"  + {name} (Drive id {fid})")
        sha, size = fetch(
            f"https://drive.google.com/uc?export=download&id={fid}", dest)
        print(f"    {size/1e9:.2f} GB, sha256 {sha[:12]}...")
        with open(journal, "a") as j:
            j.write(f"{sha}  {name}  {size}\n")
    print("asdpose fetch done.")


if __name__ == "__main__":
    main()
