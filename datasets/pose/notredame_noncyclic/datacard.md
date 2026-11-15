# Notre Dame: whole-body optical marker and ground reaction force data of non-cyclic activities

- dataset: notredame_noncyclic
- family: pose  (physical path: datasets/pose/notredame_noncyclic)
- MoveAtlas cells: C1; M1, M3
- population: 10 healthy adults (AB01 to AB10)
- n_subjects: 10
- signal: 3D marker trajectories (48 to 57 landmarks, 200 Hz, metres), C3D; GRF; OpenSim models and results
- conditions: healthy; 14 activities, 11 of them from the Berg Balance Scale (sit to stand, stand to sit, reach forward, object pickup, turn, look behind, foot on chair, feet together, tandem feet, one leg, eyes closed, squat, shoe lace, stride) (field activity)
- marker set: ISB landmark codes (LIAS, LIPS, LFTC, LFLE, LFAL, LCAJ, LHLE, LRSP, LUSP, LAH, LPH...), lateral landmarks only at elbow, knee and ankle
- license: CC BY 4.0 (CurateND 10.7274/28689221.v1, read at fetch 2026-11-12; the article is CC BY-NC-ND and covers the article only, not the data) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only notredame_noncyclic; the 10 participant zips)
- link: https://doi.org/10.7274/28689221.v1
- DOI: 10.7274/28689221.v1
- citation: Whole-body optical marker and ground reaction force data of healthy humans performing non-cyclic activities (CurateND, 2025), doi 10.7274/28689221.v1
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 12 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_isb_notredame): 430 3D pose records / 10 subjects / 1.22 h at native rates (200 Hz x 430); measured body axis +z x 430; 0 calibration or static trials skipped, 0 refused or unreadable, 7 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 2 / 2 / 2 / 2 / 2; no subject in two folds
- sampling rate per file: 200 Hz x 430 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 200 Hz x 430
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 2 / 2 / 2 / 2 / 2; no subject in two folds
- known issues (2026-11-12):
  - The 385 image members of each participant zip stay inside the zip.
  - Not fetched: the per-participant MAT, TAK and C3D copies, OpenSim geometry and MATLAB tools.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (12 files, subjects counted 10).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only notredame_noncyclic (readers in mocap_readers.py; joint map open_isb_notredame in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
