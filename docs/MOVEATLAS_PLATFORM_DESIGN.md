# MoveAtlas platform design: the MOABB transposition (2026-08-28)

Owner directive: reproduce the shape of MOABB (Mother of All BCI Benchmarks,
moabb.neurotechx.com) for this project. MOABB was mapped in depth on
2026-08-28 (site structure, philosophy, architecture, governance); this
document is the faithful transposition. It AMENDS docs/DATA_PORTAL_PLAN.md:
the static-catalogue front survives as a component, but the center of
gravity moves to a Python package + Sphinx documentation site + reproducible
benchmarks + a community contribution path.

## 0. Why MOABB is the right mold

MOABB's founding diagnosis transposes word for word: papers without code,
preprocessing choices that change scores but go unreported, datasets
scattered in heterogeneous formats, algorithms validated on one small
in-house cohort. Their answer: one API over N datasets, standardized
task definitions, fixed evaluation splits, sklearn-contract pipelines,
meta-analysis across datasets, an open leaderboard. Trajectory: 12
datasets (2018) to 160 datasets / 3,627 subjects (2026), because the unit
of contribution is one small file and contributors benefit instantly.

Three MOABB principles we adopt outright:

1. **The project never hosts data it does not own.** A dataset is a CODE
   ADAPTER that downloads from the original home and normalizes to a
   shared interchange format. This is exactly our 4-access-case design,
   and it dissolves the Zenodo-vs-HF debate: those are just hosts for the
   subset we may host (51 sets + our own artifacts), while the package is
   the product.
2. **Ride existing standards.** MOABB rode MNE-Python + scikit-learn. Our
   interchange format is the canonical contract family already written
   and validated (pose 15-joint, IMU 14x9, EMG channel-table, force,
   silhouette, EEG); pipelines keep the sklearn estimator contract.
3. **Meta-analysis, never pooling, for benchmarks.** Each dataset is an
   independent experiment; evidence combines via paired tests + Stouffer
   weighting. Our foundation-model PRETRAINING still pools (that is its
   point) under patient-level splits; the BENCHMARK layer above it treats
   datasets as experiments, and the foundation model becomes one pipeline
   among others on the leaderboard.

## 1. Concept map (MOABB -> MoveAtlas)

| MOABB | MoveAtlas |
|---|---|
| EEG dataset (BaseDataset) | movement dataset, 6 modality families, 83 catalogued |
| MNE Raw interchange | canonical contracts (configs/canonical_*.yaml) |
| paradigm tag ('imagery', 'p300') | modality family + taxonomy cells (docs/DATA_MAP.md) |
| Paradigm (MotorImagery, P300) | ClinicalTask (gait, tremor_rest, finger_tapping, reach, sit_to_stand, sleep_movement...) + FixedIntervalWindows for continuous recordings |
| events dict (left_hand: code) | label vocabulary anchored to HPO codes (build_hpo_movement_map.py), labels EVAL-ONLY (standing rule R1) |
| subject/session/run hierarchy | patient_ns / visit / trial (patient-level namespacing already in every record) |
| WithinSession / CrossSession / CrossSubject evaluations | WithinVisit / CrossVisit / CrossPatient / CrossDataset (the last is our central clinical question) |
| sklearn pipelines + YAML declarations | same, plus foundation-model embeddings as a pipeline |
| analysis: permutation/Wilcoxon + Stouffer + SMD plots | same module, same statistics |
| benchmark() one-call orchestrator | same |
| accept=True flag for consent-walled sets | access-case machinery: hosted / recipe / local-only / documented-barrier |
| LocalBIDSDataset for private data | LocalDataset pointing at a local canonical tree (CODY runs through it) |
| NEMAR mirror against link rot | our hosted tier IS the mirror where licences allow |

## 2. The package: `moveatlas`

Skeleton (names mirror MOABB so its users feel at home):

```
moveatlas/
  datasets/        # one module per dataset: metadata + fetch + parse to contract
    base.py        # BaseDataset: access_case, license, citation, taxonomy_cells,
                   #   subjects, visits_per_subject, modality, fetch()/get_data()
    local.py       # LocalDataset (private/held data; CODY, licence-restricted-held)
    compound.py    # CompoundDataset (stitched subsets)
  paradigms/       # ClinicalTask definitions: windowing, fps policy per modality,
                   #   is_valid(dataset), used_labels(dataset), scoring
  evaluations/     # WithinVisit, CrossVisit, CrossPatient, CrossDataset
  pipelines/       # baselines (features+sklearn); adapters for embeddings
  analysis/        # meta-analysis, effect sizes, summary plots (MOABB port)
  benchmark.py     # benchmark(pipelines=..., paradigms=..., evaluations=...)
```

Access cases surface in `get_data()`:
- hosted: download from the MoveAtlas record (Zenodo/HF), sha256-checked;
- recipe: instructions + automated fetch from the ORIGINAL host where
  scriptable, then OUR ingester runs locally (the ingest_*.py scripts
  become package recipes);
