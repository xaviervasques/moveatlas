# -*- coding: utf-8 -*-
"""Summarize the NeuroMorpho basal-ganglia subset by disease model and
experiment condition, against the MoveAtlas target cells.

Reads raw/metadata_<region>.json (written by fetch_neuromorpho.py),
writes processed/condition_breakdown.csv: one row per
(species, condition_tag, experiment_condition) with the neuron count
and the MoveAtlas cell the model speaks to. The tagging rules are the
documented mapping below; anything unmatched stays 'other/untagged'.

Usage: python analyze_neuromorpho_conditions.py [--repo PATH]
"""
import argparse
import collections
import csv
import glob
import json
import os

# (substring in strain+condition, tag, MoveAtlas cell it speaks to)
RULES = [
    ("q140", "HD knock-in Q140", "A7"),
    ("q175", "HD knock-in zQ175/Q175", "A7"),
    ("huntington", "HD (labeled condition)", "A7"),
    ("6-ohda", "PD 6-OHDA lesion", "B1-B3"),
    ("synuclein", "PD alpha-synuclein BAC", "B1-B3"),
    ("lrrk2", "PD LRRK2", "B1-B3"),
    ("mptp", "PD MPTP", "B1-B3"),
    ("cerebral artery occlusion", "stroke MCAO", "D3-adjacent"),
    ("cocaine", "dopaminergic pharmacology", "intervention"),
    ("nicotine", "dopaminergic pharmacology", "intervention"),
    ("sch23390", "dopaminergic pharmacology", "intervention"),
    ("d2r-overexpression", "dopaminergic pharmacology", "intervention"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "bio", "neuromorpho_bg")
    outd = os.path.join(base, "processed")
    os.makedirs(outd, exist_ok=True)
    rows = collections.Counter()
    for mpath in glob.glob(os.path.join(base, "raw", "metadata_*.json")):
        region = os.path.basename(mpath)[len("metadata_"):-len(".json")]
        neurons = json.load(open(mpath, encoding="utf-8"))
        for n in neurons:
            cond = n.get("experiment_condition")
            cond = ";".join(cond) if isinstance(cond, list) else str(cond)
            blob = (str(n.get("strain")) + " " + cond).lower()
            tag, cell = "other/untagged", ""
            if cond.strip().lower() in ("control", "none", ""):
                tag, cell = "healthy/control", "baseline"
            for sub, t, c in RULES:
                if sub in blob:
                    tag, cell = t, c
                    break
            rows[(region, str(n.get("species")), tag, cell,
                  cond[:80])] += 1
    out = os.path.join(outd, "condition_breakdown.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["region", "species", "model_tag", "moveatlas_cell",
                    "experiment_condition", "n_neurons"])
        for key, k in sorted(rows.items(), key=lambda x: -x[1]):
            w.writerow(list(key) + [k])
    total = sum(rows.values())
    tagged = sum(k for (r, s, t, c, e), k in rows.items()
                 if t not in ("other/untagged",))
    print(f"{out}: {total} neurons, {tagged} tagged "
          f"({tagged / total:.0%}), {len(rows)} distinct rows")


if __name__ == "__main__":
    main()
