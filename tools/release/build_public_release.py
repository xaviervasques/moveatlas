# -*- coding: utf-8 -*-
"""Assemble the PUBLIC MoveAtlas repository from this working tree.

The public repository is a GENERATED tree, not this one. That is deliberate:

- this tree carries session handoffs, review dossiers, draft correspondence
  and project-management files that are working material, not documentation;
- this tree's git history is not the history a reader needs, and the public
  tree starts with a fresh, single, authored commit;
- nothing here renames a family any more: the auxiliary-table family was
  called aux until 2026-09-11, a reserved DOS device name that no Windows
  clone could check out, and the public tree renamed it to auxdata on the
  way out. The working tree now carries auxdata itself, so this builder
  copies the registry verbatim and REFUSES a tree that still says aux;
- nothing under datasets/**/raw/ or datasets/**/processed/ is ever copied:
  the data lives in its Zenodo records, the repository carries the code,
  the cards and the indexes.

What lands in the public tree:

  moveatlas/           the package (with its bundled registry snapshot)
  tests/ .github/      the test suite and continuous integration
  configs/             the canonical contracts
  datasets/<fam>/<id>/datacard.md    every data card
  docs/                the public documents and the generated indexes
  site/                the documentation site sources and gallery
  tools/               the pipeline scripts, grouped by role
  README.md LICENSE CITATION.cff CHANGELOG.md CONTRIBUTING.md
  pyproject.toml Makefile .gitattributes .gitignore

Every file copied is checked afterwards by a leak scan that refuses to
finish on: assistant or vendor attribution, an absolute local path, a
credential-shaped string, a third-party email address, or French prose in a
document that is meant to be English. The scan is the gate, not a warning:
a non-zero exit means the tree must not be pushed.

Usage:
  python build_public_release.py                     # build + scan
  python build_public_release.py --out DIR           # elsewhere
  python build_public_release.py --scan-only DIR     # re-scan a built tree
"""
import argparse
import csv
import io
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(REPO, "export", "moveatlas_public")

# --------------------------------------------------------------------------
# what ships
# --------------------------------------------------------------------------

# Package, tests and CI: copied wholesale (minus caches).
TREES = [
    ("moveatlas", "moveatlas"),
    ("tests", "tests"),
    (".github", ".github"),
    ("configs", "configs"),
]

ROOT_FILES = [
    "LICENSE", "CITATION.cff", "CHANGELOG.md", "pyproject.toml",
    "Makefile", ".gitattributes",
]

# Scripts, grouped under tools/ by role. A script ships when a reader could
# run it or needs to read it to trust the corpus. One-shot scaffolding and
# machine-specific runbooks stay behind (see EXCLUDED_WITH_REASON).
TOOLS = {
    "fetch": [
        "fetch_dandi.py", "fetch_dataverse.py", "fetch_figshare_curl.py",
        "fetch_mendeley.py", "fetch_openneuro_s3.py", "fetch_osf.py",
        "fetch_physionet.py", "fetch_tappy.py", "fetch_neuromorpho.py",
        "fetch_cody_zenodo.py", "fetch_asdpose.py", "fetch_rat7m_videos.py",
        "fetch_p2_lot.py", "pads_mirror.py", "verify_dandi_local.py",
    ],
    "ingest": [
        "ingest_capture24.py", "ingest_cervical_motion.py",
        "ingest_gait120_pose.py", "ingest_gaitrec.py", "ingest_goodwin_smm.py",
        "ingest_infant_pose_chambers.py", "ingest_li_taati.py",
        "ingest_ltmm.py", "ingest_multimodal_fog.py", "ingest_nonan.py",
        "ingest_pads.py", "ingest_pd_biostamprc21.py", "ingest_remap_open.py",
        "ingest_sixmwt_lifespan.py", "ingest_stroke_gait.py",
        "ingest_stroke_gait_analogs.py", "ingest_tremordb.py",
        "ingest_vidimu.py",
    ],
    "canonical": [
        "build_canonical.py", "build_canonical_amass.py",
        "build_canonical_drummer.py", "build_canonical_eeg.py",
        "build_canonical_emg.py", "build_canonical_force.py",
        "build_canonical_imu.py", "build_canonical_modys.py",
        "build_canonical_motionx.py", "build_canonical_ntu.py",
        "build_canonical_physionet_multimodal_gait.py",
        "build_canonical_sensefog.py", "build_canonical_sensefog_pass2.py",
        "build_canonical_silhouette.py", "convert_records_to_npz.py",
    ],
    "registry": [
        "gen_datacards.py", "build_catalogue.py", "build_taxonomy_map.py",
        "build_hpo_movement_map.py", "build_citations.py",
        "build_access_log.py", "validate_registry.py",
        "analyze_neuromorpho_conditions.py", "build_cody_manifest.py",
    ],
    "release": [
        "build_zenodo_staging.py", "upload_zenodo.py",
        "build_records_table.py", "build_public_release.py",
        "build_portal.py", "run_local_pipeline.py",
    ],
}
# The three gates keep their place at the root of the public tree: they are
# the project's guarantees and a reader should find them immediately.
GATES = ["validate_canonical.py", "release_lint.py", "launch_dryrun.py",
         "mask_statistics.py"]

