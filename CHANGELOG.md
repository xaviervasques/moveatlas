# Changelog

All notable changes to the MoveAtlas corpus and the `moveatlas` package are
recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the project has not yet made a public release, so every section below is
pre-launch. Dataset counts are the value measured on the date of the entry
(rows of `docs/datasets_index.csv`), not a running total.

## [Unreleased] (2026-09-15)

### Added

- The recipe tier as library calls: `moveatlas.fetch(id)` downloads a
  dataset from its origin host into the store (resumable, sha256-journaled,
  checksums verified against the host's own manifest) and
  `moveatlas.ingest(id)` harmonizes it there with the corpus's code;
  `moveatlas.recipe(id)` says beforehand whether a recipe runs in the
  library, exists only as repository scripts (then the exact commands are
  the error message), or is not needed. Library recipes today: `fog_star`
  (Zenodo origin; rebuilt byte-identical to the corpus's records),
  `daphnet` (UCI), `hd_accel_jnet` and `monipar` (Zenodo; each rebuilt
  from its origin and equal to the corpus's records on every field the
  corpus carries) and
  `fog_turning_filho` (figshare origin, which answers programs with a
  browser challenge: `fetch()` then names the file to save where and
  accepts it once there). A `moveatlas` command line (`list`, `info`,
  `fetch`, `ingest`, `where`).
- The user store: a fresh install has an empty store (`~/.moveatlas/store`
  or `$MOVEATLAS_STORE`) laid out like the repository; recipes fill it and
  the published records front it for the hosted tier. `$MOVEATLAS_REPO`
  remains the developer's override. Nothing raises for lack of a store.
- Site: *Getting started* (install, first dataset in three lines, the
  store, the three access cases) and *User guide* (one complete walk per
  access case as executed on 2026-09-15, the record format, subject-level
  splits, paradigms) beside the data-first pages; the API lists the
  recipes, the store and the command line.

- `ds.files()` and `ds.path(name)` on every dataset: what a dataset holds
  (locally or in its published record) and a local, verified path to one
  file. Nineteen published records carry tables, archives or documents
  rather than canonical records; `get_data()` on those now says so and
  lists the files instead of naming an ingestion script. `moveatlas files`
  and `moveatlas get` on the command line. Site: a *Troubleshooting* page
  listing every error by situation.
- Tests for the three riskiest scripts (validate_canonical.py's record
  checks and family walk, including the Windows backslash defect proven
  on posix; mask_statistics.py's walker; upload_zenodo.py's offline
  paths), a portability guard on the canonical manifests, a drift guard
  pinning the bundled registry snapshot to docs/. 250 tests.
- `gen_datacards.py` refuses to shrink the registry (its 108 entries
  against 170 rows used to drop 62 datasets silently); the EEG, EMG and
  sensefog builders write forward-slash record paths on every platform.
- `datasets/_catalogue.csv` rebuilt to the registry's 170 rows (it had 80
  since the hunts); the paper tables that read it are re-run at the freeze.
- `docs/OPERATIONS.md` now holds what a reader needs (pipeline, gates,
  record format, access log); the owner's two-machine procedure moved to
  `docs/MACHINES.md`, which does not ship. `temporary/` (17 GB of
  builder input) is `builder_inputs/`.

- The Data Descriptor frozen and assembled as a submission package
  (paper/package/): manuscript v3 on the frozen numbers
  (paper/freeze_numbers.json), five figures, five tables, supplementary
  information, cover letter, bibliography for Zotero.

### Changed

- `hosted` now means exactly "served from a published MoveAtlas record":
  a redistributable dataset without a record (`fog_turning_filho`,
  `seizeit2`) classifies as `recipe` until it is staged and published.
  Registry counts: 53 hosted, 83 recipe, 34 barrier.

- The 53 harmonized Zenodo records of the hosted tier are PUBLISHED
  (2026-09-15): every draft was re-verified from the API, its reserved DOI
  bound and its publication date set on the day, then published one API
  call each and read back from the public API without a token, 53 of 53.
  `launch_dryrun.py` says LAUNCH-READY with the hosted tier live.
  `moveatlas/data/zenodo_records.json` is unchanged: the DOIs reserved at
  draft time are the published ones.
- The public repository exists (github.com/xaviervasques/moveatlas,
  private while colleagues review; one authored commit, CI green on Python
  3.9, 3.11 and 3.13) with the built site on its `gh-pages` branch. The
  resource paper does not ship in it.

- `dandi 000947` fetch complete and digest-verified: 378 files, 976.8 GB,
  378 OK / 0 BAD / 0 unverifiable / 0 orphan (`verify_dandi_local.py`).
- `sensefog` (Mendeley, CC BY 4.0) fetched (277 files, 2.45 GB, per-file
  sha256 verified) and harmonized: 45 scalp-EEG records (48 sites, 1000 Hz)
  and 45 leg-EMG records (TA/GA bilateral), 11 subjects, plus IPG monitor
  traces as aux; `--full` validation 0 errors; staged for Zenodo
  (`export/zenodo_staging/sensefog/`, 136 files, 2.28 GB). No FOG label
  array yet (the markers in the deposit are sync markers only); Percept LFP,
  APDM motion and the FOG segments are deferred to a second pass.
- `physionet_multimodal_gait` (PhysioNet, CC BY 4.0) acquired: 713/713
  files, 6.93 GB, 0 bad; 59 healthy adults with EEG, EMG, IMU and force
  plates at three speeds. Canonical integration (four families) is pending.
- Access-barrier casebook case 13: `piet_essential_tremor` withdrawn at
  source between 2026-09-05 (page-verified public, CC0) and 2026-09-07,
  with the DataCite record and portal badges still reading public
  (`docs/ACCESS_BARRIERS_CASES.md`).
- Exhaustive validity-mask statistics (`mask_statistics.py --cap 0`): 54
  (family, dataset) rows, all unsampled, over 45 harmonized datasets and
  301,735 records (`docs/mask_statistics.csv`, `site/source/_generated/mask_stats.html`).
- Root `LICENSE` (BSD-3-Clause), `CITATION.cff`, root `README.md`, this
  changelog; `bench` optional-dependency group (scikit-learn, scipy).
- `moveatlas/data/SNAPSHOT.json` and `moveatlas.registry.snapshot_info()`:
  provenance of the registry snapshot bundled with the package.
- `tests/` (105 pytest tests, corpus-free) and `.github/workflows/ci.yml`
  (ubuntu x Python 3.9/3.11/3.13).
- Site: one dataset count sourced from the registry at build time, a
  taxonomy page (cells with HPO links, absences ledger, casebook titles),
  schema.org `Dataset` JSON-LD on every dataset page (Sphinx and portal).
- `validate_registry.py` with `docs/registry_cells.csv` and
  `docs/REGISTRY_CELLS_REPORT_2026-09-08.md`: the `moveatlas_cells`
  column parsed and flagged (the closing-sweep rows were coded with a
  shifted cell legend; corrections proposed, registry unchanged).
- Paper: tables rebuilt on the 170-row registry, Figure 2, the
  harmonization table, `docs/MANIFEST_SCHEMA.md`, a Data Availability
  section.

### Changed

- Storage format: every canonical record container moved from pickle to
  the self-describing `.npz` container `moveatlas-record/1` (zip with
  `.npy` members and a `meta.json` member; `moveatlas/records.py`,
  `docs/RECORD_FORMAT.md`). 21,090 containers converted with a verified
  round trip (558 GB of pickle -> 185 GB of `.npz`); readers, validators,
  staging and the release lint follow; the superseded pickles await the
  owner's deletion GO. The staged deposits are rebuilt on the new files
  and `upload_zenodo.py` removes the old files from existing drafts.
- `frames.to_frame` names EEG channel tables by site (they collapsed to
  duplicate `eeg` columns before).
- scikit-learn is imported lazily by `moveatlas.evaluations` and
  `moveatlas.pipelines`; importing the package no longer requires it.
- `launch_dryrun.py` runs on Windows as well as POSIX (venv `Scripts/`
  layout, `git archive --format=zip` instead of `tar`; on Windows the
  archive command runs with `core.protectNTFS=false` and the unwritable
  `datasets/aux/` members are skipped at extraction).
- Bundled registry snapshot refreshed from `docs/` (170 index rows, 108
  license-matrix rows).
- Catalogue at 170 datasets; 77 hosted / 59 recipe / 34 barrier / 0
  local_only access cases.

## [In development] (2026-09-01)

Catalogue at 99 datasets (from 83).

### Added

- 16 new catalogued datasets from a licence-verified gap hunt, including
  the SSBD stereotypy annotations, Goodwin SMM accelerometry
  (internal-only), the first open dystonia MRI (OpenNeuro ds006395, CC0),
  pallidal single-unit electrophysiology with gene labels, DANDI macaque
  circuit recordings, NeuroMorpho striatal morphologies, within-subject
  levodopa ON/OFF EEG, an alcohol-responsiveness dystonia table, and real
  (non-synthetic) infant pose.
- Five confirmed open-data deserts recorded as findings: tics, akinesia,
  rigidity-as-signal, kinematic Huntington chorea, pharmacological-challenge
  kinematics.
- Scientific Data groundwork: conformity check against the journal
  policies, the descriptor outline, and a licence gate in `release_lint.py`
  (`--scidata`).

### Changed

- Taxonomy adjudication: 21 owner rulings applied (B2/B3 rule for
  parkinsonian gait; `modys_video` recognized as choreoathetosis; `gaitndd`
  ALS arm corrected from ataxia to pyramidal; `accel_fluctuations` recovered
  as the akinesia-cell candidate). `taxonomy_map.csv` is now emitted from the
  registry.
- `tremordb` clarified: ingested as an AUX velocity asset by design
  (laser-Doppler, outside the acc/gyro contract).

## [In development] (2026-08-31)

### Added

- Gallery section "Beyond the signal": ECoG + STN-LFP traces and MNI
  electrode maps (Merk and Neumann grip-force testbed), movement-disorder
  gene expression across one Allen donor's 946 sampled sites, the genetic
  landscape across five PanelApp panels. Everything shown is measured data
  on disk.
- Site: light and dark figure variants, 12-lane modality glance on the
  landing page, sortable master table with CSV export and access-case /
  harmonization badges, dataset pages in one scholarly order, taxonomy
  coverage as six named small multiples.

### Fixed

- Corpus-count double counting: the family manifests already contain the
  datasets that also keep a dedicated manifest (capture24, ltmm, pads,
  pd_biostamprc21, sixmwt_lifespan, multimodal_fog, cervical_motion); the
  site statistics read both, inflating totals by 27,147 records and about
  16,500 hours. Measured with each dataset counted once: 293,288 records /
  32,764 subjects / 40,303 hours across 40 ingested datasets. Per-dataset
  counts in the data cards were always correct.

## [0.1.0.dev0] - 2026-08-28

The founding release, local-only (pre-launch).

### Added

- The `moveatlas` package: registry over 83 catalogued datasets, four
  enforced access cases (51 hosted / 17 recipe / 12 barrier / 3
  local_only), BSD-3-Clause.
- Pilot dataset adapters: `nonan_gaitprint`, `nonan_gaitprint_young`,
  `gait120`, `cody_3` (private tier, labels eval-only), `physionet_gaitpdb`
  (VGRF insoles; 93 Parkinson, 72 controls).
- Patient-level split primitive `cross_patient_folds`.
- `moveatlas.to_frame`: any canonical record as a tidy time-indexed pandas
  DataFrame, masks rendered as NaN.
- `moveatlas.viz`: `plot_skeleton` and `plot_trace`.
- Subject-filtered shard loading.
- Documentation site (pydata-sphinx-theme + sphinx-gallery), 24 executed
  example pages in 7 sections.

### Fixed

- Data-card correction: the cdystonia table is a gzip-compressed R save
  file mislabeled `.sav` by its host; read with `pyreadr`.

### Changed

- Project renamed from MOAMB to MoveAtlas on 2026-08-28 (PyPI and trademark
  collision checks ruled out OpenMove). Historical documents keep the old
  name.
