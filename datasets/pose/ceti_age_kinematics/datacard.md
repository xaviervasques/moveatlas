# CeTI-Age-Kinematics: full-body inertial motion of older and younger adults in daily tasks

- dataset: ceti_age_kinematics
- family: pose  (physical path: datasets/pose/ceti_age_kinematics)
- MoveAtlas cells: C1, C3 (older adults); M1, M2
- population: 32 adults: 20 older (OA, 66-75 y) and 12 younger (YA, 19-28 y) (participants.tsv participant_group; ages as the README states)
- n_subjects: 32
- age: 19-28 y and 66-75 y
- signal: full-body inertial suit and gloves (Rokoko Smartsuit Pro, 19 suit IMUs, 7 per glove), exported as BVH skeletons (100 Hz) and per-segment TSV
- conditions: healthy older and younger adults; 30 daily tasks in task groups c (calibration pose), e, g and h (object placement), o, r, s (sit-to-stand), u and w; two sessions per subject
- marker set: no markers: the suit's BVH skeleton (Character1_* joints, no head joint; the neck chain's End Site stands for the head)
- license: CC BY 4.0 (figshare 10.6084/m9.figshare.26983645.v2, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only ceti_age_kinematics)
- link: https://doi.org/10.6084/m9.figshare.26983645.v2
- DOI: 10.6084/m9.figshare.26983645.v2
- citation: The CeTI-Age-Kinematics dataset: A Full-Body IMU-Based Motion Dataset of Daily Tasks by Older and Younger Adults (figshare, 2025), doi 10.6084/m9.figshare.26983645.v2
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 3 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_ceti_rokoko_bvh): 1499 3D pose records / 32 subjects / 11.19 h at native rates (100 Hz x 1499); measured body axis +y x 1499; 64 calibration or static trials skipped, 0 refused or unreadable, 0 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 7 / 7 / 6 / 6 / 6; no subject in two folds
- sampling rate per file: 100 Hz x 1499 (records of the canonical build; per-sample fps, never resampled); inventory headers: BVH 100 Hz x 1563
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 7 / 7 / 6 / 6 / 6; no subject in two folds
- known issues (2026-11-12):
  - An inertial suit, not an optical system: joint centres come from the suit's body model with fixed segment lengths (on the checked records the shank, about 0.45 m, is longer than the thigh, about 0.41 m).
  - participants.tsv records drift and data loss for some runs (tracking_comment); not applied to the records in this pass.
  - The 23 MP4 instruction videos and the one JPG stay inside the zip, never extracted or viewed; 25 PNG figures under derivatives/images/ were extracted with the other members (decision of 2026-11-12) and not viewed. The .py, .pyc and git hook files of the archive are never run.
  - Task c01 (calibration pose) is skipped at ingestion.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (3 files, subjects counted 32).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.
Archives extracted on 2026-11-12 after the fetch: extract_log.json.

## Processing

ingest_open_mocap.py --only ceti_age_kinematics (readers in mocap_readers.py; joint map open_ceti_rokoko_bvh in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
