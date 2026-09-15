# Long-Term Movement Monitoring (PhysioNet)

- dataset: ltmm
- family: imu  (physical path: datasets/imu/ltmm)
- MoveAtlas cells: C3; M2
- population: community-dwelling older adults 65-87 y, 3 days free living plus 1-minute lab walks, fallers vs non-fallers
- n_subjects: 79 distinct ids in the release (42 CO + 37 FL; the paper's 71 is its analysis cohort)
- age: 65-87 y (mean 78.4)
- signal: lower-back 6-channel IMU: v/ml/ap acceleration (g) + yaw/pitch/roll angular velocity (deg/s) at 100 Hz (WFDB, self-describing headers)
- license: ODC-By 1.0 ; redistribution: yes
- access: direct_download (fetch_p2_lot.py --only ltmm)
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-08-25 (Paris session): 22.3 GB zip, then 4,963 canonical IMU records / 79 subjects / 4,874 h, 1-hour segments (capture24 pattern). The headers revealed SIX channels, not the three the abstract suggests: accelerometer AND gyroscope, anatomical axes, mapped per the fog_turning convention (x=ML, y=AP, z=vertical; angular velocity in the slot of the axis it rotates about). A first run split every person into two subject ids because LabWalks files are lowercase (fl037_base vs FL037); caught by the subject count and fixed before any merge was committed. Faller status is a cohort attribute + eval-only label. IMU family validation after merge: no errors
- link: https://physionet.org/content/ltmm/
- ingestion: ingest_ltmm.py (WFDB reader, units enforced per header) -> processed/canonical/<record>.pkl shards + --merge into the IMU manifest
- notes: opens the aging cell C3 at scale: second-largest hour count in the corpus after seizeit2
