# GaitRec (bilateral GRF, 75k trials)

- dataset: gaitrec
- family: imu  (physical path: datasets/imu/gaitrec)
- MoveAtlas cells: E4; M3
- population: 2,084 musculoskeletal patients (hip/knee/ankle/calcaneus classes) + 211 healthy; longitudinal rehab sessions
- n_subjects: 2,295
- signal: bilateral 3-component GRF + CoP, raw 250 Hz + stance-normalized (CSV)
- license: CC0 (all 23 figshare collection items, verified 2026-08-22) ; redistribution: yes
- access: direct_download (figshare collection; landed via the owner's browser, the only client figshare's defenses accept)
- status (2026-08-22): DOWNLOADED (23/23 files, published md5s verified) AND INGESTED 2026-08-27: 75,732 canonical force records / 2,295 subjects (HC 7,755, calcaneus 13,970, hip 12,748, knee 19,873, ankle 21,386), gaitndd-style totals-only mapping (vertical -> per-foot total in N at native 250 Hz), AP/ML force + COP in per-subject aux shards, the authors' own train/test partition flags carried as attributes while OUR splits stay patient-level. PRO (time-normalized) files deliberately not ingested. Force family validation: no errors. ingest_gaitrec.py
- link: https://doi.org/10.6084/m9.figshare.c.4788012
- citation: Sci Data 2020, doi 10.1038/s41597-020-0481-z
- notes: largest labeled pathological-GRF corpus; E4 antalgic negative-control class
