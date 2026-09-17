#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage the MoveAtlas corpus record: one Zenodo record, with its own DOI,
that stands for the whole harmonized release and points at its 54
dataset records.

Why (owner decision 2026-09-17): the descriptor cited each of the 54
records in its reference list, a third of the bibliography saying what
Supplementary Table 4 already lists. A single corpus DOI is cited once;
the table keeps the per-record DOIs.

What it writes, and nothing is sent anywhere:
  docs/zenodo_corpus_index.csv   one row per dataset record: dataset id,
                                 record title, record DOI, concept DOI (the
                                 DOI that always resolves to the latest
                                 version), licence id, source identifier
  export/zenodo_staging/moveatlas_corpus/metadata.json
                                 the record: title, description, CC BY 4.0
                                 for the index itself, HasPart -> each
                                 concept DOI, keywords, version
  export/zenodo_staging/moveatlas_corpus/files.csv
                                 the index, with its sha256
  export/zenodo_staging/_plan.csv
                                 a row for moveatlas_corpus (target zenodo)

Then, in the owner's terminal with ZENODO_TOKEN, the usual road:
  python upload_zenodo.py --only moveatlas_corpus       (draft)
  python fix_zenodo_drafts.py --only moveatlas_corpus   (DOI, date)
  python verify_zenodo_drafts.py
  python publish_zenodo_drafts.py --yes --only moveatlas_corpus
and a session runs build_records_table.py, which writes the corpus DOI to
moveatlas/data/zenodo_corpus.json (kept out of the dataset table).

Concept DOIs are read from the public API (no token) and cached in the
staging directory. Usage: python build_zenodo_corpus.py [--refresh]
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.join(REPO, "export", "zenodo_staging")
CORPUS_ID = "moveatlas_corpus"
OUT = os.path.join(STAGING, CORPUS_ID)
INDEX = os.path.join("docs", "zenodo_corpus_index.csv")
SITE = "https://xaviervasques.github.io/moveatlas-site/"


def public(rec_id, tries=6):
    url = f"https://zenodo.org/api/records/{rec_id}"
    for a in range(tries):
        try:
            r = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=120) as x:
                return json.load(x)
        except (urllib.error.URLError, ValueError) as e:
            if a < tries - 1 and getattr(e, "code", None) in (None, 429, 500, 502, 503, 504):
                time.sleep(15 * (a + 1))
                continue
            raise


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true",
                    help="re-read the concept DOIs from Zenodo")
    a = ap.parse_args()
    with open(os.path.join(REPO, "moveatlas", "data", "zenodo_records.json"),
              encoding="utf-8") as f:
        records = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    cache_p = os.path.join(OUT, "concepts.json")
    cache = {}
    if os.path.exists(cache_p) and not a.refresh:
        with open(cache_p, encoding="utf-8") as f:
            cache = json.load(f)
    rows = []
    for did in sorted(records):
        rec = records[did]
        c = cache.get(did)
        if not c or c.get("record") != rec["record"]:
            j = public(rec["record"])
            c = {"record": rec["record"], "conceptdoi": j.get("conceptdoi", "")}
            if not c["conceptdoi"]:
                sys.exit(f"{did}: the public record {rec['record']} has no concept DOI")
            cache[did] = c
            with open(cache_p, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=1, sort_keys=True)
        with open(os.path.join(STAGING, did, "metadata.json"), encoding="utf-8") as f:
            m = json.load(f)["metadata"]
        src = ";".join(r.get("identifier", "") for r in m.get("related_identifiers", [])
                       if r.get("relation") == "isDerivedFrom")
        rows.append([did, m["title"], rec["doi"], c["conceptdoi"],
                     m.get("license", ""), src])
    with open(os.path.join(REPO, INDEX), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["dataset", "record_title", "record_doi", "concept_doi",
                    "licence", "source_identifier"])
        w.writerows(rows)
    n = len(rows)
    desc = (
        "<p><b>MoveAtlas harmonized corpus</b>: the release of the MoveAtlas "
        "resource, a phenotype-indexed catalogue of open recordings of movement "
        f"and its disorders. This record stands for the {n} dataset records of "
        "the release and links to each of them (HasPart, through their concept "
        "DOIs, which always resolve to the latest version).</p>"
        "<p>It holds one file, zenodo_corpus_index.csv: for every dataset record, "
        "its title, record DOI, concept DOI, licence and the identifier of its "
        "source dataset. Each dataset record is a derived work of its source, "
        "published under the licence that source states; the source must be "
        "cited alongside the record. The index itself is released under "
        "CC BY 4.0.</p>"
        f"<p>Documentation and data cards: <a href=\"{SITE}\">{SITE}</a>. "
        "Load any record with the MoveAtlas package:</p>"
        "<pre>pip install git+https://github.com/xaviervasques/moveatlas.git\n\n"
        "import moveatlas\n"
        "records, meta = moveatlas.dataset(&quot;daphnet&quot;).get_data()</pre>")
    meta = {"metadata": {
        "title": "MoveAtlas harmonized corpus, release 1",
        "upload_type": "dataset",
        "description": desc,
        "creators": [{"name": "Vasques, Xavier"}],
        "keywords": ["MoveAtlas", "movement disorders", "harmonized corpus",
                     "wearable sensors", "pose estimation", "EEG", "EMG"],
        "version": "1.0",
        "license": "cc-by-4.0",
        "related_identifiers": (
            [{"identifier": r[3], "relation": "hasPart", "scheme": "doi"}
             for r in rows]
            + [{"identifier": SITE, "relation": "isDocumentedBy", "scheme": "url"}]),
        "notes": f"{n} dataset records; index in zenodo_corpus_index.csv.",
    }}
    with open(os.path.join(OUT, "metadata.json"), "w", newline="\n",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    h = hashlib.sha256(open(os.path.join(REPO, INDEX), "rb").read()).hexdigest()
    with open(os.path.join(OUT, "files.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["path", "bytes", "sha256"])
        w.writerow([INDEX, os.path.getsize(os.path.join(REPO, INDEX)), h])
    plan_p = os.path.join(STAGING, "_plan.csv")
    with open(plan_p, newline="", encoding="utf-8") as f:
        plan = list(csv.reader(f))
    head, body = plan[0], [r for r in plan[1:] if r and r[0] != CORPUS_ID]
    body.append([CORPUS_ID, "zenodo", os.path.getsize(os.path.join(REPO, INDEX)),
                 "CC BY 4.0 (the index)", 1, "yes"])
    body.sort(key=lambda r: r[0])
    with open(plan_p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        w.writerows(body)
    print(f"{CORPUS_ID}: staged, {n} HasPart links, index {INDEX}")


if __name__ == "__main__":
    main()