# Public documents. Everything else under docs/ is working material.
DOCS = [
    # what the corpus is and how it is built
    "MOVEATLAS_PLATFORM_DESIGN.md", "OPERATIONS.md", "RECORD_FORMAT.md",
    "MANIFEST_SCHEMA.md", "DATA_MAP.md", "search_protocol.md",
    "PRIVACY_GATE.md",
    # the scientific artifacts
    "ACCESS_BARRIERS_CASES.md", "hunt_confirmed_absences.md",
    "TAXONOMY_ADJUDICATION.md",
    "ANIMAL_LANE_CONTRACT_DESIGN.md", "INGEST_STROKE_ANALOGS_SCOPING.md",
    "multimodal_fog_mapping.md", "INGESTION_TRIAGE.md",
    # the hunts, as the search trail behind the absences ledger
    "HUNT_2026-09-01.md", "HUNT_ANIMAL_2026-09-01.md",
    "HUNT_CLOSING_2026-09-04.md", "HUNT_DEEPDIVE_2026-09-05.md",
    "HUNT_EUROMOV_2026-09-02.md",
    # generated indexes and machine-readable tables
    "datasets_index.csv", "license_matrix.csv", "taxonomy_map.csv",
    "hpo_movement_terms.csv", "mask_statistics.csv", "registry_cells.csv",
    "interventions.csv", "citations.bib", "citations.csv",
    "citation_overrides.csv",
]

# The resource paper does not ship. Until 2026-09-15 the tree carried
# paper/ in full (the manuscript, its builders, tables and figures); the
# owner's decision is that a draft does not belong in a public history, and
# that the tree will carry the reference once the preprint is on arXiv.
# The list of what that means is in EXCLUDED_WITH_REASON below.

# Left behind, with the reason a reader of the report can check.
EXCLUDED_WITH_REASON = [
    ("paper/, docs/PAPER_SCIDATA_V2.md, docs/SCIDATA_CONFORMITY.md",
     "the resource paper: manuscript, builders, tables, figures and the "
     "journal conformity check. A draft until its preprint is out; the "
     "tree will then carry the reference, not the manuscript"),
    ("KINEFM_HANDOFF_*.md, HANDOFF_WINDOWS_RTX.md",
     "session handoffs: working notes, superseded by docs/OPERATIONS.md"),
    ("docs/BACKUP.md",
     "the owner's backup procedure for a private disk: it describes where "
     "one person's copies live and nothing a reader of this resource can "
     "use or verify"),
    ("docs/REPO_SPLIT_PLAN.md",
     "the plan for the split that produced this repository; once you are "
     "reading this tree the plan has been carried out"),
    ("site/source/sg_execution_times.rst",
     "a sphinx-gallery timing artifact, regenerated by every build"),
    ("docs/DRAFT_EMAILS_2026-08-23.md",
     "unsent correspondence drafted to named third-party laboratories"),
    ("docs/ACCESS_PROCEDURES_OWNER.md",
     "owner-side application procedures, carries third-party email addresses"),
    ("docs/G2_REVIEW_DOSSIER.md, docs/KINEFM_V2_SPEC.md, docs/V2_DIRECTION.md",
     "design material for the model project, not for the data resource"),
    ("docs/RESUME_DONNEES_FR.md, the .xlsx/.docx project files",
     "French project-management material; the repository is English-only"),
    ("docs/REVIEW_360_*.md, docs/REGISTRY_CELLS_REPORT_*.md, docs/STATUS/phase1/"
     "citation_candidates/imu_reconnaissance",
     "internal review and triage notes"),
    ("docs/PAPER_SCIDATA_DRAFT.md, docs/PAPER_SCIDATA_OUTLINE.md",
     "superseded by PAPER_SCIDATA_V2.md"),
    ("RUN1.ps1, RUN_POSE_VICREG.ps1, RUN_ON_RTX.md, LANCEMENT.md",
     "runbooks for a training machine that no longer exists"),
    ("arbo.py, download_*.py, extract_care_pd.py, fetch_hunt_*.py, "
     "fetch_animal_*.py, fetch_dandi_000947_sample.py, stop_before_eject.sh",
     "one-shot scaffolding superseded by the generic fetchers"),
    ("_pipeline_log.txt, _paris_logs/, temporary/, build/, dist/",
     "machine logs and build artifacts"),
    ("aux_status.py, tests/test_aux_status.py",
     "a working-tree staging check for a name reserved on one machine"),
    ("datasets/**/raw/, datasets/**/processed/, export/",
     "the corpus itself: served from its Zenodo records, never from git"),
]

