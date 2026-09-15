# Effect of DBS on parkinsonian tremor (PhysioNet; laser Doppler velocity)

- dataset: tremordb
- family: imu  (physical path: datasets/imu/tremordb)
- MoveAtlas cells: A1; M2-adjacent (velocity aux)
- population: 15 PD with DBS (GPi n=5? / Vim / STN per prefix g/v/s), high- and low-amplitude tremor cohorts, DBS/medication conditions + 15/30/45/60-min post-off washout
- n_subjects: 15 (97 recordings)
- signal: hand tremor VELOCITY by laser Doppler at 100 Hz, one text file per subject per condition (.rit right / .let left), physical units mm/s (m/s converted)
- license: PhysioNet open ; redistribution: yes
- access: downloaded
- status (2026-08-22): RE-EXAMINED AND INGESTED AS AUX 2026-08-22 (was SKIPPED in v1 as 'opaque channels': the .hea comment tables document everything). CLARIFIED 2026-09-01 (owner-confirmed): the ingestion is processed/tremordb_velocity.pkl + subject table + audit, BY DESIGN outside the canonical IMU contract (laser-Doppler velocity, not acc/gyro), so NO canonical manifest rows exist and the harmonization badge correctly reads catalogued
- link: https://physionet.org/content/tremordb/
- ingestion: ingest_tremordb.py (run this session on real data): processed/tremordb_velocity.pkl + subject table + audit. NOT the 9-channel IMU contract (velocity, not acc/gyro): aux asset for A1 severity dynamics under DBS on/off per target
- notes: unique DBS on/off + washout timeline; feeds act-2 flavor and tremor probes
