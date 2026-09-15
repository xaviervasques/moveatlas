# -*- coding: utf-8 -*-
"""Fetch NeuroMorpho.Org neurons for a brain region via the public API
(CC BY 4.0; API access explicitly allowed, scraping forbidden).

Usage: python fetch_neuromorpho.py <region> <dest_dir>
Phase 1: paginated metadata -> metadata_<region>.json + .csv
Phase 2: CNG .swc per neuron under swc/<archive>/<name>.CNG.swc
Idempotent on existing swc files.
"""
import csv
import json
import os
import sys
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (moveatlas-research)"}
API = "https://neuromorpho.org/api/neuron/select"


def gj(url):
    with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.load(r)


def main():
    region, dest = sys.argv[1], sys.argv[2]
    meta_only = "--meta-only" in sys.argv
    os.makedirs(dest, exist_ok=True)
    q = region.replace(" ", "%20")
    neurons, page = [], 0
    while True:
        data = gj(f"{API}?q=brain_region:{q}&size=500&page={page}")
        batch = data.get("_embedded", {}).get("neuronResources", [])
        if not batch:
            break
        neurons += batch
        total = data["page"]["totalPages"]
        print(f"metadata page {page + 1}/{total} ({len(neurons)})")
        page += 1
        if page >= total:
            break
        time.sleep(0.5)
    tag = region.replace(" ", "_")
    with open(os.path.join(dest, f"metadata_{tag}.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(neurons, f)
    cols = ["neuron_id", "neuron_name", "archive", "species",
            "brain_region", "cell_type", "min_age", "max_age", "gender",
            "strain", "reconstruction_software", "protocol", "domain"]
    with open(os.path.join(dest, f"metadata_{tag}.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for n in neurons:
            w.writerow([";".join(v) if isinstance(v, list) else v
                        for v in (n.get(c, "") for c in cols)])
    print(f"{len(neurons)} neurons in metadata_{tag}.csv")
    if meta_only:
        print("meta-only: no swc fetched")
        return

    n_done = n_skip = n_err = 0
    for n in neurons:
        arch = (n.get("archive") or "").lower()
        name = n.get("neuron_name") or ""
        if not arch or not name:
            continue
        out = os.path.join(dest, "swc", arch, f"{name}.CNG.swc")
        if os.path.exists(out) and os.path.getsize(out) > 0:
            n_skip += 1
            continue
        url = (f"https://neuromorpho.org/dableFiles/{arch}"
               f"/CNG%20version/{name}.CNG.swc")
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers=UA), timeout=120) as r, \
                    open(out, "wb") as f:
                f.write(r.read())
            n_done += 1
            if n_done % 200 == 0:
                print(f"  swc {n_done} done / {n_skip} skipped "
                      f"/ {n_err} errors")
        except Exception:  # noqa: BLE001 - count and continue
            n_err += 1
            try:
                os.remove(out)
            except OSError:
                pass
        time.sleep(0.15)
    print(f"swc: {n_done} downloaded, {n_skip} skipped, {n_err} errors")


if __name__ == "__main__":
    main()
