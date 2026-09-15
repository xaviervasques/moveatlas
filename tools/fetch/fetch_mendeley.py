# -*- coding: utf-8 -*-
"""Fetch a Mendeley Data record into a dataset's raw/ dir.

House discipline: licence read from DataCite at fetch time and printed
(the card gets the verification date), every file verified against the
SERVER's own sha256 (Mendeley publishes per-file hashes), journaled in
downloads.sha256 (sha256  path  bytes). Idempotent: existing files with
a matching journal entry are skipped. Stdlib only.

Usage:
  python fetch_mendeley.py <slug> <version> <dataset_dir>
  python fetch_mendeley.py fd6sdp6t7x 1 datasets/imu/mendeley_et_accel
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
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


def main():
    slug, version, dsdir = sys.argv[1], sys.argv[2], sys.argv[3]
    doi = f"10.17632/{slug}.{version}"
    dc = gj(f"https://api.datacite.org/dois/{urllib.parse.quote(doi)}")
    at = dc["data"]["attributes"]
    rights = [r.get("rights") for r in at.get("rightsList", []) if r.get("rights")]
    print(f"record: {at['titles'][0]['title'][:80]}")
    print(f"licence (DataCite, verified at fetch): {rights}")
    # A record's files can live entirely in subfolders: the root file
    # listing of such a record answers [] (the sensefog trap, 2026-09-07
    # - an "empty via API" verdict that a browser check refuted), so
    # walk the folder tree, not just root. The folders endpoint returns
    # every folder flat with parent_id; a parent id absent from the map
    # is the (unlisted) root.
    base = f"https://data.mendeley.com/public-api/datasets/{slug}"
    try:
        folders = gj(f"{base}/folders/{version}") or []
    except urllib.error.HTTPError:
        folders = []
    fmap = {f["id"]: f for f in folders}

    def fpath(fid):
        # rstrip: sensefog's remote tree holds a folder literally named
        # "SenseFOG-main " (trailing space) - not creatable on Windows.
        parts = []
        while fid in fmap:
            parts.append(fmap[fid]["name"].rstrip(" ."))
            fid = fmap[fid].get("parent_id")
        return "/".join(reversed(parts))

    listing = []  # (relpath, file entry)
    for fid, prefix in [("root", "")] + [(f["id"], fpath(f["id"]))
                                         for f in folders]:
        for f in gj(f"{base}/files?folder_id={fid}&version={version}"):
            rel = f"{prefix}/{f['filename']}" if prefix else f["filename"]
            listing.append((rel, f))

    raw = os.path.join(dsdir, "raw")
    os.makedirs(raw, exist_ok=True)
    journal = os.path.join(dsdir, "downloads.sha256")
    done = set()
    if os.path.exists(journal):
        with open(journal) as f:
            done = {ln.split()[1] for ln in f if ln.strip()}
    total = 0
    for rel, f in listing:
        cd = f["content_details"]
        dest = os.path.join(raw, *rel.split("/"))
        if rel in done and os.path.exists(dest):
            print(f"  = {rel} (journaled)")
            continue
        print(f"  + {rel} ({cd['size']/1e6:.1f} MB)")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        with urllib.request.urlopen(urllib.request.Request(
                cd["download_url"], headers=UA), timeout=600) as r, \
                open(tmp, "wb") as out:
            for b in iter(lambda: r.read(1 << 22), b""):
                out.write(b)
        got = sha256_of(tmp)
        want = (cd.get("sha256_hash") or "").lower()
        if want and got != want:
            os.remove(tmp)
            sys.exit(f"SHA256 MISMATCH on {rel}: server {want[:12]}..., "
                     f"got {got[:12]}...")
        os.replace(tmp, dest)
        with open(journal, "a", newline="\n") as j:
            j.write(f"{got}  {rel}  {cd['size']}\n")
        total += cd["size"]
    print(f"done: {len(listing)} files, {total/1e6:.1f} MB new, "
          f"server-sha256 verified, journaled in {journal}")


if __name__ == "__main__":
    main()
