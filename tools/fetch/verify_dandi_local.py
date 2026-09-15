# -*- coding: utf-8 -*-
"""Verify local DANDI files against the archive's own per-asset
sha2-256 digests (the source of truth, independent of our download
journals - written 2026-09-03 after a double-writer incident: two
concurrent fetchers per dandiset ran for ~25 h, so stream-hash
journals cannot vouch for the files on disk).

Files that mismatch, or whose asset carries no sha2-256 digest, are
DELETED so the single relaunched fetcher re-pulls them.

Usage: python verify_dandi_local.py <dandiset_id> <raw_dir>
"""
import hashlib
import json
import os
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (moveatlas-verify)"}


def gj(u):
    with urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=120) as r:
        return json.load(r)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            c = f.read(1 << 22)
            if not c:
                break
            h.update(c)
    return h.hexdigest()


def main():
    dsid, rawd = sys.argv[1], sys.argv[2]
    info = gj(f"https://api.dandiarchive.org/api/dandisets/{dsid}/")
    ver = info["most_recent_published_version"]["version"]
    u = (f"https://api.dandiarchive.org/api/dandisets/{dsid}/versions/"
         f"{ver}/assets/?page_size=200")
    assets = {}
    while u:
        p = gj(u)
        for a in p["results"]:
            assets[a["path"].replace("/", os.sep)] = a
        u = p.get("next")
    print(f"{dsid}: {len(assets)} assets in version {ver}", flush=True)

    local = []
    for root, _, files in os.walk(rawd):
        for fn in files:
            if fn.startswith("._") or fn.endswith(".sha256"):
                continue
            fp = os.path.join(root, fn)
            local.append((os.path.relpath(fp, rawd), fp))
    print(f"{len(local)} local files to verify", flush=True)

    ok = bad = noverify = orphan = 0
    for rel, fp in sorted(local):
        a = assets.get(rel)
        if a is None:
            print(f"  ORPHAN (not in version): {rel} -> DELETED")
            os.remove(fp)
            orphan += 1
            continue
        size = os.path.getsize(fp)
        if size != a["size"]:
            print(f"  BAD size {size} != {a['size']}: {rel} -> DELETED")
            os.remove(fp)
            bad += 1
            continue
        detail = gj(f"https://api.dandiarchive.org/api/assets/"
                    f"{a['asset_id']}/")
        digest = (detail.get("digest") or {}).get("dandi:sha2-256")
        if not digest:
            print(f"  NOVERIFY (no sha2-256 digest): {rel} -> DELETED")
            os.remove(fp)
            noverify += 1
            continue
        if sha256_file(fp) == digest:
            ok += 1
        else:
            print(f"  BAD digest: {rel} -> DELETED", flush=True)
            os.remove(fp)
            bad += 1
        if (ok + bad) % 100 == 0:
            print(f"  ... {ok} ok / {bad} bad so far", flush=True)
    print(f"VERDICT {dsid}: {ok} OK / {bad} BAD / {noverify} "
          f"unverifiable / {orphan} orphan (all non-OK deleted)")


if __name__ == "__main__":
    main()
