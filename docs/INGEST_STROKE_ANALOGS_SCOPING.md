# Scoping: stroke_gait_vancriekinge EMG + GRF pass (2026-09-02)

Ground truth read from the 737 canonical pose records' analog_labels
(recorded at the 2026-08-28 pose pass exactly for this): 65 distinct
analog label sets, three regimes.

## What the analogs hold

1. **Force plates, homogeneous everywhere**: 4 plates x (Fx,Fy,Fz,
   Mx,My,Mz), labels `Force.Fx1`/`Moment.Mx1` or bare `Fx1`/`Mx1`.
2. **EMG, named muscles** (the majority): `Voltage.RERS`-style or bare
   `RERS`-style. Abbreviations seen: ERS (erector spinae), RF (rectus
   femoris), VL (vastus lateralis), ST (semitendinosus), BF (biceps
   femoris, electrode variants BF1/BF2/BIF1), TA/TIA (tibialis
   anterior), GAS (gastrocnemius); side = leading L/R. Plus
   FootswitchA/B (events, not EMG) and bare `15`/`16` (anonymous).
3. **EMG, anonymous channels** (73 records, mostly one stroke
   sub-cohort): `Voltage.1..16`, `Raw.Pin NN`. NO muscle identity ->
   REFUSED under the named-muscles-never-guessed rule; count them in
   the audit as refused-anonymous.

## The pass to write (ingest_stroke_gait_analogs.py)

- Re-walk the raw zips with ezc3d (read_c3d already returns `ana`
  labels; extend it to return `c["data"]["analogs"]` and
  ANALOG:RATE + ANALOG:UNITS).
- EMG records to datasets/emg/stroke_gait_vancriekinge... NO: keep ONE
  dataset identity (rule: one id, one card). EMG records go to
  datasets/pose/stroke_gait_vancriekinge/processed/canonical_emg/ (the
  per-record layout build_canonical_emg.py uses), source id stays
  stroke_gait_vancriekinge, manifest gains modality=emg rows (the
  multimodal pairing on the statistics page expects exactly this).
- Channel dict per build_canonical_emg contract: {"kind": "emg",
  "muscle": <canonical name>, "side": "L"/"R", "resolved": True};
  explicit alias table ERS/RF/VL/ST/BF/TA/TIA/GAS -> canonical muscle
  names (reuse SEMG_ALIASES vocabulary where the names overlap);
  BF1/BF2 = two electrodes on one muscle, keep both channels with an
  electrode suffix field, same muscle name. Footswitches -> kind
  "aux"; `15`/`16`/anonymous -> refused (not silently dropped:
  audited).
- Units: C3D ANALOG:UNITS usually V for EMG; convert to mV to match
  the contract's unit field; state the scale in the audit.
- **Force plates: DESIGN FIRST, INGEST SECOND.** The canonical force
  contract (build_canonical_force.py make_record) is footstep-pair
  shaped (footL/footR + masks). Mapping 4 plates to feet needs the
  C3D FORCE_PLATFORM corner parameters crossed with the foot marker
  trajectories per trial; anything less is guessing. Write the
  assignment as its own audited step; refuse trials where no plate is
  cleanly struck by one foot.
- Validation: validate_canonical --full must stay at zero errors;
  expected new warnings only of the declared classes, if any.
- After the run: gen_datacards E-entry status update (like the pose
  pass), manifests merged dedup-by-source+modality, site regen chain.

## Expected yield

~600+ EMG-bearing records (737 minus the 73 anonymous minus trials
without EMG channels), 14 muscles nominal per the paper; force pairs
to be counted by the plate-assignment step.
