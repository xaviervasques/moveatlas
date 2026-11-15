# 100STYLE: one actor, 100 locomotion styles (BVH)

- dataset: style100
- family: pose  (physical path: datasets/pose/style100)
- MoveAtlas cells: C1; M1
- population: one actor (dataset description)
- n_subjects: 1
- signal: BVH skeletal motion, 60 fps (Frame Time 0.016667 s), 23 joints, no fingers
- conditions: healthy; 100 styles x 8 locomotion types (BR, BW, FR, FW, ID, SR, SW, TR: backward, forward and sideways run and walk, idle, transitions) (fields activity, locomotion_type)
- marker set: no markers: BVH joints (Hips, Chest..Chest4, Neck, Head, collars, shoulders, elbows, wrists, hips, knees, ankles, toes)
- license: CC BY 4.0 (Zenodo 8127870, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only style100)
- link: https://doi.org/10.5281/zenodo.8127870
- DOI: 10.1145/3522618
- citation: 100STYLE Dataset (Zenodo 8127870); article doi 10.1145/3522618
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 1 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_style100_bvh): 810 3D pose records / 1 subjects / 22.13 h at native rates (59.9988 Hz x 810); measured body axis +y x 810; 0 calibration or static trials skipped, 0 refused or unreadable, 0 with a joint unresolved in that file; no fold: 1 subject(s), fewer than the 5 folds of moveatlas.evaluations.splits (no fold: 1 subjects cannot fill 5 patient-level folds)
- sampling rate per file: 59.9988 Hz x 810 (records of the canonical build; per-sample fps, never resampled); inventory headers: BVH 60 Hz x 810
- splits: no fold: 1 subject(s), fewer than the 5 folds of moveatlas.evaluations.splits (no fold: 1 subjects cannot fill 5 patient-level folds)
- known issues (2026-11-12):
  - One person: no subject-level split is possible; the whole set sits on one side of any split.
  - The BVH unit is not stated; coordinates are kept in the file's unit (the normalization removes it).
  - Frame_Cuts.csv gives the usable frame range per style and type; it is carried as frame_cuts on the record, the takes are not trimmed.
  - 1 / Frame Time gives 59.9988 Hz, stored as such.
  - Not fetched: the labelled copy (14.75 GB).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (1 files, subjects counted None).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only style100 (readers in mocap_readers.py; joint map open_style100_bvh in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
