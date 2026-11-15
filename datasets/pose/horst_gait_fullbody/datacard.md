# Horst et al.: overground walking, full-body kinematics and kinetics of healthy adults (C3D)

- dataset: horst_gait_fullbody
- family: pose  (physical path: datasets/pose/horst_gait_fullbody)
- MoveAtlas cells: C1; M1, M3
- population: 57 healthy adults
- n_subjects: 57
- signal: 3D marker trajectories (54 markers, 250 Hz) and force plates, C3D
- conditions: healthy; overground walking at self-selected speed
- marker set: 54 markers: head, trunk and arm landmarks, thigh and shank clusters (4 each), heel and forefoot
- license: CC BY 4.0 (Mendeley Data svx74xcrjr v3, DataCite, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only horst_gait_fullbody)
- link: https://doi.org/10.17632/svx74xcrjr.3
- DOI: 10.17632/svx74xcrjr.3
- citation: Horst et al., A public dataset of overground walking kinetics and full-body kinematics in healthy adult individuals (Mendeley Data, 2019), doi 10.17632/svx74xcrjr.3
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 2 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_horst_gait): 1142 3D pose records / 57 subjects / 0.47 h at native rates (250 Hz x 1142); measured body axis +z x 1142; 109 calibration or static trials skipped, 0 refused or unreadable, 0 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 12 / 12 / 11 / 11 / 11; no subject in two folds
- sampling rate per file: 250 Hz x 1142 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 250 Hz x 1251
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 12 / 12 / 11 / 11 / 11; no subject in two folds
- known issues (2026-11-12):
  - Knee and ankle are not built: the gait trials carry thigh and shank clusters but no epicondyle or malleolus marker. A cluster-to-landmark calibration from the static trials is open.
  - Two wrist labels are misspelled in the files (WIRST, WRITS); the joint map uses them as spelled.
  - Static trials (109) are skipped at ingestion. Not fetched: the TSV exports of the same trials.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (2 files, subjects counted 57).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only horst_gait_fullbody (readers in mocap_readers.py; joint map open_horst_gait in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
