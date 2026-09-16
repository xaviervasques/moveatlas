# -*- coding: utf-8 -*-
"""Generate one documentation page per catalogued dataset.

For every registry row (docs/datasets_index.csv, the single count source)
this writes site/source/datasets/<id>.md (MyST markdown) containing: a
schema.org Dataset JSON-LD block, a key-facts table from the registry,
the full data card verbatim (the single source of truth, with its
evidence trail), and the dataset's publications rendered from
docs/citations.csv with their BibTeX from docs/citations.bib. Plus
datasets/index.md as the toctree holder. Run before the sphinx build
whenever cards or citations change.
"""
import csv
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CITATION_AUTHORS = {}
sys.path.insert(0, REPO)
os.environ.setdefault("MOVEATLAS_REPO", REPO)
import moveatlas

OUT = os.path.join(REPO, "site", "source", "datasets")
os.makedirs(OUT, exist_ok=True)

# taxonomy cell names (canonical mapping, mirrors build_portal.py)
CELL_NAME = {
    "A1": "Tremor", "A2": "Myoclonus", "A3": "Tics", "A4": "Dystonia",
    "A5": "Stereotypies", "A6": "Athetosis", "A7": "Chorea",
    "A8": "Ballismus",
    "B1": "Rigidity", "B2": "Bradykinesia", "B3": "Hypokinesia",
    "B4": "Akinesia", "B5": "Freezing of gait",
    "C1": "Normal adult movement", "C2": "Infant development",
    "C3": "Aging",
    "D1": "Epilepsy", "D2": "Ataxia", "D3": "Pyramidal syndromes",
    "D4": "Neuropathies", "D5": "Neurodevelopmental",
    "D6": "Sleep disorders", "D7": "Functional movement disorders",
    "E1": "Endocrine", "E2": "Metabolic", "E3": "Diabetes-related",
    "E4": "Musculoskeletal", "E5": "Dermatologic", "E6": "Iatrogenic",
    "E7": "Psychiatric",
    "M1": "Pose / video", "M2": "Inertial (IMU)", "M3": "Plantar force",
    "M4": "Silhouette", "M5": "EMG", "M6": "EEG", "M7": "LFP / ECoG",
    "M8": "Imaging", "M9": "Genetics", "M10": "Histology / transcr.",
    "M11": "Voice / writing", "M12": "Clinical scales",
}


# manifest source ids that differ from the registry id they belong to
SOURCE_ALIAS = {
    "semg_walking": "physionet_semg_walking",
    "cervical_motion": "cervical_motion_multiplanar",
    "modys": "modys_video",
    "ntu": "ntu_rgbd",
    "cody": "cody_1",
    "cody_external": "cody_3",
    "cap_sleep_chin": "cap_sleep",
    "seizeit2_emg": "seizeit2",
}


def ingested_ids():
    """Ids with harmonized records: union of `source` across the
    canonical manifests (the manifests are the truth), aliases mapped
    onto registry ids."""
    ids = set()
    for path in glob.glob(os.path.join(REPO, "datasets",
                                       "_canonical*manifest*.csv")):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("source"):
                    ids.add(SOURCE_ALIAS.get(row["source"], row["source"]))
    return ids


INGESTED = ingested_ids()


