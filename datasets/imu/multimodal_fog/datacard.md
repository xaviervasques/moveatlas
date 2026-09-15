# Multimodal FoG (EEG + EMG + IMU, Mendeley r8gmbtv7w2)

- dataset: multimodal_fog
- family: imu  (physical path: datasets/imu/multimodal_fog)
- MoveAtlas cells: B5; M2, M5, M6
- population: 12 PD patients (ID 008 recorded twice: OFF_1 and OFF_2), 13 experiments, 56 task files, ~3 h 42 total; dense expert FoG labels (2 physicians, video-based)
- n_subjects: 12
- signal: 500 Hz combined stream: 25 EEG (uV, 0.5-100 Hz), 5 EMG/ECG/EOG (per-patient order, block index 2 = EOG), 4 MPU6050 IMU blocks (acc self-calibrated +-4g, gyro counts/131, source low-pass 16 Hz), skin conductance, FoG 0/1 at 500 Hz
- license: CC BY 4.0 (confirmed on the Mendeley record and via DataCite) ; redistribution: yes
- access: ingested
- status (2026-08-22): FULLY INGESTED 2026-08-22 on the local machine: 56 canonical IMU records, 56 canonical EEG records, 56 canonical EMG records, 0 audit warnings. Patient identity, the EMG channel order (C-EMG-1) and the EEG reference are all RESOLVED, see below
- link: https://data.mendeley.com/datasets/r8gmbtv7w2
- ingestion: evidence: docs/multimodal_fog_mapping.md (D-ING-1..6). Patient identity RECOVERED from the Mendeley folder tree via the public API (configs/multimodal_fog_patient_index.csv, 56/56 files matched): subject_ns is the patient p001..p012, and 008's two experiments share that subject so they cannot straddle a split. EMG channel order RESOLVED (C-EMG-1 closed) from the README per-patient table into configs/multimodal_fog_channel_order.csv, keyed by (patient, experiment) because 008-1 and 008-2 differ; 5/5 channels resolved on all 56 records, ECG now explicitly typed and therefore excludable from movement pretraining. An independent QRS-periodicity test on the raw signals agreed with the README table on 16/16 confidently-detected files
- notes: the program's only EEG+EMG+IMU paired asset (stage B). EEG reference RESOLVED: TP9/TP10 mastoid average -> ref LM (contract extended). The old wall-clock grouping is retired: audited against ground truth it split 12 of the 13 experiments across sessions, i.e. it would have leaked nearly every patient; it survives only as a flagged fallback