- local-only: `LocalDataset(path=...)`, nothing downloads;
- barrier: raises an informative error carrying the datacard and the
  documented route (tim_tremor raises with its retraction evidence).

`get_data()` returns records already in the canonical contract, plus a
metadata DataFrame (patient_ns, visit, trial, dataset, cells) which is the
contract with the Evaluation layer, exactly like MOABB's (X, labels,
metadata) triple.

Every dataset class declares: license, citation (BibTeX from
build_citations.py), doi, access_case, taxonomy_cells, age range, and the
privacy flags. The datacards render FROM these declarations (single source
of truth; gen_datacards.py migrates to reading the package).

## 3. The documentation site

Single Sphinx project, PyData Sphinx Theme, sphinx-gallery, DataTables for
the dataset tables (all lifted from MOABB's stack). The existing
build_portal.py static site becomes the transition scaffold; its content
(83 dataset pages, 30 cell pages, 12 modality pages) migrates into the
Sphinx tree.

Navigation, in MOABB's order:
Home | The MoveAtlas benchmark | Datasets | Installation | Examples | API |
Citation | Release notes | GitHub

Landing page section order (MOABB's, adapted):
1. hero: logo + tagline + headline stats ("83 catalogued movement
   datasets, 6 modality families, 40,000+ hours");
2. badge row (build, PyPI, Python versions, license, DOI);
3. six feature cards: Datasets / Evaluations / Contracts (preprocessing) /
   Clinical tasks (paradigms) / Analysis and statistics / Benchmark
   results;
4. quickstart code block (load one hosted dataset, run one baseline);
5. The Problem / The Solution narrative (movement-disorders version:
   scattered corpora, incomparable pipelines, no patient-level rigor,
   licence chaos; the access-barriers cases ARE the problem section's
   evidence);
6. core team / contributors / acknowledgements / how to help;
7. citation (software DOI + papers); footer with disclaimer and contact.

Datasets section:
- master interactive table over ALL 83 (columns from our index:
  dataset, modality, cells, n_subjects, ages, hours, fps, license tier,
  access case, country, year, DOI, citation);
- per-family detail tables (pose / IMU / EMG / force / silhouette / EEG),
  schema per family mirroring our manifests (records, subjects, fps,
  n_frames, channel identities for EMG...);
- per-cell views kept from the current portal (the taxonomy is our
  per-paradigm axis);
- **Submit a new dataset**: a pinned GitHub wishlist issue (MOABB's
  issue #1 pattern) + a gallery tutorial "adding a dataset" + the rule
  that every submission passes licence triage (evidence on the card) and
  the privacy gate BEFORE merge. Our addition to MOABB's flow: the gate.

Examples gallery categories (theirs, transposed):
1. Getting started (load, visualize a canonical record per family);
2. Task-specific evaluations (gait cross-dataset, tremor within-visit...);
3. Data management (download dir, cache, local datasets, BIDS export);
4. Benchmarking (multi-pipeline, learning curves, statistics);
5. Advanced (contract internals, masks and validity, EMG channel tables,
   foundation-model embeddings as features).
Every example downloadable as .py + .ipynb (sphinx-gallery default).

Hosting: GitHub Pages from the docs build, custom domain when the owner
buys one; dual-deploy pattern like MOABB if we split site repo from code
repo. NOTHING deploys until the standing publication gate lifts.

## 4. Benchmarks

Phase 1 (resource paper): no leaderboard yet, the paper documents corpus +
contracts + access cases.
Phase 2 (benchmark paper, MOABB's 2024 move): implement baselines per
clinical task, run benchmark() across eligible datasets, publish the
results page (mean +/- SD per pipeline x dataset, methodology stated up
front, Within-Visit first). The foundation model, when it exists, enters
as one pipeline; its advantage claim is then a meta-analysis statement,
not a pooled number.

## 5. Governance (proposals, owner decides)

- package + site licence: BSD-3-Clause (MOABB's choice; maximally
  compatible with labs and industry, consistent with the open-data line);
- software DOI on Zenodo, versioned, authors = contributors list;
- two-paper trajectory: resource paper now, big-benchmark paper later;
- contribution credit: changelog entries + contributors page + versioned
  software citation (MOABB's three channels);
- community umbrella: none needed at v1; revisit if adoption comes.

## 6. Phasing

P0 (now, behind the publication gate): this design doc; freeze corpus;
final validation; HANDOFF 11.
P1: package skeleton `moveatlas` with base classes + 3 pilot dataset adapters
(one hosted CC0 set e.g. nonan_gaitprint, one recipe set e.g. amass-like,
one LocalDataset over CODY derived data); Sphinx site skeleton with the
landing page, dataset master table generated from the existing index, and
2 gallery examples.
P2: migrate all 83 cards into dataset classes; evaluations module;
first baselines; submit-a-dataset tutorial + wishlist issue.
P3: public launch when the owner lifts the gate: GitHub push, Pages,
Zenodo community + records, CODY release, resource paper.

## 7. Decisions RECORDED (owner, 2026-08-28)

(a) package/site licence: **BSD-3-Clause**;
(b) CODY derived-data release licence: **CC BY 4.0**;
(c) domain: none for now; **build and serve everything locally on disk**,
    migrate to a domain later (the Sphinx build is host-agnostic, so this
    costs nothing);
(d) MoveAtlas-Base v1: **canonical tensors only**, no raw mirrors;
(e0) PyPI: the name **moveatlas is RESERVED since 2026-08-28 18:05** (the
    owner uploaded 0.1.0.dev0, sdist + wheel, via twine; verified live on
    the PyPI JSON API). Dev versioning is deliberate: pip ignores dev
    releases by default, so nobody installs a shell package before the
    launch; publishing 0.1.0 at launch turns `pip install moveatlas` on.
(e) name: **MoveAtlas**, decided 2026-08-28 evening. The owner first
    proposed OpenMove; the availability check killed it (PyPI 'openmove'
    taken, openmove.com is an established mobility company, and
    'openmovement' is the AX3 sensor project). MoveAtlas is free on PyPI,
    collision-clean at check time, and echoes the project's original
    working title 'Atlas du mouvement'. Renamed globally the same day
    (code, docs, site, package, export tree, desktop shortcuts);
    historical handoffs and logs keep the old name as archives.

Language rule reaffirmed the same day: EVERYTHING in the repo in English.
The six handwritten datacards (cody_1/2/3, amass, motion_x, ntu_rgbd)
still carried French field labels; translated 2026-08-28.

## 8. THE cardinal UX principle: one click, one pip (owner, 2026-08-28)

Downloading a dataset must be trivially easy: a click on the site or a
pip-installed `moveatlas.load()` and the data arrives. This principle now
ranks ABOVE hosting-source purity, and it has teeth because of what
2026-08-28 proved empirically: even CC0 data behind a healthy DOI can be
undownloadable in practice (figshare's anti-bot penalty box swallowed a
19 KB xlsx exactly like a 57.8 GB bundle; the owner had to click through
a browser). Consequences:

1. **Hosted tier serves from MoveAtlas's own records, never from the
   original host.** For the 51 redistributable sets, `moveatlas.load()`
   pulls OUR harmonized canonical tensors from Zenodo/HF with sha256
   checks. The original host is provenance, not infrastructure. Site
   pages carry a direct download button for the same records.
2. **Owner-held data gets deposited.** For CODY (and any future
   owner-produced dataset), the plan's standing ask to the owner is:
   deposit the publishable derived data on Zenodo or Hugging Face (or
   Kaggle) under CC BY 4.0, and the dataset becomes a first-class
   one-click citizen. Concretely: cody_1 derived data (today on GitHub)
   gets a Zenodo record with DOI; cody_2/cody_3 releases target the same
   route when the owner publishes them.
3. **Friction anywhere is a work item, not a fact of life.** Whenever a
   recipe-tier dataset shows access friction (browser-only hosts,
   throttles, Drive links, dead forms), the response ladder is:
   (i) re-read the licence for room to mirror the harmonized form (then
   tier up to hosted); (ii) automate the original route as far as terms
   allow; (iii) only then document the friction on the card as a barrier.
   The access-barriers cases file doubles as the friction registry.
4. **The gate still rules.** One-click never overrides the privacy gate
   or a licence: mmasd stays internal-only however easy it would be to
   mirror; pointer-tier sets stay pointers.

Two clarifications recorded 2026-08-28 (owner Q&A):

- **Nothing is on Zenodo/HF yet, by design.** The original hosts' records
  belong to the source authors and are provenance only; OUR harmonized
  tensors live on this disk (order of magnitude today: pose ~2.5 GB, EMG
  ~60 GB, IMU ~178 GB, EEG ~258 GB of processed data) and get uploaded
  to MoveAtlas's own Zenodo community / HF org at P3, when the owner lifts
  the publication gate. Account creation and the upload go-ahead are
  owner actions; metadata, manifests and API-driven uploads are prepared
  and automated later. Until then the package's hosted
  resolver serves from a LOCAL record store (same layout, same sha256
  discipline), so everything is buildable and testable offline; flipping
  to Zenodo/HF later is a URL-table change, not a redesign.
- **Multimodal datasets are ONE dataset.** A dataset keeps a single
  identity (one name, one card, one DOI, one download) however many
  modality streams it carries; `moveatlas.load("gait120")` returns all its
  streams, `modality=` filters. On the site: one page per dataset, and
  the dataset also appears in each per-family table it contributes to.
  Hosting: one record per dataset holding all streams (linked records
  if a record ceiling forces a split).
