# -*- coding: utf-8 -*-
"""Generate standardized English datacards + the machine-readable dataset index
+ the license/redistribution matrix for the MoveAtlas data portal.

One entry per dataset in DATA below (source of truth composed 2026-08-22 from the
existing per-set cards, this session's format resolutions, and the dated hunt).
Emits, per entry: datasets/<path>/datacard.md (STANDARD SCHEMA, English), plus
docs/datasets_index.csv and docs/license_matrix.csv.

Cards NOT regenerated here (already English and richer than the schema): cody_1,
cody_2, cody_3, socle/amass, socle/motion_x, socle/ntu_rgbd, inversion_testbed/*.
Their ids still appear in DATA with render=False so the index and license matrix
stay complete.

DO NOT RUN THIS TO REFRESH THE REGISTRY. DATA holds 108 entries; the
registry has grown to 170 rows through the hunts and the closing sweep,
and its prose was rewritten by hand (b69b51e). A full run would emit a
108-row docs/datasets_index.csv and silently drop 62 datasets. Use --dry
to compare, and edit docs/datasets_index.csv directly.

Usage: python gen_datacards.py [--repo PATH] [--dry]
"""
import argparse
import csv
import os

D = "2026-08-22"


def E(id, path, title, cells, population, n, signal, license, redis, access,
      status, link, note="", age="", citation="", ingestion="", render=True,
      family=None):
    return dict(id=id, path=path, title=title, cells=cells,
                population=population, n=n, age=age, signal=signal,
                license=license, redis=redis, access=access, status=status,
                link=link, citation=citation, ingestion=ingestion, note=note,
                render=render, family=family or path.split("/")[0])


