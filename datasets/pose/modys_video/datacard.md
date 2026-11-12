# MODYS-video (dyskinetic cerebral palsy)

- dataset: modys_video
- family: pose  (physical path: datasets/pose/modys_video)
- MoveAtlas cells: A4, A6, A7, D3 (pediatric dyskinetic CP is choreoathetosis; DIS scores athetosis explicitly; D3 covers the spastic component); M1
- population: 34 children and young adults with dyskinetic CP (Zenodo 5638470: 188 videos of 34 children; each child filmed lying and sitting at up to three time points, T0, T3, T12); clinical scoring in data_clinical_scoring.xlsx (column ID is the child, column video the video number)
- n_subjects: 34 (corrected 2026-09-24; 63 was the row count of the variable dictionary README_data_clinical_scoring.xlsx; the canonical subject_ns is the video number, 94 ids for 34 children)
- signal: stick-figure pose video derivatives (Zenodo 5638470)
- license: CC BY 4.0 (stated on the source Zenodo record, read through DataCite 2026-09-16) ; redistribution: yes
- access: downloaded
- status (2026-08-22): INGESTED v1: 94 canonical records
- link: https://zenodo.org/records/5638470
- ingestion: build_canonical_modys.py
- notes: one of very few public dystonia-adjacent movement datasets
