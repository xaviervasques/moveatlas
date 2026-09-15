# -*- coding: utf-8 -*-
"""Fetch a Dataverse dataset (RDG, DataverseNL, Harvard...) into a
dataset's raw/ dir.

House discipline: licence read from the dataset version at fetch time
and printed; every file verified against the SERVER's checksum
(Dataverse publishes MD5 or SHA per file); journal downloads.sha256
records our sha256 + the server-verified status. Idempotent. Stdlib.

Usage:
  python fetch_dataverse.py <server> <persistent_id> <dataset_dir>
  python fetch_dataverse.py https://entrepot.recherche.data.gouv.fr \
      doi:10.57745/THHWP2 datasets/imu/drummer_tremor_model
"""
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (moveatlas-fetch)"}


def gj(url):
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.load(r)


def digests(path, chunk=1 << 22):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            md5.update(b)
            sha.update(b)
    return md5.hexdigest(), sha.hexdigest()


def main():
    server, pid, dsdir = sys.argv[1], sys.argv[2], sys.argv[3]
    d = gj(f"{server}/api/datasets/:persistentId?persistentId="
           + urllib.parse.quote(pid))
    if d.get("status") != "OK":
        sys.exit(f"dataverse error: {d.get('message')}")
    v = d["data"]["latestVersion"]
    lic = (v.get("license") or {}).get("name") or "NO LICENSE FIELD"
    print(f"licence (dataset version, verified at fetch): {lic}")
    raw = os.path.join(dsdir, "raw")
    os.makedirs(raw, exist_ok=True)
    journal = os.path.join(dsdir, "downloads.sha256")
    done = set()
    if os.path.exists(journal):
        with open(journal) as f:
            done = {ln.split("  ")[1] for ln in f if "  " in ln}
    n, total = 0, 0
    for f in v["files"]:
        df = f["dataFile"]
        rel = (f.get("directoryLabel", "") + "/" if f.get("directoryLabel")
               else "") + df["filename"]
        dest = os.path.join(raw, rel)
        if rel in done and os.path.exists(dest):
            print(f"  = {rel}")
            continue
        print(f"  + {rel} ({df['filesize']/1e6:.1f} MB)")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        url = f"{server}/api/access/datafile/{df['id']}?format=original"
        with urllib.request.urlopen(urllib.request.Request(
                url, headers=UA), timeout=900) as r, open(tmp, "wb") as out:
            for b in iter(lambda: r.read(1 << 22), b""):
                out.write(b)
        md5, sha = digests(tmp)
        ck = df.get("checksum", {})
        want = (ck.get("value") or "").lower()
        got = {"MD5": md5, "SHA-1": None, "SHA-256": sha,
               "SHA-512": None}.get(ck.get("type"))
        if want and got and got != want:
            os.remove(tmp)
            sys.exit(f"{ck.get('type')} MISMATCH on {rel}")
        os.replace(tmp, dest)
        with open(journal, "a") as j:
            j.write(f"{sha}  {rel}  {df['filesize']}  "
                    f"server-{ck.get('type','none')}-verified\n")
        n += 1
        total += df["filesize"]
    print(f"done: {n} new files, {total/1e6:.1f} MB, journal {journal}")


if __name__ == "__main__":
    main()
