# CalMS21 mouse social behavior pose corpus (Caltech)

- dataset: calms21
- family: animal  (physical path: datasets/animal/calms21)
- MoveAtlas cells: animal: healthy mouse pose/behavior socle (6M unlabeled + 1M annotated pose frames)
- population: mouse dyads, resident-intruder assays
- n_subjects: many sessions
- signal: pose estimates + TREBA features + behavior annotations
- license: CC BY 4.0. VERIFIED 2026-09-02 on the CaltechDATA record page in a browser: 'Rights / License: Creative Commons Attribution 4.0 International', record marked Open, DOI 10.22002/D1.1991; the deposit readme carries ZERO rights language, so the record licence governs everything in it. The MIXED CC BY-NC-SA caution came from the project website, not the deposit; retired with evidence ; redistribution: yes (CC BY 4.0)
- access: CaltechDATA direct download (s0vdx-0k302); the 2026-08-22 403s were network/UA-specific, plain curl works from the Mac side
- status (2026-08-22): DOWNLOADED 2026-09-02: the pose corpus WITHOUT the videos - task1_classic_classification.zip 457.4 MB + task1_MARS_features.zip 1.8 GB + task2_annotation_styles.zip 912.1 MB + task3_new_behaviors.zip 556.2 MB + readme + converter script, every file md5-checked against the record page, sha256 journaled. Video zips (28.3 + 74.2 + 3.5 GB) deliberately NOT fetched: the pose socle needs trajectories, not pixels
- link: https://data.caltech.edu/records/s0vdx-0k302