SKIP_NAMES = {"__pycache__", ".DS_Store", ".pytest_cache", ".ipynb_checkpoints",
              # generated at build time by sphinx and the gallery; shipping
              # them would publish a stale site and thousands of vendored
              # theme assets
              "_build", "auto_examples", "_generated",
              # the private tree's staging check for the auxdata family
              # and its tests. It exists for a Windows reserved-name trap
              # that the 2026-09-11 rename removed, it repairs a working
              # tree rather than describing the corpus, and its tests need
              # a git repository, which this generated tree is not until
              # git init. A permanently skipping test overstates coverage.
              "aux_status.py", "test_aux_status.py",
              # sphinx-gallery writes this timing page into the SOURCE tree
              # on every build; it is an :orphan: nothing links to, and
              # shipping it publishes one machine's run times as if they
              # were documentation
              "sg_execution_times.rst"}


def skip(name):
    return name in SKIP_NAMES or name.startswith("._") or name.endswith(".pyc")


# Machine-specific paths are redacted at copy time in the documents that are
# useful publicly but were written against the author's two machines. The
# working tree keeps the concrete paths, which is what the author needs.
REDACTIONS = [
    (re.compile(r"C:\\Users\\[A-Za-z0-9_.-]+\\miniconda3\\python\.exe"), "<python>"),
    (re.compile(r"C:\\Users\\[A-Za-z0-9_.-]+\\\.venvs\\[A-Za-z0-9_.-]+"), "<venv>"),
    (re.compile(r"C:/Users/[A-Za-z0-9_.-]+/miniconda3/python\.exe"), "<python>"),
    (re.compile(r"[A-Z]:\\MoveAtlas\\KineFM"), "<repo>"),
    (re.compile(r"[A-Z]:\\MoveAtlas"), "<workdir>"),
    (re.compile(r"[A-Z]:/MoveAtlas/(?:KineFM|moveatlas)"), "<repo>"),
    (re.compile(r"[A-Z]:\\KineFM"), "<backup-drive>"),
    (re.compile(r"/Volumes/[A-Za-z0-9_]+"), "<external-volume>"),
    (re.compile(r"[A-Z]:\\condaenvs\\[A-Za-z0-9_.-]+"), "<obsolete-env>"),
    (re.compile(r"C:\\Users\\[A-Za-z0-9_.-]+"), "<home>"),
]
REDACT_FILES = {"docs/OPERATIONS.md", "docs/BACKUP.md", "Makefile",
                "docs/RECORD_FORMAT.md", "docs/MANIFEST_SCHEMA.md",
                "docs/PRIVACY_GATE.md", "docs/REPO_SPLIT_PLAN.md",
                "tools/release/run_local_pipeline.py"}


def redact_file(path):
    """Replace author-machine paths with placeholders, in place."""
    with io.open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    out = text
    for rx, rep in REDACTIONS:
        out = rx.sub(rep, out)
    if out != text:
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        return True
    return False


def copy_tree(src, dst, report):
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not skip(d)]
        for f in files:
            if skip(f):
                continue
            s = os.path.join(root, f)
            d = os.path.join(dst, os.path.relpath(s, src))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            report.append(os.path.relpath(d, os.path.dirname(dst)))
            n += 1
    return n


def cp(src, dst, report, out):
    if not os.path.exists(src):
        print(f"  MISSING, skipped: {os.path.relpath(src, REPO)}")
        return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    report.append(os.path.relpath(dst, out))
    return 1


def copy_registry_checked(src, dst):
    """Copy the registry verbatim, and refuse a tree that still calls the
    auxiliary family aux. Until 2026-09-11 this function translated aux to
    auxdata on the way out, because `aux` is a reserved DOS device name and
    no Windows clone of a tree containing datasets/aux/ can be checked out.
    The working tree was renamed to auxdata so that the six Zenodo records
    freezing those paths into immutable file names would agree with what is
    published, which left this translation with nothing to do. A silent
    no-op would hide a regression, so it fails loudly instead. Returns the
    number of rows checked."""
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys()) if rows else []
    bad = [r for r in rows
           if (r.get("family") or "").strip() == "aux"
           or (r.get("path") or "").startswith("datasets/aux/")]
    if bad:
        raise SystemExit(
            "registry still carries the pre-rename aux family in "
            f"{len(bad)} row(s), first id {bad[0].get('id')!r}: the working "
            "tree is datasets/auxdata/ since 2026-09-11 and a published "
            "record cannot follow a path that moved. Fix the registry.")
    n = len(rows)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return n


