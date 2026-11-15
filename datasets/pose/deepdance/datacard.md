# DeepDance: motion capture of improvised dance (Qualisys TSV)

- dataset: deepdance
- family: pose  (physical path: datasets/pose/deepdance)
- MoveAtlas cells: C1; M1
- population: 30 dancers (file prefixes Subject1 to Subject30, plus Subject001 read as subject 1)
- n_subjects: 30
- signal: 3D marker trajectories (42 or 43 markers, Qualisys, 240 or 250 Hz), one TSV per one-minute take
- conditions: healthy dancers; improvised dance to music
- marker set: DD_* markers: head (4), shoulders, elbows, wrists, hands, waist (4), thighs, knees, shins, ankles, feet; one rigid-body point RID
- license: CC BY 4.0 (Zenodo 7950401, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only deepdance)
- link: https://doi.org/10.5281/zenodo.7950401
- DOI: 10.5281/zenodo.7950401
- citation: DeepDance: Motion capture data of improvised dance (2019) (Zenodo 7950401, v2.0), doi 10.5281/zenodo.7950401
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 2 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_deepdance_qtm): 539 3D pose records / 30 subjects / 8.98 h at native rates (240 Hz x 523, 250 Hz x 16); measured body axis +z x 539; 0 calibration or static trials skipped, 1 refused or unreadable, 0 with a joint unresolved in that file, 0 with joint samples beyond 8 torso lengths of the pelvis masked and 1 with samples beyond 1 km masked (labelling or export errors of the source); 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 6 / 6 / 6 / 6 / 6; no subject in two folds
- sampling rate per file: 240 Hz x 523, 250 Hz x 16 (records of the canonical build; per-sample fps, never resampled); inventory headers: TSV 240 Hz x 524, 250 Hz x 16
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 6 / 6 / 6 / 6 / 6; no subject in two folds
- known issues (2026-11-12):
  - Files named Subject001_* (11) and Subject1_* (16) are both read as subject 1, as the inventory did: one subject_ns, so they never sit on two sides of a split, whether they are one person or two.
  - The marker unit is not written in the TSV: QTM 3D exports are in millimetres, which the head markers near 1.8 m confirm.
  - Not fetched: wav.zip (the music).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (2 files, subjects counted 30).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only deepdance (readers in mocap_readers.py; joint map open_deepdance_qtm in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
