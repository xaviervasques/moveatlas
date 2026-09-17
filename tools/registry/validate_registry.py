# -*- coding: utf-8 -*-
"""Lint docs/datasets_index.csv and split its free-text `moveatlas_cells` column.

The registry's `moveatlas_cells` field mixes strict taxonomy codes with
qualifiers ("A2 context", "B5-adjacent", "B2 proxy", "M6 socle",
"animal: healthy mouse pose/behavior socle"). This tool parses every string
into structured parts and flags what a human should look at. It repairs
NOTHING: docs/datasets_index.csv is never written, label changes are the
owner's adjudication.

Source of truth for the vocabulary: build_taxonomy_map.py (CELLS_VALID,
MODS_VALID). Labels are read from build_portal.py (CELLS, MODS) and
site/gen_dataset_pages.py (CELL_NAME) through `ast`, never imported, and any
disagreement between the three files is printed. HPO anchors come from
build_hpo_movement_map.ANCHORS plus docs/hpo_movement_terms.csv.

Inputs (read only):
  docs/datasets_index.csv        the registry (id, family, path, title,
                                 moveatlas_cells, n_subjects, age, license, ...)
  build_taxonomy_map.py          CELLS_VALID / MODS_VALID (imported; main-guarded)
  build_portal.py                CELLS / MODS labels (parsed with ast)
  site/gen_dataset_pages.py      CELL_NAME labels (parsed with ast)
  build_hpo_movement_map.py      ANCHORS cell -> HPO id (imported; main-guarded)
  docs/hpo_movement_terms.csv    HPO descendants of HP:0100022 with moamb_cells
  datasets/<family>/             directory listing, exact-case path check

Output:
  docs/registry_cells.csv        id,family,cells,modalities,qualifiers,hpo_ids,flags
                                 (pipe-separated lists; hpo_ids holds the anchor
                                 id of every cell that has one, in cell order;
                                 C/D/E cells have no HPO anchor in this project)
  stdout                         flag counts, HARD rows, proposals, vocabulary check

Exit status: 1 when any HARD flag exists (unknown_code, cells_empty on a human
dataset, duplicate_id, family_unknown, path_mismatch), else 0.

Flag vocabulary (HARD flags in capitals in the console, all lower-case in the csv):
  unknown_code:<code>           code outside CELLS_VALID / MODS_VALID
  cells_empty                   no A-E code on a human-family row (not "n/a")
  duplicate_id                  id appears more than once
  family_unknown                family outside the allowed set
  path_mismatch:<expected>      path != datasets/<family>/<id> (case-sensitive)
  --- soft ---
  cells_na                      moveatlas_cells is literally "n/a" (tools)
  cells_empty_nonhuman          no A-E code on an animal/ontology row
  modality_only                 only M codes present (with cells_empty)
  class_only:<letter>           bare class letter ("D CP", "E context")
  code_dropped:<code>           "<code> dropped" in the text, code excluded
  range_expanded:<range>        "A1-A8" style range expanded to its codes
  modality_family_mismatch:<M>  M code implausible for the family column
  keyword_without_cell:<cell>(<word>)  disorder word in title/status, cell absent
  cell_without_keyword:<cell>   A-class cell present, no supporting word anywhere
  C2_without_infant_evidence    C2 assigned, no infant/neonate/preterm word
  C2_but_adult                  C2 assigned while age/title says adult
  modality_keyword_without_code:<M>(<word>)  title names a modality, code absent
  path_missing_on_disk          datasets/<family>/<id> not on disk (pre-registered)
  path_case_differs_on_disk:<name>  the directory exists with another case
  n_subjects_empty / n_subjects_nonnumeric / n_subjects_approx
  license_no_spdx_token         no CC0/CC BY*/ODC/PDDL/etalab/MIT/Apache token
  license_multiple_tokens:<a>/<b>  more than one distinct licence token
  license_token:<spdx>          informational, the token that was recognised

Usage: python validate_registry.py [--repo PATH] [--out PATH] [--quiet]
Stdlib only. House style: English, no em-dashes, LF endings.
"""
import argparse
import ast
import csv
import os
import re
import sys
from collections import Counter, OrderedDict

# --------------------------------------------------------------------------
# constants that are NOT in build_taxonomy_map.py
# --------------------------------------------------------------------------

