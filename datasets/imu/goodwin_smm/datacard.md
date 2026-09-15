# Goodwin stereotypical motor movements accelerometry (UbiComp 2014)

- dataset: goodwin_smm
- family: imu  (physical path: datasets/imu/goodwin_smm)
- MoveAtlas cells: A5; M2
- population: 6 children/adults with autism, 2 collections 3 years apart (MITes 60 Hz, Wockets 90 Hz), lab + classroom, annotated body-rocking / hand-flapping
- n_subjects: 6
- signal: 3x 3-axis accelerometers (wrists + torso), annotated SMM episodes
- license: NO data licence exists (verified 2026-09-01: the repository's LICENSE files are all third-party MATLAB libraries; the instruction Google Doc, archived at instruction_doc_20260901.txt, asks citation only). INTERNAL-ONLY ; redistribution: no
- access: anonymous git clone (bitbucket mhealthresearchgroup)
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-09-01 (owner GO, licence hunted first per instruction; none exists): 67 canonical IMU records / 6 subjects / 25 sessions, wrists + trunk, fs MEASURED per file (~58.8 MITes, ~90.9 Wockets). UNITS MEASURED: MITes calm-window gravity reads 64 counts/g (the instruction doc's +/-2g declaration is wrong by 2x, discrepancy recorded); Wockets calibrated per file from its own gravity (accepted band 80-120 counts/g), 8 files REFUSED as undetermined. 2,000 annotation intervals (Rock/Flap/Flap-Rock) parsed verbatim to processed/annotations/ with the wall-clock vs epoch-ms alignment left explicitly unresolved (offset is not a clean timezone shift; label use gets its own verification). Same six children in both studies: URI- stripped so one person = one subject_ns. INTERNAL-ONLY (mmasd precedent)
- link: https://bitbucket.org/mhealthresearchgroup/stereotypypublicdataset-sourcecodes
