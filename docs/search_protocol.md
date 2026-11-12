# Search protocol for the public movement-data accessibility audit

Date of this document: 2026-07-10.
Status: DRAFT. This protocol must exist and be dated BEFORE the catalogue freeze
(audit task 4), otherwise the coverage figure has no defined denominator.

Author role: this file records HOW the candidate dataset set was assembled, so a
third party can reproduce it. It contains no interpretation.

---

## 1. Important limitation, stated up front

The catalogue (`datasets/_catalogue.csv`, 37 datasets) was assembled BEFORE this
instrumentation existed. The exact historical search terms, the databases queried in
which order, and the last-queried date per source were NOT recorded at the time and
are therefore `unknown`. This document does two things:

1. It reconstructs, from the catalogue and the two source spreadsheets
   (`Catalogue_donnees_mouvement_telechargeables.xlsx`,
   `Catalogue_donnees_mouvement_DBS-2.xlsx`), which repositories the existing datasets
   actually came from (verifiable from the `acces` and link fields).
2. It PROPOSES a clean, reproducible search to be run once and dated, so the audit has
   a defensible denominator. The owner confirms or amends the terms before the freeze.

Do not present the reconstructed list as the historical search. It is the set of
repositories the retained datasets came from, not proof of what was queried.

## 2. Repositories observed in the current catalogue (verifiable)

Derived from the `acces` channel of the 37 catalogued datasets:

- PhysioNet (get-zip and static file endpoints)
- Synapse (synapse.org)
- Zenodo
- Mendeley Data
- IEEE DataPort
- Kaggle
- UCI Machine Learning Repository
- 4TU.ResearchData
- GitHub / git repositories (dataset code + links)
- Google Forms / institutional web forms and EULAs (AMASS, Motion-X, NTU RGB+D)
- Direct institutional URLs and by-email lab requests (Toronto NeuroFace, CARE-PD)

Stage-0 meta-catalogues and mined reviews listed in the project source spreadsheets
were the upstream sourcing tools. Their exact list is in the two xlsx catalogues.

## 3. Proposed search (to run once, then date each source)

Inclusion criteria (write these before the freeze, do not change after):
- Human subjects.
- Contains movement time series: video-derived pose, IMU/wearable, marker-based mocap,
  or force/kinematic sensor traces.
- Pathological movement OR an explicitly healthy-movement base usable for pretraining.
- Publicly listed, even if access is gated (Synapse, EULA, DataPort). Gated-but-listed
  counts as a candidate; its access outcome is the audit's subject.

Exclusion criteria:
- No movement time series (pure imaging, pure genetics, pure clinical scores, voice- or
  keystroke-only unless retained explicitly as auxiliary).
- Tools, demos, or software packages that are not themselves a subject corpus
  (for example visionMD). These are excluded from the audit DENOMINATOR and the reason
  is recorded (task 6).
- Non-public in-house data (the CODY-1/2/3 cohorts). These never enter the public
  inventory or the coverage counts; they may appear in the paper only as an example of
  what is not currently shareable.

Proposed English search terms (to confirm with owner):
- hyperkinetic movement disorder dataset; dystonia video dataset; tremor accelerometer
  dataset; chorea wearable dataset; myoclonus motion dataset; tic disorder video;
  ataxia gait dataset; Parkinson gait IMU dataset; freezing of gait dataset;
  Huntington accelerometry; human pose estimation clinical movement; markerless motion
  capture patients; SMPL healthy motion; egocentric wearable activity healthy.

Per-source procedure to run and DATE:
1. Query each repository in section 2 with the terms above.
2. Record the query string, the source, the date, and the hit count.
3. Apply inclusion/exclusion, record the count kept.
4. Write the last-queried date per source into this file.

Last-queried date per source: `unknown` for the historical pass; to be filled when the
clean pass is run.

## 4. What is `unknown` and cannot be recovered

- Historical search terms and query dates: not logged at the time.
- Hit counts and rejected candidates from the original search: not logged. The audit
  therefore cannot report a true screening funnel for the historical pass, only for the
  clean re-run proposed here. This is stated in `paper/STATUS.md`.

---

## 5. VERSION 2 (2026-08-22): extension to the MoveAtlas v2 taxonomy

The MoveAtlas redesign (taxonomy v2, project plan v2) widens the search scope. This section
replaces the criteria of section 3 for every pass after 2026-08-22; sections 1 to 4
remain valid as the record of the v1 pass.

### 5.1 Inclusion criteria v2

