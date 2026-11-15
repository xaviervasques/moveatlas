# Van der Zee et al.: healthy walking at 33 speed, step length and step width conditions (level 1 C3D)

- dataset: vanderzee_walking
- family: pose  (physical path: datasets/pose/vanderzee_walking)
- MoveAtlas cells: C1; M1
- population: 10 healthy young adults
- n_subjects: 10
- signal: 3D marker trajectories (35 markers, 120 Hz), level 1 C3D
- conditions: healthy; treadmill walking at 33 conditions of speed, step length and step width (trial_look_up.xlsx maps trial numbers to conditions)
- marker set: 35 markers: pelvis (ASIS, sacrum), trochanters, thigh and shank clusters, lateral and medial epicondyles and malleoli, foot, acromion, elbow and wrist; no head
- license: CC0 1.0 (figshare collection 10.6084/m9.figshare.c.5897423, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only vanderzee_walking; level 1 C3D only)
- link: https://doi.org/10.6084/m9.figshare.c.5897423.v1
- DOI: 10.6084/m9.figshare.c.5897423.v1
- citation: Van der Zee et al., A biomechanics dataset of healthy human walking at various speeds, step lengths and step widths (figshare collection, 2022), doi 10.6084/m9.figshare.c.5897423.v1
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 2 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_vanderzee): 329 3D pose records / 10 subjects / 5.45 h at native rates (120 Hz x 329); measured body axis +z x 329; 10 calibration or static trials skipped, 1 refused or unreadable, 33 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 2 / 2 / 2 / 2 / 2; no subject in two folds
- sampling rate per file: 120 Hz x 329 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 120 Hz x 340
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 2 / 2 / 2 / 2 / 2; no subject in two folds
- known issues (2026-11-12):
  - No head marker: the head joint is absent.
  - The condition of each trial (trial_look_up.xlsx) is not joined to the records in this pass.
  - Quiet standing trials (10) are skipped as calibration. The files use the DEC processor format (read by mocap_readers.py).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (2 files, subjects counted 10).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only vanderzee_walking (readers in mocap_readers.py; joint map open_vanderzee in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
