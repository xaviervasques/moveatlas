# Shida et al.: overground walking full-body kinematics and kinetics in Parkinson's disease, ON and OFF medication (C3D)

- dataset: shida_pd_gait
- family: pose  (physical path: datasets/pose/shida_pd_gait)
- MoveAtlas cells: B2, B3, B5 (FoG-Q score and a FoG group per patient); M1, M3, M12
- population: 26 people with Parkinson's disease (PDGinfo.xlsx: age 44-81 y, sex, disease duration, LEDD, Hoehn and Yahr, UPDRS, MoCA, mini-BESTest, FoG-Q per patient), each recorded OFF and ON medication
- n_subjects: 26
- age: 44-81 y
- signal: 3D marker trajectories (44 markers, 150 Hz) and force plates, C3D; Visual3D exports (CSV, MDH, V3S)
- conditions: Parkinson's disease, overground walking, OFF and ON medication (eval-only fields group 'pd' and medication 'on'/'off'); one patient's OFF and ON records share one subject_ns, so they always sit in one fold
- marker set: 44 markers (CLAV, STRN, C7, T10, LSHO/RSHO, elbow and wrist pairs, ASIS, PSIS, GTR, lateral and medial knee and ankle, heel, MT1, MT2, MT5) and 27 virtual points V_* that are empty in the walking trials
- license: CC BY 4.0 (figshare 14896881 v4, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only shida_pd_gait)
- link: https://doi.org/10.6084/m9.figshare.14896881.v4
- DOI: 10.6084/m9.figshare.14896881.v4
- citation: Shida et al., A dataset of overground walking full-body kinematics and kinetics in individuals with Parkinson's disease (figshare, v4), doi 10.6084/m9.figshare.14896881.v4
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 3 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_shida_pd): 887 3D pose records / 26 subjects / 0.93 h at native rates (150 Hz x 887); measured body axis +y x 887; 48 calibration or static trials skipped, 0 refused or unreadable, 0 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 6 / 5 / 5 / 5 / 5; no subject in two folds; PATIENT SOURCE, labels eval-only; likely the same persons as care_pd's BMCLab cohort: evaluation only until a person map settles it
- sampling rate per file: 150 Hz x 887 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 150 Hz x 935
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 6 / 5 / 5 / 5 / 5; no subject in two folds
- known issues (2026-11-12):
  - PATIENTS: clinical labels are evaluation-only, never training inputs (MoveAtlas label rule). The patient table also holds free-text clinical history; nothing of it enters a record.
  - PERSON OVERLAP, NOT SETTLED: CARE-PD (care_pd in MoveAtlas, EVAL in MD_FM) lists Shida among its investigators (MD_FM reports/person_ids/cross_source_name_scan.csv) and holds a BMCLab cohort of 23 subject ids (cross_source_overlap.md). These persons are very likely among the 26 here. Until a person map links the ids (which needs care_pd, not read here), shida_pd_gait takes care_pd's tier: evaluation only, never trained.
  - No head marker: the head joint is absent. Static trials (48) are skipped; two 'Trimmed_' files are kept as their own takes (*_trimmed).
  - Not fetched: 'Gait cycles.zip' (time-normalised cycles derived from the same C3D).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (3 files, subjects counted 26).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only shida_pd_gait (readers in mocap_readers.py; joint map open_shida_pd in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
