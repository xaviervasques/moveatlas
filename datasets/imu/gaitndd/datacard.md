# PhysioNet gait in neurodegenerative disease

- dataset: gaitndd
- family: imu  (physical path: datasets/imu/gaitndd)
- MoveAtlas cells: A7 (HD), B2 (PD), C1 (controls), D3 (ALS is pyramidal, not ataxic; the ataxia code was dropped, owner ruling 2026-09-01); M3
- population: 16 controls + 15 PD + 20 Huntington + 13 ALS
- n_subjects: 64
- signal: force-sensitive resistor gait series
- license: ODC-By 1.0 (Open Data Commons Attribution License v1.0, stated on the PhysioNet page, read 2026-09-16) ; redistribution: yes
- access: downloaded
- status (2026-08-22): INGESTED v1 (force contract): 64 records
- link: https://physionet.org/content/gaitndd/
- ingestion: build_canonical_force.py
- known issues (2026-09-17): the force values are the outputs of uncalibrated force-sensitive resistors (about -2 to 1.1), not newtons; records built from 2026-09-17 declare unit unknown and name the calibration, and the values are never rescaled
