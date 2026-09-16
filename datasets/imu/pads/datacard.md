# PADS: Parkinson's Disease Smartwatch dataset (PhysioNet)

- dataset: pads
- family: imu  (physical path: datasets/imu/pads)
- MoveAtlas cells: A1, B2, D3 (differential cohorts: ET, atypical parkinsonism, MS; D3 is the nearest cell for the MS arm, owner ruling 2026-09-01); M2
- population: 469 subjects: 276 PD, 79 healthy, 60 other movement disorders, 28 essential tremor, 15 atypical parkinsonism, 11 MS; NMS questionnaires
- n_subjects: 469
- signal: 2 Apple Watch (both wrists), 100 Hz, 11-task battery (Relaxed, StretchHold, LiftHold, HoldWeight, PointFinger, DrinkGlas, CrossArms, TouchIndex, TouchNose, Entrainment...), ~20.5 s each; channels+units self-described per observation (acc g, gyro rad/s)
- license: CC BY-NC-SA 4.0 (Creative Commons Attribution-NonCommercial-ShareAlike 4.0, stated on the PhysioNet page, read 2026-09-16) ; redistribution: yes (non-commercial, share-alike: the copy carries CC BY-NC-SA 4.0)
- access: downloaded (12,689 files, SHA256-verified mirror)
- status (2026-08-22): INGESTED: 10,318 canonical IMU records / 469 subjects (the full run happened; the old 'TOWER RUN PENDING' text was stale until 2026-08-25). v1 had judged the preprocessed/ tree ambiguous; raw/movement/ is fully self-describing
- link: https://physionet.org/content/pads/
- ingestion: ingest_pads.py -> canonical_imu.pkl (one record per wrist, no cross-device resampling) + pads_subject_table.csv + audit. MEASURED CAVEAT: CoreMotion userAcceleration = gravity REMOVED at source (median |acc| ~0.004 g at rest); flagged as acc_content=linear_no_gravity
- notes: rare multi-disorder differential-diagnosis corpus; labels eval-only
