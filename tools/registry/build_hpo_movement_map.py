# -*- coding: utf-8 -*-
"""Build the HPO movement-phenotype map for the MoveAtlas semantic pivot (stage C).

Input: datasets/ontology/hpo/raw/hp.obo (HPO release bundled with pyhpo 4.0.0,
data-version hp/releases/2025-01-16, obtained 2026-08-22 through PyPI because the
GitHub release assets are not reachable from the session network; refresh from
https://github.com/obophenotype/human-phenotype-ontology/releases when the tower
has network).

Outputs:
  docs/hpo_movement_terms.csv   every descendant of HP:0100022 "Abnormality of
                                movement": id, name, depth, parents, and the
                                MoveAtlas cell(s) whose anchor term contains it
  printed verification          the 13 MoveAtlas anchor terms resolved by id + name

MoveAtlas anchors (taxonomy v2, codes verified on ontology.jax.org 2026-08-21):
  A1 tremor HP:0001337, A2 myoclonus HP:0001336, A3 tics HP:0100033,
  A4 dystonia HP:0001332, A5 stereotypy HP:0000733, A6 athetosis HP:0002305,
  A7 chorea HP:0002072, A8 ballismus HP:0100248,
  B1 rigidity HP:0002063, B2 bradykinesia HP:0002067, B3 hypokinesia HP:0002375,
  B4 akinesia HP:0002304, B5 freezing of gait HP:0031825.
Env: stdlib only. Usage: python build_hpo_movement_map.py [--repo PATH]
"""
import argparse
import csv
import os
from collections import defaultdict, deque

ROOT = "HP:0100022"
ANCHORS = {"HP:0001337": "A1", "HP:0001336": "A2", "HP:0100033": "A3",
           "HP:0001332": "A4", "HP:0000733": "A5", "HP:0002305": "A6",
           "HP:0002072": "A7", "HP:0100248": "A8",
           "HP:0002063": "B1", "HP:0002067": "B2", "HP:0002375": "B3",
           "HP:0002304": "B4", "HP:0031825": "B5"}


def parse_obo(path):
    terms, cur = {}, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line == "[Term]":
            cur = {"id": None, "name": "", "is_a": [], "obsolete": False}
        elif cur is not None:
            if line.startswith("id: "):
                cur["id"] = line[4:].strip()
            elif line.startswith("name: "):
                cur["name"] = line[6:].strip()
            elif line.startswith("is_a: "):
                cur["is_a"].append(line[6:].split("!")[0].strip())
            elif line.startswith("is_obsolete: true"):
                cur["obsolete"] = True
            elif line == "":
                if cur.get("id") and not cur["obsolete"]:
                    terms[cur["id"]] = cur
                cur = None
    if cur and cur.get("id") and not cur["obsolete"]:
        terms[cur["id"]] = cur
    return terms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    obo = os.path.join(args.repo, "datasets", "ontology", "hpo", "raw", "hp.obo")
    terms = parse_obo(obo)
    print(f"{len(terms)} active terms parsed")
    children = defaultdict(list)
    for t in terms.values():
        for p in t["is_a"]:
            children[p].append(t["id"])
    # anchors sanity
    for hid, cell in sorted(ANCHORS.items(), key=lambda kv: kv[1]):
        nm = terms.get(hid, {}).get("name", "MISSING FROM ONTOLOGY")
        print(f"  {cell} {hid} = {nm}")
        if hid not in terms:
            raise SystemExit(f"anchor {hid} missing; ontology file suspect")
    # descendants of each anchor -> cell tag
    cell_of = defaultdict(set)
    for hid, cell in ANCHORS.items():
        dq = deque([hid])
        while dq:
            x = dq.popleft()
            if cell in cell_of[x]:
                continue
            cell_of[x].add(cell)
            dq.extend(children.get(x, []))
    # movement subtree with depth
    depth, dq = {ROOT: 0}, deque([ROOT])
    while dq:
        x = dq.popleft()
        for c in children.get(x, []):
            if c not in depth:
                depth[c] = depth[x] + 1
                dq.append(c)
    out = os.path.join(args.repo, "docs", "hpo_movement_terms.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hpo_id", "name", "depth_under_HP0100022", "parents",
                    "moveatlas_cells"])
        for hid in sorted(depth, key=lambda h: (depth[h], h)):
            t = terms[hid]
            w.writerow([hid, t["name"], depth[hid], "|".join(t["is_a"]),
                        "|".join(sorted(cell_of.get(hid, [])))])
    anchored = sum(1 for h in depth if cell_of.get(h))
    print(f"movement subtree: {len(depth)} terms, {anchored} inside a MoveAtlas "
          f"anchor subtree -> {out}")


if __name__ == "__main__":
    main()