DATA = [
# -------------------------------------------------------------- auxdata
E("cdystonia", "auxdata/cdystonia", "cdystonia (TWSTRS trial scores, hbiostat)",
  "A4; M12", "109 cervical dystonia patients (botulinum-toxin RCT)", "109",
  "longitudinal TWSTRS score table (CSV)", "free (hbiostat teaching repo)", "yes",
  "direct_download (fetch_p2_lot.py --only cdystonia, tower)",
  f"DOWNLOADED {D}: cdystonia.sav, 4.4 KB. The .csv the registry pointed "
  "at is gone from hbiostat (404). CORRECTED 2026-08-28: despite the .sav "
  "extension this is NOT SPSS; it is a gzip-compressed R save file (RDX2 "
  "magic once decompressed), read in one line with pyreadr.read_r. 631 "
  "rows, 109 patients across 9 sites, TWSTRS over 16 weeks, three arms. "
  "Aux table, no canonical ingestion", "https://hbiostat.org/data/repo/cdystonia.html",
  note="scale-harmonization aux (WBS 1.5 / M12)"),
E("kaggle_spiral", "auxdata/kaggle_spiral", "NIATS spiral + wave drawings",
  "A1 proxy, B2 proxy; M11", "PD patients + healthy, drawing tests", "408 images (not per-subject)",
  "spiral/wave drawing images", "Kaggle/UCI mirror terms (verify before redistribution)",
  "no, DECIDED 2026-08-28: no written licence found (the Kaggle page is JS-only, the mirror chain unclear); pointer to Kaggle", "downloaded", "raw on disk",
  "https://www.kaggle.com/datasets/kmader/parkinsons-drawings",
  citation="source study: Zham et al., Front. Neurol. 2017, "
           "doi 10.3389/fneur.2017.00435",
  note="images not individuated per subject; aux only. Link resolved 2026-08-23: "
       "raw/parkinsons-drawings.zip matches the Kaggle slug "
       "kmader/parkinsons-drawings (NIATS/UFU spiral+wave images)"),
E("nqmitcsxpd", "auxdata/nqmitcsxpd", "neuroQWERTY MIT-CSXPD (keystroke)",
  "B2 proxy; M11", "PD + controls, natural typing", "~85 published; on-disk count TBD",
  "keystroke hold/flight time series (CSV)", "PhysioNet open", "yes", "downloaded",
  "raw on disk", "https://physionet.org/content/nqmitcsxpd/",
  note="two GT_DataPD CSVs (CS1PD/CS2PD)"),
E("tappy_keystroke", "auxdata/tappy_keystroke", "Tappy keystroke (PhysioNet)",
  "B2 proxy; M11", "PD + controls, home typing", "227 users",
  "keystroke logs (User_*.txt)", "PhysioNet open", "yes", "downloaded",
  "raw on disk", "https://physionet.org/content/tappy/"),
E("uci_parkinson_voix", "auxdata/uci_parkinson_voix", "UCI Parkinson's voice",
  "B2 proxy (hypokinetic dysarthria); M11", "PD + controls, sustained phonation", "31 (195 recordings)",
  "voice feature table", "UCI open", "yes", "downloaded", "raw on disk",
  "https://archive.ics.uci.edu/dataset/174/parkinsons"),
E("ilg_ataxia_tables", "auxdata/ilg_ataxia_tables",
  "Real-life gait in degenerative cerebellar ataxia (Ilg, aggregate tables)",
  "D2; M2 (derived)", "43 degenerative cerebellar ataxia + 35 controls, lab + real life",
  "78", "aggregate step-variability/smoothness tables + SARA (172 KB, Word docs)",
  "CC0 (Dryad)", "yes", "direct_download (Dryad; tower queue)",
  f"DOWNLOADED {D}: 9 .docx tables (INAS + Tab_A..H), CC0 on Dryad. Aggregate step-variability tables, not signal: aux only, no canonical ingestion. Dryad answers 403 to a non-browser user agent, which is why the first attempt failed", "https://datadryad.org/dataset/doi:10.5061/dryad.4tmpg4f62",
  note="reference statistics only, no raw signal; D2 anchor values"),
E("clinical_scales", "auxdata/clinical_scales",
  "NINDS Common Data Elements, motor scales (machine-readable)",
  "M12", "n/a (metadata resource: PD / HD / Friedreich CRF modules)", "n/a",
  "CDE catalog Excel/Word exports of motor assessment item structures",
  "US public resource; MDS-UPDRS/UHDRS full text remain MDS/HSG copyright",
  "no, DECIDED 2026-08-28: the copyrighted scale wording contaminates any bulk copy; pointer to NINDS",
  "direct_download (tower queue)", f"NEW {D} (second hunt): queued",
  "https://commondataelements.ninds.nih.gov/",
  note="label-ontology substrate for M12 harmonization (WBS 1.5)"),
# ------------------------------------------------------------------ eeg
E("cap_sleep", "eeg/cap_sleep", "CAP Sleep Database (PhysioNet)",
  "D6 (RBD); M5 chin, M6", "108 polysomnographies incl. 22 RBD, other sleep disorders, controls",
  "108", "full PSG: EEG, chin EMG, ECG, EOG (EDF + annotations)",
  "PhysioNet open", "yes",
  "direct_download (fetch_p2_lot.py --only cap_sleep --cap-subset rbd,n)",
  "INGESTED IN FULL 2026-08-24 (Paris session): the whole rbd,n subset, 38 EDF "
  "on disk (12.9 GB), 35 canonical EEG records / 35 subjects (22 RBD + 13 "
  "normals) / 332 h, plus 4 chin-EMG records to canonical_emg. n13/n14/n15 "
  "REFUSED as designed: their headers declare no physical dimension for any "
  "channel and C-EEG-4 forbids guessing a scale; costing 3 of 38 is the "
  "cheaper error. Unrecognized labels (SX1-SX2 / DX1-DX2, STAT, TAG/THE) "
  "stay in aux exactly as surveyed: left/right of an unnamed muscle is not an "
  "identification. Validation after ingest: no errors. Ingestion chain: "
  "build_canonical_eeg.py --only cap_sleep (EDF reader + sleep-montage parser "
  "validated on synthetic EDF; first real batch is the field verification; chin "
  "EMG routes to canonical_emg, EOG/ECG to aux, C-EEG-3)",
  "https://physionet.org/content/capslpdb/",
  note="opens the sleep cell; synucleinopathy prodrome; REM-atonia reference"),
E("seizeit2", "eeg/seizeit2", "SeizeIT2 (focal epilepsy wearables, OpenNeuro ds005873)",
  "D1; A2 proxy; M2, M5, M6", "125 focal epilepsy patients, 5 European EMUs, 11,640 h, "
  "886 annotated focal seizures", "125",
  "behind-the-ear EEG (2-3 ch) + ECG + deltoid EMG + IMU; 250 Hz (EEG/ECG/EMG), 25 Hz (IMU)",
  "CC0 (verified in dataset_description.json)", "yes",
  "tool: aws s3 sync --no-sign-request s3://openneuro.org/ds005873 (fetch_p2_lot.py --only seizeit2 prints it)",
  "DOWNLOADED AND INGESTED 2026-08-24 (Paris night session): 117.6 GB raw "
  "(24,894 files), then 2,850 canonical EEG records / 125 subjects / 11,626 h, "
  "0 refusals, 0 read failures. 883 seizure events landed in the per-frame "
  "labels vs 886 in the paper; SETTLED 2026-08-24 by a census of all 2,850 "
  "events.tsv: the BIDS release itself carries 883 sz rows (FIA 391 vs paper "
  "393, FA 316 vs 317, FBTC 55 = 55), so the delta is upstream between the "
  "paper and the OpenNeuro release, not an ingestion loss. Montages: "
  "1,434 left / 906 right / 510 generalized, matching the README's placement "
  "rules. 2,804 deltoid-EMG records went to canonical_emg (46 runs lack the "
  "ECG/EMG device, the ~3 percent technical-failure rate the README declares); "
  "ECG + acc/gyro kept as aux streams. D1 epilepsy is no longer an empty cell",
  "https://openneuro.org/datasets/ds005873",
  citation="doi 10.1038/s41597-025-05580-x",
  ingestion="build_canonical_eeg.py --only seizeit2 (BIDS-EDF builder, C-EEG-7 "
  "EAR_L/EAR_R bipolar encoding; seizure labels for evaluation only, never "
  "pretraining)",
  note="the best paired EEG+EMG+IMU pathology set found (stage B interest)"),
E("tuh_eeg", "eeg/tuh_eeg", "TUH EEG Corpus (Temple University)",
  "M6 socle; D1; A2 (myoclonic events)", "hospital clinical corpus, >10,000 sessions",
  "very large", "clinical EEG, many montages (EDF)",
  "free with signed usage agreement", "no (redistribution prohibited)",
  "registration + signed form, then tower download (plan TB-scale storage)",
  "HUMAN QUEUE: registration filed; awaiting approval",
  "https://isip.piconepress.com/projects/nedc/",
  note="stage A EEG pretraining socle (spec section 5); referential-montage parser ready"),
E("pd_meg_stn_lfp_ds004998", "eeg/pd_meg_stn_lfp_ds004998",
  "MEG + STN-LFP + EMG in Parkinson's (OpenNeuro ds004998)",
  "B1, B2, A1 (PD); M5, M6 (MEG), M7", "20 PD with externalized DBS leads, med ON and OFF; "
  "rest, static forearm extension, repetitive fist-clenching", "20",
  "306-ch MEG + STN LFP + EMG + EOG at 2 kHz", "CC0", "yes",
  "tool: aws s3 sync --no-sign-request s3://openneuro.org/ds004998",
  "DOWNLOADED 2026-08-24 (Paris session): 161.8 GB, 641 files, aws sync exit 0 "
  "(one overnight interruption by a Windows Update reboot, resumed cleanly; "
  "the 5 orphaned temp files were deleted). NO canonical ingestion on purpose: "
  "LFP/MEG stays outside the movement-pretraining contracts under rule R1 and "
  "gets its own contract at phase 2.4 (scope guard in "
  "configs/README_canonical_eeg.md)",
  "https://openneuro.org/datasets/ds004998",
  citation="Sci Data 2024, doi 10.1038/s41597-024-03768-1",
  note="strongest post-Merk invasive release; movement-adjacent EMG + LFP pair; "
       "R1 scoping applies to the LFP side (never in movement pretraining)"),
E("pd_walking_eeg_ds007526", "eeg/pd_walking_eeg_ds007526",
  "PD-EEG rest + treadmill walking (OpenNeuro ds007526)",
  "B2, B5-adjacent; M6", "116 PD + 28 healthy controls; 64-ch EGI; ~4 min rest + "
  "~4 min treadmill walking; MDS-UPDRS, MoCA, LEDD", "144",
  "64-ch scalp EEG during rest and real walking", "CC0 (OpenNeuro)", "yes",
  "tool: aws s3 sync --no-sign-request s3://openneuro.org/ds007526",
  f"DOWNLOADED AND INGESTED {D}: 8.4 GB BIDS on disk -> 277 canonical EEG records from 144 subjects (144 rest + 133 walk), 60 EEG channels at 250 Hz, 0 unrecognized. AMPLITUDE CAVEAT, surfaced by validate_canonical.py: ALL 277 records carry a p99 near 5e4 uV, about 1000x too large for scalp EEG. Chased to the source rather than assumed: the .set files themselves store values with p99 ~2.7e5, mne applies the standard EEGLAB microvolt convention, and the dataset's own channels.tsv also declares uV, so the declaration and the values disagree by three orders of magnitude. The pipeline carries the declaration faithfully and FLAGS every record instead of rescaling on a hunch. Treat this set as SCALE-UNRESOLVED until the authors answer, and do not mix it with other EEG sources in an amplitude-sensitive objective. subject_ns is the BIDS subject, so a person's rest and walk runs share a subject and cannot straddle a split. EEGReference is n/a in the sidecars, so the records honestly carry REF_COMMON_UNKNOWN. EOG1-4 and VREF are labelled type=EEG by the dataset but are routed by NAME to eog and aux",
  "https://openneuro.org/datasets/ds007526",
  note="largest walking-EEG pathology cohort found; upgrade of ds002778"),
E("pd_rest_eeg_ds004584", "eeg/pd_rest_eeg_ds004584",
  "PD rest EEG, 149 subjects (OpenNeuro ds004584)",
  "B2; M6", "100 PD + 49 controls, 64-ch BrainVision, 2 min eyes-open rest", "149",
  "64-ch resting EEG", "CC0 (OpenNeuro)", "yes",
  "tool: aws s3 sync --no-sign-request s3://openneuro.org/ds004584",
  f"DOWNLOADED AND INGESTED {D}: 5.5 GB BIDS on disk -> 149 canonical EEG records, one per subject, 63 channels at 500 Hz, ALL channels parsed onto the site vocabulary. 9 of the 149 records are flagged for artifact-level amplitude (p99 above 500 uV, up to ~1700), which in resting EEG is ordinary electrode and movement artifact rather than a scale error; the other 140 sit in a normal range. Reference PZ, read from eeg.json EEGReference, not assumed. One subject (sub-068) carries three extra traces named X/Y/Z with no type and no description: routed to aux and FLAGGED, not guessed as accelerometer",
  "https://openneuro.org/datasets/ds004584"),
E("oxford_dystonia_lfp", "eeg/oxford_dystonia_lfp",
  "Oxford BNDU cervical dystonia STN/thalamic LFP + EEG + neck EMG + ACC",
  "A4; M5 (pathological neck EMG), M6, M7", "7 cervical dystonia patients "
  "(12 hemispheres), Boston Vercise leads in STN/ZI/VL thalamus, stimulation ramps",
  "7", "LFP + scalp EEG + neck EMG + accelerometer (.mat, 3 zips)",
  "CC BY-SA 4.0", "yes (share-alike)",
  "registration (free MRC data portal account), then direct download",
  "DOWNLOADED 2026-08-25 via the owner's MRC account, after several browser "
  "retries on a contended line: 3 zips, 14.7 GB total, CRC clean (P1,P2 / "
  "P3,P4 / P5,P6,P7 with per-hemisphere folders). RULE R1: invasive LFP, so "
  "NO movement-pretraining ingestion; joins ds004998 in the phase 2.4 "
  "invasive-contract queue. The only open dystonia LFP in existence is now "
  "on this disk",
  "https://data.mrc.ox.ac.uk/lfp-dystonia",
  citation="Wiest et al. 2022, Mov Disord, doi 10.1002/mds.29302",
  note="the only public dystonia LFP+EMG pairing found; distinct from the "
       "Tan/Oxford 2016 PD testbed set. R1 scoping applies"),
E("beijing_sleep_lfp", "eeg/beijing_sleep_lfp",
  "Beijing basal-ganglia sleep LFP (121 patients, NOT public)",
  "D6; M7", "121 patients (PD, dystonia, HD, Tourette, ET), PSG + LFP, 140 nights",
  "121", "sleep-stage-scored polysomnography + DBS-lead LFP",
  "no public repository", "no",
  "application: contact the authors (Jianguo Zhang lab)",
  f"NEW {D} (second hunt): HUMAN QUEUE (author contact letter)",
  "https://www.nature.com/articles/s41746-024-01115-7",
  note="would single-handedly cover D6 sleep + M7 invasive across five disorders; "
       "high-value application"),
# ------------------------------------------------------------------ emg
E("gait120", "emg/gait120", "Gait120 (mocap + sEMG, Sci Data 2025)",
  "C1; M1, M5", "120 healthy adult males, 7 locomotion tasks, 6,882 movement cycles",
  "120", "full-body optical mocap (.trc/.mot) + sEMG of 12 lower-limb muscles (.mat)",
  "CC BY 4.0 (figshare item metadata, verified 2026-08-22)", "yes",
  "direct_download (figshare; landed via the owner's browser)",
  "MCOS LOCK BROKEN 2026-08-28: the mat-io package decodes the MATLAB "
  "'table' objects scipy cannot, and build_canonical_emg.py --only gait120 "
  "emitted 3,432 canonical EMG records (raw 2000 Hz, 12 named right-leg "
  "muscles, unit volts stored as canonical mV) from all 120 subjects: "
  "4,125 records, one refusal (S058 slope_ascent trial05, a zero block the "
  "source's own trial index miscounts). Barriers case 4 closes with a "
  "tooling postscript. COMPLETE 2026-08-28: the deposit's true extent is 12 "
  "zips (S001-S120) + demographics + anthropometrics + processing codes, "
  "not the 10 zips first fetched; the last 5 files landed via the owner's "
  "browser (the figshare throttle blocks the scripted client wholesale), "
  "every published md5 verified. MOTIONCAPTURE PASS 2026-09-03: 6,882 "
  "canonical 3D pose records / 120 subjects / 7 tasks (per-step TRC "
  "segments, 39-marker full-body PiG MARKER set at 100 Hz, zero "
  "refusals, 119 static calibrations skipped; surface-marker proxies "
  "documented in configs gait120_pig_markers, PELV_C/HEAD_C virtual "
  "centroids). gait120 is now a pose+EMG multimodal dataset on the "
  "same 120 subjects. The OpenSim joint-angle .mot files ride as "
  "per-subject aux shards under processed/angles/ (model-derived, "
  "not canonical). ingest_gait120_pose.py",
  "https://doi.org/10.1038/s41597-025-05391-0", age="20-59 y (35.4 +/- 12.8)",
  note="healthy EMG socle; males only (document the bias)"),
E("ninapro", "emg/ninapro", "Ninapro (hand/forearm sEMG)",
  "C1; M5", "healthy and amputee subjects, hand movement batteries", "per sub-database",
  "multi-channel forearm sEMG arrays + hand kinematics",
  "registration; per-database terms", "no, DECIDED 2026-08-28: no written licence anywhere on the site; pointer to ninapro.hevs.ch",
  "direct download (the registration wall is gone, verified 2026-08-25)",
  "DOWNLOADED 2026-08-25: all 67 preprocessed zips, 17.6 GB, sha256 "
  "journaled, integrity sampled clean. DB1: 27 subjects, 10 Otto Bock "
  "electrodes + Cyberglove. DB2: 40 subjects, 12 Delsys electrodes at 2 kHz. "
  "INGESTED 2026-08-26: 201 canonical EMG records / 67 subjects / 64 h "
  "(build_canonical_emg.py --only ninapro). DB1 kept as the RMS envelope it "
  "is (unit unknown, C-EMG-1); DB2 V converted to mV, p99 0.15-0.20 mV, "
  "physiological. restimulus rides as the eval-only label; glove, "
  "accelerometer and inclinometer streams in aux. No explicit licence text "
  "on the site: cite Atzori 2014, redistribution stays flagged",
  "https://ninapro.hevs.ch/",
  note="distal complement of the EMG socle; electrode arrays map to muscle "
       "forearm_array in the EMG contract"),
E("physionet_semg_walking", "emg/physionet_semg_walking",
  "Long-term surface EMG during walking (PhysioNet semg 1.0.1)",
  "C1; M5", "31 healthy young adults, 5-min barefoot walking", "31",
  "sEMG of 10 leg muscles at 2 kHz, 12-bit + footswitch + electrogoniometer (WFDB)",
  "ODC-By 1.0", "yes",
  "direct_download (fetch_p2_lot.py --only semg_walking; 278.5 MB zip verified)",
  f"INGESTED AND VERIFIED {D}: 31 canonical EMG records, 14/14 channels resolved on every record, 0 unrecognized. The .hea vocabulary is closed and was read off all 31 headers: sensors semg/baso/gonio, sides LT/RT, EMG sites TIB.A LAT.G REC.F HAM LAT.V; footswitches and goniometers are routed to aux. FINDING: S01 and S21 declare mV in their header while their amplitudes are ~1000x the other 29 records (p99 155 mV vs 0.14 mV), so their header unit is wrong and the data is really uV; both are FLAGGED in the audit and deliberately NOT rescaled. Ingestion chain: build_canonical_emg.py --only semg_walking "
  "(wfdb reader, self-describing .hea enforced at run time; first real batch = "
  "the verification; extend the muscle alias table from the printed channel table)",
  "https://physionet.org/content/semg/1.0.1/",
  note="first socle of the EMG contract (WBS 1.3); preserve native rate"),
# ------------------------------------------------------------------ imu
E("alameda_tremor", "imu/alameda_tremor", "ALAMEDA wrist tremor features",
  "A1; M2 (derived)", "PD tremor, precomputed features", "11",
  "99 precomputed features per window (CSV)", "Zenodo open", "yes", "downloaded",
  "raw on disk; EXCLUDED from raw-signal ingestion (derived features, "
  "docs/imu_reconnaissance.md)", "https://zenodo.org/records/10782573"),
E("cervical_motion_multiplanar", "imu/cervical_motion_multiplanar",
  "Multi-planar cervical motion (IMU + goniometer, Sci Data 2024)",
  "A4 normative, C1; M2", "14 asymptomatic adults, 504 cervical movements in 3 planes",
  "14", "2 Delsys Trigno Avanti IMUs (quaternion CSVs, 74 Hz) + goniometer gold standard",
  "CC BY 4.0. DISCREPANCY RESOLVED 2026-08-23 and it was ours: the CC BY-NC-ND we had recorded is the licence of the Scientific Data ARTICLE (Nature says \"This article is licensed under CC BY-NC-ND\"), not of the deposited data. The paper Data Records section points at figshare 26935900, whose item licence is CC BY 4.0, and the figshare deposit governs the data. Two different objects, one of which we mislabelled", "yes",
  "direct_download (figshare; fetch_p2_lot.py resolve)",
  f"DOWNLOADED AND INGESTED {D}: 409 MB -> 127 canonical EMG records / 15 subjects, 0 failures. The registry description was wrong: this is a Delsys Avanti export with 2 EMG channels at 1785.7 Hz PLUS unit quaternions at 74.1 Hz (|q| median 1.0000), each channel on its own clock, not 2 IMU + goniometer. Orientation is not acc/gyro so it does NOT enter the IMU contract (vidimu precedent): quaternions go to processed/streams_orientation.pkl. The bundled README documents every column but NEVER states where sensors 1 and 2 were placed, so muscle, side and location stay unknown with resolved=False; read the paper to resolve, do not infer from convention",
  "https://doi.org/10.1038/s41597-024-04351-4", age="38 +/- 13 y",
  note="normative cervical ROM for cervical dystonia comparisons; ND license "
       "may restrict it to evaluation-only use, legal review required"),
E("clinical_gait_multipatho", "imu/clinical_gait_multipatho",
  "Clinical gait, multi-pathology 9-axis wearables",
  "B2, B3, D3, D4, E4; M2", "multi-pathology clinical gait (PD, stroke, neuropathies, "
  "orthopedic), 6,780 files", "unresolved from zip (needs extraction count)",
  "Xsens 9-axis (acc+gyro+mag) at ~100 Hz, 4 sensor sites (feet + shanks)",
  "CC BY 4.0 (figshare item licence, read via api.figshare.com 2026-08-23)", "yes",
  "downloaded",
  "INGESTED v1: 1,356 canonical IMU records",
  "https://doi.org/10.6084/m9.figshare.28806086",
  ingestion="build_canonical_imu.py (clinical_gait mapping)",
  note="IDENTITY SETTLED 2026-08-23: this IS the deposit the registry also lists "
       "as clinical_gait_2025 (figshare 28806086, 'A Dataset of Clinical Gait "
       "Signals with Wearable Sensors from Healthy, Neurological, and Orthopedic "
       "Cohorts'). Proof: the cached clinical_gait_2025 download URL is figshare "
       "file 53704514 and the md5 of raw/dataset.zip here matches the published "
       "md5 e7701e2ee2d8e6164a011f7c264d7649 exactly. The old 'check subject "
       "overlap' question dissolves: same record, ingested once, under this id"),
E("daphnet", "imu/daphnet", "Daphnet Freezing of Gait",
  "B5; M2", "10 PD with FoG, walking protocols", "10",
  "3 triaxial accelerometers (ankle, thigh, trunk) at 64 Hz + FoG annotations",
  "CC BY 4.0", "yes", "direct_download (UCI)", "INGESTED v1: 17 records",
  "https://archive.ics.uci.edu/dataset/245/daphnet+freezing+of+gait",
  ingestion="build_canonical_imu.py (daphnet mapping)"),
E("fog_star", "imu/fog_star", "FoG-STAR (Zenodo 17838806)",
  "B5; M2", "22 PD OFF-medication (12 h washout), 101 FoG episodes, multi-level labels "
  "(FoG y/n; manifestation shuffling/trembling/akinesia; 6 activity classes), "
  "dual-neurologist video annotation (ICC 0.80)", "22",
  "4 IMUs (both ankles, lumbar, wrist) at 60 Hz; sensor + clinical CSVs",
  "CC BY 4.0", "yes", "direct_download (Zenodo)",
  "INGESTED: 106 canonical IMU records / 22 subjects (repaired 2026-08-22: "
  "validity now derived from the data, sample_valid + dropout_fraction added). "
  "Same Zenodo record as the second hunt's 'fog_star_2026' find -> ONE "
  "dataset, no duplicate entry (status text was stale until 2026-08-25)",
  "https://zenodo.org/records/17838806",
  citation="Sci Data 2026, doi 10.1038/s41597-026-06645-1",
  ingestion="INGESTED v1: 106 canonical IMU records (build_canonical_imu.py). DATA-INTEGRITY DEFECT found and REPAIRED 2026-08-23 (owner authorised the re-ingest): 23 of the 106 records, covering 15 of the 22 subjects, carry NaN in channels that channel_mask marks as PRESENT. The bad frames are contiguous sensor dropouts, and in several records a sensor is dead for the ENTIRE recording (845/845, 2465/2465, 1910/1910, 2013/2013, 1342/1342, 3944/3944 frames) while the mask still claims all 4 locations x 6 channels are valid. Up to 75 percent of mask-valid samples in one record are NaN; 3 percent of the dataset overall. A consumer that trusts channel_mask, which is exactly what the contract tells it to do, would train on NaN. REPAIRED by deriving validity from the data itself in make_record, which now holds for every IMU source: a channel with no finite sample anywhere is an absent sensor (masked off and zeroed), a location left with no valid channel is dropped from the record, and a channel that merely drops out for a stretch keeps its place but gains a per-sample sample_valid (T, L) plus a dropout_fraction, so a gap is explicit instead of looking like a limb that stopped moving. Re-ingested: 0 NaN remain, 14 records lost a dead sensor (10 keep 3 locations, 2 keep 2, 2 keep 1) and 5 carry a real dropout, the worst 25.3 percent. The IMU family now validates with zero warnings and zero errors",
  note="manifestation-type labels incl. trembling; eval-only labels"),
E("gaitdb", "imu/gaitdb", "PhysioNet gait in aging and disease",
  "B2, B3, C3; M2 (derived)", "5 young + 5 old + 5 PD", "15",
  "stride-interval series (derived, not raw signal)", "PhysioNet open", "yes",
  "downloaded", "raw on disk; EXCLUDED from raw-signal ingestion (derived)",
  "https://physionet.org/content/gaitdb/"),
E("gaitndd", "imu/gaitndd", "PhysioNet gait in neurodegenerative disease",
  "A7 (HD), B2 (PD), C1 (controls), D3 (ALS is pyramidal, not ataxic; "
  "D2 dropped, owner ruling 2026-09-01); M3", "16 controls + 15 PD + 20 Huntington + 13 ALS",
  "64", "force-sensitive resistor gait series", "PhysioNet open", "yes",
  "downloaded", "INGESTED v1 (force contract): 64 records",
  "https://physionet.org/content/gaitndd/",
  ingestion="build_canonical_force.py"),
E("hd_accel_jnet", "imu/hd_accel_jnet", "Huntington wrist accelerometry (J-Net)",
  "A7; M2", "24 Huntington + 10 healthy; TMS, FA, TFC clinical scores", "34",
  "wrist accelerometer CSVs", "Zenodo open", "yes", "downloaded",
  "INGESTED v1: 35 records", "https://zenodo.org/records/14384260",
  ingestion="build_canonical_imu.py (hd_accel mapping)"),
E("imu_inthewild_iprognosis", "imu/imu_inthewild_iprognosis",
  "i-PROGNOSIS in-the-wild smartphone IMU",
  "A1, B2; M2", "31 PD + 14 controls, phone in pocket, daily life", "45",
  "smartphone accelerometry (pickle of 45 subjects)", "Zenodo open", "yes",
  "downloaded", "INGESTED v1: 1,017 records", "https://zenodo.org/records/3519213",
  ingestion="build_canonical_imu.py (pocket location)"),
E("kaggle_fog", "imu/kaggle_fog", "Kaggle tlVMC Freezing of Gait",
  "B5; M2", "136 unique PD subjects (173 subject-visits); UPDRS-III on/off, NFOGQ",
  "136", "lower-back accelerometer: tdcsfog 128 Hz, defog 100 Hz, daily",
  "Kaggle competition terms", "NO (competition data, redistribution restricted)",
  "Kaggle account download", "INGESTED v1: 926 records",
  "https://www.kaggle.com/competitions/tlvmc-parkinsons-freezing-gait-prediction",
  ingestion="build_canonical_imu.py (kaggle_fog mapping)",
  note="license blocks portal redistribution; usable internally, cite the competition"),
E("ltmm", "imu/ltmm", "Long-Term Movement Monitoring (PhysioNet)",
  "C3; M2", "community-dwelling older adults 65-87 y, 3 days free living plus "
  "1-minute lab walks, fallers vs non-fallers",
  "79 distinct ids in the release (42 CO + 37 FL; the paper's 71 is its "
  "analysis cohort)",
  "lower-back 6-channel IMU: v/ml/ap acceleration (g) + yaw/pitch/roll "
  "angular velocity (deg/s) at 100 Hz (WFDB, self-describing headers)",
  "ODC-By 1.0", "yes",
  "direct_download (fetch_p2_lot.py --only ltmm)",
  "DOWNLOADED AND INGESTED 2026-08-25 (Paris session): 22.3 GB zip, then "
  "4,963 canonical IMU records / 79 subjects / 4,874 h, 1-hour segments "
  "(capture24 pattern). The headers revealed SIX channels, not the three the "
  "abstract suggests: accelerometer AND gyroscope, anatomical axes, mapped "
  "per the fog_turning convention (x=ML, y=AP, z=vertical; angular velocity "
  "in the slot of the axis it rotates about). A first run split every "
  "person into two subject ids because LabWalks files are lowercase "
  "(fl037_base vs FL037); caught by the subject count and fixed before any "
  "merge was committed. Faller status is a cohort attribute + eval-only "
  "label. IMU family validation after merge: no errors",
  "https://physionet.org/content/ltmm/",
  ingestion="ingest_ltmm.py (WFDB reader, units enforced per header) -> "
  "processed/canonical/<record>.pkl shards + --merge into the IMU manifest",
  age="65-87 y (mean 78.4)",
  note="opens the aging cell C3 at scale: second-largest hour count in the "
       "corpus after seizeit2"),
E("monipar", "imu/monipar", "MoniPAR smartwatch PD",
  "A1, B2; M2", "28 PD; Hoehn & Yahr, symptom onset, weekly tests", "28",
  "smartwatch IMU (.mat) + tremor labels", "Zenodo open", "yes", "downloaded",
  "INGESTED v1: 46 records", "https://zenodo.org/records/8104853",
  ingestion="build_canonical_imu.py (monipar mapping)"),
E("multimodal_fog", "imu/multimodal_fog",
  "Multimodal FoG (EEG + EMG + IMU, Mendeley r8gmbtv7w2)",
  "B5; M2, M5, M6", "12 PD patients (ID 008 recorded twice: OFF_1 and OFF_2), "
  "13 experiments, 56 task files, ~3 h 42 total; dense expert FoG labels "
  "(2 physicians, video-based)", "12",
  "500 Hz combined stream: 25 EEG (uV, 0.5-100 Hz), 5 EMG/ECG/EOG (per-patient "
  "order, block index 2 = EOG), 4 MPU6050 IMU blocks (acc self-calibrated +-4g, "
  "gyro counts/131, source low-pass 16 Hz), skin conductance, FoG 0/1 at 500 Hz",
  "CC BY 4.0 (confirmed on the Mendeley record and via DataCite)", "yes", "ingested",
  f"FULLY INGESTED {D} on the local machine: 56 canonical IMU records, 56 canonical "
  "EEG records, 56 canonical EMG records, 0 audit warnings. Patient identity, the "
  "EMG channel order (C-EMG-1) and the EEG reference are all RESOLVED, see below",
  "https://data.mendeley.com/datasets/r8gmbtv7w2",
  ingestion="evidence: docs/multimodal_fog_mapping.md (D-ING-1..6). Patient "
  "identity RECOVERED from the Mendeley folder tree via the public API "
  "(configs/multimodal_fog_patient_index.csv, 56/56 files matched): subject_ns is "
  "the patient p001..p012, and 008's two experiments share that subject so they "
  "cannot straddle a split. EMG channel order RESOLVED (C-EMG-1 closed) from the "
  "README per-patient table into configs/multimodal_fog_channel_order.csv, keyed "
  "by (patient, experiment) because 008-1 and 008-2 differ; 5/5 channels resolved "
  "on all 56 records, ECG now explicitly typed and therefore excludable from "
  "movement pretraining. An independent QRS-periodicity test on the raw signals "
  "agreed with the README table on 16/16 confidently-detected files",
  note="the program's only EEG+EMG+IMU paired asset (stage B). EEG reference "
       "RESOLVED: TP9/TP10 mastoid average -> ref LM (contract extended). The old "
       "wall-clock grouping is retired: audited against ground truth it split 12 "
       "of the 13 experiments across sessions, i.e. it would have leaked nearly "
       "every patient; it survives only as a flagged fallback"),
E("nhanes_accel", "imu/nhanes_accel", "NHANES accelerometry (CDC, cycle G 2011-2012)",
  "C1, C3 (age-conditioned normative); M2", "US general population incl. children "
  "and 80+; age via DEMO_G demographics", "thousands",
  "wrist accelerometry: PAXHD/PAXDAY/PAXHR summaries (+ PAXMIN 7.6 GB, PAX80 raw "
  "80 Hz as deliberate extras)", "US public domain", "yes",
  "direct_download (fetch_p2_lot.py --only nhanes_accel; exact CDC URLs in registry)",
  "DOWNLOADED 2026-08-26: the 4 summary files (139 MB) AND PAXMIN_G.xpt "
  "(8.1 GB, sha256 logged; the CDC link needed three resumes across two "
  "days, mid-stream timeouts are its normal weather). PAX80 raw 80 Hz "
  "deliberately not pulled. Aux/bio lane, no canonical ingestion",
  "https://wwwn.cdc.gov/nchs/nhanes/",
  note="population age-normativity at low cost; take only needed variables"),
E("pads", "imu/pads", "PADS: Parkinson's Disease Smartwatch dataset (PhysioNet)",
  "A1, B2, D3 (differential cohorts: ET, atypical parkinsonism, MS; "
  "D3 is the nearest cell for the MS arm, owner ruling 2026-09-01); M2",
  "469 subjects: 276 PD, 79 healthy, 60 other movement disorders, 28 essential "
  "tremor, 15 atypical parkinsonism, 11 MS; NMS questionnaires", "469",
  "2 Apple Watch (both wrists), 100 Hz, 11-task battery (Relaxed, StretchHold, "
  "LiftHold, HoldWeight, PointFinger, DrinkGlas, CrossArms, TouchIndex, TouchNose, "
  "Entrainment...), ~20.5 s each; channels+units self-described per observation "
  "(acc g, gyro rad/s)", "PhysioNet open", "yes", "downloaded (12,689 files, "
  "SHA256-verified mirror)",
  "INGESTED: 10,318 canonical IMU records / 469 subjects (the full run "
  "happened; the old 'TOWER RUN PENDING' text was stale until 2026-08-25). "
  "v1 had judged the preprocessed/ tree ambiguous; raw/movement/ is fully "
  "self-describing",
  "https://physionet.org/content/pads/",
  ingestion="ingest_pads.py -> canonical_imu.pkl (one record per wrist, no "
  "cross-device resampling) + pads_subject_table.csv + audit. MEASURED CAVEAT: "
  "CoreMotion userAcceleration = gravity REMOVED at source (median |acc| ~0.004 g "
  "at rest); flagged as acc_content=linear_no_gravity",
  note="rare multi-disorder differential-diagnosis corpus; labels eval-only"),
E("pd_biostamprc21", "imu/pd_biostamprc21", "PD-BioStampRC21 (5-sensor IMU)",
  "B2, B3; M2", "34 PD", "34", "5 BioStamp RC sensors, 10.8 GB",
  "IEEE DataPort open access (no explicit reuse licence shown on the page, checked 2026-08-28)", "no, DECIDED: pointer to IEEE DataPort", "registration (free IEEE account)",
  "DOWNLOADED 2026-08-25 (owner's IEEE account) AND INGESTED 2026-08-26: "
  "7,682 canonical IMU records / 34 subjects / 7,658 sensor-hours, 1-hour "
  "segments, fs measured 31.250 Hz on every stream, gravity 0.99-1.04 g. "
  "Forearm sensors sit in PROXY wrist slots (the grid has no forearm; "
  "placement carried verbatim, G2 owns any grid change). UPDRS windows and "
  "medication ON/OFF kept per subject under processed/annotations/, eval "
  "only. ingest_pd_biostamprc21.py",
  "https://dx.doi.org/10.21227/g2g8-1503"),
E("physionet_gaitpdb", "imu/physionet_gaitpdb", "PhysioNet gaitpdb (Hausdorff)",
  "B2, B3; M3", "~93 PD + ~73 controls (165 on-disk codes)", "165",
  "vertical ground-reaction force, 8 sensors per foot, 100 Hz", "PhysioNet open",
  "yes", "downloaded", "INGESTED v1 (force contract): 306 records",
  "https://physionet.org/content/gaitpdb/", ingestion="build_canonical_force.py"),
E("tremordb", "imu/tremordb",
  "Effect of DBS on parkinsonian tremor (PhysioNet; laser Doppler velocity)",
  "A1; M2-adjacent (velocity aux)", "15 PD with DBS (GPi n=5? / Vim / STN per "
  "prefix g/v/s), high- and low-amplitude tremor cohorts, DBS/medication "
  "conditions + 15/30/45/60-min post-off washout", "15 (97 recordings)",
  "hand tremor VELOCITY by laser Doppler at 100 Hz, one text file per subject "
  "per condition (.rit right / .let left), physical units mm/s (m/s converted)",
  "PhysioNet open", "yes", "downloaded",
  f"RE-EXAMINED AND INGESTED AS AUX {D} (was SKIPPED in v1 as 'opaque "
  "channels': the .hea comment tables document everything). CLARIFIED "
  "2026-09-01 (owner-confirmed): the ingestion is processed/"
  "tremordb_velocity.pkl + subject table + audit, BY DESIGN outside the "
  "canonical IMU contract (laser-Doppler velocity, not acc/gyro), so NO "
  "canonical manifest rows exist and the harmonization badge correctly "
  "reads catalogued",
  "https://physionet.org/content/tremordb/",
  ingestion="ingest_tremordb.py (run this session on real data): "
  "processed/tremordb_velocity.pkl + subject table + audit. NOT the 9-channel "
  "IMU contract (velocity, not acc/gyro): aux asset for A1 severity dynamics "
  "under DBS on/off per target",
  note="unique DBS on/off + washout timeline; feeds act-2 flavor and tremor probes"),
E("weargait_pd", "imu/weargait_pd", "WearGait-PD (FDA/CDRH, Synapse syn52540892)",
  "B2, B3, C1 (age-matched controls); M2, M3", "100 PD + 85 age-matched controls, 1,458 gait/balance trials",
  "185", "13 Xsens IMUs (full 9-axis) + Moticon insoles (16 cells/foot) + "
  "walkway + video, all 100 Hz",
  "CC BY 4.0", "yes", "registration (free Synapse account + click-through)",
  "downloaded + INGESTED v1: 1,458 IMU records + 1,362 per-foot force totals "
  "(insole cell->anatomy layout undocumented: 16-cell mapping deferred)",
  "https://www.synapse.org/Synapse:syn52540892",
  ingestion="build_canonical_imu.py + build_canonical_force.py (totals-only)",
  note="richest inertial dataset of the corpus; also a video+IMU+force pair"),
E("sixmwt_lifespan", "imu/sixmwt_lifespan",
  "6-minute walk test across the adult lifespan (single lower-back IMU)",
  "C1, C3 (explicit age conditioning); M2", "60 healthy, 10 per decade, 21-75 y",
  "60", "acc+gyro 100 Hz at L5 + 15 gait metrics + events + MATLAB code",
  "CC BY 4.0", "yes", "direct_download (figshare collection)",
  f"DOWNLOADED AND INGESTED {D}: 148.4 MB -> 60 canonical IMU records, one per subject, lower_back, 100 Hz, ~372 s each, 0 refusals. Units were MEASURED, not assumed: the plain median |acc| runs 9.3-13.0 because a 6-minute walk inflates it, so the unit test uses the calm-window estimate (least variable 5 percent of 1 s windows), which reads 9.92-10.08 for all 60, i.e. m/s2 -> g. Gyro is deg/s and passed through. Age and anthropometrics carried; Sex is a MATLAB string object scipy cannot decode from a v5 struct, so it is reported unknown rather than guessed. The authors GaitMetrics are derived features, not signal, and stay in the zip",
  "https://doi.org/10.6084/m9.figshare.c.7954157",
  citation="Sci Data 2025, doi 10.1038/s41597-025-06506-3", age="21-75 y, decade bins"),
E("nonan_gaitprint", "imu/nonan_gaitprint", "NONAN GaitPrint (older adults, 16 IMU)",
  "C3; M2", "healthy older adults, 18 x 4-min overground trials over 2 days; "
  "SIBLING HUNT RESOLVED 2026-08-28: there are NO sibling articles, article "
  "27815034 carries ALL 41 subjects (44 files, 57.8 GB); the first pass had "
  "fetched 10, and the figshare anti-bot penalty box forced the completion "
  "through the owner's browser (Download-all bundle, every published md5 "
  "verified at extraction). COMPLETE AND RE-INGESTED 2026-08-28: 719 "
  "canonical IMU records / 41 subjects / 47.7 h. The true sibling is the "
  "separate YOUNG-adults collection (nonan_gaitprint_young, own card)",
  "41 (complete)",
  "full-body 16-IMU at 200 Hz, raw kinematics + spatiotemporal variables",
  "CC BY 4.0 (figshare item metadata, verified 2026-08-22)", "yes",
  "direct_download (figshare; landed via the owner's browser)",
  "DOWNLOADED (10/10 zips, md5-verified) AND INGESTED 2026-08-27: 180 "
  "canonical IMU records / 10 subjects / 12 h at native 200 Hz. Only the "
  "RAW sensors enter the grid (head, upper spine -> trunk, pelvis -> "
  "lower_back, mG -> g measured ~1 g); the Lower spine sensor has no honest "
  "slot and rides in aux with all 16 Noraxon segment streams (vendor fusion "
  "outputs). ingest_nonan.py. The young-adults sibling got the owner's go "
  "2026-08-28 and has its own card (nonan_gaitprint_young)",
  "https://doi.org/10.6084/m9.figshare.27815034", age="56+ y (64.7 +/- 7.5)",
  note="sibling middle-age paper s41597-025-05892-y extends the age axis"),
E("nonan_gaitprint_young", "imu/nonan_gaitprint_young",
  "NONAN GaitPrint young adults (16 IMU)",
  "C1, C3 (young end of the age axis); M2", "healthy young adults, same "
  "Noraxon 16-IMU 200 Hz overground protocol as the older cohort, 18 x "
  "4-min trials over 2 days; published as one figshare article per subject "
  "(collection 6415061)", "35",
  "full-body 16-IMU at 200 Hz, raw kinematics + spatiotemporal variables",
  "CC0 (verified per article on the figshare API, 2026-08-28)", "yes",
  "direct_download (figshare collection, one article per subject)",
  "DOWNLOADED AND INGESTED 2026-08-28 (owner go, genuinely open data "
  "line): all 40 files landed via the owner's browser (39 md5-verified; "
  "S039.zip has an empty computed_md5 in the API, verified by exact size "
  "+ zip integrity, sha256 journaled), then ingest_nonan.py --cohort "
  "young emitted 620 canonical IMU records / 35 subjects / 41.3 h at "
  "native 200 Hz, zero refusals. SEPARATE directory and namespace from "
  "the older cohort ON PURPOSE: subject IDs collide (S009/S013/S019 "
  "exist in both with different content). Full-corpus validation passed "
  "same day: no errors, the 488 known warnings only",
  "https://doi.org/10.6084/m9.figshare.c.6415061",
  age="young adults (exact range: read the descriptor at ingestion)",
  citation="Sci Data 2023, doi 10.1038/s41597-023-02704-z",
  note="the 'previous database' the older-adults descriptor cites; closes "
       "the young end of the C3 gait-aging axis with an identical protocol"),
E("gaitrec", "imu/gaitrec", "GaitRec (bilateral GRF, 75k trials)",
  "E4; M3", "2,084 musculoskeletal patients (hip/knee/ankle/calcaneus classes) + "
  "211 healthy; longitudinal rehab sessions", "2,295",
  "bilateral 3-component GRF + CoP, raw 250 Hz + stance-normalized (CSV)",
  "CC0 (all 23 figshare collection items, verified 2026-08-22)", "yes",
  "direct_download (figshare collection; landed via the owner's browser, "
  "the only client figshare's defenses accept)",
  "DOWNLOADED (23/23 files, published md5s verified) AND INGESTED "
  "2026-08-27: 75,732 canonical force records / 2,295 subjects (HC 7,755, "
  "calcaneus 13,970, hip 12,748, knee 19,873, ankle 21,386), gaitndd-style "
  "totals-only mapping (vertical -> per-foot total in N at native 250 Hz), "
  "AP/ML force + COP in per-subject aux shards, the authors' own "
  "train/test partition flags carried as attributes while OUR splits stay "
  "patient-level. PRO (time-normalized) files deliberately not ingested. "
  "Force family validation: no errors. ingest_gaitrec.py",
  "https://doi.org/10.6084/m9.figshare.c.4788012",
  citation="Sci Data 2020, doi 10.1038/s41597-020-0481-z",
  note="largest labeled pathological-GRF corpus; E4 antalgic negative-control class"),
E("clinical_gait_signals_2025", "imu/clinical_gait_signals_2025",
  "Clinical gait signals with wearables (2025; healthy/neuro/orthopedic)",
  "D3 (stroke), D4+E6 (chemo-induced neuropathy), E4; M2",
  "260 subjects: 73 healthy, 143 neurological (PD, stroke, CIPN, radiation "
  "leukoencephalopathy), 44 orthopedic; UPDRS, Fugl-Meyer, TNS, WOMAC", "260",
  "4 IMUs (head, L4/L5, both feet) at 100 Hz, 1,356 trials, >11 h",
  "CC BY 4.0. DISCREPANCY RESOLVED 2026-08-23, same cause as cervical_motion: the CC BY-NC-ND belongs to the Scientific Data ARTICLE, not to the figshare deposit 28806086, whose item licence is CC BY 4.0 and which is what governs the data", "yes",
  "direct_download (figshare)",
  "SATISFIED 2026-08-23, nothing to fetch: this record IS "
  "clinical_gait_multipatho, already on disk and ingested (1,356 canonical IMU "
  "records). Proof: the resolved download URL is figshare file 53704514 and the "
  "md5 of clinical_gait_multipatho/raw/dataset.zip matches the published md5 "
  "e7701e2ee2d8e6164a011f7c264d7649 exactly. Both flags dissolve: the licence is "
  "CC BY 4.0 (item licence via api.figshare.com) and the 'overlap' is identity",
  "https://doi.org/10.6084/m9.figshare.28806086",
  citation="Sci Data 2025, doi 10.1038/s41597-025-05959-w"),
E("osdb", "imu/osdb", "OpenSeizureDatabase (smartwatch seizure movement)",
  "D1; M2", "crowdsourced OpenSeizureDetector users; seizure / seizure-like / "
  "false-alarm labeled events", "not stated",
  "wrist 3-axis accelerometer (+HR) JSON event snippets, ~25 Hz",
  "custom CC-Share-Alike variant + publish-back obligation", "no",
  "application: email osdb@openseizuredetector.org.uk (data in private repo)",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the email-gated access stays "
  "closed under the standing no-emails decision; not reopened",
  "https://github.com/OpenSeizureDetector/OpenSeizureDatabase",
  note="toolkit code public (GPL-3); only real-world wearable seizure corpus found"),
# ------------------------------------------------------------------ pose
E("ataxie_kinect_dib", "pose/ataxie_kinect_dib", "Ataxia gait Kinect (Summa 2020)",
  "D2; M1 (table only on disk)", "ataxia patients + controls, SARA-scored", "51",
  "clinical table (supplementary mmc1.xlsx); Kinect skeleton signal NOT downloaded",
  "Data in Brief (Elsevier supplementary; no explicit data licence)", "no, DECIDED 2026-08-28: pointer to the article", "downloaded (table only)",
  "raw table on disk; skeleton data never fetched (source availability unclear)",
  "https://doi.org/10.1016/j.dib.2020.106307",
  note="subject-level SARA + diagnosis: subject-table source for D2"),
E("babypose", "pose/babypose", "babyPose (preterm infants, NICU depth video)",
  "C2; M1", "16 preterm infants in incubator, limb-joint annotated depth video",
  "16", "depth video, 16,000 annotated frames", "on request from the VRAI lab",
  "no (until granted)", "application: email the lab",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the email-gated access stays "
  "closed under the standing no-emails decision; not reopened",
  "https://vrai.dii.univpm.it/content/babypose-dataset",
  age="preterm neonates",
  note="first C2 candidate; will require the infant-skeleton contract (WBS 1.3)"),
E("care_pd", "pose/care_pd", "CARE-PD (9-cohort PD gait, canonicalized SMPL)",
  "B2, B3; M1", "362 subjects, 9 cohorts, 8 sites; UPDRS_GAIT labels on 4 cohorts "
  "(3DGait, BMCLab, PD-GaM, T-SDU-PD)", "362",
  "3D positions derived from canonicalized SMPL (24 joints), 25-150 fps per "
  "cohort, ~3.72 M frames, 8,476 walks",
  "CC BY-NC-ND 4.0, SETTLED 2026-08-25 by the official NeurIPS 2025 site "
  "(neurips2025.care-pd.ca): 'Creative Commons Attribution-NonCommercial-"
  "NoDerivatives 4.0 ... may be used for non-commercial research and "
  "educational purposes with appropriate citation but may not be modified or "
  "redistributed in altered form'. The old tag-vs-README ambiguity (pinned "
  "2026-08-22) is resolved in the tag's favour. Per-cohort originals differ "
  "(BMCLab and DNE are CC BY 4.0); the GitHub MIT covers the CODE only",
  "NO: ND. Harmonized/derived tensors must never be redistributed, and "
  "training that publishes a model is a derivative-work risk: EVAL ONLY",
  "free download (moved 2026-08-25: HuggingFace vida-adl/CARE-PD is public "
  "again, plus UofT Borealis doi:10.5683/SP3/TWIKMK; the old TaatiTeam slug "
  "404s, which looked like a lockdown and was a relocation)",
  "INGESTED v1: 8,476 canonical records; ND ruling 2026-08-25: records stay "
  "internal, eval-only, excluded from every public release and from training "
  "that publishes weights",
  "https://neurips2025.care-pd.ca/index.html",
  ingestion="extract_care_pd.py (SMPL -> 24-joint positions, conda env smpl) then "
  "build_canonical.py (smpl_carepd mapping). Verification: floor y~0, head "
  "y~1.5 m, UPDRS_GAIT distribution conform (3DGait {0:24,1:42,2:14,3:10})",
  note="the licence email is no longer needed (the NeurIPS site answered it); "
       "citations: NeurIPS 2025 paper arXiv 2510.04312, dataset DOI "
       "10.5683/SP3/TWIKMK (DataCite-verified). Corresponding authors Adeli "
       "and Taati remain the contact for any data-contribution inquiry"),
E("fog_turning_filho", "pose/fog_turning_filho", "FoG turning-in-place (Filho 2022)",
  "B5; M1, M2 (video + IMU synchronized)", "50 PD (35 with usable synchronized "
  "pairs per v1 ingestion); age, disease duration, LEDD, more-affected side",
  "50", "video + IMU (ACC ML/AP/SI in g, GYR ML/AP in deg/s) turning protocol",
  "CC0 (figshare item 14984667)", "yes", "downloaded",
  "INGESTED v1: 106 + 106 records; one of the two real pose<->IMU pairs on disk "
  "(stage B table)", "https://doi.org/10.6084/m9.figshare.14984667",
  ingestion="build_canonical_imu.py (fog_turning mapping). SPLIT FOLDER, same as capture24: card and raw/ under datasets/pose/fog_turning_filho, the 106 canonical records under datasets/imu/fog_turning_filho/processed/. These two are the only datasets in the repo whose raw and processed sit in different family folders (checked 2026-08-23)",
  citation="Frontiers in Neuroscience 2022, doi 10.3389/fnins.2022.832463",
  note="link resolved 2026-08-23: the download_data.py file ids 33413717 "
       "(IMU.zip) and 31544582 (PDFEinfo.csv) both belong to figshare article "
       "14984667 per api.figshare.com; Videos.zip (5.0 GB, same article) was "
       "never downloaded"),
E("gavd", "pose/gavd", "GAVD (gait abnormality video annotations)",
  "multi-pathology labels; M1 (annotations only)", "~382 annotated YouTube video "
  "segments (video-level, not subjects)", "~382 segments",
  "clinical annotation CSVs of YouTube gait videos; NO video redistributed",
  "MIT (LICENSE file in the repo, read 2026-08-28); videos remain YouTube-hosted", "yes (the annotation CSVs we hold are MIT; videos never distributed)",
  "downloaded", "raw annotations on disk; label/reference source, NOT a signal "
  "corpus (documented exclusion)", "https://github.com/Rahmyyy/GAVD",
  note="usable as a taxonomy-cell label source and video-reference list. Link "
       "resolved 2026-08-23 from the clone's own .git/config"),
E("hubu_fis_fingertap", "pose/hubu_fis_fingertap",
  "HUBU-FIS finger tapping (video + UPDRS ratings)",
  "B2; M1 (video)", "PD patients + controls, both hands, standardized MDS-UPDRS "
  "finger-tapping; per-clip ratings in fis_diagnostic.csv", "not stated (234 videos)",
  "234 videos, 10.8 GB single zip", "CC BY 4.0", "yes",
  "direct_download (Zenodo)", f"DOWNLOADED {D}: 10.81 GB, sha256 verified, zip opens cleanly: 234 clips "
  f"(226 mp4 + 8 MOV) plus fis_diagnostic.csv. Cohort read from that file: "
  f"118 subjects, 43 CONTROL and 75 patients, filmed one clip per hand "
  f"(DCHA right, IZDA left; 116 subjects have both, 2 have one), each clip "
  f"carrying an MDS-UPDRS finger-tapping score 0-3 (71/99/38/26). 40 of the "
  f"118 subjects score DIFFERENTLY on their two hands, which is the "
  f"asymmetry the task is meant to capture, so the per-hand clips are not "
  f"interchangeable. SPLIT SAFETY: both hands of a subject must share one "
  f"subject_ns or the same person lands on both sides. Note 27 CONTROL "
  f"clips are scored 1 rather than 0, so 'control' is not a synonym for "
  f"score 0. Video of hands; ratings are labels: eval only (R1). Ingestion "
  f"needs pose extraction and is not written yet",
  "https://zenodo.org/records/17738775",
  note="bradykinesia video cell; pose extraction pipeline needed after download"),
E("koa_pd_nm", "pose/koa_pd_nm", "KOA-PD-NM (gait video -> SAM3 silhouettes)",
  "B2, B3, C1, E4; M4", "50 knee osteoarthritis + 16 PD + 30 healthy; severity grades "
  "partition subjects (numbering RESTARTS per severity group: 001_KOA_EL and "
  "001_KOA_MD are different people)", "96",
  "frontal/sagittal gait video (2 sequences per subject) -> SAM3 body-outline "
  "silhouette timeseries (64-pt contour + 8 shape scalars), 30.3/50 fps native",
  "research only, non-commercial", "no (video); derived silhouettes internal",
  "direct download (research use)", "INGESTED v1 (silhouette contract): 190 "
  "records / 96 subjects, 111,002 frames, 97.7% detected",
  "https://data.mendeley.com/datasets/44pfnysy89",
  ingestion="SAM3 by owner -> build_canonical_silhouette.py; patient key "
  "koa_<COHORT>_<SEV>_<num>; sequences 01/02 = same subject, never split",
  note="1 NM video of 191 not processed by SAM3 (59/60 NM); all 96 subjects "
       "covered. Link resolved 2026-08-23 from download_data.py, whose Mendeley "
       "public-file URLs all live under dataset id 44pfnysy89"),
E("li_taati", "pose/li_taati", "Parkinson's pose estimation dataset (Li/Taati)",
  "B2 + L-DOPA dyskinesia (A7/A4 + E6); M1", "~135 PD patients; UDysRS, UPDRS, "
  "CAPSIT scores", "~135",
  "2D joint trajectories (communication, drinking, leg agility) + optical flow "
  "(toe tapping); normalized 0-1 coordinates, no raw video",
  "CC BY 4.0", "yes", "free download (GitHub)",
  "INGESTED v1: 643 canonical records (communication + drinking + leg_agility)",
  "https://github.com/limi44/Parkinson-s-Pose-Estimation-Dataset",
  ingestion="build_canonical.py (li_taati mapping) + ingest_li_taati.py "
  "(leg_agility state suffixes)",
  note="toe-tapping optical flow deliberately not ingested (different modality)"),
E("mini_rgbd", "pose/mini_rgbd", "MINI-RGBD (synthetic infants, TUM SMIL)",
  "C2; M1", "12 synthetic RGB-D sequences from the SMIL infant model, with "
  "ground-truth joints", "12 sequences", "RGB-D + joint ground truth",
  "research use (the old form gate is GONE: direct links on the IOSB page, "
  "found by the owner 2026-08-25)", "no", "direct download",
  "DOWNLOADED 2026-08-25: MINI-RGBD_web.zip 7.30 GB (84,225 entries, CRC "
  "clean, the full 12 sequences) + smil.zip (the SMIL model, 18 entries). "
  "Second gate this week that dissolved on inspection (ninapro precedent). "
  "Paper: Hesse et al., ECCV 2018 Workshops, doi 10.1007/978-3-030-11024-6_3",
  "https://www.iosb.fraunhofer.de/en/competences/image-exploitation/object-recognition/sensor-networks/motion-analysis.html",
  age="synthetic infants", note="infant-pose training without identifiable data; "
  "pairs with the future infant-skeleton contract"),
E("modys_video", "pose/modys_video", "MODYS-video (dyskinetic cerebral palsy)",
  "A4, A6, A7, D3 (pediatric dyskinetic CP is choreoathetosis; DIS "
  "scores athetosis explicitly; D3 covers the spastic component); M1", "63 children/adolescents with dyskinetic "
  "CP; clinical scoring in README xlsx", "63",
  "stick-figure pose video derivatives (Zenodo 5638470)", "Zenodo open", "yes",
  "downloaded", "INGESTED v1: 94 canonical records",
  "https://zenodo.org/records/5638470",
  ingestion="build_canonical_modys.py",
  note="one of very few public dystonia-adjacent movement datasets"),
E("park_fingertap", "pose/park_fingertap", "PARK finger tapping (ROC-HCI)",
  "B2; M1 (features)", "489 videos, subjects not individuated (features keyed by "
  "video filename)", "unknown", "488-row feature table, no raw pose",
  "MIT (LICENSE file in the repo, read 2026-08-28)", "yes (the feature tables are MIT)", "downloaded",
  "raw on disk; EXCLUDED from signal corpus (features only)",
  "https://github.com/ROC-HCI/finger-tapping-severity",
  note="link resolved 2026-08-23 from the clone's own .git/config"),
E("remap_open", "pose/remap_open", "REMAP open subset (Bristol)",
  "B2, B3; M1", "12 PD (mean 61.25 y) + 12 controls (mean 59.25 y); home "
  "free-living + clinical assessment; PD on/off labels", "24",
  "coarsened 2D skeletons (sit-to-stand + turns) and coarsened 3D (turns)",
  "CC BY 4.0 (warranty disclaimer)", "yes",
  "direct_download (single 351.4 MiB zip; fetch_p2_lot.py --only remap_open)",
  "DOWNLOADED AND INGESTED 2026-08-25 (Paris session): 189.4 MB zip (CRC "
  "clean, 19,711 entries), then 3,901 canonical pose records / 24 subjects, "
  "exactly the published cohort (12 PD + 12 controls), 0 refusals. Turning: "
  "1,749 episodes as H36M-17 (identification evidence in "
  "configs/canonical_skeleton.yaml), both the coarsened 2D and the "
  "source-lifted 3D (lift_provenance=videopose3d_by_source, pool config "
  "decides use). Sit-to-stand: 403 episodes as OpenPose BODY_25 with per-file "
  "frame+timestamp columns, fps measured from the data's own clock (30.0). "
  "PD/control rides as group attribute + eval-only label. Controlled sibling "
  "(full-res + 30 Hz wrist accel) stays application-gated (DOI "
  "10.5523/bris.2o94rzjooyzf42w850dqg0spfh)",
  "https://data.bris.ac.uk/data/dataset/21h9f9e30v9cl2fapjggz4q1x7",
  citation="Sci Data 2023, doi 10.1038/s41597-023-02663-5"),
E("tim_tremor", "pose/tim_tremor", "TIM-TREMOR (multi-etiology tremor video+depth)",
  "A1 (multi-etiology incl. functional and enhanced physiological); M1",
  "55 tremor patients, 910 videos, 21 tasks, clips 18-112 s", "55",
  "RGB video + aligned Kinect depth + ground-truth accelerometer on the most "
  "affected hand", "4TU (default CC BY, unverifiable: the host robots-blocks every check)",
  "no, DECIDED 2026-08-28: unverifiable licence = pointer to data.4tu.nl", "none: REMOVED AT SOURCE",
  "WRITTEN OFF 2026-08-28: the owner authorized acquisition, but the DOI "
  "(10.4121/uuid:522d14ed-3019-4206-b49e-a4e674b6440a) now resolves to a 4TU "
  "tombstone reading 'CONTENT WAS REMOVED / The content of this page has been "
  "retracted' (verified in a real browser, robots-block ruled out). Nothing "
  "left to download; mirroring a retracted deposit would be unauthorized "
  "redistribution. The v1 retirement (identifiable video) stands moot",
  "https://data.4tu.nl/articles/dataset/TIM-Tremor_An_open-source_dataset_of_structured_tremor_time_series_data/12692869",
  note="etiology labels per recording to verify on download"),
E("toronto_neuroface", "pose/toronto_neuroface", "Toronto NeuroFace (orofacial)",
  "D3 (ALS, stroke); M1", "36 subjects (ALS, stroke, "
  "controls), 68 facial landmarks, 30 fps", "36",
  "orofacial video landmark tracks + clinical scores", "application form", "no",
  "application (request form)",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the publication focuses on "
  "genuinely open data; not pursued. Evidence: the canonical request page "
  "at slp.utoronto.ca 404s (site restructured) and the only live route is "
  "direct email to the Yunusova lab + licence agreement, which also falls "
  "under the standing no-emails decision",
  "https://slp.utoronto.ca/faculty/yana-yunusova/speech-production-lab/datasets/",
  note="orofacial dystonia reference; small but unique. Link resolved "
       "2026-08-23: the access page is the Yunusova speech production lab "
       "datasets page (U Toronto); paper Bandini et al. 2020"),
E("visionmd", "pose/visionMD", "VisionMD (TOOL, not a dataset)",
  "n/a", "n/a", "n/a", "VisionMD video-based MDS-UPDRS analysis software "
  "(tutorial repo on disk)", "open-source software", "no (software tool, not data; pointer to its repo)", "n/a",
  "raw/ holds VisionMD-Tutorial-main: a TOOL for bradykinesia video analysis, "
  "not a data corpus; keep as tooling reference, excluded from the catalogue",
  "https://github.com/mea-lab/VisionMD",
  citation="npj Parkinson's Disease 2025, doi 10.1038/s41531-025-00876-6",
  note="candidate pipeline for hubu_fis_fingertap processing once that video "
       "set arrives. Link resolved 2026-08-23 (raw/ holds the tutorial repo "
       "VisionMD-Tutorial; the tool itself is mea-lab/VisionMD)"),
E("stroke_gait_vancriekinge", "pose/stroke_gait_vancriekinge",
  "Full-body mocap gait: 50 stroke + 138 able-bodied (Van Criekinge)",
  "D3; M1, M3, M5 (pathological EMG)", "50 stroke survivors + 138 able-bodied "
  "adults across the lifespan", "188", "3D marker trajectories, joint angles, "
  "GRF, joint moments/powers + EMG of 14 back/lower-limb muscles (C3D + MAT/XLSX)",
  "CC0 (all 13 figshare collection items, verified 2026-08-22)", "yes",
  "direct_download (figshare collection; landed via the owner's browser)",
  "DOWNLOADED (13/13, md5-verified); RE-INGESTED 2026-08-28: 737 canonical "
  "3D pose records / 188 subjects at native 100 Hz, PiG joint identities "
  "established by measured geometry (configs entry pig_vancriekinge). The "
  "2026-08-27 pass had refused 199 C3Ds as marker-only; the census showed "
  "192 of them carry the FULL model outputs under a 'SUBJECTID:' label "
  "prefix (geometry re-verified on the prefixed files) and 5 more lack only "
  "head/elbow/wrist outputs (those joints NaN-filled, masked invalid). "
  "PRIVACY NOTE: the prefixes look like birthdate-based Vicon IDs; they are "
  "stripped at ingestion and never propagated, and any raw-zip "
  "redistribution must account for them. 2 truly unusable C3Ds stay "
  "refused, 49 calibration/unparseable skipped. The MAT/XLSX "
  "time-normalized files are derivatives and stay raw. ANALOG PASS "
  "2026-09-03 (ingest_stroke_gait_analogs.py, per the scoping doc): "
  "559 canonical EMG records / 163 subjects (14 named muscles L+R via "
  "the ERS/RF/VL/ST/BF/TA/GAS alias table; anonymous Voltage.NN "
  "channels REFUSED and audited; AMPLITUDE FLAG on the records: the "
  "declared V converts to ~476 mV p99, ~1000x surface-EMG range, i.e. "
  "amplifier-output volts with undeclared gain or mislabeled mV - NOT "
  "rescaled, electrode-referred scale UNRESOLVED) + 557 canonical "
  "force records / 185 subjects (plate-to-foot assignment by ankle "
  "proximity to FORCE_PLATFORM centers during the loaded window, "
  "ambiguous strikes refused: 179 trials; per-foot |Fz| totals at "
  "1000 Hz; full 24-channel plate arrays under processed/aux_force/). "
  "160 subjects are now POSE+EMG+FORCE tri-modal. "
  "Pose validation: no errors. ingest_stroke_gait.py",
  "https://doi.org/10.6084/m9.figshare.c.6503791", age="19-85 y",
  citation="Sci Data 2023, doi 10.1038/s41597-023-02767-y",
  note="hemiparetic/spastic gait WITH pathological EMG: D3 anchor and an EMG "
       "contract pathology source"),
E("chop_gma_features", "pose/chop_gma_features",
  "CHOP infant GMA pipeline release (feature tables + weights)",
  "C2; M1 (derived features)", "1,053 infants filmed for GMA / fidgety-movement "
  "outcome (~10-12% FM-negative); clinical videos NOT shared", "1,053",
  "de-identified kinematic feature tables + model weights + ViTPose keypoints "
  "for YouTube-8M infant videos", "CC0 1.0 (OSF node license, verified 2026-08-22)",
  "yes", "direct_download (OSF)", f"DOWNLOADED {D}: 13 files, 8.3 MB (feature and split tables plus two pickled AutoML models), CC0 1.0 verified on the OSF node. De-identified FEATURES, not video and not signal: aux only, no canonical ingestion",
  "https://osf.io/gztmd/", age="10-20 weeks post-term",
  citation="GigaScience 2026, giag003",
  note="C2 features at scale; the clinical keypoint series themselves are not "
       "released (ethics), features only"),
E("mmasd", "pose/mmasd", "MMASD (ASD therapy movement derivatives)",
  "A5 proxy (stereotypies), D5; M1, M4", "32 children with ASD, >100 h therapy "
  "video as privacy-preserving derivatives; ADOS-2 scores", "32",
  "optical flow JPGs + 2D skeleton (OpenPose 25) + 3D skeleton (ROMP 71), 1,315 "
  "samples, 11 activities", "not specified by the authors for the DATA (the "
  "GitHub repo carries an Apache-2.0 badge, which covers the repo, not "
  "necessarily the Drive payload)", "no, DECIDED 2026-08-28: unspecified licence = pointer; the never-sent licence email stays in the barriers file",
  "direct download via Google Drive link (no form)",
  "DOWNLOADED 2026-08-28 (owner risk call: INTERNAL training only, never in "
  "any release tree): 7.1 GB via gdown from the README's Drive folder, all "
  "5 zips integrity-tested (optical_flow 481,176 entries; 2D_openpose "
  "256,379; ROMP 2D/3D/3D-71 312,773 each) + ADOS_rating.xlsx + README. "
  "Ingestion is its own future pass: needs OpenPose-25 and ROMP-71 joint "
  "maps in the skeleton contract",
  "https://github.com/Li-Jicheng/MMASD-A-Multimodal-Dataset-for-Autism-Intervention-Analysis",
  age="school-age children",
  note="best available substitute for the empty stereotypies cell alongside "
       "ethics-gated SSBD/AV-ASD; derivatives only, no raw video"),
E("syrip", "pose/syrip", "SyRIP (synthetic + real infant pose)",
  "C2; M1", "real + synthetic infant images, COCO-format 2D keypoints",
  "not stated", "annotated infant images (2D keypoints)",
  "non-commercial; dataset password by email", "no",
  "registration-like (password request)",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the password-by-email gate stays "
  "closed under the standing no-emails decision; not reopened",
  "https://github.com/ostadabbas/Infant-Pose-Estimation", age="infants",
  note="infant 2D pose pretraining aid for the infant-skeleton contract"),
E("oulp_age", "pose/oulp_age", "OU-ISIR OULP-Age (silhouette gait, ages 2-90)",
  "C1, C2, C3 (age axis at scale); M4", "63,846 subjects, 2-90 y, size-normalized "
  "gait energy images", "63,846", "GEIs 88x128 from 30 fps gait video",
  "Osaka University signed release agreement", "no",
  "application (signed institutional form)",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the postal-mail institutional "
  "form is declined as not worth the slow lane; written off",
  "http://www.am.sanken.osaka-u.ac.jp/BiometricDB/GaitLPAge.html", age="2-90 y",
  note="largest age-conditioned silhouette resource in existence; feeds the "
       "silhouette contract's age-normativity at population scale"),
E("s3_semiology", "pose/s3_semiology", "Seizure-Semiology-Suite (S3, UCLA)",
  "D1; M1 (video), labels", "116 adult epilepsy patients, 438 seizure videos, "
  ">35,000 dense labels on 20 ILAE semiology features", "116",
  "seizure videos (not yet released) + benchmark/annotation artefacts in the "
  "authors' GitHub repo",
  "repo has NO LICENSE FILE (checked 2026-08-22) = all rights reserved by default; "
  "videos under a DUA that is not open yet", "no (neither part)",
  "application (DUA) for videos; repo artefacts unlicensed",
  f"REPO LOCATED {D}: github.com/LinaZhangUCLA/SeizureSemiologySuite (ICML 2026 "
  "spotlight, pushed 2026-05-26, ~57 MB, 801 csv + 36 json + 7 jsonl). It holds "
  "the benchmark/fine-tuning artefacts and split tables, NOT the videos; the "
  "paper's Dataset link is still a placeholder. NOTHING FETCHED INTO THIS REPO: "
  "no license means no redistribution right, and the DUA is still in the human "
  "queue. DOCUMENTED BARRIER (owner, 2026-08-28): the publication focuses "
  "on genuinely open data; the DUA route is not pursued. Evidence recorded "
  "2026-08-28: the videos NEVER leave UCLA; authorized users analyze inside "
  "a UCLA-hosted secure enclave after an institutional DUA plus project IRB "
  "approval, so local training was off the table anyway; the repo's "
  "annotation CSVs stay look-don't-mirror (no licence file)",
  "https://arxiv.org/abs/2605.21852",
  note="exactly the D1 target: movement during seizures with ILAE feature labels. "
       "438 videos / 116 adults (300 ES, 138 NES), ages 18-64, tertiary EMU "
       "2019-2023, IRB-approved and de-identified; 20 ILAE features each with "
       "presence, MM:SS boundaries and free-text justification. Labels: eval only "
       "(R1), never pretraining"),
# ------------------------------------------------------------------ socle
E("amass", "socle/amass", "AMASS (healthy mocap base)", "C1; M1",
  "24 sub-datasets, ~344 subjects, SMPL-X/SMPL+H params", "~344",
  "high-rate mocap-derived body-model params (~31 GB archives)",
  "non-commercial research (per sub-dataset MPI EULA)", "no", "account + EULA",
  "downloaded + INGESTED v1: 17,154 canonical records", "https://amass.is.tue.mpg.de",
  render=False),
# path history: lived at socle/capture24 until 2026-09-02; the Aug 23
# ingestion wrote its 48 GB of canonical shards under imu/capture24 and
# the registry path now follows the data (raw moved along)
E("capture24", "imu/capture24", "Capture-24 (free-living wrist accel)",
  "C1, C3; M2", "151 healthy adults, ~24 h free living each", "151",
  "wrist accelerometer 100 Hz + activity annotations",
  "CC BY 4.0 (ORA record licence, verified 2026-08-23)", "yes", "downloaded", f"FULLY INGESTED {D}: 3,941 canonical records, 151 subjects, 3,883 HOURS. v1 had read only the first 60,000 lines of each subject (10 minutes) and kept 20 windows of 30 s: 3,020 records, 25 hours, i.e. 0.6 percent of a corpus already on disk. Per-subject shards under processed/canonical/, 1-hour records, 48 GB. Units verified per subject rather than assumed: median |acc| runs 0.888 to 1.051 across all 151, so the values are already in g and nothing is rescaled. 0 refusals. Activity annotations are now kept too (v1 discarded them), run-length encoded against the bundled 206-entry label dictionary, plus age band and sex from metadata.csv",
  "https://ora.ox.ac.uk/objects/uuid:99d7c092-d865-4a19-b096-cc16440cd001",
  ingestion="ingest_capture24.py (full). LATERALITY IS UNRESOLVED ON PURPOSE: the device is worn on the DOMINANT wrist and handedness is not distributed, so no subject side is knowable. Records keep the wrist_L slot for continuity and carry laterality=unknown with worn_on=dominant_wrist; the slot is NOMINAL, so do not use this source for anything laterality-sensitive. Writing wrist_R instead would be right for the right-handed majority and wrong for the rest. SPLIT FOLDER, do not be fooled: the datacard and raw/ live under datasets/socle/capture24 while the 3,020 canonical records sit in datasets/imu/capture24/processed/. The v2 reorganization moved cards and raw into the new family folders but left processed/ alone on purpose, because manifest paths are load-bearing. Looking only at socle/ shows raw with no output and invites a re-ingestion that would duplicate every record"),
E("motion_x", "socle/motion_x", "Motion-X++ (healthy motion base)", "C1; M1",
  "~15.6M poses / 81.1K clips", "clip-indexed",
  "SMPL-X whole-body + keypoints + text (47 GB)", "non-commercial research", "no",
  "public HuggingFace download", "downloaded + INGESTED v1: 25,865 records",
  "https://huggingface.co/datasets/YuhongZhang/Motion-Xplusplus", render=False),
E("ntu_rgbd", "socle/ntu_rgbd", "NTU RGB+D 120 (3D skeletons)", "C1; M1",
  "106 subjects, 114,480 samples, 120 action classes", "106",
  "Kinect v2 25-joint 3D skeletons at ~30 fps", "academic research only", "no",
  "ROSE portal (approved 2026-07-12)", "downloaded + INGESTED v1: 113,945 records",
  "https://rose1.ntu.edu.sg/dataset/actionRecognition", render=False),
E("vidimu", "socle/vidimu", "VIDIMU (daily activities: video pose + IMU)",
  "C1; M1, M2 (paired)", "53 healthy subjects on disk (54 published); 13 daily "
  "activities (walks, sit-to-stand, arm tasks)", "53",
  "video-derived 3D keypoints (34 landmarks, ~30 fps measured 29.42) for all; "
  "5 orientation-quaternion IMUs (dynamic lower-body or upper-body sets) for 16 "
  "subjects, ~208 same-trial pose+IMU pairs",
  "Zenodo open (CC BY 4.0 per record)", "yes", "direct download (on disk)",
  f"INGESTED {D} (this session, container run on full real data): 723 pose "
  "records / 53 subjects + 242 quaternion streams (208 paired). TOWER RERUN "
  "required to materialize outputs on disk: unzip raw/dataset.zip then "
  "python ingest_vidimu.py",
  "https://zenodo.org/records/15075076",
  citation="Sci Data 2023, doi 10.1038/s41597-023-02554-9",
  ingestion="ingest_vidimu.py -> canonical.pkl (skeleton contract) + "
  "streams_pose_imu.pkl (stage B alignment asset; quaternions are NOT the "
  "9-channel IMU contract) + audit + manifest",
  note="one of the two real pose<->IMU pairs of the stage B table"),
# ------------------------------------------------------------------ bio
E("kamath_snpc_geo", "bio/kamath_snpc_geo",
  "Kamath 2022 human SNpc snRNA-seq (GEO GSE178265)",
  "M10 (parkinsonism substrate)", "PD vs control post-mortem SNpc; 101 samples; "
  "22,048 DA neurons among 387k nuclei (human portion)", "donors per GEO record",
  "count matrix + barcodes + features (mtx.gz, ~4.8 GB human)",
  "GEO open supplementary (public-domain-like)", "yes",
  "direct_download (fetch_p2_lot.py --only kamath_snpc_geo)",
  "DOWNLOADED 2026-08-26: all 3 files, 5.09 GB matrix + barcodes + features, "
  "sha256 logged. Bio lane, no canonical ingestion",
  "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE178265",
  citation="Nat Neurosci 2022, doi 10.1038/s41593-022-01061-1",
  note="dopaminergic vulnerability; raw FASTQ stays dbGaP-gated (not needed)"),
E("clinvar", "bio/clinvar", "ClinVar bulk (movement-disorder gene subset)",
  "M9", "variant-disease interpretations, millions of records; filter to "
  "movement genes (PRKN, LRRK2, GBA1, HTT, TOR1A, THAP1, ATXN*, ...)", "n/a",
  "variant_summary.txt.gz (~0.5 GB) + optional VCFs",
  "NCBI public data (attribution requested)", "yes",
  "direct_download (fetch_p2_lot.py --only clinvar_summary)",
  "DOWNLOADED 2026-08-26: variant_summary.txt.gz 442 MB, sha256 logged. "
  "Movement-gene filtering is downstream work (M9)",
  "https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/"),
E("ixi_mri", "bio/ixi_mri", "IXI (healthy adult/aging brain MRI)",
  "C1, C3; M8", "~600 healthy subjects, 3 London sites, T1/T2/PD + MRA + DTI + "
  "demographics", "~600", "NIfTI tarballs (~10-15 GB total)",
  "CC BY-SA 3.0 (stated)", "yes (share-alike)",
  "direct_download (fetch_p2_lot.py --only ixi_mri; T1+T2+demographics queued)",
  "RETESTED 2026-08-28: biomedic.doc.ic.ac.uk still 403s this IP over both "
  "schemes; retry from another network or write off",
  "https://brain-development.org/ixi-dataset/",
  age="20-86 y", note="healthy aging imaging reference for M8"),
E("allen_human_brain", "bio/allen_human_brain",
  "Allen Human Brain Atlas (microarray + ISH histology)",
  "M10", "6 donors, whole-brain microarray (basal ganglia sampled), RNA-seq for "
  "2, Nissl/ISH images via API", "6",
  "per-donor normalized microarray zips; histology per-image API",
  "Allen Institute Terms of Use (non-commercial, cite)", "no, DECIDED 2026-08-28: the ToU forbids redistribution; pointer to brain-map.org",
  "direct_download (no registration)",
  "DOWNLOADED 2026-08-24 (Paris night session): all 6 donor microarray zips, "
  "1.65 GB, sha256 logged; one truncated transfer was caught by the "
  "content-length check and resumed cleanly. Bio lane, no canonical ingestion",
  "https://human.brain-map.org/static/download",
  note="anatomical/transcriptomic ground truth for basal ganglia circuits"),
E("panelapp", "bio/panelapp", "Genomics England PanelApp movement panels",
  "M9", "curated diagnostic gene panels: 540 + 847 dystonia/chorea (adult + "
  "childhood), 192 early-onset dystonia, 477 childhood ataxia, 1669 adult "
  "neurology superpanel", "n/a", "signed-off panel TSVs",
  "NHS GMS governance; no explicit open license shown",
  "no, DECIDED 2026-08-28: no written licence = pointer; the panels "
  "re-fetch freely from the PanelApp pages",
  "direct_download (panel pages; API robots-blocked to our fetcher)",
  f"DOWNLOADED {D}: both signed-off panels as TSV, panel 540 (adult onset, 207 "
  f"genes, v6.8) and panel 847 (childhood onset, 986 genes, v8.14), fetched from "
  f"the panel download endpoint. Gene panels, not movement data: aux/bio only",
  "https://panelapp.genomicsengland.co.uk/panels/540/"),
E("cellxgene_pd_multiregion", "bio/cellxgene_pd_multiregion",
  "Multi-region PD single-nucleus atlas (2.1M nuclei)",
  "M10", "100 post-mortem PD cases + controls, 5 regions incl. GPm and dorsal "
  "motor vagus", "100", "single h5ad ~30.5 GB",
  "CELLxGENE policy CC BY 4.0 (confirm on collection page)", "yes if CC BY",
  "direct_download (30.5 GB, deliberate pull)",
  f"NEW {D} (second hunt): HUMAN QUEUE (size decision before download)",
  "https://cellxgene.cziscience.com/collections/d5d0df8f-4eee-49d8-a221-a288f50a1590",
  citation="Sci Data 2024, doi 10.1038/s41597-024-04117-y"),
E("mdsgene", "bio/mdsgene", "MDSGene (genotype-phenotype knowledge base)",
  "M9", "2,695 causative variants, 23,830 literature patients, movement-disorder "
  "genes incl. new Ataxia Resource (548 genes)", "23,830 (literature)",
  "curated genotype-phenotype summaries (web only, no bulk export)",
  "personal/educational/research only; commercial needs MDS permission", "NO",
  "browse only", f"NEW {D} (second hunt): reference resource, NOT ingestible; "
  "cite and hand-extract at need", "https://www.mdsgene.org/"),
E("camcan", "bio/camcan", "Cam-CAN (healthy aging 18-88, MRI + MEG)",
  "C1, C3; M8", "~700 scanned adults uniformly sampled 18-88 (100/decade), "
  "T1/T2/DWI/MT, rs- task- movie-fMRI, MEG, sensorimotor tasks", "~700",
  "multi-TB neuroimaging archive", "free with data usage agreement", "no",
  "application (online DUA)",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the publication focuses on "
  "genuinely open data; application routes are not pursued. Procedure "
  "recorded as access-cost evidence: the old dataaccess URL 301-redirects "
  "to opendata.mrc-cbu.cam.ac.uk/projects/camcan; account + research "
  "proposal + data selection + 12-point T&C; academic affiliation required; "
  "up to 4 weeks review; delivery by SFTP",
  "https://opendata.mrc-cbu.cam.ac.uk/projects/camcan/", age="18-88 y"),
E("foxinsight", "bio/foxinsight", "Fox Insight / Fox DEN (PD mega-cohort)",
  "B2 self-report + genetics; M9, M12", ">50,000 PD participants, longitudinal "
  "questionnaires + 23andMe genetics + microbiome", ">50,000",
  "tabular questionnaire cuts + genetic data (institutional gating)",
  "DUA + publication policy", "no", "application (Fox DEN)",
  f"NEW {D} (second hunt): HUMAN QUEUE (application)",
  "https://foxinsight-info.michaeljfox.org/insight/explore/insight.jsp",
  note="DOCUMENTED BARRIER (owner, 2026-08-28): the publication focuses on "
       "genuinely open data; the Fox DEN application is not pursued. "
       "Procedure kept as evidence: account + use proposal + DUA, committee "
       "review ~1-2 weeks; genetics adds an institutional signatory + "
       "security questionnaire. Mostly self-report questionnaires anyway"),
E("pdbp", "bio/pdbp", "NINDS PDBP Data Management Resource",
  "B1, B2, A1; M8, M9, M12", "~4,298 participants (AMP-linked), PD/LBD deep "
  "phenotyping: clinical, genetic, imaging, biomarkers", "~4,298",
  "query portal with join/filter", "account + Data Access Request", "no",
  "application",
  "DOCUMENTED BARRIER (owner, 2026-08-28): the publication focuses on "
  "genuinely open data; the application is not pursued. Procedure kept as "
  "evidence: NIH RAS login (Login.gov or ID.me) required before the portal, "
  "then account request + signed Data Use Certificate + DAC review; site "
  "banner notes the repository is under administrative review; embargo "
  "rules on recent data",
  "https://pdbp.ninds.nih.gov/"),
# ------------------------------------------------------------------ ontology
E("hpo", "ontology/hpo", "Human Phenotype Ontology (movement pivot)",
  "semantic pivot for stage C; M9, M12",
  "knowledge base: 19,034 active terms; movement subtree HP:0100022 = 197 terms, "
  "68 inside the 13 MoveAtlas anchor subtrees (verified this session)", "n/a",
  "hp.obo (10 MB) + genes_to_phenotype.txt (19.7 MB) + phenotype.hpoa.gz + "
  "phenotype_to_genes.txt.gz; release hp/2025-01-16",
  "HPO free-use with attribution (widely mirrored)", "yes",
  "obtained VIA PyPI (pyhpo 4.0.0 bundles the release) because GitHub release "
  "assets are outside the session egress; refresh lane in fetch_p2_lot.py",
  f"DOWNLOADED {D} (this session) + verified: all 13 taxonomy anchor codes "
  "resolve to the expected names (A1 Tremor .. B5 Freezing of gait)",
  "https://hpo.jax.org/",
  ingestion="build_hpo_movement_map.py -> docs/hpo_movement_terms.csv (id, name, "
  "depth, parents, MoveAtlas cells)",
  note="the label vocabulary of rule R2 / stage C weak alignment"),
# ------------------------------------------------- CODY (in-house, tier 3)
# The docstring always promised these ids in DATA with render=False (their
# handwritten cards are richer than the schema); the entries were never
# actually added until 2026-08-28, so CODY was invisible to the index, the
# licence matrix and the portal despite being the program's own data.
E("cody_1", "pose/cody_1", "CODY-1 (in-house adult hyperkinetic cohort)",
  "A1-A8 (all eight hyperkinetic cells incl. the publicly-empty A3 tics, "
  "A6 athetosis, A8 ballismus); M1",
  "25 subjects (4 controls + 21 patients), per-frame 8-label phenomenology "
  "by expert raters", "25",
  "COCO-17 2D keypoints ~33 fps + per-frame multi-label annotations",
  "derived data CC BY 4.0 (CODY Zenodo deposit, 2026-09-01); raw source "
  "private (in-house). PUBLICATION RULING (owner, 2026-08-28): all NON-VIDEO "
  "files (keypoints, labels, silhouettes) are publishable; CONTROL raw "
  "videos are publishable; PATIENT raw videos are NOT, ever",
  "yes for the derived data the atlas serves (CC BY 4.0 on Zenodo); "
  "patient raw video never",
  "PUBLIC: the derived data (keypoints + labels) is published on "
  "GitHub by the owner (github.com/xaviervasques/CODY, MIT, verified "
  "2026-08-28) and, since 2026-09-01, in the CODY Zenodo deposit "
  "(10.5281/zenodo.22232609, CC BY 4.0, open access, verified "
  "2026-09-02: the 25 adults are dataset_0 there, labels + merged "
  "kinematics + SAM3 timeseries); patient raw video stays in-house",
  "INGESTED (cody source, 25 subjects); paper published "
  "(10.1002/acn3.70474); derived data PUBLIC on GitHub and Zenodo "
  "(2026-09-01)",
  "https://doi.org/10.5281/zenodo.22232609",
  render=False),
E("cody_2", "pose/cody_2", "CODY-2 (in-house pediatric inference split)",
  "A1-A8 pediatric; M1",
  "training = the 25 CODY adults; inference = 12 pediatric subjects", "12",
  "COCO-17 2D keypoints ~33 fps; pediatric split unlabeled",
  "derived data CC BY 4.0 (CODY Zenodo deposit, 2026-09-01); raw source "
  "private (in-house). Same publication ruling as cody_1: non-video files "
  "publishable, patient raw video never (pediatric: extra caution)",
  "yes for the derived data the atlas serves (CC BY 4.0 on Zenodo); "
  "patient raw video never (pediatric: extra caution)",
  "PUBLIC (derived) since 2026-09-01: the pediatric SAM3 timeseries "
  "and results ship inside the CODY Zenodo deposit "
  "(10.5281/zenodo.22232609, CC BY 4.0) in the datasets_1_2_3 files; "
  "raw video stays in-house",
  "inventoried; paper on arXiv (10.48550/arXiv.2606.07674), journal "
  "acceptance near; derived data PUBLIC on Zenodo (2026-09-01)",
  "https://doi.org/10.5281/zenodo.22232609",
  render=False),
E("cody_3", "pose/cody_3", "CODY-3 (in-house canonical superset + SAM3)",
  "A1-A8; M1, M4",
  "25 adults + external cohorts (P28-29, 12 pediatric, 20 external) = 59 "
  "namespaced ids", "59",
  "COCO-17 keypoints + SAM3 dense silhouettes + per-frame labels",
  "derived data CC BY 4.0 (CODY Zenodo deposit, 2026-09-01); raw source "
  "private (in-house). REFINED RULING (owner, 2026-08-28): cody_3 holds "
  "THREE classes of imagery and only one is publishable: (1) patient raw "
  "videos NEVER; (2) segmentation renders where the patient remains "
  "visible NEVER; (3) segmentation-only files (pure contours/masks, no "
  "identifiable imagery) publishable, as are keypoints and labels",
  "yes for keypoints, labels and PURE segmentations (CC BY 4.0 on "
  "Zenodo); anything where a patient is visible never",
  "PUBLIC (derived) since 2026-09-01: the CODY Zenodo deposit v1.0.0 "
  "(concept DOI 10.5281/zenodo.22232609, version 10.5281/zenodo.22232610, "
  "CC BY 4.0, open access, 15.4 GB, Vasques/Cif/Demailly, verified "
  "2026-09-02) ships dataset_0 (labels raw + merged-by-patient + "
  "merged-by-video kinematics + SAM3 timeseries: the 25 adults) and "
  "datasets_1_2_3 (SAM3 timeseries + results: the 2 adult, 12 pediatric "
  "and 20 real-world eval cohorts) with MD5SUMS. CAUTION: the deposit's "
  "dataset_0..3 numbering is NOT the repo's cody_1..3. Raw videos and "
  "patient-visible renders stay in-house per the ruling",
  "INGESTED (cody + cody_external silhouettes); paper in submission, "
  "arXiv within days; the FLAGSHIP derived-data release SHIPPED "
  "(Zenodo, 2026-09-01)",
  "https://doi.org/10.5281/zenodo.22232609",
  render=False),

# ------------------------- 2026-09-01 gap hunt (owner GO on all 15)
# plus the accel_fluctuations recovery (adjudication item 21). Licences
# verified on the hosting pages 2026-09-01 (docs/HUNT_2026-09-01.md).
E("accel_fluctuations", "imu/accel_fluctuations",
  "MJFF Levodopa Response Study (motor-fluctuation accelerometry)",
  "B4 (motor fluctuations around dosing), B2; M2",
  "PD patients, wearable accelerometry around levodopa dosing", "unknown",
  "wrist/waist accelerometry with dosing schedule and symptom ratings",
  "MJFF data use agreement", "no",
  "application via MJFF data portal",
  "DOCUMENTED BARRIER: access request refused (ACT), recorded in the "
  "2026-08 hunt; RECOVERED INTO THE REGISTRY 2026-09-01 (adjudication "
  "item 21: it existed only in taxonomy_map). The only B4 candidate in "
  "either source; nothing to fetch",
  "https://www.michaeljfox.org/data-sets"),
E("ssbd", "pose/ssbd", "SSBD (Self-Stimulatory Behaviour Dataset)",
  "A5; M1",
  "75 in-the-wild YouTube videos of children: arm flapping, head "
  "banging, spinning; XML temporal annotations + STIP features", "75 videos",
  "video (YouTube-sourced) + XML annotations + precomputed STIP features",
  "SSBD academic, non-commercial, not-for-profit licence (verbatim PDF "
  "read and archived in raw/ 2026-09-01): the dataset distributes URLs "
  "+ annotations + code, NOT the videos (YouTube ToS apply)",
  "no (academic non-commercial terms; fetch from origin)",
  "direct download at rolandgoecke.net/research/datasets/ssbd",
  "DOWNLOADED 2026-09-01 (owner GO): ssbd-release.zip (1.7 MB, 81 "
  "entries: 75 XML annotations + URL xlsx + licence + ssbd.m), sha256 "
  "journaled; licence PDF fetched and read the same day (UNDECIDED "
  "resolved: pointer tier). The YouTube videos are DELIBERATELY not "
  "fetched: identifiable children + platform ToS; any video work runs "
  "from origin URLs under the privacy gate",
  "https://rolandgoecke.net/research/datasets/ssbd/"),
E("goodwin_smm", "imu/goodwin_smm",
  "Goodwin stereotypical motor movements accelerometry (UbiComp 2014)",
  "A5; M2",
  "6 children/adults with autism, 2 collections 3 years apart (MITes "
  "60 Hz, Wockets 90 Hz), lab + classroom, annotated body-rocking / "
  "hand-flapping", "6",
  "3x 3-axis accelerometers (wrists + torso), annotated SMM episodes",
  "NO data licence exists (verified 2026-09-01: the repository's "
  "LICENSE files are all third-party MATLAB libraries; the instruction "
  "Google Doc, archived at instruction_doc_20260901.txt, asks citation "
  "only). INTERNAL-ONLY", "no",
  "anonymous git clone (bitbucket mhealthresearchgroup)",
  "DOWNLOADED AND INGESTED 2026-09-01 (owner GO, licence hunted first "
  "per instruction; none exists): 67 canonical IMU records / 6 "
  "subjects / 25 sessions, wrists + trunk, fs MEASURED per file (~58.8 "
  "MITes, ~90.9 Wockets). UNITS MEASURED: MITes calm-window gravity "
  "reads 64 counts/g (the instruction doc's +/-2g declaration is wrong "
  "by 2x, discrepancy recorded); Wockets calibrated per file from its "
  "own gravity (accepted band 80-120 counts/g), 8 files REFUSED as "
  "undetermined. 2,000 annotation intervals (Rock/Flap/Flap-Rock) "
  "parsed verbatim to processed/annotations/ with the wall-clock vs "
  "epoch-ms alignment left explicitly unresolved (offset is not a "
  "clean timezone shift; label use gets its own verification). Same "
  "six children in both studies: URI- stripped so one person = one "
  "subject_ns. INTERNAL-ONLY (mmasd precedent)",
  "https://bitbucket.org/mhealthresearchgroup/stereotypypublicdataset-sourcecodes"),
E("oxford_stn_onoff_dbs", "eeg/oxford_stn_onoff_dbs",
  "Oxford STN LFP at rest: levodopa ON/OFF and 130 Hz DBS (MRC BNDU)",
  "B1, B2; M2 (accelerometer), M6 (scalp EEG), M7 (STN LFP)",
  "30 hemispheres ON/OFF levodopa, 26 during 130 Hz DBS; rest "
  "recordings with LFP + scalp EEG + accelerometer", "~16",
  "STN LFP + scalp EEG (Fz/Cz/F3...) + accelerometer at rest, three "
  "therapy states",
  "CC BY-SA 4.0 (verified on page 2026-09-01)", "yes",
  "MRC BNDU data portal: registration + login (the owner's existing "
  "account; same portal as oxford_dystonia_lfp)",
  "NEW 2026-09-01 (gap hunt, owner GO): queued for the owner's next "
  "portal session. DISTINCT deposit from the Tan-2016 grip-force "
  "testbed card (same portal, different study). Feeds the DBS and "
  "medication questions directly",
  "https://data.mrc.ox.ac.uk/stn-lfp-on-off-and-dbs"),
E("dystonia_mri_ds006395", "bio/dystonia_mri_ds006395",
  "Upper-limb and cervical dystonia MRI (OpenNeuro ds006395)",
  "A4; M8",
  "37 healthy controls + 25 cervical dystonia + 29 upper-limb "
  "dystonia; T1, 60-dir DWI, rs-fMRI, finger-tapping task fMRI", "91",
  "structural + diffusion + functional MRI (BIDS)",
  "CC0 (verified via the OpenNeuroDatasets mirror 2026-09-01)", "yes",
  "OpenNeuro / S3 direct download",
  "DOWNLOADED 2026-09-01 (owner GO): full S3 sync COMPLETE, "
  "1,368/1,368 files / 61.9 GiB size-verified against the bucket "
  "listing (BIDS validation at ingestion). The first truly open MRI "
  "for the imaging lane (ixi_mri still 403s)",
  "https://openneuro.org/datasets/ds006395"),
E("pallidal_units_dystonia", "bio/pallidal_units_dystonia",
  "Genetic dystonia pallidal single-unit features (Zenodo 13269430)",
  "A4; M7 (microelectrode single units), M9-adjacent (per-patient "
  "gene labels)",
  "GPi microelectrode recordings during DBS surgery across genetic "
  "dystonia syndromes, per-patient mutation labels", "unknown (per-unit CSV)",
  "single-unit features: firing rate, bursts, oscillations, pauses "
  "(CSV) + MATLAB code",
  "CC BY 4.0 (verified on page 2026-09-01)", "yes",
  "Zenodo direct download",
  "DOWNLOADED 2026-09-01 (owner GO): "
  "genetic_dystonia_pallidal_neuron_activity.csv, 482,545 B, sha256 "
  "journaled; licence cc-by-4.0 confirmed via the Zenodo API at fetch",
  "https://zenodo.org/records/13269430"),
E("dandi_pd_macaque_units", "bio/dandi_pd_macaque_units",
  "Reach-related single units in parkinsonian macaque (DANDI 000947)",
  "B1, B2 (MPTP parkinsonian model); M7 (single units)",
  "2 MPTP macaques; GPi, VL thalamus and M1 single units during "
  "reaching", "2 macaques",
  "spike-sorted single units across the BG-thalamo-cortical circuit "
  "(NWB, ~1 TB)",
  "CC BY 4.0 (verified on page 2026-09-01)", "yes",
  "DANDI open download (dandi CLI)",
  "DEFERRED 2026-09-01 (owner GO stands): ~1 TB (378 monolithic NWB "
  "sessions, median ~2 GB) vs 273 GB free; needs external storage. "
  "SAMPLE FETCHED same day (raw_sample/: the 2 smallest pre-MPTP + 2 "
  "smallest post-MPTP sessions, 360 MB, sha256 journaled) and its "
  "schema READ: trials carry cue_onset / movement_start / reward "
  "times + target, i.e. EVENT-CODED movement (reaction and movement "
  "times = a primate bradykinesia readout pre vs post MPTP), no "
  "continuous hand kinematics in the sampled sessions",
  "https://dandiarchive.org/dandiset/000947"),
E("dandi_m1_mptp_units", "bio/dandi_m1_mptp_units",
  "M1 pyramidal-tract and corticostriatal recordings in MPTP macaques "
  "(DANDI 001636)",
  "B1, B2 (MPTP model); M7 (single units)",
  "2 MPTP macaques, identified pyramidal-tract and corticostriatal "
  "neurons", "2 macaques",
  "single-unit recordings (NWB, 6.4 GB)",
  "CC BY 4.0 (verified on page 2026-09-01)", "yes",
  "DANDI open download (dandi CLI)",
  "DOWNLOADED 2026-09-01 (owner GO): published version 0.260518.1819 "
  "COMPLETE, 447/447 assets / 6.4 GB via the DANDI API, sha256 "
  "journaled per asset",
  "https://dandiarchive.org/dandiset/001636"),
E("neuromorpho_bg", "bio/neuromorpho_bg",
  "NeuroMorpho.Org basal-ganglia neuron morphologies",
  "A7 (HD models), B1-B3 (PD models), M10 (cellular morphology)",
  "7,842 striatal reconstructions; DISEASE-MODEL CONTENT measured from "
  "the metadata (processed/condition_breakdown.csv, "
  "analyze_neuromorpho_conditions.py, 2026-09-01): Huntington 823 "
  "(675 Q140 labeled Huntington's Disease + 148 zQ175/Q175) -> A7; "
  "Parkinson models 248 (139 alpha-synuclein BAC rat, 71 LRRK2, 38 "
  "6-OHDA) -> B lane; stroke MCAO 52; dopaminergic pharmacology ~330 "
  "(cocaine, nicotine+SCH23390, D2R-overexpression) -> the "
  "intervention axis; 124 HUMAN neurons (all controls: no human "
  "patient morphology exists here); ~6,640 healthy/control baseline. "
  "The symptom link is via the animal disease model, not measured "
  "movement", "region-filtered subset",
  ".swc reconstructions via the public API (scraping forbidden, API "
  "allowed)",
  "CC BY 4.0 (verified on useterm.jsp 2026-09-01)", "yes",
  "NeuroMorpho API bulk download",
  "DOWNLOADED 2026-09-01 (owner GO): metadata for 7,842 striatal "
  "neurons + 7,567 CNG .swc reconstructions (372 MB; 275 neurons have "
  "no CNG file at the archive, counted as errors not retried). "
  "Metadata ALSO fetched for ventral striatum / motor cortex / "
  "cerebellum / basal forebrain (--meta-only): the region queries "
  "overlap heavily and the disease-model content was already inside "
  "the striatal pull. Condition breakdown measured: processed/"
  "condition_breakdown.csv (HD 823 -> A7 analog, PD models 248, "
  "pharmacology ~330, 124 human all controls). Region vocabulary has "
  "no pallidus/nigra/STN tokens (casebook adjacent phenomenon)",
  "https://neuromorpho.org"),
E("allen_cell_types", "bio/allen_cell_types",
  "Allen Cell Types Database (patch-clamp ephys + morphology)",
  "M7 (cellular ephys), M10 (morphology)",
  "human and mouse single neurons: patch-clamp electrophysiology + "
  "reconstructed morphologies", "database",
  "patch-clamp traces + .swc morphologies via AllenSDK",
  "Allen Institute terms: research/noncommercial use; NO commercial "
  "redistribution without written permission (verified 2026-09-01)",
  "no",
  "open download via portal / AllenSDK, no registration",
  "NEW 2026-09-01 (gap hunt, owner GO): POINTER/RECIPE TIER ONLY "
  "(redistribution restriction); local fetch allowed for internal use",
  "https://celltypes.brain-map.org"),
E("dandi_patchseq_000020", "bio/dandi_patchseq_000020",
  "Patch-seq mouse visual cortex, 1,040 cells (DANDI 000020, Allen)",
  "M7 (cellular ephys), M10 (transcriptome + morphology)",
  "1,040 mouse VISp neurons with joint transcriptome + "
  "electrophysiology + morphology", "1,040 cells",
  "patch-seq triplets (NWB, 141.9 GB)",
  "CC BY 4.0 (verified on page 2026-09-01)", "yes",
  "DANDI open download (dandi CLI)",
  "DOWNLOADED AND DIGEST-VERIFIED 2026-09-03 (post-migration disk, "
  "ethernet): 4,435/4,435 assets of published version 0.210913.1639, "
  "132.1 GB, EVERY file re-hashed against the archive's own "
  "dandi:sha2-256 digests (verify_dandi_local.py) - 4,435 OK / 0 bad. "
  "The overnight pull also survived a mid-transfer network-interface "
  "switch (the frozen partial was deleted and re-pulled)",
  "https://dandiarchive.org/dandiset/000020"),
E("lance_adams_myoclonus", "eeg/lance_adams_myoclonus",
  "Lance-Adams posthypoxic myoclonus EEG-EMG case (Zenodo 7620808)",
  "A2; M5 (leg EMG), M6 (EEG)",
  "N=1 Lance-Adams syndrome case around ECT: EEG + lower-limb EMG "
  "polygraphy + jerk-locked back averaging + patient video", "1",
  "EEG-EMG polygraphy (~10.5 MB)",
  "CC BY 4.0 (verified on page 2026-09-01)", "yes",
  "Zenodo direct download",
  "DOWNLOADED 2026-09-01 (owner GO): all 5 supplementary files (10.5 "
  "MB, sha256 journaled; two Zenodo 504 throttles resumed same day). "
  "Includes the patient video (.mov): INTERNAL raw only; release_lint "
  "hard-refuses .mov by design, so it can never ship",
  "https://zenodo.org/records/7620808"),
E("dystonia_alcohol_bfm", "auxdata/dystonia_alcohol_bfm",
  "Alcohol responsiveness in isolated dystonia (Dryad)",
  "A4; M12",
  "1,258 isolated-dystonia patients: BFM ratings from a standardized "
  "video protocol, alcohol-responsiveness phenotype", "1258",
  "clinical ratings table",
  "CC0 (Dryad, API-verified 2026-09-01)", "yes",
  "Dryad direct download",
  "DOWNLOADED 2026-09-01 (owner GO): dryad_dataset.zip 167,488 B via "
  "the version-level API endpoint (per-file links 401 anonymously), "
  "sha256 journaled; CC0 confirmed via the Dryad API at fetch",
  "https://doi.org/10.5061/dryad.hj08j85"),
E("chorea_acanthocytosis_mri", "bio/chorea_acanthocytosis_mri",
  "Chorea-acanthocytosis Swedish cohort imaging (Dryad)",
  "A7; M8",
  "chorea-acanthocytosis (VPS13A) patients: MRI/PET/DaTscan + "
  "phenotypes", "cohort table",
  "imaging-derived measures + phenotypes (not kinematics)",
  "CC0 (Dryad, API-verified 2026-09-01)", "yes",
  "Dryad direct download",
  "DOWNLOADED 2026-09-01 (owner GO): dryad_dataset.zip 18,720,483 B "
  "(version-level endpoint), sha256 journaled; CC0 confirmed via the "
  "Dryad API at fetch",
  "https://doi.org/10.5061/dryad.7h44j0zr9"),
E("pd_rest_eeg_onoff_ds002778", "eeg/pd_rest_eeg_onoff_ds002778",
  "UCSD resting-state EEG, PD ON and OFF medication (OpenNeuro "
  "ds002778)",
  "B2; M6",
  "~16 PD recorded both ON and OFF levodopa + ~16 matched controls, "
  "rest EEG", "~32",
  "resting EEG (BIDS)",
  "CC0 (OpenNeuro standard, mirror-verified 2026-09-01; curators "
  "request a courtesy note pre-publication, non-binding)", "yes",
  "OpenNeuro / S3 direct download",
  "DOWNLOADED AND INGESTED 2026-09-01 (owner GO): full S3 sync (332 "
  "files / 0.57 GB), then 46/46 canonical EEG records via the extended "
  "BIDS builder (.bdf support added; sessions ride in the task: "
  "rest_ses-hc 16 / ses-off 15 / ses-on 15; subject_ns keeps a person "
  "whole across ON and OFF for split safety). BioSemi DC-coupled "
  "recordings: amplitude plausibility measured on the demeaned signal "
  "(declared low_cutoff 0.0), offsets preserved; 2 records carry "
  "genuine artifact-level amplitude flags",
  "https://openneuro.org/datasets/ds002778"),
# --------------- 2026-09-01 ANIMAL LANE (standing owner GO: "include
# animal movement/symptom data if it exists"). CONVENTION: animal
# entries carry NO bare A-E or M codes so the clinical symptom and
# modality matrices never mix species; the mapping to target symptoms
# is written as free-text analogs. Licence quotes per the hunt report
# docs/HUNT_ANIMAL_2026-09-01.md.
E("chu_pd_moseq", "animal/chu_pd_moseq",
  "6-OHDA and MitoPark mouse open-field locomotion (Keypoint-MoSeq)",
  "animal: PD models -> bradykinesia/hypokinesia analogs; depth/RGB "
  "video-derived kinematic syllables",
  "mouse: unilateral 6-OHDA MFB lesion + MitoPark progressive genetic "
  "PD model, open field", "cohort per model (see paper)",
  "Keypoint-MoSeq behavioral modules + raw depth/RGB recordings "
  "(Kinect 2.0 / FLIR), ~10.2 GB raw",
  "CC BY 4.0 (Zenodo API, verified 2026-09-01)", "yes",
  "Zenodo direct download (record 14555868)",
  "DOWNLOADED 2026-09-01 (animal hunt): 3/3 files (Raw datasets.zip "
  "6.98 GB + figure source data + ASAP readme), cc-by-4.0 confirmed "
  "via the API at fetch, sha256 journaled",
  "https://zenodo.org/records/14555868"),
E("moseq_pharmacobehavior", "animal/moseq_pharmacobehavior",
  "MoSeq pharmacobehavioral space (~700 dosed mice, Wiltschko 2020)",
  "animal: drug-induced hypokinesia/catalepsy through stimulant "
  "stereotypies - both poles of the atlas as pharmacological analogs",
  "~700 mice dosed with neuro/psychoactive compounds (haloperidol, "
  "risperidone, stimulants...)", "~700",
  "depth-imaging scalars (position, velocity, height) + MoSeq "
  "syllable sequences (~3.1 GB)",
  "CC BY 4.0 (Zenodo, verified 2026-09-01)", "yes",
  "Zenodo direct download (record 3951698)",
  "DOWNLOADED 2026-09-01 (animal hunt): 3/3 files (dataset.pkl 2.86 "
  "GB + syllable labels + fingerprints), cc-by-4.0 via the API, "
  "sha256 journaled",
  "https://zenodo.org/records/3951698"),
E("striatal_gait_6ohda", "animal/striatal_gait_6ohda",
  "Striatal D1/D2 MSN encoding of gait in 6-OHDA mice (Zenodo 8303087)",
  "animal: 6-OHDA lesion -> hypokinetic gait analog, with opto-tagged "
  "striatal ephys",
  "mouse: unilateral 6-OHDA MFB lesion vs controls, open field",
  "see record",
  "open-field gait/movement measures + striatal single-unit ephys",
  "CC BY 4.0 (DataCite record; Zenodo page 50x-ing at verification)",
  "yes", "Zenodo direct download",
  "DOWNLOADED 2026-09-01 (animal hunt): data.zip 2.21 GB, cc-by-4.0 "
  "confirmed via the API on the retry (Zenodo had been 50x-ing "
  "earlier the same day), sha256 journaled",
  "https://zenodo.org/records/8303087"),
E("nlb_mc_maze", "animal/nlb_mc_maze",
  "Neural Latents MC_Maze: macaque reaching with hand kinematics "
  "(DANDI 000128)",
  "animal: healthy macaque reach socle - continuous hand/cursor "
  "kinematics + spiking (complements the MPTP event-coded sets)",
  "macaque, delayed center-out reaching in mazes", "1 (many sessions)",
  "spiking + continuous behavioral kinematics (NWB, 694 MB)",
  "CC BY 4.0 (DANDI, verified 2026-09-01)", "yes",
  "DANDI open download",
  "DOWNLOADED 2026-09-01 (animal hunt): both NWB assets of the "
  "published version via the DANDI API, sha256 journaled",
  "https://dandiarchive.org/dandiset/000128"),
E("rat7m", "animal/rat7m",
  "Rat 7M: 3D rat motion capture (Dunn/Olveczky)",
  "animal: healthy rat 3D kinematics socle",
  "rat, ~7M frames / 10.8 h of 20-marker mocap with multi-camera "
  "video", "several animals",
  "3D mocap (20 markers) + synchronized multi-camera video",
  "CC BY 4.0 (CONFIRMED via the figshare API on all 8 collection "
  "articles at fetch, 2026-09-01)", "yes",
  "figshare collection 10.6084/m9.figshare.c.5295370",
  "MOCAP CORE DOWNLOADED 2026-09-01 (7 .mat + camera parameters, 255 "
  "MB, sha256 journaled) - the kinematics essential. VIDEOS 403 "
  "2026-09-03: figshare answers 403 Forbidden to scripted clients on "
  "the video files (browser UA included; the mocap article had served "
  "from the same client) - the casebook case-5 pattern. NO retry "
  "storm: one spaced probe later, or the owner-browser route; videos "
  "are pose-training extras (15.3 GB)",
  "https://doi.org/10.6084/m9.figshare.c.5295370.v3"),
E("calms21", "animal/calms21",
  "CalMS21 mouse social behavior pose corpus (Caltech)",
  "animal: healthy mouse pose/behavior socle (6M unlabeled + 1M "
  "annotated pose frames)",
  "mouse dyads, resident-intruder assays", "many sessions",
  "pose estimates + TREBA features + behavior annotations",
  "CC BY 4.0. VERIFIED 2026-09-02 on the CaltechDATA record page in a "
  "browser: 'Rights / License: Creative Commons Attribution 4.0 "
  "International', record marked Open, DOI 10.22002/D1.1991; the "
  "deposit readme carries ZERO rights language, so the record licence "
  "governs everything in it. The MIXED CC BY-NC-SA caution came from "
  "the project website, not the deposit; retired with evidence",
  "yes (CC BY 4.0)",
  "CaltechDATA direct download (s0vdx-0k302); the 2026-08-22 403s "
  "were network/UA-specific, plain curl works from the Mac side",
  "DOWNLOADED 2026-09-02: the pose corpus WITHOUT the videos - task1_"
  "classic_classification.zip 457.4 MB + task1_MARS_features.zip "
  "1.8 GB + task2_annotation_styles.zip 912.1 MB + task3_new_"
  "behaviors.zip 556.2 MB + readme + converter script, every file "
  "md5-checked against the record page, sha256 journaled. Video zips "
  "(28.3 + 74.2 + 3.5 GB) deliberately NOT fetched: the pose socle "
  "needs trajectories, not pixels",
  "https://data.caltech.edu/records/s0vdx-0k302"),
E("kumar_stride_gait", "animal/kumar_stride_gait",
  "JAX stride-level mouse gait (62 strains + SOD1 ALS, Rett, Ts65Dn)",
  "animal: strain-survey gait reference + disease-model gait "
  "summaries (SOD1 ALS -> hypokinetic-adjacent analog)",
  "mouse, 62 strains + disease models, open field", "62 strains",
  "HRNet pose model + training annotations + stride-level gait "
  "summary tables (raw videos not deposited)",
  "CC BY-NC-ND 4.0 (the deposit's own LICENSE file, read verbatim on "
  "disk 2026-09-01; Zenodo API said only other-nc)",
  "no (ND: care_pd precedent applies - internal, eval-only, excluded "
  "from releases and from training that publishes weights)",
  "Zenodo direct download (10.5281/zenodo.5636430)",
  "DOWNLOADED 2026-09-01 (animal hunt): 9 files including the "
  "stride-summary CSV, pose annotations (428 MB) and the HRNet "
  "weights; the 3.6 GB container image skipped by filter. Record "
  "5708437 is an empty stub (0 files), 6380163 is the real deposit",
  "https://doi.org/10.5281/zenodo.5636430"),
E("alphasyn_catwalk", "animal/alphasyn_catwalk",
  "Alpha-synuclein transgenic mouse CatWalk gait (Data in Brief)",
  "animal: synucleinopathy gait analog (parkinsonian lane)",
  "mouse C57BL/6N: 12 WT, 13 a-syn KO, 8 human-a-syn-on-KO double "
  "transgenic, 7 months", "33",
  "CatWalk paw positions/print sizes/intensities at 100 Hz, 90 run "
  "files",
  "CC BY (open-access article statement, verified on PMC)", "yes",
  "article supplementary files (10.1016/j.dib.2017.12.067)",
  "INDEX-ONLY 2026-09-02, casebook case 11: the only supplementary "
  "that exists (PMC and Elsevier CDN, identical) is mmc1.xlsx 10.9 KB, "
  "three sheets listing 120 per-run spreadsheet FILENAMES, not the "
  "runs, despite 'The data are with this article'. CDN probed for "
  "mmc2-5 (xlsx/zip/docx): nothing; ScienceDirect 403s automation. "
  "One manual owner check of the publisher page remains before "
  "writing it off; effectively pointer-tier until the runs surface. "
  "sha256 journaled",
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC5988224/"),
E("locomouse_ataxia", "animal/locomouse_ataxia",
  "LocoMouse ataxic locomotion (reeler, pcd) stride kinematics",
  "animal: cerebellar-ataxia gait analogs (differential context for "
  "the dystonia/chorea gait question)",
  "mouse: reeler N=7 (9,392 strides), pcd N=3 (3,052 strides), "
  "controls N=12", "22",
  "3D paw/nose/tail tracking-derived stride data (per-figure source "
  "data; raw 400-fps video not deposited)",
  "CC BY (eLife source data)", "yes",
  "eLife article source data (10.7554/eLife.55356)",
  "NEW 2026-09-01 (animal hunt): queued, light",
  "https://elifesciences.org/articles/55356"),
E("infant_pose_chambers", "pose/infant_pose_chambers",
  "Chambers infant pose estimates + normative video metadata",
  "C2; M1",
  "pose estimates for the 94-infant evaluation set + domain-adapted "
  "infant OpenPose model + normative YouTube metadata (85 infants)",
  "94 + 85 meta",
  "2D pose estimate tables + model + video metadata CSV",
  "CC BY 4.0 (confirmed via the figshare API at fetch 2026-09-01; "
  "UNDECIDED resolved)", "yes",
  "figshare + GitHub direct download",
  "DOWNLOADED AND INGESTED 2026-09-01 (owner GO): all 12 files md5 "
  "MATCHED, then 116 canonical pose records / 104 infants (85 YouTube "
  "normative with age_in_weeks + 31 clinical trials from 19 CHOP "
  "infants with sex, ages and BINS risk as eval-only attributes). New "
  "chambers_coco18 joint map added to configs/canonical_skeleton.yaml "
  "(pelvis=midpoint hips, neck direct, head=proxy nose, eyes/ears "
  "dropped); missing detections -> valid_mask False. The first REAL "
  "(non-synthetic) open infant pose in the corpus",
  "https://doi.org/10.6084/m9.figshare.8161430"),
]


TEMPLATE = """# {title}

- dataset: {id}
- family: {family}  (physical path: datasets/{path})
- MoveAtlas cells: {cells}
- population: {population}
- n_subjects: {n}
{age_line}- signal: {signal}
- license: {license} ; redistribution: {redis}
- access: {access}
- status ({date}): {status}
- link: {link}
{cit_line}{ing_line}{note_line}"""


def render(e):
    def opt(label, val):
        return f"- {label}: {val}\n" if val else ""
    return TEMPLATE.format(
        title=e["title"], id=e["id"], family=e["family"], path=e["path"],
        cells=e["cells"], population=e["population"], n=e["n"],
        age_line=opt("age", e["age"]), signal=e["signal"], license=e["license"],
        redis=e["redis"], access=e["access"], status=e["status"], date=D,
        link=e["link"], cit_line=opt("citation", e["citation"]),
        ing_line=opt("ingestion", e["ingestion"]), note_line=opt("notes", e["note"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("KINEFM_REPO",
                    os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    ids = [e["id"] for e in DATA]
    assert len(ids) == len(set(ids)), "duplicate dataset ids"
    n_cards = 0
    for e in DATA:
        if not e["render"]:
            continue
        d = os.path.join(args.repo, "datasets", e["path"])
        if not args.dry:
            os.makedirs(d, exist_ok=True)
            # newline="\n": the repo convention is LF; without it a Windows run
            # rewrites all 76 cards in CRLF (found 2026-08-23 on the Paris PC)
            with open(os.path.join(d, "datacard.md"), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(render(e))
        n_cards += 1
    docs = os.path.join(args.repo, "docs")
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs, "datasets_index.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "family", "path", "title", "moveatlas_cells", "n_subjects",
                    "age", "license", "redistribution", "access", "status",
                    "link"])
        for e in DATA:
            w.writerow([e["id"], e["family"], "datasets/" + e["path"], e["title"],
                        e["cells"], e["n"], e["age"], e["license"], e["redis"],
                        e["access"], e["status"], e["link"]])
    # taxonomy_map.csv is now EMITTED from the same DATA (owner ruling
    # 2026-09-01, after 20 divergences were adjudicated): cells and M
    # codes come from the registry truth; the free-text comment column
    # is carried over from the previous file where the id matches, so
    # the two files can never drift again.
    import re as _re
    old_comments = {}
    tmap = os.path.join(docs, "taxonomy_map.csv")
    if os.path.exists(tmap):
        with open(tmap, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                old_comments[row["jeu"]] = row.get("commentaire", "")
    with open(tmap, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["jeu", "cellules", "modalites_m", "commentaire"])
        for e in DATA:
            cells = ";".join(sorted(
                set(_re.findall(r"[A-E]\d+", e["cells"])),
                key=lambda c: (c[0], int(c[1:]))))
            mods = ";".join(sorted(
                set(_re.findall(r"M\d+", e["cells"])),
                key=lambda c: int(c[1:])))
            w.writerow([e["id"], cells, mods,
                        old_comments.get(e["id"], "")])
    flagged = []
    with open(os.path.join(docs, "license_matrix.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "license", "redistribution", "portal_action"])
        n_host = n_ptr = n_priv = 0
        for e in DATA:
            r = e["redis"].lower()
            if e["license"].lower().startswith("private"):
                act = "private_collaboration_only"
                n_priv += 1
            elif r.startswith("yes"):
                act = "host_copy_ok_with_attribution"
                n_host += 1
            elif r.startswith("no"):
                act = "pointer_only"          # a DECIDED state, not a flag
                n_ptr += 1
            else:
                act = "VERIFY_BEFORE_PORTAL"
                flagged.append(e["id"])
            w.writerow([e["id"], e["license"], e["redis"], act])
    print(f"{n_cards} datacards rendered / {len(DATA)} indexed; "
          f"tiers: {n_host} hosted / {n_ptr} pointer / {n_priv} private; "
          f"{len(flagged)} UNDECIDED flag(s)"
          + (": " + ", ".join(flagged) if flagged else ""))


if __name__ == "__main__":
    main()
