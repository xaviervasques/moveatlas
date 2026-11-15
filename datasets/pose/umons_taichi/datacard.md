# UMONS-TAICHI: motion capture of Taijiquan gestures across expertise levels (C3D)

- dataset: umons_taichi
- family: pose  (physical path: datasets/pose/umons_taichi)
- MoveAtlas cells: C1; M1
- population: 12 participants of different Taijiquan expertise
- n_subjects: 12
- signal: 3D marker trajectories (68 markers, 179 Hz), C3D; segmentation labels (.lab)
- conditions: healthy; Taijiquan forms (take T<t>C<c>)
- marker set: 68 markers: ISB lower-limb landmarks and clusters, Plug-in Gait head and trunk, arm landmarks
- license: CC BY 4.0 (Zenodo 2784581, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only umons_taichi)
- link: https://doi.org/10.5281/zenodo.2784581
- DOI: 10.1016/j.dib.2018.05.088
- citation: UMONS-TAICHI: A multimodal motion capture dataset of expertise in Taijiquan gestures (Zenodo 2784581); article doi 10.1016/j.dib.2018.05.088
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 2 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_isb_umons): 131 3D pose records / 12 subjects / 7.78 h at native rates (179 Hz x 131); measured body axis +z x 131; 0 calibration or static trials skipped, 0 refused or unreadable, 0 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 3 / 3 / 2 / 2 / 2; no subject in two folds
- sampling rate per file: 179 Hz x 131 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 179 Hz x 131
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 3 / 3 / 2 / 2 / 2; no subject in two folds
- known issues (2026-11-12):
  - The .lab segmentation files are not joined to the records in this pass.
  - Not fetched: the TSV, segmented and Kinect copies.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (2 files, subjects counted 12).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only umons_taichi (readers in mocap_readers.py; joint map open_isb_umons in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