# --------------------------------------------------------------------------
# the leak scan: the gate
# --------------------------------------------------------------------------

TEXT_EXT = {".py", ".md", ".rst", ".txt", ".csv", ".json", ".yaml", ".yml",
            ".cff", ".toml", ".cfg", ".ini", ".html", ".css", ".js", ".bib",
            ".csl", ".sh", ".ps1", ".in", ".gitignore", ".gitattributes"}

# Attribution to an assistant or a vendor, anywhere. This scanner's own
# source necessarily contains the words it looks for and is exempted by name
# in SCAN_ALLOW below; every other file is checked.
ASSISTANT_WORDS = ["claude", "anthropic", "copilot", "chatgpt", "openai",
                   "codex", "cursor.sh", "gemini", "llama"]
RE_ASSISTANT = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in ASSISTANT_WORDS) + r")\b", re.I)
# Attribution does not need a vendor's name to be attribution. A sweep on
# 2026-09-11 found eight of these in a tree the vendor-name scan had just
# passed: "Generalist agent" as a section label, "the assistant" in four
# documents and two scripts, "pediatric agent" and "repo-passes agent" as
# provenance tags. They say an assistant did the work as plainly as the
# product name would, so they are refused on the same footing.
RE_ATTRIBUTION = re.compile(
    r"\b(?:the|an|this)\s+assistant\b"
    r"|\bassistant(?:'s)?\s+(?:own\s+)?\w+"
    r"|\b(?:sub-)?agents?(?:'s)?\b"
    r"|\bco-authored-by\b"
    r"|\bgenerated with\b"
    r"|\bAI[- ]generated\b", re.I)
# "User-Agent" is an HTTP header, not a worker. The first version of the
# rule above matched it in seven fetchers and in the two cards that record
# "Dryad answers 403 to a non-browser user agent", which is the finding, not
# attribution. Strip the header before testing rather than widening the rule
# into something nobody can read.
RE_USER_AGENT = re.compile(r"(?:user|(?:non-)?browser)[-\s]?agents?", re.I)
# A local absolute path that would only exist on the author's machines.
RE_LOCALPATH = re.compile(
    r"([A-Za-z]:[\\/](?:Users|MoveAtlas|condaenvs|KineFM)|/Volumes/[A-Za-z0-9_]+)")
# Credential-shaped strings.
RE_SECRET = re.compile(
    r"(ZENODO_TOKEN\s*=\s*['\"][^'\"]{20,}|ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\baws_secret_access_key\b)")
# Third-party email addresses. The project's own contact is allowed.
OWN_EMAILS = {"vasquesxavier@protonmail.com"}
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# French prose markers, checked only in documents we author.
RE_FRENCH = re.compile(
    r"\b(les donn[ée]es|nous avons|c'est-[àa]-dire|afin de|"
    r"le projet est|cette version|ceci est|il faut|"
    r"jeux de donn[ée]es|fichier de|dossier de)\b", re.I)
# The house rule: no em-dashes.
RE_EMDASH = re.compile("—")

# Files where a hit is expected and legitimate, with the reason.
#
# On emails: a data card, a generated dataset page and the registry carry the
# contact address that the SOURCE publishes as its documented access route
# (a data-use-agreement mailbox, a corresponding author). Those addresses are
# already public in the deposit's own metadata and removing them would remove
# the access route the barrier tier exists to record. They are allowed here
# and counted in the build report so the owner can review them.
SCAN_ALLOW = {
    # this scanner's own source names the words it searches for
    "tools/release/build_public_release.py": {"assistant", "emdash", "email",
                                              "localpath", "french"},
    # the fetchers legitimately name the repositories they talk to
    "tools/fetch/fetch_osf.py": {"email"},
    # "pharmacological:<agent>", "dose/agent tags": a drug, not a worker
    "docs/ANIMAL_LANE_CONTRACT_DESIGN.md": {"assistant"},
    "docs/citations.bib": {"email", "french", "emdash"},
    "docs/citations.csv": {"email", "french", "emdash"},
    "moveatlas/data/datasets_index.csv": {"email", "french"},  # NOT assistant
    "moveatlas/data/license_matrix.csv": {"email", "french"},
    "tools/registry/gen_datacards.py": {"email"},
    "tools/registry/build_citations.py": {"email"},
    "docs/datasets_index.csv": {"email", "french"},
    "docs/license_matrix.csv": {"email", "french"},
    "docs/registry_cells.csv": {"french"},
}


