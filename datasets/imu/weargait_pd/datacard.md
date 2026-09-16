# WearGait-PD (FDA/CDRH, Synapse syn52540892)

- dataset: weargait_pd
- family: imu  (physical path: datasets/imu/weargait_pd)
- MoveAtlas cells: B2, B3, C1 (age-matched controls); M2, M3
- population: 100 PD + 85 age-matched controls, 1,458 gait/balance trials
- n_subjects: 185
- signal: 13 Xsens IMUs (full 9-axis) + Moticon insoles (16 cells/foot) + walkway + video, all 100 Hz
- license: CC BY 4.0 ; redistribution: yes
- access: registration (free Synapse account + click-through)
- status (2026-08-22): downloaded + INGESTED v1: 1,458 IMU records + 1,362 per-foot force totals (insole cell->anatomy layout undocumented: 16-cell mapping deferred)
- link: https://www.synapse.org/Synapse:syn52540892
- ingestion: build_canonical_imu.py + build_canonical_force.py (totals-only)
- notes: richest inertial dataset of the corpus; also a video+IMU+force pair
- known issues (2026-09-17): the source exports gyroscope rates in rad/s and magnetometer values normalized to the local field; records built from 2026-09-17 carry the gyroscope in deg/s, keep the magnetometer as recorded (declared in mag_unit) and mark sensor dropouts in sample_valid instead of writing zeros (earlier records held 20 partly missing accelerometer traces in m/s2 under the unit g)
