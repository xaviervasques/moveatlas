# MoveAtlas data map: find the data by clinical question (2026-08-22)

Human-readable projection of the corpus onto the MoveAtlas taxonomy. One line per
dataset: `id  [state]  what it brings`. States: INGESTED (canonical records on
disk or script tested and tower-pending), RAW (on disk, not yet canonical),
QUEUED (download registered in fetch_p2_lot.py / OpenNeuro lane), HUMAN
(registration/application/decision pending, see datasets/PENDING_HUMAN.md).
Physical paths and full details: the per-set `datacard.md`, indexed in
docs/datasets_index.csv. Machine view: paper/matrix_taxonomy.csv.

## A. Hyperkinetic

- A1 Tremor: tremordb [INGESTED: DBS on/off laser velocity], pads [INGESTED*:
  469 subjects incl. 28 essential tremor], monipar [INGESTED], iprognosis
  [INGESTED], alameda [RAW, features], tim_tremor [HUMAN: G0 re-admission
  decision, only multi-etiology tremor video], mpower [HUMAN].
- A2 Myoclonus: NO public dataset exists (confirmed twice, 2026-08-22): internal
  high-rate protocol is the only route. Proxies: tuh_eeg myoclonic events
  [HUMAN], seizeit2 [QUEUED].
- A3 Tics: NO public dataset exists (confirmed): CODY + internal only.
- A4 Dystonia: cody_* [INGESTED, private], modys_video [INGESTED, dyskinetic
  CP], oxford_dystonia_lfp [HUMAN: LFP+EEG+neck-EMG+ACC, NEW], cdystonia
  [QUEUED: TWSTRS scores], cervical_motion [QUEUED, ND license flag, normative
  ROM], toronto_neuroface [HUMAN, orofacial].
- A5 Stereotypies: mmasd [HUMAN: ASD therapy derivatives, best proxy], ssbd/
  av-asd [HUMAN: ethics ruling], otherwise CODY only.
- A6 Athetosis / A7 Chorea / A8 Ballismus: cody_* [INGESTED, private],
  hd_accel_jnet [INGESTED: chorea wrist accel], gaitndd [INGESTED: 20 HD gait],
  modys_video [INGESTED]; no other public source (confirmed).

## B. Hypokinetic

- B1 Rigidity: NO public instrumented dataset (confirmed; MJFF refused):
  internal T8 protocol. Subject-level proxies: pdbp, ppmi [HUMAN].
- B2 Bradykinesia: care_pd [INGESTED, license flag], li_taati [INGESTED],
  pads [INGESTED*], hubu_fis [QUEUED: 234 rated finger-tap videos],
  remap_open [QUEUED], weargait_pd [INGESTED], pd_walking_eeg + pd_rest_eeg
  [QUEUED: EEG side], clinical_gait sets [INGESTED / QUEUED-flagged].
- B3 Hypokinesia / B4 Akinesia: remap_open [QUEUED], mpower medTimepoint
  [HUMAN], fog_star manifestation labels include akinetic FoG [INGESTED].
- B5 Freezing of gait: kaggle_fog [INGESTED], daphnet [INGESTED], fog_star
  [INGESTED], fog_turning [INGESTED], multimodal_fog [INGESTED*: the
  EEG+EMG+IMU pair], clinical_gait_multipatho [INGESTED].

## C. Normal, conditioned on age

- C1 Adult: amass, ntu_rgbd, motion_x, capture24 [INGESTED socles], vidimu
  [INGESTED*: 53 subjects, 13 activities + pose-IMU pairs], semg_walking +
  gait120 [QUEUED: EMG socle], cervical_motion [QUEUED], ixi_mri [QUEUED, M8].
- C2 Infant / developmental: chop_gma_features [QUEUED: 1,053 infants,
  features], babypose, mini_rgbd, syrip [HUMAN], NeoVault [HUMAN, dossier list];
  internal GMA cohort remains the strategic play.
