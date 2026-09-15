# MEG + STN-LFP + EMG in Parkinson's (OpenNeuro ds004998)

- dataset: pd_meg_stn_lfp_ds004998
- family: eeg  (physical path: datasets/eeg/pd_meg_stn_lfp_ds004998)
- MoveAtlas cells: B1, B2, A1 (PD); M5, M6 (MEG), M7
- population: 20 PD with externalized DBS leads, med ON and OFF; rest, static forearm extension, repetitive fist-clenching
- n_subjects: 20
- signal: 306-ch MEG + STN LFP + EMG + EOG at 2 kHz
- license: CC0 ; redistribution: yes
- access: tool: aws s3 sync --no-sign-request s3://openneuro.org/ds004998
- status (2026-08-22): DOWNLOADED 2026-08-24 (Paris session): 161.8 GB, 641 files, aws sync exit 0 (one overnight interruption by a Windows Update reboot, resumed cleanly; the 5 orphaned temp files were deleted). NO canonical ingestion on purpose: LFP/MEG stays outside the movement-pretraining contracts under rule R1 and gets its own contract at phase 2.4 (scope guard in configs/README_canonical_eeg.md)
- link: https://openneuro.org/datasets/ds004998
- citation: Sci Data 2024, doi 10.1038/s41597-024-03768-1
- notes: strongest post-Merk invasive release; movement-adjacent EMG + LFP pair; R1 scoping applies to the LFP side (never in movement pretraining)
