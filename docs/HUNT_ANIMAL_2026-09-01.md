# Animal-lane hunt report (2026-09-01, standing owner GO)

Owner directive: explore animal movement/symptom data and include it
if it exists. Agent sweep with page-verified licences, curated same
day; acquisitions started immediately under the standing GO.
CONVENTION adopted: animal registry entries carry NO bare A-E or M
codes (free-text "analog" mapping instead) so clinical symptom and
modality matrices never mix species.

## Included in the catalogue (9 entries, family `animal`)

| Dataset | Model/species | Licence | State |
|---|---|---|---|
| chu_pd_moseq | mouse 6-OHDA + MitoPark, Keypoint-MoSeq open field | CC BY 4.0 (API) | downloading (10.2 GB) |
| moseq_pharmacobehavior | ~700 dosed mice (haloperidol...stimulants) | CC BY 4.0 | downloading (~3.1 GB) |
| striatal_gait_6ohda | mouse 6-OHDA gait + opto-tagged striatal ephys | CC BY 4.0 (DataCite) | queued (Zenodo 50x at hunt time) |
| nlb_mc_maze | macaque reach, continuous hand kinematics + spikes | CC BY 4.0 (DANDI) | downloading (694 MB) |
| rat7m | rat 3D mocap socle (7M frames) | CC BY 4.0 (all 8 articles API-verified) | mocap core DOWNLOADED (7 .mat, 255 MB); 15.3 GB video queued |
| calms21 | mouse pose/behavior socle | MIXED (dataset CC BY-NC-SA / components CC BY) | queued behind on-page licence verify (CaltechDATA 403s scripts) |
| kumar_stride_gait | 62 strains + SOD1 ALS gait summaries | other-nc (NON-COMMERCIAL) | downloading tables (container skipped); pointer tier |
| alphasyn_catwalk | a-syn transgenic CatWalk gait, 90 runs | CC BY (article) | supplementary NOT reachable from PMC (publisher page; owner-browser route) |
| locomouse_ataxia | reeler/pcd ataxic strides | CC BY (eLife source data) | queued, light |

Runner-up recorded, not catalogued: MARS, MABe22, OpenMonkeyStudio,
OpenApePose, AP-10K, DLC benchmarks incl. Horse-30 (all licence-
unverified or NC; socle-only value), IBL mouse behavior (CC BY, task
wheel kinematics, not gait; revisit if the model needs it), SLEAP
fixtures.

## The asymmetry finding (casebook case 10)

The animal side REPEATS the human open-data asymmetry: the
hypokinetic/parkinsonian pole is servable (6-OHDA, MitoPark,
pharmacological catalepsy, a-syn and ALS gait), while the
hyperkinetic pole is a desert: NO open harmaline tremor, NO dystonia
model kinematics (the Tor1a DYT1 MoSeq study is
data-available-on-request), NO tic-model video, NO HD-model raw
kinematics (R6/2 and Q175 corridor data exists only as supplementary
tables; CHDI/HDinHD is registration-gated), NO levodopa-induced
dyskinesia video. Veterinary movement data (canine, equine disease)
is entirely proprietary; zebrafish/fly PD-model locomotion is
published without deposits.

## Taxonomy plan for the animal lane (to formalize at ingestion time)

species tag (mus_musculus, rattus_norvegicus, macaca_mulatta...),
model tag (6-ohda, mitopark, mptp, sod1-g93a, pharmacological/...),
translational tier (toxin / genetic / pharmacological /
naturally-occurring), and symptom-ANALOG mapping in free text. NC
licences (kumar, DLC benchmarks) constrain training use and stay
pointer-tier.

## DANDI cross-check

No additional MPTP/6-OHDA/HD dandiset carries downloadable kinematic
or video behavior (001177 is ephys-only open-field, 001538 is
imaging/ephys LID). Confirmed via the API.
