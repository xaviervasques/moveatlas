# PD rest EEG, 149 subjects (OpenNeuro ds004584)

- dataset: pd_rest_eeg_ds004584
- family: eeg  (physical path: datasets/eeg/pd_rest_eeg_ds004584)
- MoveAtlas cells: B2; M6
- population: 100 PD + 49 controls, 64-ch BrainVision, 2 min eyes-open rest
- n_subjects: 149
- signal: 64-ch resting EEG
- license: CC0 (OpenNeuro) ; redistribution: yes
- access: tool: aws s3 sync --no-sign-request s3://openneuro.org/ds004584
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-08-22: 5.5 GB BIDS on disk -> 149 canonical EEG records, one per subject, 63 channels at 500 Hz, ALL channels parsed onto the site vocabulary. 9 of the 149 records are flagged for artifact-level amplitude (p99 above 500 uV, up to ~1700), which in resting EEG is ordinary electrode and movement artifact rather than a scale error; the other 140 sit in a normal range. Reference PZ, read from eeg.json EEGReference, not assumed. One subject (sub-068) carries three extra traces named X/Y/Z with no type and no description: routed to aux and FLAGGED, not guessed as accelerometer
- link: https://openneuro.org/datasets/ds004584
