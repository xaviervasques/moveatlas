# cdystonia (TWSTRS trial scores, hbiostat)

- dataset: cdystonia
- family: auxdata  (physical path: datasets/auxdata/cdystonia)
- MoveAtlas cells: A4; M12
- population: 109 cervical dystonia patients (botulinum-toxin RCT)
- n_subjects: 109
- signal: longitudinal TWSTRS score table (CSV)
- license: free (hbiostat teaching repo) ; redistribution: yes
- access: direct_download (fetch_p2_lot.py --only cdystonia, tower)
- status (2026-08-22): DOWNLOADED 2026-08-22: cdystonia.sav, 4.4 KB. The .csv the registry pointed at is gone from hbiostat (404). CORRECTED 2026-08-28: despite the .sav extension this is NOT SPSS; it is a gzip-compressed R save file (RDX2 magic once decompressed), read in one line with pyreadr.read_r. 631 rows, 109 patients across 9 sites, TWSTRS over 16 weeks, three arms. Aux table, no canonical ingestion
- link: https://hbiostat.org/data/repo/cdystonia.html
- notes: scale-harmonization aux (WBS 1.5 / M12)
