# VIDIMU (daily activities: video pose + IMU)

- dataset: vidimu
- family: socle  (physical path: datasets/socle/vidimu)
- MoveAtlas cells: C1; M1, M2 (paired)
- population: 53 healthy subjects on disk (54 published); 13 daily activities (walks, sit-to-stand, arm tasks)
- n_subjects: 53
- signal: video-derived 3D keypoints (34 landmarks, ~30 fps measured 29.42) for all; 5 orientation-quaternion IMUs (dynamic lower-body or upper-body sets) for 16 subjects, ~208 same-trial pose+IMU pairs
- license: Zenodo open (CC BY 4.0 per record) ; redistribution: yes
- access: direct download (on disk)
- status (2026-08-22): INGESTED 2026-08-22 (this session, container run on full real data): 723 pose records / 53 subjects + 242 quaternion streams (208 paired). TOWER RERUN required to materialize outputs on disk: unzip raw/dataset.zip then python ingest_vidimu.py
- link: https://zenodo.org/records/15075076
- citation: Sci Data 2023, doi 10.1038/s41597-023-02554-9
- ingestion: ingest_vidimu.py -> canonical.pkl (skeleton contract) + streams_pose_imu.pkl (stage B alignment asset; quaternions are NOT the 9-channel IMU contract) + audit + manifest
- notes: one of the two real pose<->IMU pairs of the stage B table
