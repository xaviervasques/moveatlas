# Multimodal FoG (Mendeley r8gmbtv7w2): format resolved, evidence and decisions

Date: 2026-08-22. Status: UNBLOCKED (deferred since phase 1 for a risk of mis-mapping).
Tool: `ingest_multimodal_fog.py` (repository root), validated on real samples.
Stake: the program's only paired EEG + EMG + IMU dataset (12 PD patients, ~3 h 42); the
pairing asset for stage B of KineFM v2 (spec section 7) and the first EEG/EMG source of MoveAtlas.

## 1. What blocked it in v1

phase1_remaining.md: "the per-patient task_N.txt is a COMBINED 61-column stream... the value
magnitudes do NOT cleanly align with those offsets (raw gyro counts, a 14-zero block from
disconnected sensors at unexpected positions)". Verdict v1: DEFER.

## 2. The key: the internal README + a signal-by-signal check

The `afcde674__README.docx` of the raw folder documents the filtered format exactly (60 columns,
500 Hz); the file on disk has 61 because the first one is a pandas index. Check made on
2026-08-22 on 3 files of different patients (50,000 rows each):

| block (disk columns) | expected (README) | measured | verdict |
|---|---|---|---|
| 0 | index | increasing integers | OK |
| 1 | timestamp, 500 Hz | HH:MM:SS.mmm, median dt 2.00 ms | OK, exactly 500 Hz |
| 2-26 (25) | EEG uV (FP1...CP6) | max abs 46-293 | OK, EEG range |
| 27-31 (5) | EMG/ECG/EOG, order per patient | max abs 340-6000; column 29 is the weakest everywhere | OK; 29 = IO (EOG) as in the README table |
| 32-38 | LShank acc3+gyro3+NC | IMU counts or zeros | OK |
| 39-45 | RShank same | same | OK |
| 46-52 | Waist same | same | OK |
| 53-59 | Arm acc3+gyro3+SC | counts + 7th column 880-1090 (SC) | OK; the 7th channel of the 3 other blocks is NC (~77, invalid) |
| 60 | FoG label 0/1 | {0,1}; files with 60,000 to 663,952 samples at 1 | OK, dense expert annotation |

The v1 "block of 14 zeros" = the RShank + Waist blocks (7+7) of the patients who wore only
2 units. The position varies because it is PER PATIENT; the ingestion DETECTS the active blocks
per file instead of trusting a fixed position.

## 3. Ingestion decisions (to be ratified, already implemented)

- D-ING-1: location by the documented POSITION of the blocks (LShank -> shank_L, RShank ->
  shank_R, Waist -> lower_back, Arm -> wrist_L), active blocks detected per file.
  Finding to report to the authors: the README says "2 sensors = LEFT shin + wrist", but one
  tested patient has their data in the RShank block. The position is authoritative (checkable),
  the README note is not.
- D-ING-2: acceleration self-calibrated in g by the median gravity norm PER SENSOR
  (measured: ~8,600 counts/g, so an MPU6050 configured at +-4g and not +-2g; the fixed
  assumption of 16,384 would have given g values wrong by a factor of 2). Scale per file
  recorded in the audit.
- D-ING-3: gyroscope divided by 131 (assumption of +-250 dps, the MPU6050 default), NOT
  checkable from the data alone; no consequence for the encoder (robust per-channel
  normalisation at the input), flagged in the audit.
- D-ING-4: patient identity by TIME GROUPING (the tasks of one session follow each other on
  the wall clock; threshold 90 min). Evidence on samples: two different hashes 22 s apart = a
  single patient. Anti-leak policy: when in doubt, MERGE (merging never leaks; splitting a
  patient would). Group report written; expected: ~11 patients, 008 in two experiments
  (README).
- D-ING-5: outputs = canonical_imu.pkl (standard IMU contract, dense FoG labels kept,
  eval/segmentation use only) + streams_eeg_emg.pkl (EEG 25 named channels, EMG/ECG/EOG
  block with the per-patient order still to resolve except EOG, SC, labels): the pairing asset
  of stage B. EEG/EMG NEVER enters the movement pre-training (rule R1/R2 of the v2 spec).
- D-ING-6: source filtering known and accepted: ACC low-pass 16 Hz, EEG 0.5-100 Hz, EMG
  10-500 Hz, notch 50 Hz (README). The ACC of this dataset therefore cannot serve as a
  high-frequency reference; sufficient for FOG (trembling 3-8 Hz).

## 4. Still to do

1. Tower: `python ingest_multimodal_fog.py` on the 56 files (~10-20 min), reread
   patient_grouping_report.csv (check ~11-14 sessions, merge by hand if a group is
   doubtful), then merge the manifest into _canonical_imu_manifest.csv and rerun
   build_catalogue.py. THEN (added 2026-08-22): `python build_canonical_eeg.py --only
   multimodal_fog` and `python build_canonical_emg.py --only multimodal_fog` (contracts WBS 1.3
   and 1.4, tested on the samples of that day).
2. Assign the EMG order per patient (README table, columns 27-31) once the
   session -> patient ID correspondence is established from the counts (11 patients, 008 twice).
   The entry point exists: fill configs/multimodal_fog_channel_order.csv then rerun
   build_canonical_emg.py (C-EMG-1); a clue measured on a sample: the channel of index 3 of the
   block has a kurtosis of 102 (QRS-like peaks), an ECG candidate to confirm from the table.
3. DONE 2026-08-22: configs/canonical_imu.yaml, the multimodal_fog stub replaced by the mapping
   verified above.
4. Report to the authors the README / block position inconsistency (D-ING-1).
5. Read the EEG reference electrode in the README.docx of the raw folder (the canonical_eeg
   records carry REF_COMMON_UNKNOWN meanwhile) and audit over the whole corpus the spectrum of
   the EMG block (on a sample, centroid 3.8-6.3 Hz: the announced 10-500 Hz band is not
   verified).
