# HUBU-FIS finger tapping (video + UPDRS ratings)

- dataset: hubu_fis_fingertap
- family: pose  (physical path: datasets/pose/hubu_fis_fingertap)
- MoveAtlas cells: B2; M1 (video)
- population: PD patients + controls, both hands, standardized MDS-UPDRS finger-tapping; per-clip ratings in fis_diagnostic.csv
- n_subjects: not stated (234 videos)
- signal: 234 videos, 10.8 GB single zip
- license: CC BY 4.0 ; redistribution: yes
- access: direct_download (Zenodo)
- status (2026-08-22): DOWNLOADED 2026-08-22: 10.81 GB, sha256 verified, zip opens cleanly: 234 clips (226 mp4 + 8 MOV) plus fis_diagnostic.csv. Cohort read from that file: 118 subjects, 43 CONTROL and 75 patients, filmed one clip per hand (DCHA right, IZDA left; 116 subjects have both, 2 have one), each clip carrying an MDS-UPDRS finger-tapping score 0-3 (71/99/38/26). 40 of the 118 subjects score DIFFERENTLY on their two hands, which is the asymmetry the task is meant to capture, so the per-hand clips are not interchangeable. SPLIT SAFETY: both hands of a subject must share one subject_ns or the same person lands on both sides. Note 27 CONTROL clips are scored 1 rather than 0, so 'control' is not a synonym for score 0. Video of hands; ratings are labels: eval only (R1). Ingestion needs pose extraction and is not written yet
- link: https://zenodo.org/records/17738775
- notes: bradykinesia video cell; pose extraction pipeline needed after download