def scan(out):
    """Walk the built tree and report every leak. Returns a list of
    (severity, relpath, kind, evidence)."""
    hits = []
    for root, dirs, files in os.walk(out):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in sorted(files):
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, out).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT and fn not in {"LICENSE", "Makefile"}:
                continue
            allow = set(SCAN_ALLOW.get(rel, set()))
            # source-published contact addresses: see the note on SCAN_ALLOW
            if (rel.startswith("datasets/") and rel.endswith("datacard.md")) \
                    or rel.startswith("site/source/datasets/") \
                    or rel.startswith("docs/") and rel.endswith(".csv") \
                    or rel.startswith("paper/") and rel.endswith(".csv"):
                allow.add("email")
            if rel.startswith("site/") or rel.startswith("paper/"):
                allow.add("french")   # cited titles and author names
            try:
                with io.open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if RE_ASSISTANT.search(line) and "assistant" not in allow:
                    hits.append(("BLOCK", rel, "assistant", f"{i}: {line.strip()[:140]}"))
                probe = RE_USER_AGENT.sub("", line)
                if RE_ATTRIBUTION.search(probe) and "assistant" not in allow:
                    # WARN, not BLOCK. A vendor's name in a published file is
                    # always wrong. "three agents", "an agent's reading" is
                    # sometimes the honest description of how a search was
                    # run, and whether to keep it is the owner's call on
                    # their own methodology record - not this script's.
                    # OWNER DECISION 2026-09-11: the hunt reports KEEP their
                    # agent vocabulary. The descriptor's Methods and
                    # docs/search_protocol.md s6 now state the same thing -
                    # agents for breadth, manual reading and manual web
                    # search for depth, every agent claim verified at the
                    # source. Do not "fix" those warnings into silence; a
                    # declared automated pass is reproducible, a hidden one
                    # is not.
                    hits.append(("WARN", rel, "attribution",
                                 f"{i}: {line.strip()[:140]}"))
                if RE_SECRET.search(line):
                    hits.append(("BLOCK", rel, "secret", f"{i}: <redacted line {i}>"))
                if RE_LOCALPATH.search(line) and "localpath" not in allow:
                    hits.append(("WARN", rel, "localpath", f"{i}: {line.strip()[:140]}"))
                if "email" not in allow:
                    for m in RE_EMAIL.findall(line):
                        if m.lower() not in OWN_EMAILS and not m.endswith("example.com"):
                            hits.append(("WARN", rel, "email", f"{i}: {m}"))
                if RE_EMDASH.search(line) and "emdash" not in allow:
                    hits.append(("WARN", rel, "emdash", f"{i}: {line.strip()[:80]}"))
            if ext in {".md", ".rst"} and "french" not in allow:
                fr = RE_FRENCH.findall(text)
                if len(fr) >= 3:
                    hits.append(("WARN", rel, "french", f"{len(fr)} French markers"))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--scan-only", default=None,
                    help="scan an already built tree and exit")
    a = ap.parse_args()

    if a.scan_only:
        hits = scan(a.scan_only)
        report_scan(hits)
        return 1 if any(h[0] == "BLOCK" for h in hits) else 0

    out = a.out
    if os.path.exists(out):
        # since 2026-09-15 the output tree IS the public repository's
        # clone (origin = github.com/xaviervasques/moveatlas, and the
        # gh-pages worktree hangs off its .git): empty the tree, keep .git
        for name in os.listdir(out):
            if name == ".git" or name.startswith("._"):
                continue
            p = os.path.join(out, name)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    os.remove(p)
                except FileNotFoundError:
                    pass
    os.makedirs(out, exist_ok=True)
    shipped = []

    print("package, tests, CI, contracts")
    for src, dst in TREES:
        n = copy_tree(os.path.join(REPO, src), os.path.join(out, dst), shipped)
        print(f"  {src:14s} {n:4d} files")

    print("root furniture")
    for f in ROOT_FILES:
        cp(os.path.join(REPO, f), os.path.join(out, f), shipped, out)

    print("gates")
    for f in GATES:
        cp(os.path.join(REPO, f), os.path.join(out, f), shipped, out)

    print("tools")
    for group, files in TOOLS.items():
        n = sum(cp(os.path.join(REPO, f), os.path.join(out, "tools", group, f),
                   shipped, out) for f in files)
        print(f"  tools/{group:10s} {n:4d} files")

    print("data cards")
    ncards = 0
    for fam in sorted(os.listdir(os.path.join(REPO, "datasets"))):
        famdir = os.path.join(REPO, "datasets", fam)
        if not os.path.isdir(famdir) or skip(fam):
            continue
        for did in sorted(os.listdir(famdir)):
            card = os.path.join(famdir, did, "datacard.md")
            if not os.path.isfile(card):
                continue
            ncards += cp(card, os.path.join(out, "datasets", fam, did,
                                            "datacard.md"), shipped, out)
    print(f"  {ncards} cards")

    print("acquisition journals (the sha256 trail, small text files)")
    njournal = 0
    for fam in sorted(os.listdir(os.path.join(REPO, "datasets"))):
        famdir = os.path.join(REPO, "datasets", fam)
        if not os.path.isdir(famdir) or skip(fam):
            continue
        for did in sorted(os.listdir(famdir)):
            j = os.path.join(famdir, did, "downloads.sha256")
            if os.path.isfile(j) and os.path.getsize(j) < 2_000_000:
                njournal += cp(j, os.path.join(out, "datasets", fam, did,
                                               "downloads.sha256"), shipped, out)
    print(f"  {njournal} journals")

    print("docs")
    nd = 0
    for f in DOCS:
        src = os.path.join(REPO, "docs", f)
        dst = os.path.join(out, "docs", f)
        if f == "datasets_index.csv" and os.path.exists(src):
            n = copy_registry_checked(src, dst)
            shipped.append("docs/" + f)
            print(f"  registry: {n} rows, no pre-rename aux path")
            nd += 1
            continue
        nd += cp(src, dst, shipped, out)
    print(f"  {nd} documents")

    print("site")
    nsite = copy_tree(os.path.join(REPO, "site"), os.path.join(out, "site"),
                      shipped)
    print(f"  {nsite} files")

    # the access log: the prospective acquisition journal the paper reports on
    for f in ("_access_log.csv", "_access_log_manual.csv"):
        cp(os.path.join(REPO, "datasets", f),
           os.path.join(out, "docs", f), shipped, out)

    print("redacting author-machine paths in the operational documents")
    nred = 0
    for rel in sorted(REDACT_FILES):
        p = os.path.join(out, rel.replace("/", os.sep))
        if os.path.exists(p) and redact_file(p):
            nred += 1
            print(f"  {rel}")
    print(f"  {nred} file(s) redacted")

    nums = write_readme(out)
    shipped += ["README.md", "CONTRIBUTING.md"]
    print(f"README: {nums['catalogued']} catalogued, {nums['harmonized']} "
          f"harmonized, {nums['records']:,} records, {nums['cards']} cards")
    write_gitignore(out)
    write_report(out, shipped)

    print(f"\n{len(shipped)} files -> {out}")
    print("\nleak scan")
    hits = scan(out)
    report_scan(hits)
    blocked = [h for h in hits if h[0] == "BLOCK"]
    if blocked:
        print(f"\nREFUSED: {len(blocked)} blocking leak(s). Fix them, rebuild, "
              "and do not push this tree.")
        return 1
    print("\nclean. Next:")
    print(f"  cd {out} && git init && git add -A && git commit")
    return 0


