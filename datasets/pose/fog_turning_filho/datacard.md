# FoG turning-in-place (Filho 2022)

- dataset: fog_turning_filho
- family: pose  (physical path: datasets/pose/fog_turning_filho)
- MoveAtlas cells: B5; M1, M2 (source video and IMU; MoveAtlas holds the IMU only)
- population: 35 PD with FoG (paper: a convenience sample of 35 patients, 16 female and 19 male; PDFEinfo.csv holds PDFE01 to PDFE35); age, disease duration, LEDD, more-affected side
- n_subjects: 35 (corrected 2026-09-24; 50 did not come from the source)
- signal: one Physilog 5 IMU (Gait Up) on the shank of the more affected side at 128 Hz (source files: ACC ML/AP/SI in g, GYR ML/AP/SI in deg/s; the records carry ACC ML/AP/SI and GYR ML/AP) and one Sony camera at 30 Hz filming the lower limbs; turning in place, recorded ON medication, on up to three visits one month apart; MoveAtlas holds the IMU only (106 records: 71 turning recordings of 120 s and 35 standing recordings)
- license: CC BY 4.0 (figshare item 14984667; the API states CC BY 4.0; verified 2026-09-16; an earlier CC0 reading was wrong) ; redistribution: yes
- access: downloaded
- status (2026-09-28): INGESTED v1: 106 canonical IMU records (71 turning-in-place recordings of 120 s from 35 patients and 35 standing recordings, 128 Hz); the source video (Videos.zip, 73 videos) was never part of MoveAtlas, so no pose record exists here and the dataset is not a pose-IMU pair in this corpus
- link: https://doi.org/10.6084/m9.figshare.14984667
- citation: Frontiers in Neuroscience 2022, doi 10.3389/fnins.2022.832463
- library recipe (2026-09-15): `moveatlas.fetch("fog_turning_filho")` (figshare answers programs with a browser challenge; fetch() names the file to save where and accepts it once there) then `moveatlas.ingest("fog_turning_filho")`, which writes the 106 IMU records under THIS path (datasets/pose/fog_turning_filho/processed/), where moveatlas.dataset() looks.
- ingestion (repository builder): build_canonical_imu.py (fog_turning mapping) writes to datasets/imu/fog_turning_filho/processed/; the 106 records on disk and in the published record sit under datasets/pose/fog_turning_filho/processed/canonical_imu.npz, the path the library recipe writes and moveatlas.dataset() reads (checked 2026-09-28)
- notes: link resolved 2026-08-23: the download_data.py file ids 33413717 (IMU.zip) and 31544582 (PDFEinfo.csv) both belong to figshare article 14984667 per api.figshare.com; Videos.zip (5.0 GB, same article) was never downloaded
- known issues (2026-09-28): the records declare the sensor location lower_back, but the single IMU sits on the shank of the more affected side (data paper, Methods; the side per patient is in PDFEinfo.csv); the records leave out two columns of the source IMU files, the third gyroscope axis (GYR SI) and the per-sample freezing flag; that flag and the PDFEinfo episode table are one consensus annotation of the video by two movement disorder specialists, carried to the IMU timeline by a procedure the source does not describe, with no inter-rater agreement reported