- Human subjects.
- Movement time series (video pose, IMU, mocap, force, silhouette) OR any modality of the
  MoveAtlas 360 view that carries a motor phenomenon: EMG, EEG, LFP / ECoG, polysomnography,
  actimetry, handwriting / typing, motor voice.
- A pathological population from any cell of the taxonomy (classes A, B, comorbidities D and E),
  OR an age-conditioned normal reference (C1 adult, C2 infant / child, C3 older adult).
- Publicly listed, even when access is on request, under an EULA or by application.

Exclusions unchanged (no time series at all; tools without a corpus; data simulated by
healthy subjects imitating a pathology) plus: clinical case videos published with an article
(article licence, not a corpus).

### 5.2 Search terms per cell (used in pass P1 of 2026-08-22)

- A1 video: tremor video dataset pose hand public download camera smartphone assessment
- A2: myoclonus dataset EMG EEG recordings public download movement disorder
- A3: Tourette syndrome tic video dataset public machine learning detection
- A4 sensors: cervical dystonia wearable IMU EMG sensor dataset public recordings torticollis
- A5: self-stimulatory behavior dataset autism video stereotypy SSBD ESBD public download
- A8: hemiballismus ballism video recordings dataset public
- B1: Parkinson rigidity quantification robotic passive movement torque dataset public instrumented
- B4: mPower Parkinson smartphone dataset Sage Bionetworks access Levodopa Response Study wearable
- C2: infant general movements assessment video dataset pose estimation public preterm fidgety;
  MINI-RGBD BabyPose infant dataset download request preterm NICU depth video
- C3: elderly long-term movement monitoring accelerometer dataset PhysioNet fallers daily activity public
- D1: epileptic seizure accelerometer wearable movement dataset public download detection
- D6: CAP sleep database PhysioNet RBD REM behavior disorder polysomnography public dataset
- D7: functional tremor psychogenic movement disorder accelerometer dataset public entrainment
- M5: surface EMG public dataset walking gait patients PhysioNet clinical neurology
- E3: diabetic peripheral neuropathy gait plantar pressure dataset public download

### 5.3 Passes run, with their dates

- Pass P1: 2026-08-22, general web search engine (US index), 14 queries. Results, candidates and
  absences documented in MoveAtlas/MoveAtlas_Chasse_P1_2026-08-22.md (project disk); candidates entered in
  MoveAtlas_Matrice_couverture_v2.xlsx with the status "Identifie chasse P1". Outcome: 12 new sources,
  7 confirmed absences (A1 video, A2, A3, A8, B1, D7, E3).
- Next pass: after screening the reviews (Pecoraro 2025, Martinez-Garcia-Pena 2025,
  paroxysmal dyskinesias 2025) and the hubs (NeoVault, the GitHub EEG meta-list), and after the
  replies to the requests filed.

### 5.4 Repositories added to the list of section 2

OpenNeuro; National Sleep Research Resource / PhysioNet sleep; Temple TUH EEG Corpus; Sage
Bionetworks / Synapse (mPower); CDC NHANES; neonatal hubs (NeoVault); Epilepsy Ecosystem.

---

## 6. VERSION 3 (2026-09-11): how the search was actually executed

Sections 1-5 say what was searched and with which terms. This section
says by what, because the descriptor's Methods now states it and the two
must agree.

Three instruments, and the dated reports say which found each row:

- **Automated search passes** supplied the breadth, web-search based,
  over repository APIs and search pages. Three campaigns:
  `HUNT_2026-09-01.md` (gap-targeted), `HUNT_CLOSING_2026-09-04.md`
  (three parallel passes on the under-covered axes: non-English
  repositories, generalist repositories, recency),
  `HUNT_DEEPDIVE_2026-09-05.md` (eight passes past the protocol's edges,
  paediatric and genetic-rare phenotypes, systematic per-repository
  sweeps). The animal lane has its own, `HUNT_ANIMAL_2026-09-01.md`.
- **Manual reading** supplied the depth: review bibliographies, citation
  chasing from known deposits, the per-cell literature.
- **Manual web search** covered registries and institutional portals
  that answer no API.

The rule that makes automated breadth usable: **no automated result enters
the catalogue unchecked.** Every claim is a reading of a record page or of a
repository API, its licence verified on the hosting page; a curation pass
removes rows already held (two on 2026-09-01); every catalogued row
carries RE-VERIFY-AT-FETCH, and the fetch-time read is what settles it -
it corrected several licences and one claimed size by an order of
magnitude (MobilityAPP: 31 KB of derived parameters, not 31 MB).

This is recorded rather than smoothed away. An automated pass that is
declared, bounded and verified at the source is reproducible; one that is
hidden is not.
