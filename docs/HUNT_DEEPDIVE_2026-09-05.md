# The deep-dive sweep (2026-09-05): eight agents past the protocol's edges

Sequel to HUNT_CLOSING_2026-09-04. Three axes the closing sweep did not
touch: clinical-phenotype depth (14 fine phenotypes), big-cohort
platforms, neglected modalities - then pediatric/genetic-rare and
systematic per-repository passes (EBRAINS, DABI, OpenNeuro, PhysioNet,
Dryad, GIN, Synapse). Owner grants: autonomous fetch of in-criteria
finds and integration up to Zenodo DRAFTS. Every catalogued row carries
RE-VERIFY-AT-FETCH; fetch-time reads again corrected agent guesses
(the day's score: several licences and one order of magnitude - the
"31 MB" MobilityAPP is 31 KB of derived parameters).

## Headlines

1. THE CATALOGUE GREW 130 -> ~170 rows in one day, most of it
   DOCUMENTED BARRIERS - by design: the road-blocker ledger is paper
   material equal to the data itself.
2. THE ACCESS-MODEL TAXONOMY IS NOW A BESTIARY, each with a live
   exemplar: enclave (PPP, AIHub), fee (UK Biobank), consortium
   (WATCH-PD), application (Dystonia Coalition, TIRCON, Enroll-HD's
   two-tier), per-project agreement (DABI), request (REMPARK, ICEBERG,
   Duke WC), form (NCER-PD), ethics-proof (MASS), qualified-researcher
   (mPower), commercial product (MEEI), SUSPENDED-mid-migration
   (OPDC), family-mediated registry (GNAO1/ADCY5/RARE-X - new class),
   matchmaking (dbsmatchmaker), circular pointer (sensefog), withdrawn
   -at-source (TIM-Tremor, 410 CONFIRMED), broken availability
   statement (LSR github; Dryad CD deposit holding a single .docx).
3. SINGULARITY FINDINGS (the paper's sharpest sentences):
   - Tourette signal data exists in EXACTLY ONE repository on earth
     (DABI 1UH3NS119844, 221 GB, gated).
   - Sydenham chorea is the cleanest absolute void found: zero
     datasets, zero registries, zero deposited recordings.
   - Huntington/chorea and myoclonus signal are absent from ALL seven
     repositories swept.
   - Oculomotor recordings are absent across EVERY movement disorder.
   - Blepharospasm's own literature admits it: "No publicly available
     blepharospasm dataset currently exists" (npj Digit Med 2025).
4. THE OASES (open where deserts were assumed):
   - cervical dystonia: mrc_lfp_dystonia (LFP+neck EMG+accel, CC
     BY-SA, MRC login tier - same portal as the pending owner login).
   - spasmodic dysphonia: SVD subset FETCHED (2031 WAV+EGG, CC BY).
   - functional disorders: the OSF pair FETCHED (EEG + limb
     kinematics; licence-pending, INTERNAL-ONLY).
   - atypical parkinsonism: mobilityapp FETCHED (derived parameters
     only - honest verdict on the card).
   - CP at scale: mobile_gaitlab (1,026 patients of video-derived
     keypoints, free GitHub) + Leuven mocap.
   - invasive ET: Dryad's 77.8 GB intraop VIM record, CC0 (disk
     queue), + STN-kinematics 6.5 GB CC0.
5. THE INTEGRATION TEMPLATE PROVED OUT in one day on
   drummer_tremor_model: hunt -> fetch (etalab) -> canonical EMG (131
   trials; unit contradiction disclosed per policy) -> full-family
   validation (8038 records, 0/0) -> staging -> ZENODO DRAFT
   10.5281/zenodo.22358617. Record count: 49.

## Fetched this day (licence verified at source, sha256 journaled)
svd_spasmodic_dysphonia (492.7 MB), osf_fmd_eeg (217 MB),
osf_fmd_kinematics (117.5 MB), obf_psychiatric (10.4 MB),
mobilityapp_atypical (31 KB), drummer_tremor_model (3.1 GB, Friday) -
plus the Friday batch (haspa, mendeley_et_accel, osf_tremor_amplitude,
asdpose 12.9 GB).

## Fetch queue (open, authorized, pending bandwidth/disk)
dryad_irbd_smartphone (52 MB), dryad_pd_5imu_adl (621 MB),
physionet_multimodal_gait (6.5 GB), dryad_stn_kinematics (6.5 GB),
mobile_gaitlab + leuven_cp_gait (probe sizes), piet (30.6 GB, after
000947), DABI public tier (ERNA 155 MB + UMinn 9.5 GB, account
needed), then the disk-decision pair dryad_vim_et_intraop 77.8 GB /
dataversenl 107 GB / open_dbs 613 GB.

## Owner-decision ledger (all documented on cards, none exercised)
MRC login (collects oxford_stn_onoff_dbs + mrc_lfp_dystonia in one
session), mPower qualified tier, DABI account, Synapse gates (MJFF
levodopa = held accel_fluctuations; CIS-PD/REAL-PD), Dystonia
Coalition / TIRCON / Enroll-HD applications, ScienceDB shanghai DUA,
children-video ethics (mindts, osf_tic), FMD/NewHandPD/asdpose
licence adjudications, and the request-tier contact list (Duke WC,
STOPme Rett, Gupta A-T, Aravamuthan WashU - one contact covers
GNAO1 + CP-dystonia).

Assistant recommendation on the internal-only tier (2026-09-07, for
the owner pass): (1) highest-leverage action is a one-line author
contact for asdpose and the FMD pair asking for an explicit data
licence (both OSF FMD nodes re-checked via API 2026-09-07: license
NONE; asdpose's JAMA statement says everyone/any purpose but names no
instrument) - two to three hosted-tier promotions for two emails.
(2) mindts/osf_tic: the de-identification review only decides
INTERNAL use; redistribution stays off the table regardless.
(3) care_pd, kumar, mmasd, goodwin, osf_tremor_amplitude (NC-SA):
leave as-is and claim the quarantined eval tier in the paper as a
feature - uncontaminatable held-out cohorts under R1, not a failure
of openness. Do not add an NC-SA record to the launch corpus; the
licence-homogeneity cost outweighs one dataset.

## OpenNeuro triage list (catalogued: ds008768, ds008174; to triage)
ds007020 (PD mortality EEG), ds004574/79/80 (Narayanan siblings of
held ds004584), ds003490/506/509 (Cavanagh family), ds005385 (lifespan
EEG incl. PD), ds008336 (ET MRI), motor-fMRI ds005263-66, ds005906/
ds005849 (DBS fMRI), healthy walking-EEG ds001971/ds004475/ds007222/
ds007788.

## Method note
Two waves; wave two was killed mid-flight by the session usage limit
(~17:30) and relaunched as single agents - sub-agent sprawl is a
budget hazard, mono-agent passes complete. Agent claims were spot-
corrected at fetch time all day; nothing enters the registry as
verified unless a fetch or an API read confirmed it.

## Postscript (evening): Dryad's fresh hardening, measured live

Fetching the two CC0 finds produced a probe matrix worth the casebook:
dataset-level /download 401, file-level /download 401 (anonymous),
web stash route 403, version-level /download 200 for the 52 MB set
but 405 for the 621 MB one ("large dataset" sync-download refusal).
Our own 2026-09-01 Dryad fetches used the version endpoint freely -
the gate moved WITHIN FOUR DAYS. dryad_irbd_smartphone is in hand
(CC0, journaled); dryad_pd_5imu_adl waits on a free Dryad account
(owner decision) or two browser clicks. Transport-layer access decay
now has a four-day-resolution data point.
