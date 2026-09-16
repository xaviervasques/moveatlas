# -*- coding: utf-8 -*-
"""Sphinx configuration for the MoveAtlas documentation site.

Stack deliberately mirrors MOABB's (pydata-sphinx-theme + sphinx-gallery
+ sphinx-design): docs/MOVEATLAS_PLATFORM_DESIGN.md section 3. Built locally
for now (owner decision 2026-08-28: no domain yet, migrate later).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..", "..")))

project = "MoveAtlas"
author = "MoveAtlas contributors"
copyright = "2026, MoveAtlas contributors"
release = "0.1.0.dev0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
    "myst_parser",
    "sphinx_copybutton",
]

copybutton_prompt_text = ">>> "

myst_enable_extensions = ["colon_fence"]
# the hunt ledger (docs/hunt_confirmed_absences.md) is included into
# taxonomy.rst as a fragment: its "##" headings are right for the fragment
# and myst's "document starts at H2" check is not about fragments
suppress_warnings = ["myst.header"]

sphinx_gallery_conf = {
    "examples_dirs": ["../examples"],
    "gallery_dirs": ["auto_examples"],
    "filename_pattern": r"plot_",
    "download_all_examples": True,
    "remove_config_comments": True,
}

templates_path = ["_templates"]
# macOS writes AppleDouble sidecars (._foo.rst) on exFAT volumes and the
# source glob would pick them up as binary "documents"; Sphinx's **/ needs
# a directory segment, so the root level takes its own pattern
exclude_patterns = ["._*", "**/._*"]

html_theme = "pydata_sphinx_theme"
html_title = "MoveAtlas"
html_theme_options = {
    "header_links_before_dropdown": 7,
    "icon_links": [],
    "footer_start": ["copyright"],
    "logo": {
        "image_light": "_static/logo_light.svg",
        "image_dark": "_static/logo_dark.svg",
        "alt_text": "MoveAtlas",
    },
}
html_static_path = ["_static"]
html_css_files = ["moveatlas.css"]
html_context = {"default_mode": "auto"}

# leaf pages have no section children: drop the empty left sidebar
html_sidebars = {
    "statistics": [], "modalities": [], "install": [], "cite": [],
    "submit_dataset": [], "dataset_summary": [], "whats_new": [],
    "taxonomy": [],
}

autosummary_generate = True
autodoc_member_order = "bysource"

# ---------------------------------------------------------------------
# One number, one source: every dataset count quoted in the .rst pages is
# a substitution computed here from the registry, never typed by hand.
#   |n_catalogued|  rows of docs/datasets_index.csv, software rows excluded
#   |n_human|       rows whose family is not "animal"
#   |n_animal|      rows whose family is "animal"
#   |n_harmonized|  distinct `source` values in docs/mask_statistics.csv
#                   (datasets with measured canonical records)
#   |n_records|     sum of n_records_seen over docs/mask_statistics.csv
# ---------------------------------------------------------------------
_REPO = os.path.abspath(os.path.join(__file__, "..", "..", ".."))


def _registry_counts():
    import csv as _csv
    with open(os.path.join(_REPO, "docs", "datasets_index.csv"),
              newline="", encoding="utf-8") as f:
        reg = list(_csv.DictReader(f))
    # software rows (moveatlas.registry.TOOLS) are not datasets: the same
    # rule as the library and the descriptor
    from moveatlas.registry import TOOLS as _TOOLS
    reg = [r for r in reg if r["id"] not in _TOOLS]
    with open(os.path.join(_REPO, "docs", "mask_statistics.csv"),
              newline="", encoding="utf-8") as f:
        mask = list(_csv.DictReader(f))
    n_animal = sum(1 for r in reg if r["family"] == "animal")
    # subjects and hours come from the canonical manifests, the same
    # source the statistics page and the paper use, so no page can drift
    manifests = {
        "pose": "_canonical_manifest.csv", "imu": "_canonical_imu_manifest.csv",
        "eeg": "_canonical_eeg_manifest.csv",
        "emg": "_canonical_emg_manifest.csv",
        "force": "_canonical_force_manifest.csv",
        "silhouette": "_canonical_silhouette_manifest.csv"}
    subjects, hours = set(), 0.0
    for name in manifests.values():
        path = os.path.join(_REPO, "datasets", name)
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                if row.get("subject_ns"):
                    subjects.add(row["subject_ns"])
                try:
                    fps = float(row.get("fps") or 0)
                    n = float(row.get("n_frames") or 0)
                    if fps > 0:
                        hours += n / fps / 3600.0
                except ValueError:
                    pass
    import glob as _glob
    n_examples = len(_glob.glob(os.path.join(
        _REPO, "site", "examples", "*", "plot_*.py")))
    # what the published records actually serve (LAUNCH_PLAN 1.9): the
    # harmonized records split by availability, computed from the registry,
    # the records table and the exhaustive mask pass, never typed
    from moveatlas.registry import records_table as _records_table
    served = _records_table()
    per = {}
    for r in mask:
        if r.get("source"):
            per[r["source"]] = per.get(r["source"], 0) + int(r["n_records_seen"] or 0)
    reg_by = {r["id"]: r for r in reg}
    split = {"served": [0, 0], "recipe": [0, 0], "unstaged": [0, 0]}
    for did, k in per.items():
        red = (reg_by.get(did, {}).get("redistribution") or "").strip().lower()
        key = ("served" if did in served else
               "unstaged" if red.startswith("yes") else "recipe")
        split[key][0] += 1
        split[key][1] += k
    return {
        "n_served_datasets": f"{split['served'][0]:,}",
        "n_served_records": f"{split['served'][1]:,}",
        "n_recipe_datasets": f"{split['recipe'][0]:,}",
        "n_recipe_records": f"{split['recipe'][1]:,}",
        "n_unstaged_datasets": f"{split['unstaged'][0]:,}",
        "n_unstaged_records": f"{split['unstaged'][1]:,}",
        "n_published_records": f"{len(served):,}",
        "n_catalogued": f"{len(reg):,}",
        "n_human": f"{len(reg) - n_animal:,}",
        "n_animal": f"{n_animal:,}",
        "n_harmonized": f"{len({r['source'] for r in mask if r['source']}):,}",
        "n_records": f"{sum(int(r['n_records_seen'] or 0) for r in mask):,}",
        "n_subjects": f"{len(subjects):,}",
        "n_hours": f"{round(hours):,}",
        "n_examples": f"{n_examples:,}",
    }


COUNTS = _registry_counts()
rst_prolog = "\n".join(
    f".. |{k}| replace:: {v}" for k, v in COUNTS.items()) + "\n"

# ---------------------------------------------------------------------
# Generate the dataset master table from the moveatlas registry at build time
# (single source of truth: docs/datasets_index.csv via moveatlas.list_datasets).
# ---------------------------------------------------------------------
# manifest source ids that differ from the registry id they belong to
_SOURCE_ALIAS = {
    "semg_walking": "physionet_semg_walking",
    "cervical_motion": "cervical_motion_multiplanar",
    "modys": "modys_video",
    "ntu": "ntu_rgbd",
    "cody": "cody_1",
    "cody_external": "cody_3",
    "cap_sleep_chin": "cap_sleep",
    "seizeit2_emg": "seizeit2",
}


def _ingested_ids():
    """Dataset ids with harmonized records: the union of the `source`
    column across every canonical manifest (the manifests are the truth,
    never the status prose), aliases mapped onto registry ids."""
    import csv as _csv
    import glob as _glob
    repo = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
    ids = set()
    for path in _glob.glob(os.path.join(repo, "datasets",
                                        "_canonical*manifest*.csv")):
        with open(path, newline="", encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                if row.get("source"):
                    ids.add(_SOURCE_ALIAS.get(row["source"], row["source"]))
    return ids


_TABLE_JS = """<script>
document.addEventListener('DOMContentLoaded', function () {
  var table = document.getElementById('dataset-table');
  if (!table) return;
  var input = document.getElementById('ds-filter');
  var note = document.getElementById('ds-count');
  var rows = function () {
    return Array.prototype.slice.call(table.tBodies[0].rows);
  };
  var total = rows().length;
  function refresh() {
    var shown = rows().filter(function (tr) {
      return tr.style.display !== 'none';
    }).length;
    note.textContent = shown + ' / ' + total + ' datasets';
  }
  input.addEventListener('input', function () {
    var q = input.value.toLowerCase();
    rows().forEach(function (tr) {
      tr.style.display =
        tr.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
    });
    refresh();
  });
  var dir = {};
  Array.prototype.forEach.call(table.tHead.rows[0].cells,
      function (th, i) {
    th.title = 'Sort by ' + th.textContent.trim();
    th.addEventListener('click', function () {
      dir[i] = -(dir[i] || -1);
      var body = table.tBodies[0];
      rows().sort(function (a, b) {
        var x = a.cells[i].textContent.trim();
        var y = b.cells[i].textContent.trim();
        var nx = parseFloat(x.replace(/,/g, ''));
        var ny = parseFloat(y.replace(/,/g, ''));
        if (!isNaN(nx) && !isNaN(ny)) return (nx - ny) * dir[i];
        return x.localeCompare(y) * dir[i];
      }).forEach(function (tr) { body.appendChild(tr); });
    });
  });
  document.getElementById('ds-csv').addEventListener('click',
      function () {
    var lines = [];
    Array.prototype.forEach.call(table.rows, function (tr) {
      if (tr.style.display === 'none') return;
      var cells = Array.prototype.map.call(tr.cells, function (td) {
        return '"' + td.textContent.trim().replace(/"/g, '""') + '"';
      });
      lines.push(cells.join(','));
    });
    var a = document.createElement('a');
    a.href = 'data:text/csv;charset=utf-8,'
      + encodeURIComponent(lines.join('\\n'));
    a.download = 'moveatlas_datasets.csv';
    a.click();
  });
  refresh();
});
</script>"""


def _access_badge(case):
    return f"<span class=\"ma-badge ma-{case}\">{case}</span>"


def _status_badge(ingested):
    label = "harmonized" if ingested else "catalogued"
    return f"<span class=\"ma-badge ma-{label}\">{label}</span>"


def _fam_chip(fam):
    return f"<span class=\"ma-fam ma-{fam}\">{fam}</span>"


def _gen_dataset_table():
    import html as _html
    import moveatlas
    out_dir = os.path.join(os.path.dirname(__file__), "_generated")
    os.makedirs(out_dir, exist_ok=True)
    rows = moveatlas.list_datasets()
    ingested = _ingested_ids()
    cells = ["<div class=\"ma-toolbar\">",
             "<input id=\"ds-filter\" type=\"search\" "
             f"placeholder=\"Filter {len(rows)} datasets: family, cell, "
             "licence, keyword...\">",
             "<button id=\"ds-csv\" type=\"button\">Export CSV</button>",
             "<span id=\"ds-count\" class=\"ma-count-note\"></span>",
             "</div>",
             _TABLE_JS,
             "<table class=\"table datatable\" id=\"dataset-table\">",
             "<thead><tr><th>Dataset</th><th>Family</th><th>Status</th>"
             "<th>Access</th><th>Cells</th><th>Subjects</th>"
             "<th>License</th><th>Link</th></tr></thead><tbody>"]
    for r in sorted(rows, key=lambda x: (x["family"], x["id"])):
        link = r.get("link") or ""
        a = (f"<a href=\"{_html.escape(link)}\">source</a>" if link else "")
        cells.append(
            "<tr>"
            f"<td><b><a href=\"datasets/{r['id']}.html\">"
            f"{_html.escape(r['id'])}</a></b></td>"
            f"<td>{_fam_chip(_html.escape(r['family']))}</td>"
            f"<td>{_status_badge(r['id'] in ingested)}</td>"
            f"<td>{_access_badge(_html.escape(r['access_case']))}</td>"
            f"<td>{_html.escape(r['moveatlas_cells'])}</td>"
            f"<td>{_html.escape(r['n_subjects'])}</td>"
            f"<td>{_html.escape(r['license'][:60])}</td>"
            f"<td>{a}</td></tr>")
    cells.append("</tbody></table>")
    with open(os.path.join(out_dir, "dataset_table.html"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(cells))
    # per-family detail tables (the MOABB per-paradigm tables, transposed)
    fams = sorted({r["family"] for r in rows})
    for fam in fams:
        sub = [r for r in rows if r["family"] == fam]
        t = [f"<h3>{_fam_chip(_html.escape(fam))} "
             f"<span class=\"ma-count-note\">{len(sub)} datasets</span></h3>",
             "<table class=\"table\">",
             "<thead><tr><th>Dataset</th><th>Title</th><th>Status</th>"
             "<th>Cells</th><th>Subjects</th><th>Ages</th><th>Access</th>"
             "</tr></thead><tbody>"]
        for r in sorted(sub, key=lambda x: x["id"]):
            t.append(
                "<tr>"
                f"<td><b><a href=\"datasets/{r['id']}.html\">"
                f"{_html.escape(r['id'])}</a></b></td>"
                f"<td>{_html.escape(r['title'][:70])}</td>"
                f"<td>{_status_badge(r['id'] in ingested)}</td>"
                f"<td>{_html.escape(r['moveatlas_cells'][:40])}</td>"
                f"<td>{_html.escape(r['n_subjects'][:20])}</td>"
                f"<td>{_html.escape((r.get('age') or '')[:30])}</td>"
                f"<td>{_access_badge(_html.escape(r['access_case']))}</td>"
                "</tr>")
        t.append("</tbody></table>")
        with open(os.path.join(out_dir, f"family_{fam}.html"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(t))
    with open(os.path.join(out_dir, "family_tables.html"), "w",
              encoding="utf-8") as f:
        for fam in fams:
            f.write(open(os.path.join(out_dir, f"family_{fam}.html"),
                         encoding="utf-8").read() + "\n")


_gen_dataset_table()


# ---------------------------------------------------------------------
# Taxonomy page inputs (site/source/taxonomy.rst). The cell CODES come from
# build_taxonomy_map.py (the validator every mapping passes through), the
# cell NAMES from build_portal.py (the portal's canonical mapping), the HPO
# terms from docs/hpo_movement_terms.csv (build_hpo_movement_map.py). The
# absences ledger and the barriers casebook live in docs/ and are copied
# or summarized into _generated/ so the page can include them without
# reaching outside the source tree.
# ---------------------------------------------------------------------
def _gen_taxonomy():
    import csv as _csv
    import html as _html
    import re as _re
    import build_portal as _portal
    import build_taxonomy_map as _tax
    out_dir = os.path.join(os.path.dirname(__file__), "_generated")
    os.makedirs(out_dir, exist_ok=True)

    # the two definitions must agree; a mismatch is a build error, not a
    # silent choice
    missing = [c for c in _tax.CELLS_VALID + _tax.MODS_VALID
               if c not in _portal.CELLS and c not in _portal.MODS]
    extra = [c for c in list(_portal.CELLS) + list(_portal.MODS)
             if c not in _tax.CELLS_VALID + _tax.MODS_VALID]
    if missing or extra:
        raise RuntimeError(
            f"taxonomy drift: codes without a name {missing}; names without "
            f"a code {extra} (build_taxonomy_map.py vs build_portal.py)")

    hpo = {}
    with open(os.path.join(_REPO, "docs", "hpo_movement_terms.csv"),
              newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            for c in (r.get("moamb_cells") or "").split("|"):
                c = c.strip()
                if c:
                    hpo.setdefault(c, []).append((r["hpo_id"], r["name"]))

    def hpo_cell(code):
        terms = sorted(hpo.get(code, []))
        if not terms:
            return "<span class=\"ma-count-note\">no HPO term mapped</span>"
        return ", ".join(
            f"<a href=\"https://hpo.jax.org/app/browse/term/{_html.escape(i)}\">"
            f"{_html.escape(i)}</a> {_html.escape(n)}" for i, n in terms)

    parts = []
    for letter, cname in _portal.CLASSES:
        codes = [c for c in _tax.CELLS_VALID if c.startswith(letter)]
        parts += [f"<h3>Class {letter}: {_html.escape(cname)} "
                  f"<span class=\"ma-count-note\">{len(codes)} cells</span></h3>",
                  "<table class=\"table\"><thead><tr><th>Cell</th><th>Name</th>"
                  "<th>HPO terms mapped to this cell</th></tr></thead><tbody>"]
        for c in codes:
            parts.append(f"<tr><td><code>{c}</code></td>"
                         f"<td>{_html.escape(_portal.CELLS[c])}</td>"
                         f"<td>{hpo_cell(c)}</td></tr>")
        parts.append("</tbody></table>")
    parts += ["<h3>Modality codes "
              f"<span class=\"ma-count-note\">{len(_tax.MODS_VALID)} lanes"
              "</span></h3>",
              "<table class=\"table\"><thead><tr><th>Code</th><th>Modality</th>"
              "</tr></thead><tbody>"]
    for m in _tax.MODS_VALID:
        parts.append(f"<tr><td><code>{m}</code></td>"
                     f"<td>{_html.escape(_portal.MODS[m])}</td></tr>")
    parts.append("</tbody></table>")
    n_terms = sum(len(v) for v in hpo.values())
    parts.append(f"<p class=\"ma-count-note\">{n_terms} HPO term-to-cell "
                 f"links over {len(hpo)} cells, from docs/hpo_movement_terms.csv."
                 "</p>")
    with open(os.path.join(out_dir, "taxonomy_cells.html"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")

    # confirmed absences: the cells no catalogued human dataset covers, and
    # the cells covered only by datasets behind a barrier, computed from
    # the registry at build time (the dated search reports and the ledger
    # stay in the repository: they are working documents, not pages)
    from moveatlas.registry import list_datasets as _ld
    rows = [r for r in _ld() if r["family"] != "animal"]
    covered, open_ = {}, {}
    for r in rows:
        cells = [c.strip() for c in (r.get("moveatlas_cells") or "").replace(";", ",").split(",")]
        for c in cells:
            code = c.split()[0] if c else ""
            if code in _tax.CELLS_VALID:
                covered[code] = covered.get(code, 0) + 1
                if r["access_case"] in ("hosted", "recipe"):
                    open_[code] = open_.get(code, 0) + 1
    absent = [c for c in _tax.CELLS_VALID if covered.get(c, 0) == 0]
    barrier_only = [c for c in _tax.CELLS_VALID
                    if covered.get(c, 0) and not open_.get(c, 0)]
    parts = ["<table class=\"table\"><thead><tr><th>Cell</th><th>Name</th>"
             "<th>Status at build time</th></tr></thead><tbody>"]
    for c in absent:
        parts.append(f"<tr><td><code>{c}</code></td><td>{_html.escape(_portal.CELLS[c])}</td>"
                     "<td>no open dataset found</td></tr>")
    for c in barrier_only:
        parts.append(f"<tr><td><code>{c}</code></td><td>{_html.escape(_portal.CELLS[c])}</td>"
                     f"<td>catalogued only behind an access barrier ({covered[c]} dataset"
                     f"{'s' if covered[c] > 1 else ''})</td></tr>")
    parts.append("</tbody></table>")
    parts.append(f"<p class=\"ma-count-note\">{len(absent)} cells with no dataset and "
                 f"{len(barrier_only)} reachable only through a barrier, over "
                 f"{len(_tax.CELLS_VALID)} cells; human datasets only.</p>")
    with open(os.path.join(out_dir, "absences.html"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")

    # barriers casebook: the KINDS of case, without the dataset names and
    # dates the repository's casebook carries (a public page does not
    # point at datasets; the evidence stays in the repository)
    cases = _re.findall(
        r"^## Case \d+: (.*)$",
        open(os.path.join(_REPO, "docs", "ACCESS_BARRIERS_CASES.md"),
             encoding="utf-8").read(), _re.M)
    kinds = []
    for c in cases:
        k = _re.sub(r"\s*\([^)]*\)", "", c)          # drop parentheticals
        k = _re.sub(r"\s*\d{4}-\d{2}-\d{2}[^,;]*", "", k)
        k = k.strip(" ,;:").replace("our own", "the atlas's own")
        k = k[0].upper() + k[1:] if k else k
        if k and k not in kinds:
            kinds.append(k)
    lines = [f"{len(cases)} documented cases, of these kinds:", ""]
    lines += [f"- {k}" for k in kinds]
    with open(os.path.join(out_dir, "barriers_cases.rst"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    # age and sex per harmonized dataset: docs/demographics.csv, the same
    # table the descriptor's Supplementary Table 3 is built from
    # (paper/build_demographics.py writes both), so the site and the paper
    # quote the same statements and the same counts
    dp = os.path.join(_REPO, "docs", "demographics.csv")
    demo = []
    if os.path.exists(dp):
        with open(dp, newline="", encoding="utf-8") as f:
            demo = list(_csv.DictReader(f))
    NR = '<span class="ma-count-note">not reported by source</span>'
    parts = ["<table class=\"table datatable\"><thead><tr><th>Dataset</th>"
             "<th>Subjects (canonical)</th><th>Age</th><th>Sex</th><th>Read from</th>"
             "<th>Per-subject table</th></tr></thead><tbody>"]
    n_age = n_sex = 0
    for r in demo:
        age = "" if r["age_source"] == "not_reported" else r["age_statement"]
        sex = "" if r["sex_source"] == "not_reported" else r["sex_statement"]
        n_age += bool(age)
        n_sex += bool(sex)
        src = {"source_paper": "source publication or record", "registry": "registry",
               "card": "data card"}.get(r["age_source"] if age else r["sex_source"], "")
        url = (r.get("demographics_url") or "").split(";")[0].strip()
        link = (f"<a href=\"{_html.escape(url)}\">{_html.escape(src)}</a>"
                if url and src == "source publication or record" else _html.escape(src))
        table = r.get("subject_table_card") or ""
        table = "" if table.startswith("not reported") else table
        parts.append(f"<tr><td><code>{_html.escape(r['dataset_id'])}</code></td>"
                     f"<td>{_html.escape(r['n_subjects_canonical'])}</td>"
                     f"<td>{_html.escape(age) if age else NR}</td>"
                     f"<td>{_html.escape(sex) if sex else NR}</td>"
                     f"<td>{link}</td><td>{_html.escape(table)[:80]}</td></tr>")
    parts.append("</tbody></table>")
    parts.append(f"<p class=\"ma-count-note\">Age stated for {n_age} and sex for "
                 f"{n_sex} of {len(demo)} harmonized datasets; the statements are "
                 "quoted from the source publication or record (read 2026-09-15), "
                 "the registry or the data card, in that order.</p>")
    with open(os.path.join(out_dir, "demographics_sources.html"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")


_gen_taxonomy()
