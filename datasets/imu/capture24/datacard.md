# Capture-24 (free-living wrist accel)

- dataset: capture24
- family: imu  (physical path: datasets/imu/capture24)
- MoveAtlas cells: C1, C3; M2
- population: 151 healthy adults, ~24 h free living each
- n_subjects: 151
- signal: wrist accelerometer 100 Hz + activity annotations
- license: CC BY 4.0 (ORA record licence, verified 2026-08-23) ; redistribution: yes
- access: downloaded
- status (2026-08-22): FULLY INGESTED 2026-08-22: 3,941 canonical records, 151 subjects, 3,883 HOURS. v1 had read only the first 60,000 lines of each subject (10 minutes) and kept 20 windows of 30 s: 3,020 records, 25 hours, i.e. 0.6 percent of a corpus already on disk. Per-subject shards under processed/canonical/, 1-hour records, 48 GB. Units verified per subject rather than assumed: median |acc| runs 0.888 to 1.051 across all 151, so the values are already in g and nothing is rescaled. 0 refusals. Activity annotations are now kept too (v1 discarded them), run-length encoded against the bundled 206-entry label dictionary, plus age band and sex from metadata.csv
- link: https://ora.ox.ac.uk/objects/uuid:99d7c092-d865-4a19-b096-cc16440cd001
- ingestion: ingest_capture24.py (full). LATERALITY IS UNRESOLVED ON PURPOSE: the device is worn on the DOMINANT wrist and handedness is not distributed, so no subject side is knowable. Records keep the wrist_L slot for continuity and carry laterality=unknown with worn_on=dominant_wrist; the slot is NOMINAL, so do not use this source for anything laterality-sensitive. Writing wrist_R instead would be right for the right-handed majority and wrong for the rest. SPLIT FOLDER, do not be fooled: the datacard and raw/ live under datasets/socle/capture24 while the 3,020 canonical records sit in datasets/imu/capture24/processed/. The v2 reorganization moved cards and raw into the new family folders but left processed/ alone on purpose, because manifest paths are load-bearing. Looking only at socle/ shows raw with no output and invites a re-ingestion that would duplicate every record
