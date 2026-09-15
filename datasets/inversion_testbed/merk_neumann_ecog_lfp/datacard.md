# Data card : Merk-Neumann ECoG vs STN-LFP (inversion testbed, PRIMARY)

- Paper : Merk et al. 2022, "Electrocorticography is superior to subthalamic local field
  potentials for movement decoding in Parkinson's disease", eLife 2022;11:e75126.
- Source : Harvard Dataverse, doi:10.7910/DVN/IO2FLM (BIDS iEEG).
- Code (reference) : https://github.com/neuromodulation/ECoG_vs_STN
- Licence : CC0 1.0 (public domain). ~1.44 GB, 537 files.
- Format : BIDS iEEG, BrainVision (.vhdr / .eeg / .vmrk), 73 runs, + .json sidecars,
  channels/events .tsv, electrodes + coordsystem, participants.tsv. 3 ea_ui .mat
  (Lead-DBS electrode-localisation UI files).

## Signals (the pairing that matters)

- MOTOR : continuous grip force (dynamometer), z-scored, recorded simultaneously.
- ELECTROPHYSIOLOGY, same subject, same time window :
  - subthalamic LFP : 3 bipolar STN channels,
  - ECoG : sensorimotor strip, ~9.5 +/- 11 channels per hemisphere.
- Sampling : 30 kHz acquired, resampled to 1 kHz for analysis (BIDS files at 1 kHz).
- Task : Go/No-Go cued grip-force task, randomized inter-trial intervals, 10-25 min/run.
- Scale : 2,685 movements total (244 +/- 149 per patient), 11 PD patients.

## Role in the project

The core of the inversion testbed: motor output (grip force) paired with the subthalamic
circuit's electrophysiology in the same patient at the same instants. Used to test the
INVERSE direction (predict LFP/ECoG spectral + burst features FROM the motor signal),
leave-one-patient-out, against a temporal-permutation null. See `eval/inversion_probe.md`.

## Scope discipline

The LFP/ECoG is the TARGET of a downstream probe. It NEVER enters KineFM pretraining
(Handoff 2 section 2 circularity argument; Handoff 3 section 3.4). Grip force is a scalar
motor signal, NOT whole-body kinematics: this validates the inversion METHOD, not the
dystonia clinical target.

## Status (downloaded + verified 2026-07-16)

Fetched from Dataverse via `download_inversion_merk.py` (gentle, resumable, per-file):
537/537 files, ~1.8 GB on disk (originals; .tsv larger than the ingested .tab). BIDS is
laid out FLAT under raw/ (Dataverse did not preserve subfolders; files keep their
sub-XXX_ prefixes).

Verified from the channels.tsv across all 73 runs:
- subject IDs sub-000 .. sub-015 (16 IDs; the paper analyses 11 patients - some IDs are
  extra/second hemispheres, confirm against participants.tsv before splits).
- channel types: 871 ECOG, 60 SEEG (= STN-LFP: STN_LEFT 36 + STN_RIGHT 24), 292 MISC.
- MOVEMENT (grip force) channels MOV_LEFT / MOV_RIGHT (+ *_CLEAN) in EVERY run (73/73).
- STN-LFP present in 20/73 runs. So the STN+force pairing (core inversion probe) covers
  20 runs; the ECOG+force pairing covers all 73. Units µV.

No canonical contract: the inversion testbed is a separate modality (electrophysiology +
scalar force), out of the pose/IMU/force/silhouette pretraining contracts by design.
