# NONAN GaitPrint young adults (16 IMU)

- dataset: nonan_gaitprint_young
- family: imu  (physical path: datasets/imu/nonan_gaitprint_young)
- MoveAtlas cells: C1, C3 (young end of the age axis); M2
- population: healthy young adults, same Noraxon 16-IMU 200 Hz overground protocol as the older cohort, 18 x 4-min trials over 2 days; published as one figshare article per subject (collection 6415061)
- n_subjects: 35
- age: young adults (exact range: read the descriptor at ingestion)
- signal: full-body 16-IMU at 200 Hz, raw kinematics + spatiotemporal variables
- license: CC0 (verified per article on the figshare API, 2026-08-28) ; redistribution: yes
- access: direct_download (figshare collection, one article per subject)
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-08-28 (owner go, genuinely open data line): all 40 files landed via the owner's browser (39 md5-verified; S039.zip has an empty computed_md5 in the API, verified by exact size + zip integrity, sha256 journaled), then ingest_nonan.py --cohort young emitted 620 canonical IMU records / 35 subjects / 41.3 h at native 200 Hz, zero refusals. SEPARATE directory and namespace from the older cohort ON PURPOSE: subject IDs collide (S009/S013/S019 exist in both with different content). Full-corpus validation passed same day: no errors, the 488 known warnings only
- link: https://doi.org/10.6084/m9.figshare.c.6415061
- citation: Sci Data 2023, doi 10.1038/s41597-023-02704-z
- notes: the 'previous database' the older-adults descriptor cites; closes the young end of the C3 gait-aging axis with an identical protocol
