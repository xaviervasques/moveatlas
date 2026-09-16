# Huntington wrist accelerometry (J-Net)

- dataset: hd_accel_jnet
- family: imu  (physical path: datasets/imu/hd_accel_jnet)
- MoveAtlas cells: A7; M2
- population: 24 Huntington + 10 healthy; TMS, FA, TFC clinical scores
- n_subjects: 34
- signal: wrist accelerometer CSVs
- license: CC BY 4.0 (stated on the source Zenodo record, read through DataCite 2026-09-16) ; redistribution: yes
- access: downloaded
- status (2026-08-22): INGESTED v1: 35 records
- link: https://zenodo.org/records/14384260
- ingestion: build_canonical_imu.py (hd_accel mapping)
- known issues (2026-09-17): the CSV files carry no time column; the 100 Hz rate comes from the deposit's description and is stored in records built from 2026-09-17 (earlier records stored no rate)
