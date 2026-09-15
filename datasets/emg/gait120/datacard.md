# Gait120 (mocap + sEMG, Sci Data 2025)

- dataset: gait120
- family: emg  (physical path: datasets/emg/gait120)
- MoveAtlas cells: C1; M1, M5
- population: 120 healthy adult males, 7 locomotion tasks, 6,882 movement cycles
- n_subjects: 120
- age: 20-59 y (35.4 +/- 12.8)
- signal: full-body optical mocap (.trc/.mot) + sEMG of 12 lower-limb muscles (.mat)
- license: CC BY 4.0 (figshare item metadata, verified 2026-08-22) ; redistribution: yes
- access: direct_download (figshare; landed via the owner's browser)
- status (2026-08-22): MCOS LOCK BROKEN 2026-08-28: the mat-io package decodes the MATLAB 'table' objects scipy cannot, and build_canonical_emg.py --only gait120 emitted 3,432 canonical EMG records (raw 2000 Hz, 12 named right-leg muscles, unit volts stored as canonical mV) from all 120 subjects: 4,125 records, one refusal (S058 slope_ascent trial05, a zero block the source's own trial index miscounts). Barriers case 4 closes with a tooling postscript. COMPLETE 2026-08-28: the deposit's true extent is 12 zips (S001-S120) + demographics + anthropometrics + processing codes, not the 10 zips first fetched; the last 5 files landed via the owner's browser (the figshare throttle blocks the scripted client wholesale), every published md5 verified. MOTIONCAPTURE PASS 2026-09-03: 6,882 canonical 3D pose records / 120 subjects / 7 tasks (per-step TRC segments, 39-marker full-body PiG MARKER set at 100 Hz, zero refusals, 119 static calibrations skipped; surface-marker proxies documented in configs gait120_pig_markers, PELV_C/HEAD_C virtual centroids). gait120 is now a pose+EMG multimodal dataset on the same 120 subjects. The OpenSim joint-angle .mot files ride as per-subject aux shards under processed/angles/ (model-derived, not canonical). ingest_gait120_pose.py
- link: https://doi.org/10.1038/s41597-025-05391-0
- notes: healthy EMG socle; males only (document the bias)
