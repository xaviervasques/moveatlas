# Moore et al.: treadmill gait and the effect of mechanical perturbations

- dataset: moore_perturbed_gait
- family: pose  (physical path: datasets/pose/moore_perturbed_gait)
- MoveAtlas cells: C1; M1, M3, M5
- population: 15 healthy adults (subject ids 1 to 17 in the trial meta files; id 0 marks unloaded trials)
- n_subjects: 15
- age: 19-32 y
- signal: D-Flow mocap text export per trial: 47 (full) or 27 (lower) marker trajectories, force plates, EMG and accelerometer analog channels; trial meta YAML
- conditions: healthy; instrumented treadmill walking at nominal speeds, with longitudinal belt perturbations and, in some trials, lateral sway (field condition, nominal_speed_m_s)
- marker set: 'full' set of 47 markers (head, trunk, arms, pelvis, legs) or 'lower' set of 27; D-Flow names (LASIS, LGTRO, LLEK, LSHO, LLEE, LMEE, LLW, LMW...; the lateral malleolus markers are read as LMALL and RMALL)
- license: CC0 1.0 (Zenodo 13030, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only moore_perturbed_gait)
- link: https://doi.org/10.5281/zenodo.13030
- DOI: 10.5281/zenodo.13030
- citation: Moore, Hnat and van den Bogert, An elaborate data set on human gait and the effect of mechanical perturbations (Zenodo, 2014), doi 10.5281/zenodo.13030
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 2 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_moore_dflow): 43 3D pose records / 14 subjects / 7.64 h at native rates (100.01 Hz x 16, 100 Hz x 5, 100.01 Hz x 4, 100.02 Hz x 3, 100.03 Hz x 3, 100.01 Hz x 2, 100 Hz x 2, 100 Hz x 2, 100.03 Hz x 1, 100.04 Hz x 1, 100.04 Hz x 1, 100 Hz x 1, 100.02 Hz x 1, 100.01 Hz x 1); measured body axis +y x 43; 30 calibration or static trials skipped, 3 refused or unreadable, 0 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 3 / 3 / 3 / 3 / 2; no subject in two folds
- sampling rate per file: 100.01 Hz x 16, 100 Hz x 5, 100.01 Hz x 4, 100.02 Hz x 3, 100.03 Hz x 3, 100.01 Hz x 2, 100 Hz x 2, 100 Hz x 2, 100.03 Hz x 1, 100.04 Hz x 1, 100.04 Hz x 1, 100 Hz x 1, 100.02 Hz x 1, 100.01 Hz x 1 (records of the canonical build; per-sample fps, never resampled); inventory headers: TXT 100 Hz x 75, 98 Hz x 1
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 3 / 3 / 3 / 3 / 2; no subject in two folds
- known issues (2026-11-12):
  - The inventory counted 16 subject ids where the survey said 15: id 0 marks the 30 unloaded trials (no person on the treadmill, per their meta notes); they are skipped, which leaves 15 persons.
  - The D-Flow text has no rate field: the rate is measured per record (1 / median TimeStamp step, about 100 Hz) and fps_provenance gives the step range. The steps are irregular; nothing is resampled.
  - The three trials of subject 12 (T049 to T051) carry unlabelled markers (M1 to M47) and are refused: 14 of the 15 persons have records. Labelling them is open.
  - Lower marker set trials have no upper body: neck, head and arm joints are absent and the record keeps scale 1.0 (metres).
  - The two tar.gz were extracted with Python tarfile, filter='data' (extract_log.json).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (2 files, subjects counted 16).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.
Archives extracted on 2026-11-12 after the fetch: extract_log.json.

## Processing

ingest_open_mocap.py --only moore_perturbed_gait (readers in mocap_readers.py; joint map open_moore_dflow in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
