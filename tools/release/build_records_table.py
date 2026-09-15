# -*- coding: utf-8 -*-
"""Build moveatlas/data/zenodo_records.json: dataset id -> MoveAtlas
harmonized Zenodo record. Source of truth: the campaign journal
(export/zenodo_staging/_uploaded.json, written by upload_zenodo.py) -
record ids and pre-reserved DOIs are known at draft time and stay
identical at publication, so this table can be built before the owner
clicks Publish (RemoteStore answers honestly on a 404 until then).

Run after every campaign change; ship the JSON with the package.
Stdlib only. Usage: python build_records_table.py
"""
import json
import os

REPO = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(REPO, "export", "zenodo_staging", "_uploaded.json")
OUT = os.path.join(REPO, "moveatlas", "data", "zenodo_records.json")


def main():
    with open(JOURNAL, encoding="utf-8") as f:
        journal = json.load(f)
    table = {}
    for did, entry in sorted(journal.items()):
        table[did] = {"record": entry["deposition"], "doi": entry["doi"]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(table, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"wrote {OUT}: {len(table)} records")


if __name__ == "__main__":
    main()
