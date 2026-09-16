# Full-body mocap gait: 50 stroke + 138 able-bodied (Van Criekinge)

- dataset: stroke_gait_vancriekinge
- family: pose  (physical path: datasets/pose/stroke_gait_vancriekinge)
- MoveAtlas cells: D3; M1, M3, M5 (pathological EMG)
- population: 50 stroke survivors + 138 able-bodied adults across the lifespan
- n_subjects: 188
- age: 19-85 y
- signal: 3D marker trajectories, joint angles, GRF, joint moments/powers + EMG of 14 back/lower-limb muscles (C3D + MAT/XLSX)
- license: CC0 (all 13 figshare collection items, verified 2026-08-22) ; redistribution: yes
- access: direct_download (figshare collection; landed via the owner's browser)
- status (2026-08-22): DOWNLOADED (13/13, md5-verified); RE-INGESTED 2026-08-28: 737 canonical 3D pose records / 188 subjects at native 100 Hz, PiG joint identities established by measured geometry (configs entry pig_vancriekinge). The 2026-08-27 pass had refused 199 C3Ds as marker-only; the census showed 192 of them carry the FULL model outputs under a 'SUBJECTID:' label prefix (geometry re-verified on the prefixed files) and 5 more lack only head/elbow/wrist outputs (those joints NaN-filled, masked invalid). PRIVACY NOTE: the prefixes look like birthdate-based Vicon IDs; they are stripped at ingestion and never propagated, and any raw-zip redistribution must account for them. 2 truly unusable C3Ds stay refused, 49 calibration/unparseable skipped. The MAT/XLSX time-normalized files are derivatives and stay raw. ANALOG PASS 2026-09-03 (ingest_stroke_gait_analogs.py, per the scoping doc): 559 canonical EMG records / 163 subjects (14 named muscles L+R via the ERS/RF/VL/ST/BF/TA/GAS alias table; anonymous Voltage.NN channels REFUSED and audited; AMPLITUDE FLAG on the records: the declared V converts to ~476 mV p99, ~1000x surface-EMG range, i.e. amplifier-output volts with undeclared gain or mislabeled mV - NOT rescaled, electrode-referred scale UNRESOLVED) + 557 canonical force records / 185 subjects (plate-to-foot assignment by ankle proximity to FORCE_PLATFORM centers during the loaded window, ambiguous strikes refused: 179 trials; per-foot |Fz| totals at 1000 Hz; full 24-channel plate arrays under processed/aux_force/). 160 subjects are now POSE+EMG+FORCE tri-modal. Pose validation: no errors. ingest_stroke_gait.py
- link: https://doi.org/10.6084/m9.figshare.c.6503791
- citation: Sci Data 2023, doi 10.1038/s41597-023-02767-y
- notes: hemiparetic/spastic gait WITH pathological EMG: D3 anchor and an EMG contract pathology source
- known issues (2026-09-17): 555 of 559 EMG records carry an amplitude flag: the declared volts convert to about 476 mV at the 99th percentile, about 1000 times the surface-EMG range, and are not rescaled; the 4 other records come from a 7-channel acquisition within range
