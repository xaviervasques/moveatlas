# Canonical EMG: design note

Companion to `configs/canonical_emg.yaml`. Date: 2026-08-22. Status: draft for the G2
review (WBS 1.3). Builder: `build_canonical_emg.py` (multimodal_fog path implemented and
tested on real sample files; other sources declared, verified at their first ingestion).

## Why a variable channel table and not a fixed block

The IMU contract could fix a 14-location x 9-channel grid because body-worn inertial
sensing has a stable anatomy of placements. Surface EMG does not: our sources range from
5 mixed EMG/ECG/EOG columns (multimodal_fog), to 10 named leg muscles (semg_walking), to
circumferential forearm arrays where the electrode is a slot, not a muscle (ninapro), to
a single chin channel inside a PSG (CAP). Forcing a grid would either explode (every
muscle x side) or lie (arrays are not muscles). A per-record channel table with a
versioned muscle vocabulary keeps identity explicit and masks trivial.

## Decisions (C-EMG-1..6, to ratify at G2)

- **C-EMG-1, unresolved is a status.** multimodal_fog's 4 non-EOG columns are EMG+ECG in
  a per-patient order we cannot prove yet (README table needs the session -> patient-ID
  correspondence). They are ingested as `kind: unresolved_emg_ecg, resolved: false`:
  usable for label-free SSL and for the stage B paired asset (window-level alignment
  does not need muscle identity), EXCLUDED from any muscle-specific analysis. When
  `configs/multimodal_fog_channel_order.csv` is filled, the builder re-emits resolved
  records. Inventing identities would be the exact v1 mis-map trap.
- **C-EMG-2, signal_kind is first-class.** raw, bandpassed, envelope and rectified EMG
  are different objects; some repositories ship envelopes. Mixing them silently would
  poison the stem. Every record declares its kind; envelope records never mix with raw
  in one batch without the stem being told.
- **C-EMG-3, units honest, not uniform.** Canonical target mV, but a source without a
  documented unit keeps as-recorded values with `unit: unknown` and an audit flag. The
  encoder normalizes per channel (robust stats, like IMU), so scale HONESTY beats scale
  uniformity. No gravity-norm trick exists for EMG; there is no self-calibration to lean
  on, hence no guessing.
- **C-EMG-4, native rate always.** The taxonomy sets EMG >= 1000 Hz as the capture bar
  for myoclonus; the contract stores whatever the source gives (500 Hz fog, 2 kHz semg)
  and never resamples. Same continuous-time clock as every family.
- **C-EMG-5, non-EMG co-recorded channels keep their kind.** ECG, EOG, footswitch,
  goniometer are kept in the record (kind ecg / eog / aux) because they share the time
  base and cost nothing, but only kind emg defines the family. Chin EMG extracted from
  PSG (CAP) lands HERE with muscle submentalis, paired with its canonical_eeg record by
  subject and time base: that pairing is a free stage B asset.
- **C-EMG-6, per-record pkl storage.** gait120 and ninapro arrive in GB; the v1
  single-pickle pattern would not scale. New families use one pkl per record + a
  manifest (`datasets/_canonical_emg_manifest.csv`). v1 families keep their format.

## What the model side gets

A fifth stem for the movement-family encoder (spec section 5): per-channel robust
normalization, muscle+side identity embedding with an unknown bucket, fps-aware
windows on the shared RoPE clock. Whether EMG shares the movement trunk or gets its own
encoder is G2 open question 2; the sample-based statistics in the G2 dossier inform it.

## First runnable paths

1. multimodal_fog (today, from streams_eeg_emg.pkl; tested on real samples).
2. semg_walking as soon as the 278.5 MB zip lands (wfdb reader, self-describing .hea
   verified at run time).
3. cap_sleep chin EMG together with the EEG ingestion of the same EDF files.