# The ten directory families used by docs/datasets_index.csv and datasets/.
# datasets/inversion_testbed is a testbed, not a registry family. There is no
# FAMILIES constant for the registry elsewhere in the repo (validate_canonical.py
# only lists the canonical signal families), so the set lives here.
FAMILIES_ALLOWED = ("animal", "auxdata", "bio", "eeg", "emg", "imu",
                    "ontology", "pose", "socle", "video")
NON_HUMAN_FAMILIES = ("animal", "ontology")

# family -> M codes that are plausible for a dataset filed under it. Built from
# the modality definitions (build_portal.MODS): M1 pose/video, M2 IMU, M3 plantar
# force, M4 silhouette, M5 EMG, M6 EEG, M7 LFP/ECoG/units, M8 imaging,
# M9 genetics, M10 histology/transcriptomics, M11 voice/writing, M12 scales.
# A code outside the set is flagged, not rejected: multimodal labs exist.
FAMILY_MODS = {
    "pose": {"M1", "M2", "M3", "M4", "M5", "M12"},
    "imu": {"M1", "M2", "M3", "M5", "M6", "M12"},
    "emg": {"M1", "M2", "M3", "M5", "M12"},
    "eeg": {"M2", "M5", "M6", "M7", "M12"},
    "bio": {"M7", "M8", "M9", "M10", "M12"},
    "auxdata": {"M2", "M3", "M9", "M11", "M12"},
    "video": {"M1", "M8", "M12"},
    "socle": {"M1", "M2"},
    "ontology": {"M9", "M12"},
    "animal": {"M%d" % i for i in range(1, 13)},
}

# Disorder words -> expected cell. Built from the cell labels (build_portal.CELLS)
# plus the disease names that name a cell in this corpus (Huntington -> chorea,
# Tourette -> tics, spasmodic dysphonia / torticollis -> dystonia, NBIA/PKAN ->
# dystonia). "B-any" means any hypokinetic cell satisfies the word.
# Patterns run case-insensitively on id + title + status; abbreviations are
# bounded so "tic" never fires inside "genetic" or "kinetic".
DISORDER_KEYWORDS = [
    ("A1", "tremor", r"tremor"),
    ("A2", "myoclonus", r"myoclon"),
    ("A3", "tics", r"\btics?\b|tourette"),
    ("A4", "dystonia", r"dyston|torticollis|blepharospasm|spasmodic[- ]dysphonia|writer'?s cramp|\bNBIA\b|\bPKAN\b"),
    ("A5", "stereotypies", r"stereotyp|self-stimulatory"),
    ("A6", "athetosis", r"athetos"),
    ("A7", "chorea", r"chorea|huntington|\bHD\b"),
    ("A8", "ballismus", r"ballism"),
    ("B1", "rigidity", r"rigidity"),
    ("B2", "bradykinesia", r"bradykines"),
    ("B3", "hypokinesia", r"hypokines"),
    ("B4", "akinesia", r"\bakines"),
    ("B5", "freezing of gait", r"freezing|\bfog\b"),
    ("B-any", "parkinson", r"parkinson|\bPD\b"),
    ("C2", "infant", r"infant|neonat|preterm|newborn|\bbab(y|ies)\b|\bGMA\b"),
    ("C3", "aging", r"\bag(e)?ing\b|older adults|elderly|lifespan"),
    ("D1", "epilepsy", r"epilep|seizure"),
    ("D2", "ataxia", r"ataxi"),
    ("D3", "pyramidal", r"\bstroke\b|\bALS\b|cerebral palsy|\bCP\b|spastic|pyramidal syndrome|hemipar(?:esis|etic)"),
    ("D4", "neuropathy", r"neuropath"),
    ("D5", "neurodevelopmental", r"autism|\bASD\b|neurodevelop"),
    ("D6", "sleep", r"\bsleep\b|\bRBD\b|\bPSG\b|\bPLM\b|restless"),
    ("D7", "functional", r"functional movement|\bFMD\b"),
    ("E4", "musculoskeletal", r"osteoarthr|orthopedic|\bKOA\b|musculoskeletal"),
    ("E6", "iatrogenic", r"drug-induced|iatrogenic|antipsychotic|levodopa-induced|L-DOPA dyskinesia|chemo-induced"),
    ("E7", "psychiatric", r"psychiatric"),
]
# Extra evidence accepted for a cell that is already assigned (the converse
# check): PD sets legitimately carry A1 (TAXONOMY_ADJUDICATION.md rows 14-15),
# seizure sets carry "A2 proxy", L-DOPA dyskinesia is choreo-dystonic.
CELL_EVIDENCE_EXTRA = {
    "A1": r"parkinson|\bPD\b|spiral",
    "A2": r"seizure|epilep",
    "A4": r"dyskines|choreoathet|cervical",
    "A7": r"dyskines|choreoathet",
}
INFANT_RE = re.compile(r"infant|neonat|preterm|newborn|\bbab(y|ies)\b|post-term|\bGMA\b", re.I)
ADULT_RE = re.compile(r"\badults?\b", re.I)

