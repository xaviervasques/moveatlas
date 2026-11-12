# The closing sweep (2026-09-04): three search passes before the paper freeze

Purpose: bound the completeness claim. The paper can only say
"exhaustive under protocol P at date D"; this sweep re-dates D, probes
the axes the original protocol under-covered (non-English
repositories, generalist repositories, recency), and re-verifies the
confirmed absences. Three parallel automated search passes, web-search
based; every claim below is a pass's reading of a record page or API -
catalogue-tier rows carry RE-VERIFY AT FETCH flags.

## Headline results

1. COMPLETENESS HELD BETTER THAN FEARED: the large majority of
   everything the three passes surfaced was ALREADY catalogued
   (weargait_pd, fog_star, multimodal_fog, li_taati, tlvmc, daphnet,
   care_pd, gavd, visionmd, modys, hd_accel_jnet, ds006395, tim_tremor,
   pads mirrors...). The sweep's genuinely-new yield: 16 catalogued
   rows.
2. TWO OF FIVE CONFIRMED ABSENCES MOVED:
   - A5 stereotypies: REFUTED at the skeleton level (ASDPose 2024,
     241 children, 7,352 annotated SMM segments); holds for raw video.
   - A3 tics: revision PENDING VERIFICATION (MindTS-MMD, 60 children,
     >120 h annotated; OSF 46vxm) - ethics/de-identification check
     first, video of minors.
   Athetosis-as-labelled-corpus, ballismus, akinesia: re-confirmed
   absent. The revisions themselves are a paper point: our own
   absence claims aged within a year (access-metadata decay measured
   on ourselves).
3. THE ENCLAVE BARRIER CLASS: AIHub (Korea) hosts the only Korean PD
   gait-signal corpus (~500 subjects) and a 3,719-patient parkinsonism
   imaging cohort behind a nationals-only, IRB-plus-security-agreement
   "Online Safety Zone" - analysis in enclave, no export. The
   strongest documented instance of the analysis-not-data access
   model; belongs in the casebook family.
4. NEGATIVES WORTH CITING: J-STAGE Data (Japan) - zero
   movement-disorder datasets; NII/CiNii - everything traces back to
   Dryad/figshare; RADAR (Germany) - zero; Chinese-language terms on
   ScienceDB - no PD kinematics beyond the imaging cohorts; Kaggle/
   Mendeley/OSF/Dataverse - no chorea, myoclonus, athetosis,
   ballismus signal anywhere.
5. TRAPS RE-SIGHTED, KNOWN PATTERNS:
   - CARE-PD surfaced as "open, MIT" via its GitHub - that is the
     CODE licence; the DATA ruling stays CC BY-NC-ND (casebook case
     2). The sweep re-triggering the same mislabel is evidence the
     trap is systematic.
   - Recherche Data Gouv was in MAINTENANCE during the sweep (the
     owner queue's "RDG retry" failures explained); its two findings
     came via the DataCite index and need re-verification when the
     portal returns.
   - ScienceDB and DANS block generic fetchers (anti-bot); DataCite
     is the workable side door for metadata.

## Catalogued from this sweep (16 rows, all catalogue-tier)

Recency pass: asdpose.
Non-English pass: piet_essential_tremor, open_dbs_pd,
shanghai_child_gait3d, aihub_path_gait, aihub_pd_imaging, pearl_pd,
stil_orthosis_tremor, haspa_spasticity, drummer_tremor_model.
Open-web pass: mindts_tourette, osf_tic_video_46vxm,
dataversenl_pd_ema (the sweep's largest open find: 107 GB free-living
PD EDF, CC0), sensefog, mendeley_et_accel, osf_tremor_amplitude.

Noted, not catalogued: OSF vuah8 (a 1.3 GB harmonized FOG benchmark -
derived from datasets we hold; a benchmark artifact, not a source),
Kaggle mirrors of held sources (recorded here as mirrors), NeuroPose-
AHM (literature-extracted kinematic knowledge base, not recordings),
simulated-ataxia Kaggle set (healthy actors), AIST gait database
(Japan, contract-only barrier), Mendeley PD gait record family
(gdgw7m36v3, dkm67bz4j7, 44pfnysy89, vfvfprdyxp, xvz8y7dtvh +
siblings, z39mhdsynx keystroke; individually small - triage into the
registry at the next ingestion pass if the corpus wants more PD
mass), DANS healthy extras, RADAR4KIT healthy/synthetic EMG,
DataverseNL AR-gait U5LUGX, Harvard facial-kinematics CT34N0 +
normative gait M0NKN9, Borealis FOG features UFZTLV, SciDB stroke
pair (scope-adjacent), drummer/archery physiological-tremor extras.

## Method notes for reproducibility

The passes probed: ScienceDB + RDG via DataCite (anti-bot), DANS via its
Dataverse API, J-STAGE/AIHub via live browsing, Mendeley/OSF/Kaggle/
GitHub/Dataverse via their public APIs + web search; native-language
terms tried where supported. The passes' full working logs are
not published; this file is the durable record.
