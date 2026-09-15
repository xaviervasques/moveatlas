# FoG turning-in-place (Filho 2022)

- dataset: fog_turning_filho
- family: pose  (physical path: datasets/pose/fog_turning_filho)
- MoveAtlas cells: B5; M1, M2 (video + IMU synchronized)
- population: 50 PD (35 with usable synchronized pairs per v1 ingestion); age, disease duration, LEDD, more-affected side
- n_subjects: 50
- signal: video + IMU (ACC ML/AP/SI in g, GYR ML/AP in deg/s) turning protocol
- license: CC0 (figshare item 14984667) ; redistribution: yes
- access: downloaded
- status (2026-08-22): INGESTED v1: 106 + 106 records; one of the two real pose<->IMU pairs on disk (stage B table)
- link: https://doi.org/10.6084/m9.figshare.14984667
- citation: Frontiers in Neuroscience 2022, doi 10.3389/fnins.2022.832463
- library recipe (2026-09-15): `moveatlas.fetch("fog_turning_filho")` (figshare answers programs with a browser challenge; fetch() names the file to save where and accepts it once there) then `moveatlas.ingest("fog_turning_filho")`, which writes the 106 IMU records under THIS path (datasets/pose/fog_turning_filho/processed/), where moveatlas.dataset() looks.
- ingestion (repository builder): build_canonical_imu.py (fog_turning mapping). SPLIT FOLDER, same as capture24: card and raw/ under datasets/pose/fog_turning_filho, the 106 canonical records under datasets/imu/fog_turning_filho/processed/. These two are the only datasets in the repo whose raw and processed sit in different family folders (checked 2026-08-23)
- notes: link resolved 2026-08-23: the download_data.py file ids 33413717 (IMU.zip) and 31544582 (PDFEinfo.csv) both belong to figshare article 14984667 per api.figshare.com; Videos.zip (5.0 GB, same article) was never downloaded
