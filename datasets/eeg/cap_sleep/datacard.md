# CAP Sleep Database (PhysioNet)

- dataset: cap_sleep
- family: eeg  (physical path: datasets/eeg/cap_sleep)
- MoveAtlas cells: D6 (RBD); M5 chin, M6
- population: 108 polysomnographies incl. 22 RBD, other sleep disorders, controls
- n_subjects: 108
- signal: full PSG: EEG, chin EMG, ECG, EOG (EDF + annotations)
- license: PhysioNet open ; redistribution: yes
- access: direct_download (fetch_p2_lot.py --only cap_sleep --cap-subset rbd,n)
- status (2026-08-22): INGESTED IN FULL 2026-08-24 (Paris session): the whole rbd,n subset, 38 EDF on disk (12.9 GB), 35 canonical EEG records / 35 subjects (22 RBD + 13 normals) / 332 h, plus 4 chin-EMG records to canonical_emg. n13/n14/n15 REFUSED as designed: their headers declare no physical dimension for any channel and C-EEG-4 forbids guessing a scale; costing 3 of 38 is the cheaper error. Unrecognized labels (SX1-SX2 / DX1-DX2, STAT, TAG/THE) stay in aux exactly as surveyed: left/right of an unnamed muscle is not an identification. Validation after ingest: no errors. Ingestion chain: build_canonical_eeg.py --only cap_sleep (EDF reader + sleep-montage parser validated on synthetic EDF; first real batch is the field verification; chin EMG routes to canonical_emg, EOG/ECG to aux, C-EEG-3)
- link: https://physionet.org/content/capslpdb/
- notes: opens the sleep cell; synucleinopathy prodrome; REM-atonia reference
