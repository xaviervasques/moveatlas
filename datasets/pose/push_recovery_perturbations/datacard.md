# Push recovery: full-body motion capture after external perturbations from five directions (C3D)

- dataset: push_recovery_perturbations
- family: pose  (physical path: datasets/pose/push_recovery_perturbations)
- MoveAtlas cells: C1; M1
- population: 21 healthy young adults (10 women, 11 men), 20-38 y (ReadMe)
- n_subjects: 21
- age: 20-38 y
- signal: 3D marker trajectories (40 body markers and 3 pole markers, Qualisys, 200 Hz), C3D, and CSV exports
- conditions: healthy; standing balance after a push at shoulder height, 5 angles x 3 intensities x 2 repetitions, in two blocks: NI (no impairment) and SI (noise-cancelling headset and limited peripheral vision) (fields condition, perturbation)
- marker set: Plug-in Gait style names (LFHD, LSHO, LHUM, LRAD, LWRA, LKNE, LKNI, LANE, LANI...), P1-P3 on the pole (dropped)
- license: CC BY 4.0 (Zenodo 10512652, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only push_recovery_perturbations)
- link: https://doi.org/10.5281/zenodo.10512652
- DOI: 10.5281/zenodo.10512652
- citation: Chatagnon et al., Full Body Motion Capture of Single Individuals Following External Perturbations from Different Directions (Zenodo, 2024), doi 10.5281/zenodo.10512652; article doi 10.1016/j.jbiomech.2023.111703 (ReadMe)
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 2 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_push_recovery): 1260 3D pose records / 21 subjects / 2.45 h at native rates (200 Hz x 1260); measured body axis +z x 1260; 0 calibration or static trials skipped, 0 refused or unreadable, 0 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 5 / 4 / 4 / 4 / 4; no subject in two folds
- sampling rate per file: 200 Hz x 1260 (records of the canonical build; per-sample fps, never resampled)
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 5 / 4 / 4 / 4 / 4; no subject in two folds
- known issues (2026-11-12):
  - The 7z archive was extracted with the system tar.exe after its 8,894 member paths were listed and none was absolute or held '..' (extract_log.json).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (2 files, subjects counted 21).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.
Archives extracted on 2026-11-12 after the fetch: extract_log.json.

## Processing

ingest_open_mocap.py --only push_recovery_perturbations (readers in mocap_readers.py; joint map open_push_recovery in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
