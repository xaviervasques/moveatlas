# Lencioni et al.: kinematic, kinetic and EMG data of walking variants and stairs

- dataset: lencioni_gait_stairs
- family: pose  (physical path: datasets/pose/lencioni_gait_stairs)
- MoveAtlas cells: C1, C2 (children from 6 y); M1, M3, M5
- population: 50 healthy subjects, 6-72 y
- n_subjects: 50
- age: 6-72 y
- signal: per-trial marker trajectories (29 markers, LAMB total-body protocol), GRF, EMG, joint angles, moments and powers in one MATLAB struct per subject
- conditions: healthy; level walking, toe walking, heel walking, step up and step down (stairs)
- marker set: 29 markers (s.MarkerVarName: cheeks, C7, shoulders, elbows, wrists, PSIS, ASIS, thighs, lateral condyles, fibular heads, shanks, lateral malleoli, heels, toes, fifth metatarsals)
- license: CC BY 4.0 applied: every figshare item of collection 10.6084/m9.figshare.c.4494755 states CC0, the data paper states CC BY 4.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied ; redistribution: yes (with attribution, CC BY 4.0 applied)
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only lencioni_gait_stairs)
- link: https://doi.org/10.6084/m9.figshare.c.4494755.v1
- DOI: 10.6084/m9.figshare.c.4494755.v1
- citation: Lencioni et al., Human kinematic, kinetic and EMG data during level walking, toe/heel-walking, stairs ascending/descending (figshare collection, 2019), doi 10.6084/m9.figshare.c.4494755.v1
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 54 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_lencioni_mat): 1613 3D pose records / 50 subjects / 0.53 h at native rates (200 Hz x 959, 60 Hz x 654); measured body axis +y x 1613; 0 calibration or static trials skipped, 2 refused or unreadable, 0 with a joint unresolved in that file, 6 with joint samples beyond 8 torso lengths of the pelvis masked and 0 with samples beyond 1 km masked (labelling or export errors of the source); 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 10 / 10 / 10 / 10 / 10; no subject in two folds
- sampling rate per file: 200 Hz x 959, 60 Hz x 654 (records of the canonical build; per-sample fps, never resampled)
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 10 / 10 / 10 / 10 / 10; no subject in two folds
- known issues (2026-11-12):
  - The inventory found no rate (it read headers only); the subject struct holds it (KinFreq: 200 Hz for 25 subjects, 60 Hz for 25), and the build reads it per subject.
  - Trials are short segments around one stride (s.Data(k).Marker), not continuous recordings.
  - The marker unit is not stated in the file; values span 0 to 2 and are read as metres.
  - A few trials have a malformed marker array and are refused (ingest_audit.csv). All_Subjects.zip duplicates the 50 loose files and is not extracted.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (54 files, subjects counted 50).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only lencioni_gait_stairs (readers in mocap_readers.py; joint map open_lencioni_mat in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
