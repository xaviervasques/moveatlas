# ClinVar bulk (movement-disorder gene subset)

- dataset: clinvar
- family: bio  (physical path: datasets/bio/clinvar)
- MoveAtlas cells: M9
- population: variant-disease interpretations, millions of records; filter to movement genes (PRKN, LRRK2, GBA1, HTT, TOR1A, THAP1, ATXN*, ...)
- n_subjects: n/a
- signal: variant_summary.txt.gz (~0.5 GB) + optional VCFs
- license: NCBI public data (attribution requested) ; redistribution: yes
- access: direct_download (fetch_p2_lot.py --only clinvar_summary)
- status (2026-08-22): DOWNLOADED 2026-08-26: variant_summary.txt.gz 442 MB, sha256 logged. Movement-gene filtering is downstream work (M9)
- link: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/
