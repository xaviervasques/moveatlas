# Schreiber and Moissenet: gait at five walking speeds in injury-free adults (C3D)

- dataset: schreiber_moissenet_gait
- family: pose  (physical path: datasets/pose/schreiber_moissenet_gait)
- MoveAtlas cells: C1; M1
- population: 50 injury-free adults, 19-67 y
- n_subjects: 50
- age: 19-67 y
- signal: 3D marker trajectories (52 anatomical landmarks, ISB codes, 100 Hz), C3D
- conditions: healthy; overground walking at five speed conditions C1 to C5, very slow included (field condition)
- marker set: 52 landmarks (ISB / Van Sint Jan codes: IAS, IPS, FTC, FLE, FME, FAL, TAM, SAE, HLE, HME, RSP, UHE...), no head marker
- license: CC BY 4.0 (figshare 7734767 v8, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only schreiber_moissenet_gait)
- link: https://doi.org/10.6084/m9.figshare.7734767.v8
- DOI: 10.6084/m9.figshare.7734767.v8
- citation: Schreiber and Moissenet, A multimodal dataset of human gait at different walking speeds established on injury-free adult participants (figshare, v8), doi 10.6084/m9.figshare.7734767.v8
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 3 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_isb_schreiber): 1143 3D pose records / 50 subjects / 0.79 h at native rates (100 Hz x 1143); measured body axis +z x 1143; 50 calibration or static trials skipped, 0 refused or unreadable, 38 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 10 / 10 / 10 / 10 / 10; no subject in two folds
- sampling rate per file: 100 Hz x 1143 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 100 Hz x 1193
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 10 / 10 / 10 / 10 / 10; no subject in two folds
- known issues (2026-11-12):
  - No head marker: the head joint is absent.
  - Static trials (_ST, 50) are skipped at ingestion.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (3 files, subjects counted 50).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only schreiber_moissenet_gait (readers in mocap_readers.py; joint map open_isb_schreiber in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
