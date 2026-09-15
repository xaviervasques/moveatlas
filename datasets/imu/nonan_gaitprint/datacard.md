# NONAN GaitPrint (older adults, 16 IMU)

- dataset: nonan_gaitprint
- family: imu  (physical path: datasets/imu/nonan_gaitprint)
- MoveAtlas cells: C3; M2
- population: healthy older adults, 18 x 4-min overground trials over 2 days; SIBLING HUNT RESOLVED 2026-08-28: there are NO sibling articles, article 27815034 carries ALL 41 subjects (44 files, 57.8 GB); the first pass had fetched 10, and the figshare anti-bot penalty box forced the completion through the owner's browser (Download-all bundle, every published md5 verified at extraction). COMPLETE AND RE-INGESTED 2026-08-28: 719 canonical IMU records / 41 subjects / 47.7 h. The true sibling is the separate YOUNG-adults collection (nonan_gaitprint_young, own card)
- n_subjects: 41 (complete)
- age: 56+ y (64.7 +/- 7.5)
- signal: full-body 16-IMU at 200 Hz, raw kinematics + spatiotemporal variables
- license: CC BY 4.0 (figshare item metadata, verified 2026-08-22) ; redistribution: yes
- access: direct_download (figshare; landed via the owner's browser)
- status (2026-08-22): DOWNLOADED (10/10 zips, md5-verified) AND INGESTED 2026-08-27: 180 canonical IMU records / 10 subjects / 12 h at native 200 Hz. Only the RAW sensors enter the grid (head, upper spine -> trunk, pelvis -> lower_back, mG -> g measured ~1 g); the Lower spine sensor has no honest slot and rides in aux with all 16 Noraxon segment streams (vendor fusion outputs). ingest_nonan.py. The young-adults sibling got the owner's go 2026-08-28 and has its own card (nonan_gaitprint_young)
- link: https://doi.org/10.6084/m9.figshare.27815034
- notes: sibling middle-age paper s41597-025-05892-y extends the age axis
