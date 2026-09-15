# NHANES accelerometry (CDC, cycle G 2011-2012)

- dataset: nhanes_accel
- family: imu  (physical path: datasets/imu/nhanes_accel)
- MoveAtlas cells: C1, C3 (age-conditioned normative); M2
- population: US general population incl. children and 80+; age via DEMO_G demographics
- n_subjects: thousands
- signal: wrist accelerometry: PAXHD/PAXDAY/PAXHR summaries (+ PAXMIN 7.6 GB, PAX80 raw 80 Hz as deliberate extras)
- license: US public domain ; redistribution: yes
- access: direct_download (fetch_p2_lot.py --only nhanes_accel; exact CDC URLs in registry)
- status (2026-08-22): DOWNLOADED 2026-08-26: the 4 summary files (139 MB) AND PAXMIN_G.xpt (8.1 GB, sha256 logged; the CDC link needed three resumes across two days, mid-stream timeouts are its normal weather). PAX80 raw 80 Hz deliberately not pulled. Aux/bio lane, no canonical ingestion
- link: https://wwwn.cdc.gov/nchs/nhanes/
- notes: population age-normativity at low cost; take only needed variables