# Title words -> expected modality code (title only: status text is too noisy).
MODALITY_KEYWORDS = [
    ("M1", "video/pose", r"video|\bpose\b|mocap|motion capture|skeleton|keypoint|kinect"),
    ("M2", "IMU/accelerometry", r"accelerom|\bIMU\b|wearable|smartwatch|actigraph|inertial|wrist"),
    ("M3", "force", r"\bforce\b|\bGRF\b|plantar|insole"),
    ("M4", "silhouette", r"silhouette"),
    ("M5", "EMG", r"\bs?EMG\b|electromyo"),
    ("M6", "EEG/PSG", r"\bEEG\b|\bPSG\b|polysomno"),
    ("M7", "LFP/units", r"\bLFP\b|\bECoG\b|\bSTN\b|single[- ]unit|\bunits\b|electrophys|intraoperative|ephys"),
    ("M8", "imaging", r"\bf?MRI\b|imaging"),
    ("M9", "genetics", r"genet|genotype|variant|\bgene\b|panel|clinvar|monogenic"),
    ("M10", "histology/transcriptomics", r"snRNA|single-nucleus|histolog|morpholog|transcript|patch-seq|cell types"),
    ("M11", "voice/writing", r"voice|speech|vowel|dysphonia|handwriting|spiral|drawing|keystroke|smart-pen"),
    ("M12", "clinical scales", r"\bscales?\b|UPDRS|TWSTRS|\bscores\b|self-report"),
]

# licence tokens -> SPDX-style id. Order = specificity; the earliest match in
# the string wins (a row can mention the article's licence after the data's).
SPDX_TOKENS = [
    (r"CC[ -]?BY[ -]NC[ -]ND", "CC-BY-NC-ND"),
    (r"CC[ -]?BY[ -]NC[ -]SA", "CC-BY-NC-SA"),
    (r"CC[ -]?BY[ -]NC(?![ -](?:ND|SA))", "CC-BY-NC"),
    (r"CC[ -]?BY[ -]SA", "CC-BY-SA"),
    (r"CC[ -]?BY(?![ -](?:NC|SA|ND))", "CC-BY"),
    (r"CC0", "CC0-1.0"),
    (r"ODC[ -]?By", "ODC-By-1.0"),
    (r"ODbL", "ODbL-1.0"),
    (r"PDDL", "PDDL-1.0"),
    (r"etalab", "etalab-2.0"),
    (r"\bMIT\b", "MIT"),
    (r"Apache", "Apache-2.0"),
]
VERSION_RE = re.compile(r"^[ -]?(\d\.\d)")

HARD_FLAGS = ("unknown_code", "cells_empty", "duplicate_id", "family_unknown",
              "path_mismatch")

CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-E]|M)(\d{1,2})(?![A-Za-z0-9])")
RANGE_RE = re.compile(r"(?<![A-Za-z0-9])([A-E]|M)(\d{1,2})-\1(\d{1,2})(?![A-Za-z0-9])")
DROPPED_RE = re.compile(r"(?<![A-Za-z0-9])([A-E]\d{1,2})\s+dropped\b")
CLASS_ONLY_RE = re.compile(r"(?<![A-Za-z0-9/&-])([A-E])(?![A-Za-z0-9&-])")


# --------------------------------------------------------------------------
# vocabulary
# --------------------------------------------------------------------------

