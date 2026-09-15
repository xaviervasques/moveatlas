# Operations: the pipeline, the gates, the record format, the access log

Extracted 2026-09-08 from the handoff chain and the 360 review, split on
2026-09-15: this file is what a READER of the resource needs (how records
are produced, what checks they pass, what a record is, how access is
logged). The two-machine procedure of the ingestion setup (mounts, line
endings, AppleDouble, tokens, log locations) moved to docs/MACHINES.md,
which does not ship. Rules cite the handoff section they came from
(H8 s6 = KINEFM_HANDOFF_8.md section 6; R360 = docs/REVIEW_360_2026-09-07.md).

## 1. Pipeline order

Taken from README "Pipeline order", H21 s1-s2 and H19 s13. Run from the
repo root; every step is idempotent and resumable.

1. `fetch_*.py` / `ingest_*.py`: acquire raw data from the origin host
   with a sha256-journaled, resumable download; licence read at fetch
   time, never at catalogue time (README; memory rule "verify at
   fetch").
2. `build_canonical_*.py` / `ingest_*.py`: harmonize into the contracts
   under `configs/`, writing the per-family manifests in `datasets/`.
3. `convert_records_to_npz.py`: builders other than build_canonical_eeg
   still write pickle; run the converter after any ingestion until each
   builder is switched to `moveatlas.records.save` (H21 s1, list in
   docs/RECORD_FORMAT.md).
4. `validate_canonical.py` (gate 1, see s5).
5. `mask_statistics.py --cap 0`: the exhaustive validity-mask numbers
   the paper reports (H15 s1, H20 s3); run with the disk quiet.
6. `build_zenodo_staging.py --hash`: `export/zenodo_staging/<id>/`
   (metadata.json, files.csv, provenance.html prepended; H21 s2).
7. `upload_zenodo.py --bundle` then `upload_zenodo.py`: DRAFT deposits
   only, stale draft files removed, resumable through
   `export/zenodo_staging/_uploaded.json` (H15 s7, H21 s2).
8. The owner publishes from zenodo.org/uploads (H19 s7b). The code
   never publishes and never touches a published record (H21 s2).
9. `build_records_table.py`: `moveatlas/data/zenodo_records.json`,
   shipped with the package (README, H19 s9).
10. `launch_dryrun.py` (gate 3) must say LAUNCH-READY (H19 s9).
11. Site regeneration: `gen_datacards.py`, `site/gen_dataset_pages.py`,
    `build_portal.py` (stdlib, run anywhere; H19 s13 point 3), then the
    Sphinx build on the Mac (H21 s5).

## 2. The three gates

All three before any release; each exits non-zero on a gap (README
"The three gates"):

- `validate_canonical.py`: contract conformity of the harmonized
  records (full pass or sampled).
- `release_lint.py <release_dir> [--scidata]`: the automated half of
  the privacy and licence gate (docs/PRIVACY_GATE.md); anything not
  allowed by `docs/license_matrix.csv` is refused; `*.pkl` is no longer
  allowlisted (H21 s1).
- `launch_dryrun.py`: builds the package from a clean `git archive` of
  HEAD, installs it into a fresh venv with the local store hidden, and
  walks a stranger's path (README, H19 s9).

Tests: `<python> -m pytest -q` (105
corpus-free tests, CI on ubuntu x 3.9/3.11/3.13; H21 s4).

## 3. The record format

`moveatlas-record/1`: one ZIP per container with extension `.npz`, a
`meta.json` header, one `.npy` member per array at any depth (token
`{"$npy": path}` in the metadata), readable with numpy alone; spec in
docs/RECORD_FORMAT.md, implementation moveatlas/records.py (H21 s1).
Container granularity is unchanged from the pickle era (per record for
eeg/emg, per dataset or shard elsewhere) because of the 1 MiB clusters
(H21 s1). The 519.7 GB of superseded pickles are still on disk; their
deletion (`convert_records_to_npz.py --workers 12 --delete-pkl`) is an
owner GO (H21 s1, s9).

## 4. The access log

`datasets/_access_log_manual.csv` is human-owned and gets every new
row by hand on the PC; `build_access_log.py` rebuilds the output csv
and must NOT run on Windows: its stat pass would degrade every aux
dossier row (H20 s1, README). The rebuild is a Mac task (H20 s1, H21
s9 point 5).

