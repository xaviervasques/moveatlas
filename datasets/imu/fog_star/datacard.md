# FoG-STAR (Zenodo 17838806)

- dataset: fog_star
- family: imu  (physical path: datasets/imu/fog_star)
- MoveAtlas cells: B5; M2
- population: 22 PD OFF-medication (12 h washout), 101 FoG episodes, multi-level labels (FoG y/n; manifestation shuffling/trembling/akinesia; 6 activity classes), dual-neurologist video annotation (ICC 0.80)
- n_subjects: 22
- signal: 4 IMUs (both ankles, lumbar, wrist) at 60 Hz; sensor + clinical CSVs
- license: CC BY 4.0 ; redistribution: yes
- access: direct_download (Zenodo)
- status (2026-08-22): INGESTED: 106 canonical IMU records / 22 subjects (repaired 2026-08-22: validity now derived from the data, sample_valid + dropout_fraction added). Same Zenodo record as the second hunt's 'fog_star_2026' find -> ONE dataset, no duplicate entry (status text was stale until 2026-08-25)
- link: https://zenodo.org/records/17838806
- citation: Sci Data 2026, doi 10.1038/s41597-026-06645-1
- ingestion: INGESTED v1: 106 canonical IMU records (build_canonical_imu.py). DATA-INTEGRITY DEFECT found and REPAIRED 2026-08-23 (owner authorised the re-ingest): 23 of the 106 records, covering 15 of the 22 subjects, carry NaN in channels that channel_mask marks as PRESENT. The bad frames are contiguous sensor dropouts, and in several records a sensor is dead for the ENTIRE recording (845/845, 2465/2465, 1910/1910, 2013/2013, 1342/1342, 3944/3944 frames) while the mask still claims all 4 locations x 6 channels are valid. Up to 75 percent of mask-valid samples in one record are NaN; 3 percent of the dataset overall. A consumer that trusts channel_mask, which is exactly what the contract tells it to do, would train on NaN. REPAIRED by deriving validity from the data itself in make_record, which now holds for every IMU source: a channel with no finite sample anywhere is an absent sensor (masked off and zeroed), a location left with no valid channel is dropped from the record, and a channel that merely drops out for a stretch keeps its place but gains a per-sample sample_valid (T, L) plus a dropout_fraction, so a gap is explicit instead of looking like a limb that stopped moving. Re-ingested: 0 NaN remain, 14 records lost a dead sensor (10 keep 3 locations, 2 keep 2, 2 keep 1) and 5 carry a real dropout, the worst 25.3 percent. The IMU family now validates with zero warnings and zero errors
- notes: manifestation-type labels incl. trembling; eval-only labels
