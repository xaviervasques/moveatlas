# 6-minute walk test across the adult lifespan (single lower-back IMU)

- dataset: sixmwt_lifespan
- family: imu  (physical path: datasets/imu/sixmwt_lifespan)
- MoveAtlas cells: C1, C3 (explicit age conditioning); M2
- population: 60 healthy, 10 per decade, 21-75 y
- n_subjects: 60
- age: 21-75 y, decade bins
- signal: acc+gyro 100 Hz at L5 + 15 gait metrics + events + MATLAB code
- license: CC BY 4.0 ; redistribution: yes
- access: direct_download (figshare collection)
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-08-22: 148.4 MB -> 60 canonical IMU records, one per subject, lower_back, 100 Hz, ~372 s each, 0 refusals. Units were MEASURED, not assumed: the plain median |acc| runs 9.3-13.0 because a 6-minute walk inflates it, so the unit test uses the calm-window estimate (least variable 5 percent of 1 s windows), which reads 9.92-10.08 for all 60, i.e. m/s2 -> g. Gyro is deg/s and passed through. Age and anthropometrics carried; Sex is a MATLAB string object scipy cannot decode from a v5 struct, so it is reported unknown rather than guessed. The authors GaitMetrics are derived features, not signal, and stay in the zip
- link: https://doi.org/10.6084/m9.figshare.c.7954157
- citation: Sci Data 2025, doi 10.1038/s41597-025-06506-3
