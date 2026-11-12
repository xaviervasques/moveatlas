# Parkinson's pose estimation dataset (Li/Taati)

- dataset: li_taati
- family: pose  (physical path: datasets/pose/li_taati)
- MoveAtlas cells: B2 + L-DOPA dyskinesia (A7/A4 + E6); M1
- population: ~135 PD patients; UDysRS, UPDRS, CAPSIT scores
- n_subjects: ~135
- signal: 2D joint trajectories (communication, drinking, leg agility) + optical flow (toe tapping); normalized 0-1 coordinates, no raw video, video at 30 frames per second per the data paper (stored as fps in the records, marked nominal in fps_provenance)
- license: CC BY 4.0 ; redistribution: yes
- access: free download (GitHub)
- status (2026-09-29): INGESTED v1: 643 canonical records (communication + drinking + leg_agility); no file of the deposit states a frame rate; the data paper (Li et al. 2018, doi 10.1186/s12984-018-0446-z) states that the videos were captured at 30 frames per second, and the records carry that rate, marked nominal in fps_provenance
- link: https://github.com/limi44/Parkinson-s-Pose-Estimation-Dataset
- ingestion: build_canonical.py (li_taati mapping) + ingest_li_taati.py (leg_agility state suffixes); no script in the tree writes canonical_leg_agility.npz; the frame rate of all 643 records was set by set_stated_fps.py on 2026-09-29
- notes: toe-tapping optical flow deliberately not ingested (different modality)
- known issues (2026-09-28, 2026-09-29): the exports carry no time field and no file of the deposit states a frame rate; the data paper (Li et al. 2018, doi 10.1186/s12984-018-0446-z) states that the videos were captured at 30 frames per second, at 480 x 640 or 540 x 960 pixels, and does not say whether every frame was posed; its own analysis smoothed the trajectories with a Savitzky-Golay filter (order 3, 11 samples), and it does not say whether the released trajectories were smoothed; the 643 records carry the stated rate as fps 30.0 from 2026-09-29, marked nominal in fps_provenance (earlier records stored no rate)
