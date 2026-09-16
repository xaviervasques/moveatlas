# SeizeIT2 (focal epilepsy wearables, OpenNeuro ds005873)

- dataset: seizeit2
- family: eeg  (physical path: datasets/eeg/seizeit2)
- MoveAtlas cells: D1; A2 proxy; M2, M5, M6
- population: 125 focal epilepsy patients, 5 European EMUs, 11,640 h, 886 annotated focal seizures
- n_subjects: 125
- signal: behind-the-ear EEG (2-3 ch) + ECG + deltoid EMG + IMU; 250 Hz (EEG/ECG/EMG), 25 Hz (IMU)
- license: CC0 (verified in dataset_description.json) ; redistribution: yes
- access: tool: aws s3 sync --no-sign-request s3://openneuro.org/ds005873 (fetch_p2_lot.py --only seizeit2 prints it)
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-08-24 (Paris night session): 117.6 GB raw (24,894 files), then 2,850 canonical EEG records / 125 subjects / 11,626 h, 0 refusals, 0 read failures. 883 seizure events landed in the per-frame labels vs 886 in the paper; SETTLED 2026-08-24 by a census of all 2,850 events.tsv: the BIDS release itself carries 883 sz rows (FIA 391 vs paper 393, FA 316 vs 317, FBTC 55 = 55), so the delta is upstream between the paper and the OpenNeuro release, not an ingestion loss. Montages: 1,434 left / 906 right / 510 generalized, matching the README's placement rules. 2,804 deltoid-EMG records went to canonical_emg (46 runs lack the ECG/EMG device, the ~3 percent technical-failure rate the README declares); ECG + acc/gyro kept as aux streams. D1 epilepsy is no longer an empty cell
- link: https://openneuro.org/datasets/ds005873
- citation: doi 10.1038/s41597-025-05580-x
- ingestion: build_canonical_eeg.py --only seizeit2 (BIDS-EDF builder, C-EEG-7 EAR_L/EAR_R bipolar encoding; seizure labels for evaluation only, never pretraining)
- notes: the best paired EEG+EMG+IMU pathology set found (stage B interest)
- known issues (2026-09-17): a screen on 2026-09-16 found 168 of 2,850 EEG records outside 0.5-250 µV, 4 of them flat, and 10 flat deltoid-EMG records; the values are kept as recorded
