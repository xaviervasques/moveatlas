# Oxford BNDU cervical dystonia STN/thalamic LFP + EEG + neck EMG + ACC

- dataset: oxford_dystonia_lfp
- family: eeg  (physical path: datasets/eeg/oxford_dystonia_lfp)
- MoveAtlas cells: A4; M5 (pathological neck EMG), M6, M7
- population: 7 cervical dystonia patients (12 hemispheres), Boston Vercise leads in STN/ZI/VL thalamus, stimulation ramps
- n_subjects: 7
- signal: LFP + scalp EEG + neck EMG + accelerometer (.mat, 3 zips)
- license: CC BY-SA 4.0 ; redistribution: yes (share-alike)
- access: registration (free MRC data portal account), then direct download
- status (2026-08-22): DOWNLOADED 2026-08-25 via the owner's MRC account, after several browser retries on a contended line: 3 zips, 14.7 GB total, CRC clean (P1,P2 / P3,P4 / P5,P6,P7 with per-hemisphere folders). RULE R1: invasive LFP, so NO movement-pretraining ingestion; joins ds004998 in the phase 2.4 invasive-contract queue. The only open dystonia LFP in existence is now on this disk
- link: https://data.mrc.ox.ac.uk/lfp-dystonia
- citation: Wiest et al. 2022, Mov Disord, doi 10.1002/mds.29302
- notes: the only public dystonia LFP+EMG pairing found; distinct from the Tan/Oxford 2016 PD testbed set. R1 scoping applies
