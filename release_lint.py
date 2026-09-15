# -*- coding: utf-8 -*-
"""The automated half of the privacy gate (docs/PRIVACY_GATE.md).

Point it at a candidate release tree; it re-derives what is allowed from
license_matrix.csv and the ALLOWLIST below, and prints every violation.
Exit 0 = clean, exit 1 = the release does not ship. ALLOWLIST philosophy:
anything not explicitly allowed is refused; refusal is the default state.

Usage: python release_lint.py <release_dir> [--repo PATH] [--scidata]

--scidata adds the Nature Scientific Data licence gate (policy checked
2026-09-01, docs/SCIDATA_CONFORMITY.md): every dataset whose DATA ships
in the tree must carry an open licence the journal's repository policy
accepts ("CC0 and CC-BY, or their equivalents, are required in most
cases"); anything else is reported, and refused when the flag is set.
"""
import argparse
import csv
import fnmatch
import os
import re
import sys

# licence strings acceptable for a Scientific Data redistribution
# (equivalents of CC0/CC-BY per the repository policy)
SCIDATA_LICENCE_OK = [
    r"\bcc0\b", r"\bcc[ -]?by\b(?![ -]?(nc|nd))", r"\bcc[ -]?by[ -]?sa\b",
    r"physionet open", r"zenodo open", r"\bmit\b", r"\bbsd\b",
    r"public domain", r"\bodc\b", r"\bcc by 4\.0\b",
]

# path patterns allowed in ANY release tree (documentation and metadata)
DOC_ALLOW = ["*.md", "*.csv", "*.bib", "*.yaml", "*.yml", "*.json", "*.html",
             "*.css", "*.py", "*.txt", "*.pdf", "LICENSE*", "*.sha256"]
# data-file patterns allowed ONLY under a dataset dir whose licence row says
# host_copy_ok_with_attribution
# *.pkl left the allowlist with the moveatlas-record/1 migration
# (2026-09-08): a pickle in a release tree is a finding, not a record
DATA_ALLOW = ["*.npz", "*.parquet"]
# The PUBLIC SOURCE tree (export/moveatlas_public) is a repository, not a data
# release: it carries packaging metadata, reStructuredText pages and the site's
# generated figures, none of which DOC_ALLOW knew about, and the gate refused
# all 40 of them (found 2026-09-11, on the tree that was about to go online).
# These patterns are matched on the path RELATIVE TO THE RELEASE ROOT, not on
# the bare filename, which is the point: a .png is allowed where the site and
# the paper keep figures they generate, and stays refused anywhere else - in
# particular anywhere under datasets/, where an image would be a finding.
SOURCE_ALLOW = [
    ".gitignore", ".gitattributes", "LICENSE", "Makefile",
    "pyproject.toml", "CITATION.cff",
    "site/source/*.rst", "site/source/_static/*.png",
    "site/source/_static/*.svg", "site/source/_static/*.ico",
    "site/examples/*.rst", "site/examples/*/*.rst",
    "paper/*.png", "paper/*.csl",
]
# CODY-specific allowlist (the ONLY imagery ever allowed from cody paths)
CODY_ALLOW = ["*_sam3_mask.mp4", "*_sam3_timeseries.xlsx",
              "*keypoints*.xlsx", "*labels*.xlsx", "*.csv"]