- C3 Aging: ltmm [QUEUED], nhanes_accel [QUEUED, resolved URLs], sixmwt_lifespan
  [QUEUED: explicit 21-75 decade bins], nonan_gaitprint [QUEUED: 56+],
  gaitdb [RAW, derived], oulp_age [HUMAN: ages 2-90 silhouettes at scale],
  camcan [HUMAN: 18-88 imaging].

## D. Neurological comorbidity routes

- D1 Epilepsy: seizeit2 [QUEUED: EEG+EMG+IMU seizures], s3_semiology [HUMAN:
  ILAE-labeled seizure video], osdb [HUMAN: wearable seizures], tuh_eeg [HUMAN].
- D2 Ataxia: ataxie_kinect_dib [RAW: SARA table], ilg_ataxia_tables [QUEUED:
  real-life gait statistics], gaitndd ALS arm [INGESTED, pyramidal-adjacent].
- D3 Pyramidal / spasticity: stroke_gait_vancriekinge [QUEUED: mocap+EMG+GRF,
  50 stroke], clinical_gait sets [stroke arms], toronto_neuroface [HUMAN].
- D4 Neuropathies: clinical_gait_signals_2025 [QUEUED, flagged: chemo-induced
  neuropathy with TNS scores]; diabetic-neuropathy gait: watch list (DFN-DS
  "will be available").
- D5 Neurodevelopmental: mmasd [HUMAN], C2 sets above.
- D6 Sleep / RBD: cap_sleep [QUEUED: 22 RBD, the only open PSG with RBD],
  beijing_sleep_lfp [HUMAN: the strategic application].
- D7 Functional: NOTHING public exists (confirmed twice). tim_tremor functional
  arm is the only proxy [HUMAN: G0 decision]. Internal production remains the
  only route.

## E. Systemic comorbidity routes

- E1 Endocrine / E2 Wilson / E5 dermatology / E7 catatonia: zero public movement
  data (confirmed). Route: internal + case collaboration.
- E3 Diabetes: nothing today; DFN-DS on watch list.
- E4 Musculoskeletal: gaitrec [QUEUED: 2,084 patients GRF], koa_pd_nm
  [INGESTED], clinical_gait orthopedic arms.
- E6 Iatrogenic: li_taati L-DOPA dyskinesia [INGESTED], chemo-neuropathy arm of
  clinical_gait_signals_2025 [QUEUED]; tardive dyskinesia: nothing public.

## Modalities and biology

- M5 EMG: semg_walking + gait120 + ninapro [QUEUED/HUMAN socle], multimodal_fog
  block [INGESTED*], stroke EMG [QUEUED], chin EMG via cap_sleep [QUEUED],
  oxford_dystonia_lfp neck EMG [HUMAN]. Contract: configs/canonical_emg.yaml.
- M6 EEG: multimodal_fog [INGESTED*], cap_sleep + pd_rest/pd_walking EEG +
  seizeit2 [QUEUED], tuh_eeg [HUMAN]. Contract: configs/canonical_eeg.yaml.
- M7 LFP/ECoG: merk_neumann + oxford_stn [testbed, R1], pd_meg_stn_lfp
  [QUEUED: 162 GB], oxford_dystonia_lfp + beijing [HUMAN].
- M8 Imaging: ixi_mri [QUEUED], camcan / pdbp / ppmi [HUMAN].
- M9 Genetics: hpo [ON DISK, verified], clinvar + panelapp [QUEUED], mdsgene
  [reference only], foxinsight [HUMAN].
- M10 Histology/cellular: kamath_snpc_geo [QUEUED], allen_human_brain [QUEUED],
  cellxgene_pd_multiregion [HUMAN: size decision].
- M12 Scales: cdystonia [QUEUED], clinical_scales/NINDS CDE [QUEUED], hpo map
  [ON DISK].

(*) INGESTED* = ingestion script written AND tested on the real data this
session; the tower run materializes the outputs (docs/TOWER_RUNBOOK.md).
