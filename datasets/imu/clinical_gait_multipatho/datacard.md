# Clinical gait, multi-pathology 9-axis wearables

- dataset: clinical_gait_multipatho
- family: imu  (physical path: datasets/imu/clinical_gait_multipatho)
- MoveAtlas cells: B2, B3, D3, D4, E4; M2
- population: multi-pathology clinical gait (PD, stroke, neuropathies, orthopedic), 6,780 files
- n_subjects: unresolved from zip (needs extraction count)
- signal: Xsens 9-axis (acc+gyro+mag) at ~100 Hz, 4 sensor sites (feet + shanks)
- license: CC BY 4.0 (figshare item licence, read via api.figshare.com 2026-08-23) ; redistribution: yes
- access: downloaded
- status (2026-08-22): INGESTED v1: 1,356 canonical IMU records
- link: https://doi.org/10.6084/m9.figshare.28806086
- ingestion: build_canonical_imu.py (clinical_gait mapping)
- notes: IDENTITY SETTLED 2026-08-23: this IS the deposit the registry also lists as clinical_gait_2025 (figshare 28806086, 'A Dataset of Clinical Gait Signals with Wearable Sensors from Healthy, Neurological, and Orthopedic Cohorts'). Proof: the cached clinical_gait_2025 download URL is figshare file 53704514 and the md5 of raw/dataset.zip here matches the published md5 e7701e2ee2d8e6164a011f7c264d7649 exactly. The old 'check subject overlap' question dissolves: same record, ingested once, under this id
