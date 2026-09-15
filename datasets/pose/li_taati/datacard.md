# Parkinson's pose estimation dataset (Li/Taati)

- dataset: li_taati
- family: pose  (physical path: datasets/pose/li_taati)
- MoveAtlas cells: B2 + L-DOPA dyskinesia (A7/A4 + E6); M1
- population: ~135 PD patients; UDysRS, UPDRS, CAPSIT scores
- n_subjects: ~135
- signal: 2D joint trajectories (communication, drinking, leg agility) + optical flow (toe tapping); normalized 0-1 coordinates, no raw video
- license: CC BY 4.0 ; redistribution: yes
- access: free download (GitHub)
- status (2026-08-22): INGESTED v1: 643 canonical records (communication + drinking + leg_agility)
- link: https://github.com/limi44/Parkinson-s-Pose-Estimation-Dataset
- ingestion: build_canonical.py (li_taati mapping) + ingest_li_taati.py (leg_agility state suffixes)
- notes: toe-tapping optical flow deliberately not ingested (different modality)