# absolute refusals: if one of these matches anywhere, the gate fails hard
HARD_REFUSE = ["*_sam3_overlay.*", "*_sam3_sidebyside.*",
               "*.wmv", "*.mov", "*.avi", "*.mkv",
               "*.pem", "*.key", "*token*", "*password*", "*.env"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("release_dir")
    ap.add_argument("--repo", default=os.environ.get(
        "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--scidata", action="store_true",
                    help="fail on datasets shipping data under a licence "
                         "Scientific Data would not accept")
    args = ap.parse_args()
    # A gate that passes on nothing is not a gate. An absent or empty tree
    # used to print "0 file(s) allowed" and exit 0, so a typo in the path
    # looked exactly like a clean release (found 2026-09-09).
    if not os.path.isdir(args.release_dir):
        print(f"GATE: FAILED. No such release directory: {args.release_dir}")
        return 1
    matrix, licences = {}, {}
    with open(os.path.join(args.repo, "docs", "license_matrix.csv"),
              newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            matrix[row["id"]] = row["portal_action"]
            licences[row["id"]] = row.get("license") or ""

    refused, hard, n_ok = [], [], 0
    shipped_data = set()
    for root, dirs, files in os.walk(args.release_dir):
        # the release tree is a git clone since 2026-09-15; its own
        # metadata is not a shipped file. Everything else is walked.
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in files:
            if fn.startswith("._") or fn == ".DS_Store":
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, args.release_dir).replace(os.sep, "/")
            low = fn.lower()
            if any(fnmatch.fnmatch(low, pat) for pat in HARD_REFUSE):
                hard.append(rel)
                continue
            is_cody = "cody" in rel.lower()
            if is_cody:
                # cody imagery: mask/timeseries/keypoints/labels only, and
                # .mp4 ONLY when it is a _sam3_mask
                if low.endswith(".mp4") and not fnmatch.fnmatch(
                        low, "*_sam3_mask.mp4"):
                    hard.append(rel + "  [cody video that is not a pure mask]")
                    continue
                if any(fnmatch.fnmatch(low, pat) for pat in
                       CODY_ALLOW + DOC_ALLOW):
                    n_ok += 1
                    continue
                refused.append(rel)
                continue
            if low.endswith(".mp4"):
                hard.append(rel + "  [video outside cody mask rules]")
                continue
            if any(fnmatch.fnmatch(low, pat) for pat in DOC_ALLOW):
                n_ok += 1
                continue
            if any(fnmatch.fnmatch(rel, pat) for pat in SOURCE_ALLOW):
                n_ok += 1
                continue
            if any(fnmatch.fnmatch(low, pat) for pat in DATA_ALLOW):
                # data file: its dataset dir must be hosted-tier
                ds = next((part for part in rel.split("/")
                           if part in matrix), None)
                if ds and matrix[ds] == "host_copy_ok_with_attribution":
                    n_ok += 1
                    shipped_data.add(ds)
                else:
                    refused.append(rel + f"  [data file, dataset "
                                   f"{ds or 'UNKNOWN'} is not hosted-tier]")
                continue
            refused.append(rel + "  [no allowlist rule matches]")

    # Scientific Data licence gate: datasets whose data ships must be
    # openly licensed (CC0/CC-BY equivalents per the journal policy)
    scidata_bad = []
    for ds in sorted(shipped_data):
        lic = licences.get(ds, "").lower()
        if not any(re.search(pat, lic) for pat in SCIDATA_LICENCE_OK):
            scidata_bad.append(f"{ds}  [licence: "
                               f"{licences.get(ds, '?')[:70]}]")

    print(f"privacy gate on {args.release_dir}")
    print(f"  {n_ok} file(s) allowed")
    if scidata_bad:
        tag = "REFUSED" if args.scidata else "warning"
        print(f"  {len(scidata_bad)} dataset(s) ship data under a licence "
              f"Scientific Data may not accept ({tag}):")
        for r in scidata_bad:
            print("    ?", r)
        if args.scidata:
            hard.extend(scidata_bad)
    if hard:
        print(f"  {len(hard)} HARD refusal(s) (the gate fails outright):")
        for r in hard[:40]:
            print("    !!", r)
    if refused:
        print(f"  {len(refused)} refused by default (not on any allowlist):")
        for r in refused[:40]:
            print("    -", r)
    if hard or refused:
        print("\nGATE: FAILED. Nothing ships. Fix the tree or extend the "
              "allowlist DELIBERATELY (and say why in the commit).")
        return 1
    if n_ok == 0:
        print("\nGATE: FAILED. The tree contains no allowed file at all, so "
              "there is nothing to certify. Check the path.")
        return 1
    print("\nGATE: PASSED (automated half). The human checklist in "
          "docs/PRIVACY_GATE.md still applies before upload.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
