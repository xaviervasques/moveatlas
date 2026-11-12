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

Every file copied is checked afterwards by a leak scan. It refuses to
finish (BLOCK) on: the name of a software vendor or product of the kind the
owner's rule of 2026-11-10 keeps out of the tree, a credential-shaped
string, French prose in a document we author, or a file of a non-commercial
body model or derived from one (the body-model rule of 2026-11-12: a body
model's file, its arrays in a data file, or the statement of an output made
with it; no exemption). It reports (WARN) a model
name that is also an ordinary word, the field's two-letter abbreviation, a
provenance word or phrase, an absolute local path, a third-party email
address and an em-dash. The scan is the gate: a non-zero exit means the
tree must not be pushed, and every WARN is read before a push.

Usage:
  python build_public_release.py                     # build + scan
  python build_public_release.py --out DIR           # elsewhere
  python build_public_release.py --scan-only DIR     # re-scan a built tree
  python build_public_release.py --hash WORD         # digest for a word list
"""
import argparse
import csv
import hashlib
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
        "set_stated_fps.py",
    ],
    "registry": [
        "gen_datacards.py", "build_catalogue.py", "build_taxonomy_map.py",
        "build_hpo_movement_map.py", "build_citations.py",
        "build_access_log.py", "validate_registry.py",
        "analyze_neuromorpho_conditions.py", "build_cody_manifest.py",
    ],
    "release": [
        "build_zenodo_staging.py", "build_zenodo_corpus.py", "upload_zenodo.py",
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
    "citation_overrides.csv", "demographics_curated.csv", "demographics.csv",
    "record_titles.csv", "zenodo_corpus_index.csv",
]

# The resource paper does not ship. Until 2026-09-15 the tree carried
# paper/ in full (the manuscript, its builders, tables and figures); the
# owner's decision is that a draft does not belong in a public history, and
# that the tree will carry the reference once the preprint is on arXiv.
# The list of what that means is in EXCLUDED_WITH_REASON below.

# Left behind, with the reason a reader of the report can check.
EXCLUDED_WITH_REASON = [
    ("paper/, docs/SCIDATA_CONFORMITY.md",
     "the resource paper: manuscript, builders, tables, figures and the "
     "journal conformity check. A draft until its preprint is out; the "
     "tree will then carry the reference, not the manuscript"),
    ("KINEFM_HANDOFF_*.md, HANDOFF_WINDOWS_RTX.md",
     "session handoffs: working notes, superseded by docs/OPERATIONS.md"),
    ("docs/BACKUP.md",
     "the owner's backup procedure for a private disk: it describes where "
     "one person's copies live and nothing a reader of this resource can "
     "use or verify"),
    ("docs/MACHINES.md",
     "the owner's two-machine ingestion procedure (mounts, line endings, "
     "AppleDouble, token hygiene, log locations), split out of "
     "docs/OPERATIONS.md on 2026-09-15 so that what ships is what a reader "
     "needs: the pipeline, the gates, the record format, the access log"),
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
     "superseded drafts of the descriptor (the manuscript is built under "
     "paper/package/source/ since 2026-09-16; the v2 source was removed "
     "on 2026-09-17)"),
    ("RUN1.ps1, RUN_POSE_VICREG.ps1, RUN_ON_RTX.md, LANCEMENT.md",
     "runbooks for a training machine that no longer exists"),
    ("arbo.py, download_*.py, extract_care_pd.py, fetch_hunt_*.py, "
     "fetch_animal_*.py, fetch_dandi_000947_sample.py, stop_before_eject.sh",
     "one-shot scaffolding superseded by the generic fetchers"),
    ("_pipeline_log.txt, _paris_logs/, builder_inputs/, build/, dist/",
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
    (re.compile(r"[A-Z]:\\Users\\[A-Za-z0-9_.-]+\\miniconda3\\python\.exe"), "<python>"),
    (re.compile(r"[A-Z]:\\Users\\[A-Za-z0-9_.-]+\\\.venvs\\[A-Za-z0-9_.-]+"), "<venv>"),
    (re.compile(r"[A-Z]:/Users/[A-Za-z0-9_.-]+/miniconda3/python\.exe"), "<python>"),
    (re.compile(r"[A-Z]:\\MoveAtlas\\KineFM"), "<repo>"),
    (re.compile(r"[A-Z]:\\MoveAtlas"), "<workdir>"),
    (re.compile(r"[A-Z]:/MoveAtlas/(?:KineFM|moveatlas)"), "<repo>"),
    # one backslash in a document, two in a Python string literal
    (re.compile(r"[A-Z]:\\+KineFM"), "<backup-drive>"),
    (re.compile(r"/Volumes/[A-Za-z0-9_]+"), "<external-volume>"),
    (re.compile(r"[A-Z]:\\condaenvs\\[A-Za-z0-9_.-]+"), "<obsolete-env>"),
    (re.compile(r"[A-Z]:\\Users\\[A-Za-z0-9_.-]+"), "<home>"),
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

# The rule (owner instruction of 2026-11-10): no shipped file names a
# vendor or a product of the listed kind, nor a model, nor carries a
# provenance statement about the tools text or code was produced with. That
# instruction replaced the decision of 2026-09-11 under which the search
# reports kept the vocabulary of how their automated passes were run. The
# method itself stays stated, in neutral words: automated search passes for
# breadth, manual reading at the source for depth, every claim verified at
# the source (docs/search_protocol.md section 6).
#
# The word lists are stored as the sha256 of each lower-case token, never
# as the words. A list in clear text would put in the shipped tree the very
# names the rule keeps out of it, and this file would need an exemption that
# would also hide a real leak in it. Each line is tokenized and each token
# hashed; a dotted name (a domain) is also tried whole and by its dotted
# runs. To add a word, print its digest with
#   python build_public_release.py --hash WORD
# and paste the digest into the list it joins (never the word itself).
#
# Product and maker names that have no ordinary English meaning: BLOCK.
VENDOR_SHA256 = frozenset({
    "053ea4804ef1bb33d4a3d6fb024a614b6d257cebc2bc7cd915da9c9522f37ffc",
    "3ea125d0bff386e6754b3782b300016fc79a9cf8f8669c0a5c3db64467ddb681",
    "57de4cf40144bdf7d00010f2f5557a7d642c2b9705309bfade167dd313e2ca93",
    "60965168ce762e949600281ba6d01fee136e5b6e8257b1f216f9025ed324474c",
    "67f2d22514622d1be30c14ee9f3cb104503a159a33a656ca91a1953aa9616429",
    "6f7ac1823da81d2e52d1a1549ee69c85bbf8bb56d06682849e7c09da2785ce3b",
    "7558a1564a10a003e3ce8ecf4e864128f2258d01acb53a23d67cf74b5fcc2b3b",
    "7d3194f79e645c42e4396dda38be04766810ec6a00d00aced3ffc2a0a1f1a9ef",
    "90642c3dd333bc0e602c9fa887ab0f0482886d0ed52ce8762a27a5f901528fcc",
    "c70eca6b0f88f44d81a41311647e50fda1ac454ec04ffd442b0eb4743a993131",
    "c857d09db23e6822e3600bc06ad8d58f92ed62bc8efd81c753f77048662cb97d",
})
# Model names that are also ordinary English words (a literary form, a
# poem, an animal, a constellation, a wind): WARN, since a cited title or a
# third-party proper name may carry one legitimately; SCAN_ALLOW records
# each such file with its reason.
MODEL_SHA256 = frozenset({
    "09cf980b5ff304ac11b7f6d2c5c263da2a867425798ef5cc5d2ebcf55c4fcd23",
    "5a5110ebe1544b31e6d4207a419bc1deb148735f89ae984ff0a2ab809b51f1df",
    "5d72436256ada53828b51895a94bb8489e9f1ac4fe937a8024ef1594e7045ff6",
    "920510199770f4d65cb8aaa2cd12bdb2b8c37f5b3907c50a734a0e3409da2823",
    "add92b9cde2bdbf3daaf65a0db79e9b1a7fa428b71b4d6ce38c742eb6dca0c1c",
    "c9ad8f2cc1294afa0ef22fc2c019ff7243cdd272b2147ddca3f34c5036b05768",
    "e12ce8285efc67c6d93d3a122e2589ed95089bcbb775ba5634d94e2b8385db07",
    "fc5a1047f5919892fcdf8aa79ea5d6bb6531b5c176939ef0110906cb225941c1",
})
# The English and French two-letter abbreviations for the field, matched
# only when the token is written in capitals (a lower-case loop index of
# the same two letters is code, not a mention): WARN.
ACRONYM_SHA256 = frozenset({
    "26138d8a757dd1dc09df6301bc4a47f0a1f7f785a725ae72574c6862127a2201",
    "32e83e92d45d71f69dcf9d214688f0375542108631b45d344e5df2eb91c11566",
})
# Provenance words: the generic nouns for an automated helper and for the
# technology behind it, singular and plural: WARN. A sweep on 2026-09-11
# found eight provenance phrases (a section label and provenance tags, and
# the helper noun in four documents and two scripts) in a tree the name scan
# had just passed: a provenance word states automated help as plainly as a
# product name. These words also have ordinary senses (in pharmacology, in
# an HTTP header), hence WARN and the two exemptions: HEADER_PREFIXES below
# and the allow entry of docs/ANIMAL_LANE_CONTRACT_DESIGN.md.
HELPER_SHA256 = frozenset({
    "386ebc0efd04339aa982703eb666c335d8458b8657343d9783185debf0bf0c26",
    "487b91042c7cf27a19e23ea8699f5f354b1a0c3af9e418138dc6150d830f970d",
    "4c7047d4bc759e60b916d1936cf3d41f201c18fdb883a48b59d0eb592d51707a",
    "8c70b25cbbbe8e7935bbc70516181551934ae5e917b40d25c4a72bbbd865f2e4",
    "94a168d2da574b00ec6c787377278465271cf2b97e68af076fc3eee87eba8664",
    "a39a7ffad4a3013f29da97b84f264337f234c1cf9b3c40c7c30c677a8a18609a",
    "a5ea7d719f7aba21d3f940a263d619ebb130a56a7faf669f8e333bcf59b65603",
    "d298391b07433318a02bd922ed5b90112a4302606c4928b54e3fb1c18130d92e",
    "d4f0bc5a29de06b510f9aa428f1eedba926012b591fef7a518e776a7c9bd1824",
    "de2187af3fb011708ca4ff6d21e4845236d6a6d25e7e90531b26a7923d16c73f",
    "eea82f53ecaed277e542e8a867863be69c50efc4b94dad1f50a33944ca0c2f1f",
})
# Provenance phrases of two or three tokens, joined by one space (a commit
# trailer, "made with", the compound adjective for machine-made text, the
# model family): WARN.
PHRASE_SHA256 = frozenset({
    "2e8aae79d9566c6391cbf216d0b40760bde9bd51a6c5b0b970a248f679cd718f",
    "442e56863b7e9cf893fd1d134d4b24b57e98acc6a3f8501d163d042259065871",
    "5eff592cc497fccb48ebfffaca38a83f9167bc1661b4477e1fc1b66b658cd5a0",
    "7c38d5864015fc722b62d2f5b8cf69be50bcea73de4cfb745c8b9780e9e8d9f5",
    "cdcbb68a3444fdd629ab0af770af3fc99e4d5dde43b576d5f855691e155283ec",
})
# The HTTP header and the "non-browser ..." finding: a provenance word right
# after one of these is the header, not a worker. The first version of the
# rule matched it in seven fetchers and in the two cards that record "Dryad
# answers 403 to a non-browser" client, which is the finding.
HEADER_PREFIXES = {"user", "browser"}

_WORD = re.compile(r"[A-Za-z0-9]+")
_DOTTED = re.compile(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)+")
_DIGEST = {}


def digest(token):
    """sha256 hex digest of a token, lower-cased; cached."""
    t = token.lower()
    d = _DIGEST.get(t)
    if d is None:
        d = hashlib.sha256(t.encode("utf-8")).hexdigest()
        _DIGEST[t] = d
    return d


def word_kinds(line):
    """The word-list kinds a line carries: a subset of {"vendor", "model",
    "acronym", "attribution"}."""
    found = set()
    words = _WORD.findall(line)
    for i, w in enumerate(words):
        d = digest(w)
        if d in VENDOR_SHA256:
            found.add("vendor")
        elif d in MODEL_SHA256:
            found.add("model")
        elif d in ACRONYM_SHA256:
            if w.isupper():
                found.add("acronym")
        elif d in HELPER_SHA256:
            if not (i and words[i - 1].lower() in HEADER_PREFIXES):
                found.add("attribution")
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            if digest(" ".join(words[i:i + n])) in PHRASE_SHA256:
                found.add("attribution")
    if "." in line:
        for tok in _DOTTED.findall(line):
            parts = tok.split(".")
            for a in range(len(parts)):
                for b in range(a + 2, len(parts) + 1):
                    if digest(".".join(parts[a:b])) in VENDOR_SHA256:
                        found.add("vendor")
    return found


# A local absolute path that would only exist on the author's machines:
# Windows drive paths under the home, project, backup and environment
# folders (any drive letter, either slash), the same folders written the
# Git Bash way (/d/...), and macOS volume mounts.
RE_LOCALPATH = re.compile(
    r"(?<![A-Za-z])[A-Za-z]:[\\/]+(?i:Users|MoveAtlas|MD_FM|Backup|condaenvs|KineFM)\b"
    r"|(?<![\w.~-])/[A-Za-z]/(?i:Users|MoveAtlas|MD_FM|Backup)\b"
    r"|/Volumes/[A-Za-z0-9_]+")
# Credential-shaped strings: a Zenodo token assignment, GitHub classic and
# fine-grained tokens, a PEM private key, the AWS secret key name, and the
# Hugging Face, PyPI and "sk-" API token shapes.
RE_SECRET = re.compile(
    r"ZENODO_TOKEN\s*=\s*['\"][^'\"]{20,}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\baws_secret_access_key\b"
    r"|(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{30,}"
    r"|(?<![A-Za-z0-9_-])pypi-[A-Za-z0-9_-]{40,}"
    r"|(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}")
# Third-party email addresses. The project's own contact is allowed.
OWN_EMAILS = {"vasquesxavier@protonmail.com"}
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# French prose, two detectors. Markers: phrases that do not occur in English
# prose. Lines: a line carrying three or more French function words, which
# also catches French typed without accents (the first version of this rule
# had only markers with accents and missed two shipped documents written that
# way). A file is French when it has FRENCH_MIN markers or FRENCH_MIN lines.
RE_FRENCH = re.compile(
    r"\b(les donn[ée]es|des donn[ée]es|nous avons|c'est-[àa]-dire|afin de|"
    r"le projet est|cette version|ceci est|il faut|il y a|c'est|n'est pas|"
    r"parce que|ce qui|pour les|avec les|dans les|sur les|une fois|"
    r"jeux de donn[ée]es|fichier de|dossier de)\b", re.I)
FRENCH_WORDS = frozenset(
    "les des une dans avec nous cette sont aux qui pas est du sur pour par "
    "ou au la le et en".split())
_LETTERS = re.compile(r"[A-Za-zÀ-ÿ]+")
FRENCH_MIN = 3


def french_evidence(text):
    """(number of markers, number of French lines, first French line no.)"""
    markers = len(RE_FRENCH.findall(text))
    lines, first = 0, None
    for i, line in enumerate(text.splitlines(), 1):
        n = sum(1 for w in _LETTERS.findall(line) if w.lower() in FRENCH_WORDS)
        if n >= 3:
            lines += 1
            first = first or i
    return markers, lines, first
# The house rule: no em-dashes (written as an escape so that this file
# carries none).
RE_EMDASH = re.compile("\u2014")

# The body-model rule (owner decision of 2026-11-12: the project is fully
# open source). The SMPL family of body models (SMPL, SMPL+H, SMPL-X, MANO)
# is licensed by the Max Planck Institute for Intelligent Systems for
# non-commercial use only, and the MANO/SMPL+H licence forbids making the
# model, or animations made with it, available in any form. So no shipped
# file may be a body-model file or carry what was computed with one. The
# rule targets data files and pages, not prose or code: a citation of AMASS
# or SMPL, a data card saying the body model is needed, and the AMASS builder
# that loads a user's own copy of the model (naming its arrays and its file)
# are legitimate and pass. Three checks, each a BLOCK of kind "bodymodel":
#
# 1. the path, for every shipped file whatever its type: a file under a
#    body_models/ folder, or named like a body-model file of the family
#    (SMPLH_male.pkl, MANO_RIGHT.pkl, smplh/neutral/model.npz, ...);
# 2. the content of a data file: an array container (BODY_DATA_EXT, read as
#    bytes; a .npz lists its member names uncompressed) or a table or JSON
#    file (BODY_TEXT_EXT) carrying a body model's own arrays (template mesh,
#    blend shapes, joint regressor, kinematic tree, hand components) or the
#    keys of an AMASS motion file (its frame-rate keys, its DMPL
#    coefficients). Code, prose and HTML are not read for these keys: the
#    builder and its tests name them, the AMASS card cites them, and a built
#    site's pages and search index repeat the card;
# 3. the statement a derived output carries, in any text file: the MPI
#    acknowledgement for animation made with the model, or a release under
#    that licence (the credit and licence lines such an output must carry).
#
# Out of reach: an image or a video rendered from the model carries no such
# mark. None ships: BODY_DATA_EXT holds no image type and the public
# .gitignore keeps *.npz and *.pkl out. The patterns are written so that
# this file does not match them.
_BODY_FAMILY = r"(?:smpl|smplh|smplx|mano)"
RE_BODY_MODEL_PATH = re.compile(
    r"(?:^|/)body_models/"
    r"|(?:^|/)" + _BODY_FAMILY + r"_(?:male|female|neutral|left|right)\b"
    r"[^/]*\.(?:pkl|npz|npy|pt|pth|json|obj|fbx|ply)$"
    r"|(?:^|/)" + _BODY_FAMILY + r"/(?:male|female|neutral)/model\.(?:npz|pkl)$",
    re.I)
BODY_DATA_EXT = {".npz", ".npy", ".pkl", ".pickle", ".pt", ".pth", ".ckpt",
                 ".h5", ".hdf5", ".mat", ".joblib", ".safetensors", ".bin"}
BODY_TEXT_EXT = {".json", ".csv", ".tsv"}
BODY_KEYS = ("v_template", "shapedirs", "posedirs", "J_regressor",
             "kintree_table", "hands_components", "hands_componentsl",
             "hands_componentsr", "hands_mean", "hands_meanl", "hands_meanr",
             "mocap_framerate", "mocap_frame_rate", "dmpls")
RE_BODY_KEY = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(BODY_KEYS)
                         + r")(?![A-Za-z0-9])")
RE_BODY_KEY_BYTES = re.compile(RE_BODY_KEY.pattern.encode("ascii"))
RE_BODY_STATEMENT = re.compile(
    r"used\s+for\s+character\s+animation\s+courtesy\s+of"
    r"|under\s+the\s+(?:MANO\s*/\s*)?SMPL\s*\+\s*H\s+licen[cs]e", re.I)


def body_model_file_hits(path, rel, ext):
    """Checks 1 and 2 of the body-model rule on one shipped file, before its
    text is read: a list of evidence strings."""
    found = []
    if RE_BODY_MODEL_PATH.search(rel):
        found.append("the path names a body-model file")
    if ext in BODY_DATA_EXT:
        try:
            with open(path, "rb") as f:
                m = RE_BODY_KEY_BYTES.search(f.read())
        except OSError:
            m = None
        if m:
            found.append("the data carries the body-model key "
                         + m.group(0).decode("ascii"))
    return found


# Files where a hit is expected and legitimate, with the reason. The keys of
# each set are hit kinds: vendor, model, acronym, attribution, localpath,
# email, emdash, french.
#
# On emails: a data card, a generated dataset page and the registry carry the
# contact address that the SOURCE publishes as its documented access route
# (a data-use-agreement mailbox, a corresponding author). Those addresses are
# already public in the deposit's own metadata and removing them would remove
# the access route the barrier tier exists to record. They are allowed here
# and counted in the build report so the owner can review them.
SCAN_ALLOW = {
    # the fetchers legitimately name the repositories they talk to
    "tools/fetch/fetch_osf.py": {"email"},
    # the design names the drug given to the animals ("pharmacological:<...>",
    # the per-mouse dose tags): a pharmacology term, not provenance
    "docs/ANIMAL_LANE_CONTRACT_DESIGN.md": {"attribution"},
    # cited titles, verbatim: the park_fingertap paper (npj Digital Medicine
    # 2023, 10.1038/s41746-023-00905-9) has the field's abbreviation in its
    # title; French-language titles and author names; third-party contacts
    "docs/citations.bib": {"email", "french", "emdash", "acronym"},
    "docs/citations.csv": {"email", "french", "emdash", "acronym"},
    # the generated page of that dataset prints the same citation and BibTeX
    "site/source/datasets/park_fingertap.md": {"acronym"},
    "moveatlas/data/datasets_index.csv": {"email", "french"},
    "moveatlas/data/license_matrix.csv": {"email", "french"},
    "tools/registry/gen_datacards.py": {"email"},
    "tools/registry/build_citations.py": {"email"},
    "docs/datasets_index.csv": {"email", "french"},
    # verbatim quotes of source papers and record pages, with their URLs
    "docs/demographics_curated.csv": {"email", "french", "emdash"},
    "docs/demographics.csv": {"email", "french", "emdash"},
    "docs/license_matrix.csv": {"email", "french"},
    "docs/registry_cells.csv": {"french"},
}

# Where French is checked, and how hard. Documents we author (.md, .rst,
# anywhere in the tree, the site sources included): BLOCK, the repository
# is English-only. The site's scripts and templates (.py, .html under
# site/), which render into pages: WARN. Not checked: the generated dataset
# pages (site/source/datasets/), which quote source titles and author names
# verbatim, and the files allowed above.
FRENCH_BLOCK_EXT = {".md", ".rst"}
FRENCH_WARN_SITE_EXT = {".py", ".html"}


def scan(out):
    """Walk the built tree and report every leak. Returns a list of
    (severity, relpath, kind, evidence)."""
    hits = []
    for root, dirs, files in os.walk(out):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        for fn in sorted(files):
            if fn.startswith("._"):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, out).replace(os.sep, "/")
            ext = os.path.splitext(fn)[1].lower()
            for ev in body_model_file_hits(p, rel, ext):
                hits.append(("BLOCK", rel, "bodymodel", ev))
            if ext not in TEXT_EXT and fn not in {"LICENSE", "Makefile"}:
                continue
            allow = set(SCAN_ALLOW.get(rel, set()))
            # source-published contact addresses: see the note on SCAN_ALLOW
            if (rel.startswith("datasets/") and rel.endswith("datacard.md")) \
                    or rel.startswith("site/source/datasets/") \
                    or rel.startswith("docs/") and rel.endswith(".csv") \
                    or rel.startswith("paper/") and rel.endswith(".csv"):
                allow.add("email")
            if rel.startswith("site/source/datasets/") or rel.startswith("paper/"):
                allow.add("french")   # cited titles and author names
            try:
                with io.open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                ev = f"{i}: {line.strip()[:140]}"
                kinds = word_kinds(line) - allow
                if "vendor" in kinds:
                    hits.append(("BLOCK", rel, "vendor", ev))
                for kind in ("model", "acronym", "attribution"):
                    if kind in kinds:
                        hits.append(("WARN", rel, kind, ev))
                if RE_SECRET.search(line):
                    hits.append(("BLOCK", rel, "secret", f"{i}: <redacted line {i}>"))
                if RE_LOCALPATH.search(line) and "localpath" not in allow:
                    hits.append(("WARN", rel, "localpath", ev))
                if "email" not in allow:
                    for m in RE_EMAIL.findall(line):
                        if m.lower() not in OWN_EMAILS and not m.endswith("example.com"):
                            hits.append(("WARN", rel, "email", f"{i}: {m}"))
                if RE_EMDASH.search(line) and "emdash" not in allow:
                    hits.append(("WARN", rel, "emdash", f"{i}: {line.strip()[:80]}"))
                if RE_BODY_STATEMENT.search(line):
                    hits.append(("BLOCK", rel, "bodymodel",
                                 f"{i}: a statement of output made with the body model"))
                if ext in BODY_TEXT_EXT:
                    m = RE_BODY_KEY.search(line)
                    if m:
                        hits.append(("BLOCK", rel, "bodymodel",
                                     f"{i}: the data carries the body-model key {m.group(0)}"))
            if "french" not in allow:
                if ext in FRENCH_BLOCK_EXT:
                    sev = "BLOCK"
                elif rel.startswith("site/") and ext in FRENCH_WARN_SITE_EXT:
                    sev = "WARN"
                else:
                    sev = None
                if sev:
                    markers, lines, first = french_evidence(text)
                    if markers >= FRENCH_MIN or lines >= FRENCH_MIN:
                        hits.append((sev, rel, "french",
                                     f"{markers} French marker(s), {lines} French "
                                     f"line(s), first at line {first}"))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--scan-only", default=None,
                    help="scan an already built tree and exit")
    ap.add_argument("--hash", default=None, metavar="WORD",
                    help="print the sha256 a word list stores for WORD and exit")
    a = ap.parse_args()

    if a.hash:
        print(digest(a.hash))
        return 0
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

moveatlas.fetch("fog_star")                 # a recipe: fetched at its origin, journaled
moveatlas.ingest("fog_star")                # harmonized on your machine, same code as the corpus
moveatlas.recipe("ninapro")                 # what a recipe needs before you run it
```

Hosted datasets download on demand from their Zenodo record into a local
cache and are verified against the record's own sha256 manifest. Recipe
datasets are fetched from their origin host and harmonized into the store
(`~/.moveatlas/store`, or `$MOVEATLAS_STORE`). Nothing needs credentials.
The same verbs exist on the command line: `moveatlas list | info <id> |
fetch <id> | ingest <id> | where`. The site's *Getting started* and *User
guide* walk one complete example per access case.

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
        "refuses to finish when it finds a software vendor's or product's",
        "name, a credential-shaped string or French prose in an English",
        "document; it reports a local absolute path, a third-party email",
        "address and provenance wording for review. Its word lists are stored",
        "as sha256 digests of the words. Re-run the scan at any time with",
        "`python tools/release/build_public_release.py --scan-only .`",
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