def read_dict_literal(path, name):
    """Return the dict literal assigned to `name` in a python file, without
    importing it (site/gen_dataset_pages.py has import-time side effects)."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return ast.literal_eval(node.value)
    return None


def load_vocabulary(repo):
    sys.path.insert(0, repo)
    import build_taxonomy_map as btm  # noqa: E402  (stdlib, main-guarded)
    import build_hpo_movement_map as bhm  # noqa: E402  (stdlib, main-guarded)
    voc = {
        "cells": list(btm.CELLS_VALID),
        "mods": list(btm.MODS_VALID),
        "anchors": {cell: hpo for hpo, cell in bhm.ANCHORS.items()},
        "portal_cells": read_dict_literal(os.path.join(repo, "build_portal.py"), "CELLS") or {},
        "portal_mods": read_dict_literal(os.path.join(repo, "build_portal.py"), "MODS") or {},
        "site_names": read_dict_literal(os.path.join(repo, "site", "gen_dataset_pages.py"), "CELL_NAME") or {},
    }
    return voc


def vocabulary_report(voc):
    """Compare the three vocabularies; return a list of human-readable lines."""
    lines = []
    tax_cells, tax_mods = set(voc["cells"]), set(voc["mods"])
    portal_cells, portal_mods = set(voc["portal_cells"]), set(voc["portal_mods"])
    site_cells = {k for k in voc["site_names"] if not k.startswith("M")}
    site_mods = {k for k in voc["site_names"] if k.startswith("M")}

    def diff(label, a, b):
        if a != b:
            lines.append(f"  DISAGREE {label}: only-left={sorted(a - b)} only-right={sorted(b - a)}")

    diff("cells taxonomy_map vs build_portal", tax_cells, portal_cells)
    diff("cells taxonomy_map vs gen_dataset_pages", tax_cells, site_cells)
    diff("mods taxonomy_map vs build_portal", tax_mods, portal_mods)
    diff("mods taxonomy_map vs gen_dataset_pages", tax_mods, site_mods)
    labels_portal = dict(voc["portal_cells"])
    labels_portal.update(voc["portal_mods"])
    for code in sorted(set(labels_portal) & set(voc["site_names"])):
        a, b = labels_portal[code], voc["site_names"][code]
        if a != b:
            kind = "case/abbreviation only" if a.lower().split()[0] == b.lower().split()[0] else "DIFFERENT"
            lines.append(f"  label {code}: build_portal='{a}' gen_dataset_pages='{b}' ({kind})")
    anchors_outside = sorted(c for c in voc["anchors"] if c not in tax_cells)
    if anchors_outside:
        lines.append(f"  DISAGREE hpo anchors outside CELLS_VALID: {anchors_outside}")
    if not lines:
        lines.append("  codes agree across build_taxonomy_map.py, build_portal.py, site/gen_dataset_pages.py")
    return lines


def load_hpo_anchors(repo, voc):
    """cell -> HPO id. Prefer the shallowest term tagged with the cell in
    docs/hpo_movement_terms.csv; fall back to build_hpo_movement_map.ANCHORS
    (B1 rigidity and B2 bradykinesia are not descendants of HP:0100022)."""
    anchors = dict(voc["anchors"])
    path = os.path.join(repo, "docs", "hpo_movement_terms.csv")
    notes = []
    if os.path.isfile(path):
        best = {}
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                for cell in [c for c in (r.get("moveatlas_cells") or r.get("moamb_cells") or "").split("|") if c]:
                    d = int(r["depth_under_HP0100022"])
                    if cell not in best or d < best[cell][0]:
                        best[cell] = (d, r["hpo_id"], r["name"])
        for cell, (_, hpo, name) in best.items():
            if cell in anchors and anchors[cell] != hpo:
                notes.append(f"  hpo anchor {cell}: ANCHORS={anchors[cell]} csv shallowest={hpo} ({name})")
            anchors.setdefault(cell, hpo)
    else:
        notes.append("  docs/hpo_movement_terms.csv missing; ANCHORS only")
    return anchors, notes


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def split_outside_parens(text):
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in ";," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def parse_cells(text, voc):
    """Return dict(cells, mods, qualifiers, class_only, unknown, dropped, ranges)."""
    raw = (text or "").strip()
    cells_valid, mods_valid = set(voc["cells"]), set(voc["mods"])
    dropped = set(DROPPED_RE.findall(raw))
    found = []  # (pos, code)
    ranges = []
    spans = []
    for m in RANGE_RE.finditer(raw):
        letter, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
        ranges.append(m.group(0))
        spans.append(m.span())
        for i in range(lo, hi + 1):
            found.append((m.start(), f"{letter}{i}"))
    for m in CODE_RE.finditer(raw):
        if any(s <= m.start() < e for s, e in spans):
            continue
        found.append((m.start(), m.group(1) + m.group(2)))
        spans.append(m.span())
    found.sort()
    codes = list(OrderedDict.fromkeys(c for _, c in found))
    codes = [c for c in codes if c not in dropped]
    cells = [c for c in codes if not c.startswith("M")]
    mods = [c for c in codes if c.startswith("M")]
    unknown = [c for c in cells if c not in cells_valid] + [c for c in mods if c not in mods_valid]

    # qualifiers = everything that is not a code
    stripped = raw
    for s, e in sorted(spans, reverse=True):
        stripped = stripped[:s] + " " + stripped[e:]
    class_only = [m.group(1) for m in CLASS_ONLY_RE.finditer(stripped)]
    quals = []
    for frag in split_outside_parens(stripped):
        frag = re.sub(r"\s+", " ", frag).strip()
        for _ in range(2):
            frag = frag.strip(" +/:-")
            if frag.startswith("(") and frag.endswith(")"):
                frag = frag[1:-1]
        frag = frag.replace("|", "/")
        if frag and frag not in ("+", "->"):
            quals.append(frag)
    return {"raw": raw, "cells": cells, "mods": mods, "qualifiers": quals,
            "class_only": class_only, "unknown": unknown,
            "dropped": sorted(dropped), "ranges": ranges}


def parse_license(text):
    hits = []
    for idx, (pat, spdx) in enumerate(SPDX_TOKENS):
        for m in re.finditer(pat, text or "", re.I):
            ver = VERSION_RE.match(text[m.end():m.end() + 6])
            tok = spdx
            if ver and spdx.startswith("CC-") and spdx != "CC0-1.0":
                tok = f"{spdx}-{ver.group(1)}"
            hits.append((m.start(), idx, tok))
    hits.sort()
    tokens = list(OrderedDict.fromkeys(t for _, _, t in hits))
    return tokens


def parse_n_subjects(text):
    s = (text or "").strip()
    if not s:
        return None, "empty"
    if re.fullmatch(r"\d{1,3}(,\d{3})+|\d+", s):
        return int(s.replace(",", "")), "numeric"
    m = re.match(r"^[~>]?\s*(\d{1,3}(?:,\d{3})+|\d+)\+?", s)
    if m and re.fullmatch(r"[~>]?\s*\d[\d,]*\+?", s):
        return int(m.group(1).replace(",", "")), "approx"
    return (int(m.group(1).replace(",", "")) if m else None), "nonnumeric"


# --------------------------------------------------------------------------
# row checks
# --------------------------------------------------------------------------

def check_row(r, voc, anchors, repo, id_counts, other_ids=()):
    flags = []
    rid, fam = r["id"], r["family"]
    parsed = parse_cells(r.get("moveatlas_cells", ""), voc)
    human = fam not in NON_HUMAN_FAMILIES
    title = r.get("title", "")
    # forward check (word present, cell absent) reads id + title + status;
    # the converse check (cell present, no word) also accepts the cells text
    # itself ("A2 (myoclonic events)" is its own evidence). Other datasets'
    # ids are blanked out of the status first ("the tim_tremor host" is not
    # evidence that ankle_fog_4tu records tremor).
    status = r.get("status", "")
    for oid in other_ids:
        if oid != rid and oid in status:
            status = status.replace(oid, " ")
    evidence_fwd = " ".join([rid.replace("_", " "), title, status])
    evidence_conv = evidence_fwd + " " + parsed["raw"]
    keyword_checks = human and parsed["raw"].lower() != "n/a"

    # --- HARD -------------------------------------------------------------
    for c in parsed["unknown"]:
        flags.append(f"unknown_code:{c}")
    if id_counts[rid] > 1:
        flags.append("duplicate_id")
    if fam not in FAMILIES_ALLOWED:
        flags.append("family_unknown")
    expected = f"datasets/{fam}/{rid}"
    if r.get("path", "") != expected:
        flags.append(f"path_mismatch:{expected}")
    if not parsed["cells"]:
        if parsed["raw"].lower() == "n/a":
            flags.append("cells_na")
        elif human:
            flags.append("cells_empty")
            if parsed["mods"]:
                flags.append("modality_only")
        else:
            flags.append("cells_empty_nonhuman")

    # --- structure -------------------------------------------------------
    for letter in parsed["class_only"]:
        flags.append(f"class_only:{letter}")
    for c in parsed["dropped"]:
        flags.append(f"code_dropped:{c}")
    for rg in parsed["ranges"]:
        flags.append(f"range_expanded:{rg}")

    # --- modality vs family --------------------------------------------
    plausible = FAMILY_MODS.get(fam, set())
    for m in parsed["mods"]:
        if m in voc["mods"] and m not in plausible:
            flags.append(f"modality_family_mismatch:{m}")

    # --- disorder words vs cells ----------------------------------------
    cells = set(parsed["cells"])
    for cell, word, pat in DISORDER_KEYWORDS:
        if not keyword_checks or not re.search(pat, evidence_fwd, re.I):
            continue
        if cell == "B-any":
            if not any(c.startswith("B") for c in cells):
                flags.append(f"keyword_without_cell:B?({word})")
        elif cell not in cells:
            flags.append(f"keyword_without_cell:{cell}({word})")
    ranged = set()
    for rg in parsed["ranges"]:
        m = RANGE_RE.match(rg)
        ranged.update(f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1))
    kw_by_cell = {cell: pat for cell, _, pat in DISORDER_KEYWORDS}
    for c in parsed["cells"]:
        if c.startswith("A") and c in kw_by_cell and c not in ranged:
            pat = kw_by_cell[c]
            if c in CELL_EVIDENCE_EXTRA:
                pat = f"(?:{pat})|(?:{CELL_EVIDENCE_EXTRA[c]})"
            if not re.search(pat, evidence_conv, re.I):
                flags.append(f"cell_without_keyword:{c}")
    if "C2" in cells and "C2" not in ranged:
        age_title = " ".join([title, r.get("age", ""), status])
        if not INFANT_RE.search(age_title):
            flags.append("C2_without_infant_evidence")
        age_first = re.match(r"\s*(\d+)", r.get("age", ""))
        if ADULT_RE.search(title + " " + r.get("age", "")) or (age_first and int(age_first.group(1)) >= 18):
            flags.append("C2_but_adult")

    # --- modality words in the title vs M codes -------------------------
    for m, word, pat in MODALITY_KEYWORDS:
        if keyword_checks and re.search(pat, title, re.I) and m not in parsed["mods"]:
            flags.append(f"modality_keyword_without_code:{m}({word})")

    # --- path on disk (exact case) ---------------------------------------
    parent = os.path.join(repo, "datasets", fam)
    if os.path.isdir(parent):
        names = os.listdir(parent)
        if rid not in names:
            same = [n for n in names if n.lower() == rid.lower()]
            if same:
                flags.append(f"path_case_differs_on_disk:{same[0]}")
            else:
                flags.append("path_missing_on_disk")
    else:
        flags.append("path_missing_on_disk")

    # --- n_subjects ------------------------------------------------------
    n_num, n_kind = parse_n_subjects(r.get("n_subjects", ""))
    if n_kind != "numeric":
        flags.append(f"n_subjects_{n_kind}")

    # --- licence -----------------------------------------------------------
    tokens = parse_license(r.get("license", ""))
    if not tokens:
        flags.append("license_no_spdx_token")
    else:
        flags.append(f"license_token:{tokens[0]}")
        if len(tokens) > 1:
            flags.append("license_multiple_tokens:" + "/".join(tokens))

    hpo = [anchors[c] for c in parsed["cells"] if c in anchors]
    return parsed, hpo, flags, n_num, tokens


def is_hard(flag):
    return flag.split(":")[0] in HARD_FLAGS


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO", os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--out", default=None, help="default docs/registry_cells.csv")
    ap.add_argument("--quiet", action="store_true", help="counts and HARD rows only")
    ap.add_argument("--migrate", default=None, metavar="PATH",
                    help="also write a copy of the registry with the split columns "
                         "(cells, cell_qualifier, modalities, hpo_ids, license_id, "
                         "n_subjects_num) appended, to a NEW file; the registry itself "
                         "is never written")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    reg_path = os.path.join(repo, "docs", "datasets_index.csv")
    out_path = args.out or os.path.join(repo, "docs", "registry_cells.csv")
    if args.migrate and os.path.abspath(args.migrate) == os.path.abspath(reg_path):
        sys.exit("refusing to overwrite docs/datasets_index.csv; give --migrate a new path")

    voc = load_vocabulary(repo)
    anchors, hpo_notes = load_hpo_anchors(repo, voc)
    with open(reg_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    id_counts = Counter(r["id"] for r in rows)

    results = []
    other_ids = sorted(id_counts, key=len, reverse=True)
    for r in rows:
        parsed, hpo, flags, n_num, tokens = check_row(r, voc, anchors, repo, id_counts, other_ids)
        results.append((r, parsed, hpo, flags, n_num, tokens))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "family", "cells", "modalities", "qualifiers", "hpo_ids", "flags"])
        for r, parsed, hpo, flags, _, _ in results:
            w.writerow([r["id"], r["family"], "|".join(parsed["cells"]), "|".join(parsed["mods"]),
                        "|".join(parsed["qualifiers"]), "|".join(hpo), "|".join(flags)])

    if args.migrate:
        new_cols = ["cells", "cell_qualifier", "modalities", "hpo_ids", "license_id", "n_subjects_num"]
        with open(args.migrate, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(list(rows[0].keys()) + new_cols)
            for r, parsed, hpo, _, n_num, tokens in results:
                w.writerow(list(r.values()) + [
                    "|".join(parsed["cells"]), "|".join(parsed["qualifiers"]),
                    "|".join(parsed["mods"]), "|".join(hpo),
                    tokens[0] if tokens else "", "" if n_num is None else n_num])
        print(f"migrated : {args.migrate} (original columns kept, {len(new_cols)} appended)")

    # ---- console summary ----------------------------------------------------
    counts = Counter()
    for _, _, _, flags, _, _ in results:
        for fl in flags:
            counts[fl.split(":")[0]] += 1
    hard_rows = [(r, flags) for r, _, _, flags, _, _ in results if any(is_hard(x) for x in flags)]
    distinct = len({r["moveatlas_cells"] for r in rows})

    print(f"registry : {reg_path}")
    print(f"rows     : {len(rows)} ({distinct} distinct moveatlas_cells strings, {len(id_counts)} distinct ids)")
    print(f"written  : {out_path}")
    print()
    print("flag counts (rows carrying the flag at least once):")
    for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        tag = "HARD" if name in HARD_FLAGS else "    "
        print(f"  {tag} {n:4d}  {name}")
    print()
    print(f"HARD rows: {len(hard_rows)}")
    for r, flags in hard_rows:
        print(f"  {r['id']:32s} {r['family']:9s} cells='{r['moveatlas_cells'][:60]}'  "
              + ", ".join(x for x in flags if is_hard(x)))

    if not args.quiet:
        print()
        print("proposals (soft evidence, owner adjudicates):")
        interest = ("keyword_without_cell", "cell_without_keyword", "C2_without_infant_evidence",
                    "C2_but_adult", "modality_family_mismatch", "modality_keyword_without_code",
                    "class_only")
        for r, parsed, _, flags, _, _ in results:
            hits = [x for x in flags if x.split(":")[0] in interest]
            if hits:
                print(f"  {r['id']:32s} [{r['family']}] '{r['title'][:64]}'")
                print(f"      cells='{parsed['raw'][:90]}'")
                print(f"      {'; '.join(hits)}")
        print()
        print("vocabulary check:")
        for line in vocabulary_report(voc):
            print(line)
        for line in hpo_notes:
            print(line)
        no_anchor = [c for c in voc["cells"] if c not in anchors]
        print(f"  cells without an HPO anchor in this project: {', '.join(no_anchor)}")

    return 1 if hard_rows else 0


if __name__ == "__main__":
    sys.exit(main())
