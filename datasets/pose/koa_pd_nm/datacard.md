# KOA-PD-NM (gait video -> SAM3 silhouettes)

- dataset: koa_pd_nm
- family: pose  (physical path: datasets/pose/koa_pd_nm)
- MoveAtlas cells: B2, B3, C1, E4; M4
- population: 50 knee osteoarthritis + 16 PD + 30 healthy; severity grades partition subjects (numbering RESTARTS per severity group: 001_KOA_EL and 001_KOA_MD are different people)
- n_subjects: 96
- signal: frontal/sagittal gait video (2 sequences per subject) -> SAM3 body-outline silhouette timeseries (64-pt contour + 8 shape scalars), 30.3/50 fps native
- license: research only, non-commercial ; redistribution: no (video); derived silhouettes internal
- access: direct download (research use)
- status (2026-08-22): INGESTED v1 (silhouette contract): 190 records / 96 subjects, 111,002 frames, 97.7% detected
- link: https://data.mendeley.com/datasets/44pfnysy89
- ingestion: SAM3 by owner -> build_canonical_silhouette.py; patient key koa_<COHORT>_<SEV>_<num>; sequences 01/02 = same subject, never split
- notes: 1 NM video of 191 not processed by SAM3 (59/60 NM); all 96 subjects covered. Link resolved 2026-08-23 from download_data.py, whose Mendeley public-file URLs all live under dataset id 44pfnysy89
