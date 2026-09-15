# Long-term surface EMG during walking (PhysioNet semg 1.0.1)

- dataset: physionet_semg_walking
- family: emg  (physical path: datasets/emg/physionet_semg_walking)
- MoveAtlas cells: C1; M5
- population: 31 healthy young adults, 5-min barefoot walking
- n_subjects: 31
- signal: sEMG of 10 leg muscles at 2 kHz, 12-bit + footswitch + electrogoniometer (WFDB)
- license: ODC-By 1.0 ; redistribution: yes
- access: direct_download (fetch_p2_lot.py --only semg_walking; 278.5 MB zip verified)
- status (2026-08-22): INGESTED AND VERIFIED 2026-08-22: 31 canonical EMG records, 14/14 channels resolved on every record, 0 unrecognized. The .hea vocabulary is closed and was read off all 31 headers: sensors semg/baso/gonio, sides LT/RT, EMG sites TIB.A LAT.G REC.F HAM LAT.V; footswitches and goniometers are routed to aux. FINDING: S01 and S21 declare mV in their header while their amplitudes are ~1000x the other 29 records (p99 155 mV vs 0.14 mV), so their header unit is wrong and the data is really uV; both are FLAGGED in the audit and deliberately NOT rescaled. Ingestion chain: build_canonical_emg.py --only semg_walking (wfdb reader, self-describing .hea enforced at run time; first real batch = the verification; extend the muscle alias table from the printed channel table)
- link: https://physionet.org/content/semg/1.0.1/
- notes: first socle of the EMG contract (WBS 1.3); preserve native rate