def load_citations():
    rows = {}
    with open(os.path.join(REPO, "docs", "citations.csv"), newline="",
              encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.setdefault(r["dataset"], []).append(r)
    bib = {}
    txt = open(os.path.join(REPO, "docs", "citations.bib"),
               encoding="utf-8").read()
    for m in re.finditer(r"@\w+\{([^,]+),.*?\n\}\n", txt, re.S):
        bib[m.group(1)] = m.group(0).rstrip()
    return rows, bib


CITS, BIB = load_citations()


def esc(s):
    return (s or "").replace("|", "\\|")


# ---------------------------------------------------------------- schema.org
_LICENSE_URLS = [
    ("cc0", "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("cc-zero", "https://creativecommons.org/publicdomain/zero/1.0/"),
    ("cc by-nc-nd", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
    ("cc by-nc-sa", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    ("cc by-nc", "https://creativecommons.org/licenses/by-nc/4.0/"),
    ("cc by-sa", "https://creativecommons.org/licenses/by-sa/4.0/"),
    ("cc by", "https://creativecommons.org/licenses/by/4.0/"),
    ("odc-by", "https://opendatacommons.org/licenses/by/1-0/"),
    ("pddl", "https://opendatacommons.org/licenses/pddl/1-0/"),
    ("etalab", "https://www.etalab.gouv.fr/licence-ouverte-open-licence"),
    ("apache", "https://www.apache.org/licenses/LICENSE-2.0"),
    ("mit", "https://opensource.org/license/mit"),
]


def license_url(r):
    """A licence URL when the registry's prose names a known instrument.
    The registry column is an evidence trail ("CC BY 4.0, SETTLED
    2026-08-25 by the owner after ..."), which is not a licence for a
    machine; emitting the prose as schema.org license was wrong."""
    lic = (r.get("license") or "").lower()
    for token, url in _LICENSE_URLS:
        if token in lic:
            return url
    return ""


def is_free(r):
    """Freely accessible means a reader can obtain the bytes without a
    gate. The access case is computed here rather than read from the row,
    because the two generators build their rows differently; anything the
    registry does not record as redistributable, or that carries a
    documented barrier, is not free."""
    case = r.get("access_case") or access_case(r)
    if case == "hosted":
        return True
    redist = (r.get("redistribution") or "").strip().lower()
    return case == "recipe" and redist.startswith("yes")


def creator_of(r):
    """The dataset's own authors, from the generated citation table, so
    the record credits the people who made the data. Absent rather than
    wrong when the citation could not be resolved."""
    if not _CITATION_AUTHORS:
        _CITATION_AUTHORS.update(_load_citation_authors(REPO))
    names = _CITATION_AUTHORS.get(r["id"])
    if not names:
        return None
    return [{"@type": "Person", "name": n} for n in names[:12]]


def _load_citation_authors(repo):
    out = {}
    p = os.path.join(repo, "docs", "citations.csv")
    if not os.path.exists(p):
        return out
    with open(p, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("kind") != "data" or not row.get("authors"):
                continue
            out.setdefault(row["dataset"], [
                a.strip() for a in row["authors"].split(";") if a.strip()])
    return out


_FILLED = False


def describe(r):
    """One reader-facing sentence: the title, the family, the subject
    count when the source states one. The status column stays on the
    card as the evidence trail."""
    bits = [r["title"] or r["id"]]
    fam = r.get("family")
    if fam:
        bits.append(f"MoveAtlas {fam} family")
    n = (r.get("n_subjects") or "").strip()
    if n and n[0].isdigit():
        bits.append(f"{n} subjects" if not n.lower().endswith("subjects") else n)
    lic = (r.get("license") or "").split("(")[0].split(",")[0].strip()
    if lic:
        bits.append(f"licence {lic[:60]}")
    return ". ".join(bits) + "."


def jsonld(r, cells):
    """schema.org Dataset record for one registry row (same shape as the
    portal's, build_portal.py). isAccessibleForFree follows the access
    case: hosted and recipe download without a gate; barrier and
    local_only do not."""
    link = (r.get("link") or "").strip()
    # The description a reader (and a search engine) sees must describe the
    # dataset, not our workflow: the status column starts with CATALOGUED /
    # DOWNLOADED / DOCUMENTED BARRIER and is an evidence trail, not prose.
    desc = describe(r)
    keywords = [r["family"]] + [f"{c} {CELL_NAME[c]}" if c in CELL_NAME
                                else c for c in cells]
    atlas = {"@type": "Organization", "name": "MoveAtlas"}
    d = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": r["title"] or r["id"],
        "description": desc,
        "identifier": link or r["id"],
        "license": license_url(r) or (r.get("license") or "")[:120],
        # MoveAtlas catalogues and harmonizes; it did not create or publish
        # these datasets. sdPublisher is the schema.org term for the party
        # that published the METADATA record, which is what this block is.
        "sdPublisher": atlas,
        "keywords": keywords,
        "url": link,
        "isAccessibleForFree": is_free(r),
        "measurementTechnique": r["family"],
        "includedInDataCatalog": {"@type": "DataCatalog",
                                  "name": "MoveAtlas"},
    }
    creators = creator_of(r)
    if creators:
        d["creator"] = creators
    if not link:
        del d["url"]
    txt = json.dumps(d, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return ["```{raw} html",
            '<script type="application/ld+json">', txt, "</script>",
            "```", ""]



# ---------------------------------------------------------------- public rendering
# The cards are working documents: their status prose records who decided
# what, on which machine and in which session. A public page shows the
# dataset, not the workflow (owner request, 2026-09-16): every displayed
# string goes through _public(), the status row is normalised to a state and
# a date, and the card body shows its factual lines only.
_INTERNAL = re.compile(
    r"owner|session|\bGO\b|tower|DECIDED|agent|Paris|handoff|casebook|"
    r"\bH\d+\b|ruling|internal|the paper|assistant|queue", re.I)


def _public(text):
    """Drop parentheticals and clauses that talk about the workflow."""
    t = " ".join(str(text or "").split())
    # parentheticals carrying workflow words
    t = re.sub(r"\s*\(([^()]*)\)", lambda m: "" if _INTERNAL.search(m.group(1)) else m.group(0), t)
    # "DECIDED 2026-08-28:" and "CORRECTED 2026-..:" trails
    t = re.sub(r"\b(DECIDED|CORRECTED|RESOLVED|SETTLED)\s+\d{4}-\d{2}-\d{2}[^:;]*:\s*", "", t)
    # clauses after ";" or ". " that carry workflow words
    parts = re.split(r"(?<=[.;])\s+", t)
    kept = [x for x in parts if not _INTERNAL.search(x)]
    t = " ".join(kept) if kept else (parts[0] if parts else t)
    t = re.sub(r"\s+([,;.])", r"\1", t).strip(" ;,")
    return t.replace("tower download", "download")


_STATES = [
    (r"DOWNLOADED AND INGESTED|INGESTED", "harmonized"),
    (r"DOCUMENTED BARRIER|WRITTEN OFF|HUMAN QUEUE|BARRIER", "documented access barrier"),
    (r"SCRIPTED-CLIENT BLOCKED|BLOCKED", "blocked at the host for scripted clients"),
    (r"DOWNLOADED|raw on disk|ACQUIRED", "acquired"),
    (r"INDEX-ONLY|CATALOGUED|NEW|queued", "catalogued"),
]


def _status_public(text):
    """'DOWNLOADED AND INGESTED 2026-08-24 (Paris night session): ...' ->
    'harmonized (2026-08-24)'. The prose stays in the repository's card."""
    t = str(text or "")
    state = "catalogued"
    for pat, name in _STATES:
        if re.search(pat, t):
            state = name
            break
    m = re.search(r"\d{4}-\d{2}-\d{2}", t)
    return f"{state} ({m.group(0)})" if m else state


def _redistribution_public(text):
    t = " ".join(str(text or "").split())
    low = t.lower()
    head = "yes" if low.startswith("yes") else "no" if low.startswith("no") else "unknown"
    m = re.search(r"pointer to ([^;,.)]+)", t)
    if head == "no" and m:
        return f"no (fetch from {m.group(1).strip()})"
    m2 = re.search(r"^yes\s*\(([^)]*)\)", t, re.I)
    if head == "yes" and m2 and not _INTERNAL.search(m2.group(1)):
        return f"yes ({m2.group(1).strip()})"
    return head


_CARD_KEEP = ("dataset", "family", "MoveAtlas cells", "population", "n_subjects",
              "age", "signal", "channel types", "license", "access", "link",
              "citation", "ingestion", "library recipe")


def _card_public(body):
    """The card's factual lines, scrubbed; status, notes and the Retrieval /
    Processing sections stay in the repository."""
    out = []
    for line in body.splitlines():
        m = re.match(r"^- ([A-Za-z_ ]+?)\s*(\(.*?\))?\s*:\s*(.*)$", line)
        if not m:
            continue
        key, _date, val = m.group(1).strip(), m.group(2), m.group(3)
        if key not in _CARD_KEEP:
            continue
        if key == "family":
            val = re.sub(r"\s*\(physical path:[^)]*\)", "", val)
        val = _public(val)
        if val:
            out.append(f"- **{key}**: {esc(val)}")
    return out


def _row_public(r):
    """The registry row as the page shows it: every free-text field scrubbed
    of workflow prose, the status reduced to a state and a date."""
    pub = dict(r)
    for k in ("license", "access", "age", "moveatlas_cells", "title"):
        if pub.get(k):
            pub[k] = _public(pub[k]).replace("tower download", "download")
    if pub.get("status"):
        pub["status"] = _status_public(pub["status"])
    if pub.get("redistribution"):
        pub["redistribution"] = _redistribution_public(pub["redistribution"])
    return pub


def page(r):
    """One dataset page in a fixed scholarly order: JSON-LD (invisible),
    identity badges, key facts, how to load, license and access,
    publications with BibTeX, then the factual lines of the data card."""
    r = _row_public(r)
    rid = r["id"]
    status = "harmonized" if rid in INGESTED else "catalogued"
    cells = list(dict.fromkeys(
        re.findall(r"[A-E]\d+|M\d+", r.get("moveatlas_cells") or "")))
    lines = [f"# {r['title']}", ""]
    lines += jsonld(r, cells)
    lines += [f'<span class="ma-fam ma-{r["family"]}">{r["family"]}</span>'
              f'&nbsp; <span class="ma-badge ma-{status}">{status}</span>'
              f'&nbsp; <span class="ma-badge ma-{r["access_case"]}">'
              f'{r["access_case"]}</span>&nbsp; <code>{rid}</code>', ""]
    if cells:
        tags = "".join(
            f'<span class="ma-tag">{CELL_NAME.get(c, c)}</span>'
            for c in cells)
        lines += [tags, ""]
    lines += ["| | |", "|---|---|"]
    for label, key, cap in (("Taxonomy cells", "moveatlas_cells", 400),
                            ("Subjects", "n_subjects", 400),
                            ("Ages", "age", 400),
                            ("Status", "status", 300),
                            ("License", "license", 400)):
        v = r.get(key)
        if v:
            v = v if key == "status" else _public(v)
            if len(v) > cap:
                v = v[:cap].rstrip() + "..."
            if v:
                lines.append(f"| **{label}** | {esc(v)} |")
    lines.append("")
    lines += ["Cell codes are defined on the {doc}`taxonomy page "
              "</taxonomy>`.", ""]
    lines += ["## How to load", "",
              "```python",
              "import moveatlas",
              f"ds = moveatlas.dataset(\"{rid}\")",
              "records, meta = ds.get_data()"
              if r["access_case"] in ("hosted", "local_only") else
              f"ds.info   # {r['access_case']}: get_data() explains the route",
              "```", ""]
    lines += ["## License and access", ""]
    for label, key in (("License", "license"),
                       ("Redistribution", "redistribution"),
                       ("Access route", "access")):
        v = r.get(key)
        if v:
            v = v if key == "redistribution" else _public(v)
            if v:
                lines.append(f"- **{label}**: {esc(v[:400])}")
    if r.get("link"):
        lines.append(f"- **Source**: <{r['link']}>")
    lines.append("")
    if rid in CITS:
        lines += ["## Publications", ""]
        for c in CITS[rid]:
            doi = f" DOI: [{c['doi']}](https://doi.org/{c['doi']})" \
                if c.get("doi") else ""
            lines.append(f"- {c['authors']} ({c['year']}). "
                         f"*{c['title']}*. {c['venue']}.{doi}")
        lines.append("")
        keys = [c["bibkey"] for c in CITS[rid] if c.get("bibkey") in BIB]
        if keys:
            lines += ["```bibtex"]
            for k in keys:
                lines.append(BIB[k])
            lines += ["```", ""]
    card = os.path.join(REPO, r["path"], "datacard.md")
    if os.path.exists(card):
        body = open(card, encoding="utf-8").read()
        facts = _card_public(body)
        if facts:
            lines += ["## Data card", "",
                      "The dataset's card, factual lines; the full card with its "
                      "verification dates, download journal and processing notes "
                      "is in the repository.", ""]
            lines += facts + [""]
    return "\n".join(lines)


rows = moveatlas.list_datasets()
for r in rows:
    with open(os.path.join(OUT, f"{r['id']}.md"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write(page(r))

index = ["# Dataset pages", "",
         "One page per catalogued dataset: key facts, publications with "
         "BibTeX, and the factual lines of the data card (the full card, "
         "with its verification dates and download journal, is in the "
         "repository). Cell codes are defined on the "
         "{doc}`taxonomy page </taxonomy>`.", "",
         "```{toctree}", ":maxdepth: 1", ""]
for r in sorted(rows, key=lambda x: (x["family"], x["id"])):
    index.append(f"{r['id']}")
index += ["```", ""]
with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8",
          newline="\n") as f:
    f.write("\n".join(index))
n_cit = sum(1 for r in rows if r["id"] in CITS)
print(f"{len(rows)} dataset pages ({n_cit} with publications)")
