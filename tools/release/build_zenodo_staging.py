# -*- coding: utf-8 -*-
"""Prepare the Zenodo/HF upload staging for the hosted tier.

For each hosted dataset this writes export/zenodo_staging/<id>/:
  metadata.json   Zenodo deposition metadata (title, description, license,
                  keywords, related identifiers pointing at the SOURCE
                  DOI and paper), ready for the deposition API
  files.csv       the canonical files that make the record (path, size;
                  sha256 filled by --hash, a long pass kept separate)
plus _plan.csv at the staging root: id, target (zenodo|hf), size, license.

Nothing uploads from here: publishing needs the owner's Zenodo/HF
accounts and the publication-gate go (docs/MOVEATLAS_PLATFORM_DESIGN.md
section 8). This script only makes that day a mechanical one.

Usage: python build_zenodo_staging.py [--hash] [--only id1,id2]
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moveatlas

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "export", "zenodo_staging")
ZENODO_CAP = 50e9

# Zenodo licence ids, every one checked against
# https://zenodo.org/api/vocabularies/licenses on 2026-09-09.
#
# A note on the two ids this table used before that date, "cc-zero" and
# "odc-by": they answer 404 in that vocabulary, which is the InvenioRDM
# one. The legacy deposition API still accepts them AND still reports
# them back for the classic licences (a deposit set to "cc0-1.0" reads
# back as "cc-zero", "mit" reads back as "mit-license"), so the old
# values were not breaking anything. The table uses the vocabulary
# spellings because those are the ones that resolve when checked, and
# the API normalises them either way.
#
# Ordered: the first matching token wins, so the more specific strings
# come first.
#
# A source that is open but carries no formal instrument ("PhysioNet
# open", "UCI open", "free") is NOT relabelled as CC0 or CC BY: it gets
# "other-open" ("Other (Open)"), which is what it is. Public-domain-like
# government data gets "other-pd". Inventing a licence for a dataset whose
# author never granted one would be the worst kind of wrong.
LICENSE_IDS = [
    ("cc by-nc-nd", None),          # never deposited; refused upstream
    ("cc by-nc-sa", "cc-by-nc-sa-4.0"),
    ("cc by-nc", "cc-by-nc-4.0"),
    ("cc by-sa", "cc-by-sa-4.0"),
    ("cc0", "cc0-1.0"),
    ("cc-zero", "cc0-1.0"),
    ("public domain dedication", "cc0-1.0"),
    ("cc-by-4.0", "cc-by-4.0"),
    ("cc by 4.0", "cc-by-4.0"),
    ("cc by", "cc-by-4.0"),
    ("odc-by", "odc-by-1.0"),
    ("pddl", "pddl-1.0"),
    ("etalab", "etalab-2.0"),
    ("apache", "apache-2.0"),
    ("mit", "mit"),
    ("bsd-3", "bsd-3-clause"),
    ("us public domain", "other-pd"),
    ("public-domain-like", "other-pd"),
    ("ncbi public data", "other-pd"),
    ("physionet open", "other-open"),
    ("zenodo open", "other-open"),
    ("uci open", "other-open"),
    ("open supplementary", "other-open"),
    ("free-use with attribution", "other-open"),
    ("free (", "other-open"),
]


def license_id(text):
    """The Zenodo licence id for a registry licence string, or None when
    the string names no instrument this table recognises. The list is
    ordered: the first token that appears wins, so "cc by-nc-sa" is tested
    before "cc by"."""
    # Match the LEADING statement only. The column is an evidence trail:
    # "CC BY 4.0. DISCREPANCY RESOLVED 2026-08-23 ... the CC BY-NC-ND
    # belongs to the ARTICLE, not to the deposit" is a CC BY 4.0 dataset,
    # and scanning the whole string would read it as NC-ND.
    full = (text or "").lower()
    head = re.split(r"[.;(]| - ", full, 1)[0].strip()
    for candidate in (head, full):
        for token, lid in LICENSE_IDS:
            if token in candidate:
                return lid
    return None            # free-text licence: carried in the description


def licence_sentence(text):
    """The licence as a reader should see it: the leading statement only.
    The registry column continues with our adjudication trail, which is
    internal ("DISCREPANCY RESOLVED 2026-08-23 and it was ours: ...") and
    was being published verbatim in 18 record descriptions."""
    # Do not split on a period that belongs to a version number:
    # "CC BY 4.0. DISCREPANCY ..." must yield "CC BY 4.0", not "CC BY 4".
    head = re.split(r"(?<!\d)[.;(]|\.(?!\d)|;|\(| - ",
                    (text or "").strip(), 1)[0].strip()
    return head.rstrip(",") or "see the source record"


def _citation_dois(repo):
    """dataset id -> the DOI of the DEPOSIT, from the generated citation
    table. Preferred over the registry link column, which is often a
    landing page when a DOI exists."""
    out = {}
    p = os.path.join(repo, "docs", "citations.csv")
    if not os.path.exists(p):
        return out
    with open(p, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("kind") == "data" and row.get("doi"):
                out.setdefault(row["dataset"], row["doi"].strip())
    return out


_DOIS = {}


def related_ids(r):
    """isDerivedFrom the source: its DOI when one is known, else its
    landing page. A DOI is what makes the derivation machine-followable."""
    if not _DOIS:
        _DOIS.update(_citation_dois(REPO))
    doi = _DOIS.get(r["id"])
    if doi:
        return [{"identifier": doi, "relation": "isDerivedFrom",
                 "scheme": "doi"}]
    if r.get("link"):
        return [{"identifier": r["link"], "relation": "isDerivedFrom",
                 "scheme": "url"}]
    return []


RAW_FALLBACK_CAP = 100e6   # raw fallback is for small aux tables only

# Never deposited, whatever the walk finds them in.
JUNK_DIRS = {".git", ".svn", ".hg", "__pycache__", ".ipynb_checkpoints",
             ".pytest_cache", ".idea", ".vscode", "__MACOSX"}
JUNK_FILES = {".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes"}
# Media that shows a patient. A deposit is irreversible, so these are never
# staged automatically: the privacy gate (docs/PRIVACY_GATE.md) is an owner
# decision even when the source published the file openly. Stage such a file
# by naming it explicitly in <staging>/<id>/include_media.txt, one relative
# path per line, which records the decision next to the record it affects.
MEDIA_EXT = {".mov", ".mp4", ".avi", ".mkv", ".wmv", ".m4v", ".mpg", ".mpeg",
             ".webm", ".mts", ".3gp"}


def is_pickle(path):
    """A Python pickle, recognised by its opcode header rather than by its
    name. The corpus left pickle for moveatlas-record/1 precisely because
    unpickling a downloaded file executes arbitrary code, and a source can
    ship one under any name: chop_gma_features carries two protocol-4
    pickles named by bare OSF ids with no extension, which every
    name-based rule missed (found 2026-09-09)."""
    try:
        with open(path, "rb") as f:
            head = f.read(2)
    except OSError:
        return False
    # protocol 2+ starts with PROTO (0x80) followed by the version byte;
    # protocol 0/1 start with a printable opcode, too loose to test safely
    return head[:1] == b"\x80" and len(head) > 1 and head[1] <= 5


def canonical_files(info, staging_dir=None):
    """Collect what the record would hold. Returns (files, from_raw, held):
    processed/ canonical artifacts normally; small raw/ tables as a
    fallback for aux-style entries that are served as-is. Large
    raw-only sets are NOT staged (their source repository already
    serves the raw; the harmonized record joins after ingestion).
    `held` lists media files withheld pending an owner decision."""
    base = os.path.join(REPO, info["path"], "processed")
    from_raw = not os.path.isdir(base)
    if from_raw:
        base = os.path.join(REPO, info["path"], "raw")
    allow_media = set()
    if staging_dir:
        inc = os.path.join(staging_dir, "include_media.txt")
        if os.path.exists(inc):
            with open(inc, encoding="utf-8") as f:
                allow_media = {ln.strip().replace("\\", "/")
                               for ln in f if ln.strip()
                               and not ln.startswith("#")}
    files, held = [], []
    for dirpath, dirnames, names in os.walk(base):
        # Never deposit version-control internals, caches or editor litter.
        # A raw tree that came from `git clone` carries a whole .git
        # directory; 29 of those files reached a draft on 2026-09-05 before
        # this filter existed (packfiles, hooks, reflog).
        dirnames[:] = [d for d in dirnames if d not in JUNK_DIRS]
        present = set(names)
        for n in names:
            if n.startswith("._") or n in JUNK_FILES or n.endswith(".pyc"):
                continue
            # moveatlas-record/1 migration: a legacy .pkl whose .npz
            # sibling exists is superseded and must not enter a record
            if n.endswith(".pkl") and n[:-4] + ".npz" in present:
                continue
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, REPO).replace("\\", "/")
            if os.path.splitext(n)[1].lower() in MEDIA_EXT \
                    and rel not in allow_media:
                held.append(rel)
                continue
            if is_pickle(p):
                held.append(rel + "  (Python pickle, refused by content)")
                continue
            files.append((rel, os.path.getsize(p)))
    return files, from_raw, held


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", action="store_true",
                    help="compute sha256 for every staged file (slow)")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    os.makedirs(OUT, exist_ok=True)
    plan = []
    for r in moveatlas.list_datasets(case="hosted"):
        if only and r["id"] not in only:
            continue
        # The hosted case already requires redistribution to start with
        # "yes" (moveatlas.registry.access_case), but a deposit is
        # irreversible: re-state the condition here so a future change to
        # the classifier cannot silently make a forbidden dataset
        # depositable. Anything not explicitly permitted is refused.
        redist = (r.get("redistribution") or "").strip().lower()
        if not redist.startswith("yes"):
            sys.exit(f"REFUSED to stage '{r['id']}': its registry row records "
                     f"redistribution as {r.get('redistribution')!r}, which is "
                     "not an explicit permission. Nothing was written.")
        files, from_raw, held = canonical_files(
            r, os.path.join(OUT, r["id"]))
        if held:
            print(f"  {r['id']:28s} HELD   {len(held)} media file(s) withheld "
                  "pending an owner decision (privacy gate):")
            for h in held:
                print(f"      {h}")
            print(f"      to include them: list the paths in "
                  f"export/zenodo_staging/{r['id']}/include_media.txt")
        if not files:
            # nothing under processed/: not ingested yet, so there is no
            # canonical record to deposit (found the hard way 2026-09-02:
            # cellxgene_pd_multiregion, ixi_mri, clinical_gait_signals_2025
            # staged as empty deposits)
            print(f"  {r['id']:28s} SKIP   no canonical artifacts yet")
            continue
        size = sum(s for _, s in files)
        if from_raw and size > RAW_FALLBACK_CAP:
            # a big raw-only set is a verbatim mirror of its source
            # repository, not a MoveAtlas record; it joins the staging
            # once its ingestion produces canonical artifacts
            print(f"  {r['id']:28s} SKIP   raw-only and "
                  f"{size/1e9:.2f} GB > fallback cap (ingest first)")
            continue
        target = "zenodo" if size <= ZENODO_CAP else "hf"
        d = os.path.join(OUT, r["id"])
        os.makedirs(d, exist_ok=True)
        # a hand-written provenance paragraph (recipe, unit caveats,
        # deferred streams) lives in <staging>/<id>/provenance.html and is
        # prepended to the generated description on every run, so a
        # re-stage never erases it (drummer 09-05 and sensefog 09-07 were
        # edited straight into metadata.json before this existed)
        prov_path = os.path.join(d, "provenance.html")
        provenance = ""
        if os.path.exists(prov_path):
            with open(prov_path, encoding="utf-8") as f:
                provenance = f.read().strip()
        if from_raw:
            body = (
                "<p>This record holds the source table(s) MoveAtlas "
                "serves AS-IS for this auxiliary entry, redistributed "
                "unmodified under the source licence. The source below "
                "must be cited alongside this record.</p>")
        else:
            body = (
                "<p>This record holds the CANONICAL artifacts produced "
                "by the MoveAtlas ingestion (contracts in configs/"
                "canonical_*.yaml): harmonized tensors, manifests and "
                "audits. It is a derived work; the original data remains "
                "at the source below, which must be cited alongside this "
                "record.</p>")
        # The licence column of the registry is an evidence trail
        # ("CC BY 4.0. DISCREPANCY RESOLVED 2026-08-23 and it was ours:
        # ..."), written for us, not for a reader of a public record.
        # Publish the licence, keep the adjudication out of it.
        lic_public = licence_sentence(r["license"])
        # The registry's n_subjects is free text for many rows and
        # sometimes an internal note ("unresolved from zip (needs
        # extraction count)"), which has no business in a public record.
        # Publish it only when it begins with a number.
        subjects = (r.get("n_subjects") or "").strip()
        subj_txt = f" Subjects: {subjects}." if subjects[:1].isdigit() else ""
        desc = provenance + (
            f"<p>MoveAtlas harmonized release of <b>{r['title']}</b> "
            f"(dataset id: {r['id']}, family: {r['family']}).</p>"
            + body +
            f"<p>Source licence: {lic_public}. Taxonomy cells: "
            f"{r['moveatlas_cells']}.{subj_txt}</p>"
            f"<p>Load it with the MoveAtlas package:</p>"
            f"<pre>pip install moveatlas\n\n"
            f"import moveatlas\n"
            f"records, meta = moveatlas.dataset(&quot;{r['id']}&quot;)"
            f".get_data()</pre>")
        meta = {"metadata": {
            "title": f"MoveAtlas harmonized: {r['title']}",
            "upload_type": "dataset",
            "description": desc,
            # the record credits the HARMONIZATION (a derived work); the
            # source datasets keep their own authorship through the
            # isDerivedFrom identifier and the citation requirement in
            # the description (owner decision 2026-09-02)
            "creators": [{"name": "Vasques, Xavier"}],
            "keywords": ["MoveAtlas", "movement disorders", r["family"],
                         "harmonized", r["id"]],
            "related_identifiers": related_ids(r),
            "notes": "Assembled by the MoveAtlas release pipeline; "
                     "sha256 manifest in files.csv of this record.",
        }}
        lid = license_id(r["license"])
        if lid:
            meta["metadata"]["license"] = lid
        with open(os.path.join(d, "metadata.json"), "w", newline="\n",
                  encoding="utf-8") as f:
            json.dump(meta, f, indent=1, ensure_ascii=False)
        with open(os.path.join(d, "files.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["path", "bytes", "sha256"])
            for relp, s in files:
                h = ""
                if args.hash:
                    hh = hashlib.sha256()
                    with open(os.path.join(REPO, relp), "rb") as fh:
                        for chunk in iter(lambda: fh.read(1 << 22), b""):
                            hh.update(chunk)
                    h = hh.hexdigest()
                w.writerow([relp, s, h])
        plan.append([r["id"], target, size, r["license"][:50],
                     len(files), "yes" if lid else "free-text"])
        print(f"  {r['id']:28s} {target:6s} {size/1e9:8.2f} GB "
              f"{len(files):6d} files")
    # --only must MERGE into the plan, not replace it: two --only runs
    # (drummer 2026-09-05, sensefog 2026-09-07) each left a one-row plan
    # behind, which the paper cites as the deposit crosswalk.
    plan_path = os.path.join(OUT, "_plan.csv")
    if args.only and os.path.exists(plan_path):
        with open(plan_path, newline="", encoding="utf-8") as f:
            old = [r for r in csv.reader(f)][1:]
        mine = {p[0] for p in plan}
        plan = [r for r in old if r and r[0] not in mine] + plan
        plan.sort(key=lambda r: r[0])
    with open(plan_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "target", "bytes", "license", "n_files",
                    "spdx_mapped"])
        w.writerows(plan)
    print(f"\n{len(plan)} in plan ({len(mine) if args.only else len(plan)} "
          f"staged this run) -> {OUT}")


if __name__ == "__main__":
    main()
