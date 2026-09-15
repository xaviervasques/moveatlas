# Canonical EEG: design note

Companion to `configs/canonical_eeg.yaml`. Date: 2026-08-22. Status: draft for the G2
review (WBS 1.4). Builder: `build_canonical_eeg.py` (multimodal_fog path implemented and
tested on real sample files; EDF reader written with hard assertions, verified on the
first real CAP/TUH ingestion).

## The montage is the contract's center of gravity

Across our four sources the same physical site appears as: FP1 against an unknown common
reference (multimodal_fog), 'EEG FP1-REF' or 'EEG FP1-LE' (TUH), 'F4-C4' bipolar pairs
(CAP sleep montages), and behind-the-ear wearable channels that are not 10-20 sites at
all (SeizeIT2). Two clean options existed:

1. Re-reference everything in software to one virtual montage.
2. Store as recorded and make the montage explicit per channel.

Option 2 is chosen (C-EEG-1). Re-referencing needs the full electrode set and the exact
recording reference; when either is wrong the corruption is silent, which is the one
failure mode this program refuses (v1 lesson, multimodal_fog deferral). The encoder
consumes (site, ref) pair embeddings; heterogeneity becomes learnable identity instead
of a preprocessing risk.

## Decisions (C-EEG-1..6, to ratify at G2)

- **C-EEG-1, store as recorded, montage explicit.** Channel = (site, ref) with ref a
  site, AVG, LE or REF_COMMON_UNKNOWN. No software re-referencing, no interpolation.
- **C-EEG-2, modern site names, alias-normalized.** T3/T4/T5/T6 -> T7/T8/P7/P8 at
  ingestion (TUH uses the old names). A1/A2 and M1/M2 stay distinct. Wearable ear sites
  get EAR_L/EAR_R rather than being forced onto the 10-20 grid.
- **C-EEG-3, eeg-only records.** PSG files carry EOG, ECG, chin EMG, respiration. Only
  kind eeg lives in canonical_eeg; chin EMG routes to canonical_emg (submentalis), the
  rest to an aux stream in the same processed dir. All outputs of one EDF share subject,
  task and time base, so the pairing survives the split (and D6 needs exactly that
  EEG + chin-EMG pair for REM-without-atonia).
- **C-EEG-4, units enforced by the file itself.** EDF headers declare per-channel
  physical dimensions; ingestion converts to uV when the header says mV and FAILS
  LOUDLY on anything else. multimodal_fog's uV was amplitude-verified (46-293 max abs).
- **C-EEG-5, native rate, continuous records.** No epoching at ingestion, no
  resampling; sleep corpora at 100-256 Hz and wearables at 250-500 Hz coexist through
  the per-record fps and the continuous-time RoPE clock.
- **C-EEG-6, per-record pkl storage.** One PSG night is ~0.5 GB at contract precision;
  a corpus cannot live in one pickle. Per-record pkls + manifest
  (`datasets/_canonical_eeg_manifest.csv`), same choice as EMG (C-EMG-6).
- **C-EEG-7, behind-the-ear derivations (added 2026-08-23 for SeizeIT2, to ratify at
  G2).** The SensorDot records two bipolar channels whose electrodes all sit on the
  mastoids, in exactly three configurations (surveyed across every synced run):
  same-side left ('BTEleft SD'), same-side right ('BTEright SD'), cross-head
  ('CROSStop SD'). Encoding: a same-side pair is (EAR_L, EAR_L) or (EAR_R, EAR_R),
  meaning BOTH electrodes at that ear, and the cross-head channel is (EAR_L, EAR_R).
  Nothing is mapped onto the 10-20 grid because nothing was recorded there (C-EEG-2).
  Seizure annotations (BIDS events.tsv, ILAE 2017 vocabulary) become a per-frame int8
  label (0 background, 1 seizure, 2 impedance check) plus the verbatim event rows in
  the record; labels are evaluation material and never enter pretraining.

## Scope guard

LFP / ECoG / DBS electrodes are NOT this contract: invasive electrophysiology stays in
`inversion_testbed/` under rule R1 (never in movement pretraining) and gets its own
contract with per-electrode anatomical metadata at phase 2.4. Keeping scalp and
invasive signals in separate contracts is what lets rule R1 stay auditable.

## What the model side gets

Stage A EEG encoder tokens = (channel, time-patch) with (site, ref) identity embeddings
and band-power prediction targets (spec section 5). The multimodal_fog EEG stream is
simultaneously the first stage B paired asset (EEG <-> EMG <-> IMU, 12 patients).

## First runnable paths

1. multimodal_fog (today, from streams_eeg_emg.pkl; tested on real samples; reference
   electrode still to read from the bundled README.docx, channel meaning unaffected).
2. cap_sleep rbd+n subset as soon as it lands (EDF reader + sleep-montage parser).
3. TUH on approval (referential parser ready; corpus cut is a G2 storage decision).
