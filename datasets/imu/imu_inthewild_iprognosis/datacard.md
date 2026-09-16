# i-PROGNOSIS in-the-wild smartphone IMU

- dataset: imu_inthewild_iprognosis
- family: imu  (physical path: datasets/imu/imu_inthewild_iprognosis)
- MoveAtlas cells: A1, B2; M2
- population: 31 PD + 14 controls, phone in pocket, daily life
- n_subjects: 45
- signal: smartphone accelerometry (pickle of 45 subjects)
- license: CC BY 4.0 (stated on the source Zenodo record, read through DataCite 2026-09-16) ; redistribution: yes
- access: downloaded
- status (2026-08-22): INGESTED v1: 1,017 records
- link: https://zenodo.org/records/3519213
- ingestion: build_canonical_imu.py (pocket location)
- known issues (2026-09-17): phones sample irregularly (99 to 1000 Hz across devices); fps is each session's median rate from the nanosecond timestamps in records built from 2026-09-17 (earlier records stored a rate near 2e-7 Hz); the acceleration includes gravity
