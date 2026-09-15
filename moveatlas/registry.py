# -*- coding: utf-8 -*-
"""The dataset registry: one row per catalogued dataset.

Single source of truth is the repository's generated index
(docs/datasets_index.csv + docs/license_matrix.csv, both emitted by
gen_datacards.py). Resolution order for the CSVs:

1. $MOVEATLAS_REPO/docs/ when the env var is set;
2. the repository docs/ next to an editable install (../docs from here);
3. the snapshot bundled as package data (moveatlas/data/), refreshed by the
   release pipeline.

The registry does not open any data file; it only serves metadata and the
access-case classification that datasets/base.py enforces.
"""
import csv
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def snapshot_info():
    """Provenance of the registry snapshot bundled as package data
    (moveatlas/data/SNAPSHOT.json: generated_at, datasets_index_rows,
    license_matrix_rows, source). Returns {} when the file is absent.
    This describes the bundled copy only; the registry itself may be
    reading docs/ instead (see _docs_dir)."""
    path = os.path.join(_HERE, "data", "SNAPSHOT.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


_RECORDS = None


def records_table():
    """dataset id -> {"record": zenodo record id, "doi": ...}: the published
    MoveAtlas records, shipped with the package
    (moveatlas/data/zenodo_records.json, written by build_records_table.py).
    {} when the file is absent. Read once per process."""
    global _RECORDS
    if _RECORDS is None:
        p = os.path.join(_HERE, "data", "zenodo_records.json")
        try:
            with open(p, encoding="utf-8") as f:
                _RECORDS = json.load(f)
        except (OSError, ValueError):
            _RECORDS = {}
    return _RECORDS


def _docs_dir():
    cand = []
    env = os.environ.get("MOVEATLAS_REPO")
    if env:
        cand.append(os.path.join(env, "docs"))
    cand.append(os.path.abspath(os.path.join(_HERE, "..", "docs")))
    cand.append(os.path.join(_HERE, "data"))
    for c in cand:
        if os.path.exists(os.path.join(c, "datasets_index.csv")):
            return c
    raise FileNotFoundError(
        "datasets_index.csv not found; set MOVEATLAS_REPO to the repository "
        "root or reinstall the package (bundled snapshot missing)")


def _read(name):
    with open(os.path.join(_docs_dir(), name), newline="",
              encoding="utf-8") as f:
        return list(csv.DictReader(f))


def access_case(row):
    """Classify a registry row into the four access cases.

    - hosted: redistribution allowed, our record store serves it.
    - local_only: private-tier data on disk (empty since 2026-09-01: the
      CODY derived release went public on Zenodo and the cody ids
      classify as hosted; raw patient video stays in-house, outside
      the atlas).
    - barrier: a documented access barrier (no automated route).
    - recipe: everything else (fetch from origin + local ingestion).
    """
    redist = (row.get("redistribution") or "").strip().lower()
    status = (row.get("status") or "")
    lic = (row.get("license") or "").lower()
    if lic.startswith("private"):
        return "local_only"
    if redist.startswith("yes"):
        # Since the 53 records went public (2026-09-15) "hosted" means
        # exactly "served from a published MoveAtlas record". A
        # redistributable dataset without a record is fetched at its
        # origin like any recipe until it is staged and published.
        if row.get("id") in records_table():
            return "hosted"
        return "recipe"
    up = status.upper()
    if ("DOCUMENTED BARRIER" in up or "WRITTEN OFF" in up
            or "HUMAN QUEUE" in up):
        return "barrier"
    return "recipe"


def list_datasets(family=None, case=None):
    """Return registry rows (dicts), optionally filtered by family or
    access case. Each row gains an 'access_case' key."""
    rows = _read("datasets_index.csv")
    lic = {r["id"]: r for r in _read("license_matrix.csv")}
    out = []
    for r in rows:
        r = dict(r)
        r.setdefault("license", lic.get(r["id"], {}).get("license", ""))
        r["portal_action"] = lic.get(r["id"], {}).get("portal_action", "")
        r["access_case"] = access_case(r)
        if family and r["family"] != family:
            continue
        if case and r["access_case"] != case:
            continue
        out.append(r)
    return out


def dataset_info(code):
    """The registry row for one dataset id, or raise with the known ids."""
    for r in list_datasets():
        if r["id"] == code:
            return r
    known = ", ".join(sorted(x["id"] for x in list_datasets()))
    raise KeyError(f"unknown dataset '{code}'; known: {known}")
