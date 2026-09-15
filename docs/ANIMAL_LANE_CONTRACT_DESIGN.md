# Animal-lane canonical contract: design (2026-09-03)

Design-first per house rule; implementation is the next ingestion
pass. Goal: animal movement records that a foundation model can
consume alongside (never mixed into) the human corpus.

## 1. Principles

- **Species separation is structural, not advisory.** Animal records
  live in their own manifests (_canonical_animal_manifest.csv) and
  never enter the six human family manifests; the site's clinical
  matrices stay single-species by construction (the no-bare-codes
  registry convention already guarantees the catalogue side).
- **One record schema, species-tagged**, mirroring the human pose
  record where physics matches:
  required fields: species (NCBI-style snake_case:
  mus_musculus, rattus_norvegicus, macaca_mulatta), model
  (none | 6-ohda | mitopark | mptp | q140 | zq175 | sod1-g93a |
  pharmacological:<agent> ...), translational_tier (healthy | toxin |
  genetic | pharmacological | naturally-occurring),
  symptom_analog (free text, e.g. "bradykinesia/hypokinesia"),
  plus the usual source, subject_ns, task, fps, n_frames.
- **Per-species skeletons are their own canonical sets** (no mapping
  onto the human 15 joints, ever): configs/canonical_animal_pose.yaml
  will declare one keypoint set per species-format pair, with the
  same direct/midpoint/proxy semantics and validity-mask rules.
- **Derived behavior representations** (MoSeq syllables, depth
  scalars) are NOT canonical signal: they ride as documented aux
  shards with their extraction provenance, exactly like OpenSim
  angles in gait120.
- Labels (lesion side, dose, genotype) are eval-only (R1 applies to
  animals too).

## 2. Per-dataset plan

| Dataset | Canonical? | Shape |
|---|---|---|
| rat7m | YES: animal pose 3D | 20-marker rat mocap at 120 Hz (verify rate on file); skeleton set `rat7m_20` from the collection's marker definition; subject_ns rat7m:s1..s5 with day in the task |
| calms21 | YES: animal pose 2D | 7-keypoint mouse set `calms21_mouse7`, two animals per frame -> TWO records per sequence (resident/intruder suffix in subject_ns, same task), pixels, validity from confidence if present |
| nlb_mc_maze | YES: animal kinematics (hand/cursor 2D trajectories) + spikes stay aux | NWB processing/behavior arrays; continuous hand position/velocity at 1 kHz bins |
| chu_pd_moseq | aux (syllables + scalars) + RAW depth kept | extraction provenance = Keypoint-MoSeq, model/lesion tags from the readme |
| moseq_pharmacobehavior | aux (scalars + syllables) | per-mouse dose/agent tags from dataset.pkl metadata |
| striatal_gait_6ohda | inspect zip first; likely aux gait measures + ephys stays raw | |
| kumar_stride_gait | aux only (summary tables; ND licence, internal) | |
| goodwin_smm (human) | already canonical IMU - not animal | |
| dandi_pd_macaque_units / 001636 | trial-event tables as aux (bradykinesia readouts: reaction/movement times); spikes stay raw pending the invasive contract | |

## 3. Validation

validate_canonical gains an `animal` family entry reading the animal
manifest with species-aware bands (no human amplitude assumptions);
mask statistics extend naturally (same valid_mask semantics).

## 4. Order of implementation (next pass)

1. configs/canonical_animal_pose.yaml + build_canonical_animal.py
   (records + manifest writer).
2. ingest_rat7m.py (mocap .mat: verify structure first), then
   ingest_calms21.py.
3. nlb behavior extraction; aux packagers for chu/moseq.
4. Site: the statistics page gains an "Animal lane" section fed by
   the animal manifest (records/hours/subjects per species), still
   fully separated from the human tables.