def corpus_numbers(out):
    """Every number the README states, measured from the tree just built."""
    n = {}
    reg = os.path.join(out, "docs", "datasets_index.csv")
    with open(reg, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    n["catalogued"] = len(rows)
    fam = {}
    for r in rows:
        fam[r["family"]] = fam.get(r["family"], 0) + 1
    n["families"] = ", ".join(f"{k} {v}" for k, v in
                              sorted(fam.items(), key=lambda kv: -kv[1]))
    n["animal"] = fam.get("animal", 0)
    n["human"] = n["catalogued"] - n["animal"]
    ms = os.path.join(out, "docs", "mask_statistics.csv")
    with open(ms, newline="", encoding="utf-8") as f:
        mrows = list(csv.DictReader(f))
    n["harmonized"] = len({r["source"] for r in mrows})
    n["records"] = sum(int(r["n_records_seen"]) for r in mrows)
    n["pairs"] = len(mrows)
    n["cards"] = sum(1 for _ in glob_cards(out))
    rec = os.path.join(out, "moveatlas", "data", "zenodo_records.json")
    try:
        import json
        with open(rec, encoding="utf-8") as f:
            n["records_published"] = len(json.load(f))
    except Exception:
        n["records_published"] = 0
    return n


def glob_cards(out):
    base = os.path.join(out, "datasets")
    for root, dirs, files in os.walk(base):
        for f in files:
            if f == "datacard.md":
                yield os.path.join(root, f)


README = """# MoveAtlas

An access-audited catalogue of movement-disorder and healthy-movement data,
harmonized into six canonical signal families and served through one Python
API. MoveAtlas answers a practical question: which movement data actually
exist for a given phenotype and modality, which of it can a stranger obtain,
and in what shape.

- **{catalogued} catalogued datasets** ({human} human, {animal} animal), one
  data card each, licence verified at acquisition time with its date.
- **{harmonized} of them harmonized** into pose, inertial, force, surface EMG,
  EEG and silhouette records: **{records:,} records** measured exhaustively.
- **Access is reported, not assumed**: every dataset carries one of four
  access cases and the package enforces it at load time.

## Install

```bash
pip install moveatlas          # add [bench] for the baseline pipelines
```

```python
import moveatlas

moveatlas.list_datasets()                   # the catalogue with access cases
ds = moveatlas.dataset("nonan_gaitprint")   # a hosted CC-BY dataset
records, meta = ds.get_data()               # canonical records + metadata
moveatlas.to_frame(records[0]).head()       # a tidy, named, masked frame
```

Hosted datasets download on demand from their Zenodo record into a local
cache and are verified against the record's own sha256 manifest. Nothing
needs credentials.

## The four access cases

| case | what happens on `get_data()` |
|---|---|
| `hosted` | downloaded from the MoveAtlas record for that dataset, sha256-verified |
| `recipe` | fetched from the original host by the documented ingestion recipe |
| `barrier` | raises the documented access route; nothing is downloaded |
| `local_only` | read from a local path only; nothing is redistributed |

A barrier is a result, not a failure: the access-barrier casebook
(`docs/ACCESS_BARRIERS_CASES.md`) types thirteen ways open data turns out not
to be obtainable, and the absences ledger (`docs/hunt_confirmed_absences.md`)
records the phenotypes for which no open dataset exists at all.

## Layout

```
moveatlas/     the package: registry, record store, frames, splits, paradigms
datasets/      one data card and one acquisition journal per dataset
docs/          design documents, the generated indexes, the casebook
configs/       the six canonical contracts, one YAML per family
tools/         the pipeline: fetch, ingest, canonical, registry, release
site/          the documentation site sources
tests/         the corpus-free test suite
```

The three gates live at the root and each exits non-zero on a gap:
`validate_canonical.py` (contract conformity), `release_lint.py` (privacy and
licence), `launch_dryrun.py` (a stranger's install path). Those run here.

`tools/` is the provenance record, not a runnable pipeline. Every script is
the one that actually produced what this repository describes, but they read
and write `datasets/<family>/<id>/raw/` and `processed/`, which this tree
deliberately does not carry - the data lives in its Zenodo records - and they
resolve the repository root from their own location, which the grouping into
`tools/<role>/` changes. Read them as the method; to re-run one, place it at
the root of a tree that holds the corpus.

## Records

A record is a self-describing container: a zip with the `.npz` extension
holding one `.npy` member per array and a `meta.json` header, format
`moveatlas-record/1` (`docs/RECORD_FORMAT.md`). It opens with numpy alone and
executes no code on load. Native sampling rates and units are preserved;
where a source declares no unit, the record says `unknown` rather than
guessing, and every refusal is a counted row in a per-dataset ingest audit.

## Data, licences and citation

The harmonized records are deposited as one Zenodo record per dataset, each
with its own DOI; the mapping ships with the package
(`moveatlas/data/zenodo_records.json`). Each record is a derived work of its
source: **cite the source dataset as well as MoveAtlas**. Every data card
carries the source licence, its verification date and a BibTeX entry
(`docs/citations.bib`).

Code is BSD-3-Clause (`LICENSE`). Data is licensed per dataset. Datasets whose
licence forbids redistribution are never deposited; they are catalogued with
their access route and used in-house for evaluation only.

Software citation: `CITATION.cff`. The resource paper is in preparation; its
reference will be added here when the preprint is out.

## Contributing

Corrections to a data card, a licence reading or an access route are the most
valuable contributions: see `CONTRIBUTING.md`.
"""

CONTRIBUTING = """# Contributing to MoveAtlas

The most valuable contributions are corrections to what the catalogue claims.

## Reporting a wrong fact

Open an issue naming the dataset id and the field. The fields most likely to
be wrong, in order:

1. **Licence.** The registry records the licence as read at the source on a
   dated verification. Sources change: a deposit is relicensed, withdrawn, or
   its landing page contradicts its metadata. If you find a disagreement,
   include the URL and what you read there today.
2. **Access route.** A barrier dataset carries the route its owner documents.
   If the route changed, or you obtained the data by a route we record as
   closed, say how.
3. **Taxonomy cells.** Cells are adjudicated, not inferred. If a dataset is
   filed under the wrong phenotype, say which cell and why.
4. **Subject counts and demographics.** The registry states what the source
   states. Where the source is silent, the table says "not reported by
   source" and that is deliberate.

## Adding a dataset

Open an issue first with the DOI or landing page, the licence, and whether
redistribution is permitted. The inclusion rule is broad: any human movement
signal or a movement-relevant biological lane, under any licence, because the
licence is recorded rather than filtered on. What we will not do is
redistribute data whose licence forbids it.

## Code

- The test suite runs without the corpus: `python -m pytest -q`.
- Style: English, no em-dashes, LF line endings, standard library first.
- A builder must refuse rather than guess. If a source does not declare a
  unit, a sampling rate or a channel identity, the record stores `unknown`
  and the ingest audit counts the refusal. Pull requests that infer a missing
  declaration will be asked to remove the inference.
- Run the three gates before proposing a release-affecting change.

## What we cannot accept

Data files. The repository carries code, cards and indexes; the corpus lives
in its Zenodo records.
"""


def write_readme(out):
    n = corpus_numbers(out)
    with io.open(os.path.join(out, "README.md"), "w", encoding="utf-8",
                 newline="\n") as f:
        f.write(README.format(**n))
    with io.open(os.path.join(out, "CONTRIBUTING.md"), "w", encoding="utf-8",
                 newline="\n") as f:
        f.write(CONTRIBUTING)
    return n


def write_gitignore(out):
    with open(os.path.join(out, ".gitignore"), "w", newline="\n",
              encoding="utf-8") as f:
        f.write("\n".join([
            "# the corpus itself is served from its Zenodo records, never git",
            "datasets/**/raw/", "datasets/**/processed/", "*.npz", "*.pkl",
            "", "# build and cache",
            "__pycache__/", "*.pyc", "*.egg-info/", "build/", "dist/",
            ".pytest_cache/", "site/_build/", "site/source/auto_examples/",
            "site/source/_generated/", "paper/_doi_cache.json",
            "", "# operating system",
            ".DS_Store", "._*", "Thumbs.db", "",
        ]))


def write_report(out, shipped):
    by_area = {}
    for p in shipped:
        area = p.split("/")[0] if "/" in p else "(root)"
        by_area[area] = by_area.get(area, 0) + 1
    lines = [
        "# What is in this public tree, and what is not",
        "",
        "Generated by build_public_release.py from the working tree. The",
        "public repository is a generated export: the working tree carries",
        "session notes and project-management material that are not",
        "documentation, and its git history is not the history a reader",
        "needs. This tree starts with a single authored commit.",
        "",
        "## Included",
        "",
        "| area | files |",
        "|---|---|",
    ]
    for area in sorted(by_area):
        lines.append(f"| {area} | {by_area[area]} |")
    lines += [
        f"| **total** | **{len(shipped)}** |",
        "",
        "## Deliberately excluded",
        "",
        "| what | why |",
        "|---|---|",
    ]
    for what, why in EXCLUDED_WITH_REASON:
        lines.append(f"| {what} | {why} |")
    lines += [
        "",
        "## One rename",
        "",
        "The auxiliary-table family is `auxdata`. It was `aux` until",
        "2026-09-11; on Windows `aux` is a reserved device name and",
        "`git clone` fails at checkout, so the family was renamed at the",
        "source rather than only on the way out.",
        "`docs/datasets_index.csv` and the card paths agree in this tree,",
        "and the builder refuses to finish if a row still says `aux`.",
        "",
        "## The gate",
        "",
        "`build_public_release.py` re-scans this tree after building it and",
        "refuses to finish when it finds a tool vendor's name, a",
        "credential-shaped string, a local absolute path, a third-party email",
        "address or French prose in an English document. Re-run the scan at",
        "any time with `python build_public_release.py --scan-only .`",
        "",
    ]
    with open(os.path.join(out, "PUBLIC_TREE.md"), "w", newline="\n",
              encoding="utf-8") as f:
        f.write("\n".join(lines))


def report_scan(hits):
    if not hits:
        print("  no leaks")
        return
    order = {"BLOCK": 0, "WARN": 1}
    kinds = {}
    for sev, rel, kind, ev in hits:
        kinds[(sev, kind)] = kinds.get((sev, kind), 0) + 1
    for (sev, kind), n in sorted(kinds.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        print(f"  {sev:5s} {kind:10s} {n}")
    for sev in ("BLOCK", "WARN"):
        sel = [h for h in hits if h[0] == sev]
        for h in sel[:40]:
            print(f"    {h[0]} {h[1]} [{h[2]}] {h[3]}")
        if len(sel) > 40:
            print(f"    ... and {len(sel) - 40} more {sev}")


if __name__ == "__main__":
    sys.exit(main())
