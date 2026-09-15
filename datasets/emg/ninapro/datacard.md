# Ninapro (hand/forearm sEMG)

- dataset: ninapro
- family: emg  (physical path: datasets/emg/ninapro)
- MoveAtlas cells: C1; M5
- population: healthy and amputee subjects, hand movement batteries
- n_subjects: per sub-database
- signal: multi-channel forearm sEMG arrays + hand kinematics
- license: registration; per-database terms ; redistribution: no, DECIDED 2026-08-28: no written licence anywhere on the site; pointer to ninapro.hevs.ch
- access: direct download (the registration wall is gone, verified 2026-08-25)
- status (2026-08-22): DOWNLOADED 2026-08-25: all 67 preprocessed zips, 17.6 GB, sha256 journaled, integrity sampled clean. DB1: 27 subjects, 10 Otto Bock electrodes + Cyberglove. DB2: 40 subjects, 12 Delsys electrodes at 2 kHz. INGESTED 2026-08-26: 201 canonical EMG records / 67 subjects / 64 h (build_canonical_emg.py --only ninapro). DB1 kept as the RMS envelope it is (unit unknown, C-EMG-1); DB2 V converted to mV, p99 0.15-0.20 mV, physiological. restimulus rides as the eval-only label; glove, accelerometer and inclinometer streams in aux. No explicit licence text on the site: cite Atzori 2014, redistribution stays flagged
- link: https://ninapro.hevs.ch/
- notes: distal complement of the EMG socle; electrode arrays map to muscle forearm_array in the EMG contract
