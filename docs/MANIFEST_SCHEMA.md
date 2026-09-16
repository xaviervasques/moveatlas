# Canonical manifests and record dicts: column-by-column schema

Written 2026-09-08 from the files on disk (headers, first rows, and one
record opened per source), cross-checked against configs/canonical_*.yaml.
Six canonical families, six manifests under datasets/, one record-dict
contract per family. Examples below are verbatim first rows, not invented.

The manifests are the source of truth for splits and counts: every
record on disk has exactly one manifest row, and paper/build_figure2.py,
paper/build_harmonization_table.py and paper/build_demographics.py read
only these files (records are never opened to count anything).

On-disk container: since 2026-09-08 every canonical container is a
self-describing `moveatlas-record/1` .npz (a zip with one .npy member per
array plus meta.json carrying a `"format": "moveatlas-record/1"` tag);
the pickles the migration replaced still sit next to them until deletion
and must not be opened by new code. The format itself is documented in
docs/RECORD_FORMAT.md (reference implementation moveatlas/records.py).

Conventions shared by all six manifests:

- `source`: the record-level dataset name. It is NOT always the registry
  id: mask_statistics.SOURCE_ALIAS maps the eight record-level names that
  differ (semg_walking -> physionet_semg_walking, cervical_motion ->
  cervical_motion_multiplanar, modys -> modys_video, ntu -> ntu_rgbd,
  cody -> cody_1, cody_external -> cody_3, cap_sleep_chin -> cap_sleep,
  seizeit2_emg -> seizeit2, weargait -> weargait_pd). Every consumer
  must apply the alias before joining on docs/datasets_index.csv.
- `subject_ns`: the namespaced subject id, the leakage key for
  patient-level splits. Format `<namespace>:<id>` with optional extra
  colon-separated levels (`care_pd:3DGait:0`,
  `stroke_gait:able_bodied:S001`); the silhouette family uses
  underscores instead (`koa_KOA_EL_001`, `cody_ext_ds1_P28`), see the
  disagreement list at the end. A namespace is shared by every packaging
  of the same humans (the CODY studies), so one person cannot sit on
  both sides of a split.
- `fps`: the NATIVE sampling rate of that record, float, never resampled.
  Blank when the source does not declare it and it could not be measured
  (pose only, see below).
- `n_frames`: the number of time samples of the record; hours =
  n_frames / fps / 3600.
- Encoding: UTF-8, LF, comma-separated, header row, one row per record,
  no quoting unless a field contains a comma.

## 1. Pose: datasets/_canonical_manifest.csv

Header: `source,subject_ns,take,dim,fps,n_frames,modality`

Example rows:

```
care_pd,care_pd:3DGait:0,vid0073_0055,3,30,204,3d_meter
care_pd,care_pd:3DGait:0,vid0073_0152,3,30,226,3d_meter
care_pd,care_pd:3DGait:1,vid0077_0061,3,30,312,3d_meter
```

| column | type | meaning | example |
|---|---|---|---|
| source | str | record-level dataset name (alias to registry id) | `care_pd`, `ntu`, `cody` |
| subject_ns | str | namespaced subject id | `amass:ACCAD:ACCAD_Female1Gestures_c3d` |
| take | str | the recording / clip / trial id within the subject | `vid0073_0055`, `S001C003P004R002A038` |
| dim | int | native dimensionality, 2 or 3; never lifted | `3` |
| fps | float or blank | native frame rate; blank when undeclared and unmeasurable | `30`, `120.0`, blank for li_taati / modys / remap_open |
| n_frames | int | frames in the record | `204` |
| modality | str | source space token: `2d_pixel` or `3d_meter` | `3d_meter` |

Written by: build_canonical.py (li_taati, care_pd, cody),
build_canonical_amass.py, build_canonical_motionx.py, build_canonical_ntu.py,
build_canonical_modys.py, ingest_vidimu.py, ingest_infant_pose_chambers.py,
and the remap_open / stroke_gait / gait120 pose ingest scripts that append
rows with the same header.

Record dict (configs/canonical_skeleton.yaml), as observed:

| field | type / shape | meaning |
|---|---|---|
| coords | float32 [n_frames, 15, 3] | the 15 canonical joints; z is zero-filled and masked when dim == 2 |
| coord_mask | bool [3] | which coordinate axes are real (x, y, z) |
| joint_mask | bool [15] | which canonical joints the source provides (direct / midpoint / proxy) |
| valid_mask | bool [n_frames, 15] | per-frame, per-joint validity (missing detections, NaN-filled joints); the family's honesty mechanism |
| dim | int | 2 or 3 |
| fps | float or None | native frame rate |
| modality | str | `2d_pixel` or `3d_meter` |
| source | str | dataset name |
| subject_ns | str | namespaced subject id |
| take | str | recording id |
| activity | str, optional | activity label where the source names the take (vidimu: `walk_forward`); absent elsewhere |
| n_frames | int | frames |
| scale | float | per-record normalization scale (torso length in native units) |
| label / labels / group | optional | eval-only labels where the source has them (stroke_gait, remap_open: `label` int8 + `group` str; cody: `labels` dict) |

Optional provenance fields observed on some sources: `analog_labels`,
`label_prefix_stripped`, `nan_filled_joints` (stroke_gait_vancriekinge).

## 2. IMU: datasets/_canonical_imu_manifest.csv

Header: `source,subject_ns,task,fps,n_frames,locations`

Example rows:

```
weargait_pd,weargait:HC100,SelfPace_matTURN,100.0,3606,head|trunk|lower_back|wrist_L|wrist_R|thigh_L|thigh_R|shank_L|shank_R|ankle_L|ankle_R|foot_L|foot_R
weargait_pd,weargait:HC108,Balance,100.0,14265,head|trunk|lower_back|wrist_L|wrist_R|thigh_L|thigh_R|shank_L|shank_R|ankle_L|ankle_R|foot_L|foot_R
weargait_pd,weargait:HC108,TUG,100.0,4381,head|trunk|lower_back|wrist_L|wrist_R|thigh_L|thigh_R|shank_L|shank_R|ankle_L|ankle_R|foot_L|foot_R
```

| column | type | meaning | example |
|---|---|---|---|
| source | str | dataset name | `weargait_pd` |
| subject_ns | str | namespaced subject id | `weargait:HC100` |
| task | str | task / run / trial id | `TUG`, `S01R01` |
| fps | float or blank | native sampling rate (blank when the source declares none) | `100.0` |
| n_frames | int | samples | `3606` |
| locations | str | pipe-separated canonical sensor locations present, in record order | `head\|trunk\|...` |

Written by: build_canonical_imu.py (HEADER constant) and the per-dataset
ingest scripts that append rows: ingest_pads.py, ingest_multimodal_fog.py,
ingest_sixmwt_lifespan.py, ingest_capture24.py, ingest_ltmm.py,
ingest_goodwin_smm.py.

Record dict (configs/canonical_imu.yaml), as observed:

| field | type / shape | meaning |
|---|---|---|
| signal | float32 [n_frames, n_locations, 9] | per present location the fixed 9-channel block acc_xyz (g), gyro_xyz (deg/s), mag_xyz (uT); absent channels are zero |
| location_ids | int64 [n_locations] | indices into the 14-location taxonomy of the config, one per stored location |
| channel_mask | bool [n_locations, 9] | which of the 9 channels are real per location |
| sample_valid | bool [n_frames, n_locations], optional | per-sample validity where the source marks gaps (fog_star only) |
| fps | float or None | native rate |
| subject_ns, task, source | str | ids |
| n_frames | int | samples |
| label | ndarray or None | eval-only dense label; dtype varies by source (daphnet float64, fog_star / hd_accel_jnet int64) |

## 3. EEG: datasets/_canonical_eeg_manifest.csv

Header: `source,subject_ns,task,fps,n_frames,n_channels,sites,record_path`

Example rows:

```
multimodal_fog,multimodal_fog:p005,task_1,500.0,127644,25,FP1|FP2|F3|F4|C3|C4|P3|P4|O1|O2|F7|F8|P7|P8|FZ|CZ|PZ|FC1|FC2|CP1|CP2|FC5|FC6|CP5|CP6,datasets/imu/multimodal_fog/processed/canonical_eeg/multimodal_fog__multimodal_fog_p005__task_1.pkl
multimodal_fog,multimodal_fog:p008,OFF_1/task_1,500.0,228047,25,FP1|...|CP6,datasets/imu/multimodal_fog/processed/canonical_eeg/multimodal_fog__multimodal_fog_p008__OFF_1_task_1.pkl
multimodal_fog,multimodal_fog:p005,task_2,500.0,10501,25,FP1|...|CP6,datasets/imu/multimodal_fog/processed/canonical_eeg/multimodal_fog__multimodal_fog_p005__task_2.pkl
```

| column | type | meaning | example |
|---|---|---|---|
| source | str | dataset name | `seizeit2` |
| subject_ns | str | namespaced subject id | `cap_sleep:n1` |
| task | str | task / session / run | `OFF_1/task_1`, `szMonitoring` |
| fps | float | native sampling rate | `500.0` |
| n_frames | int | samples | `127644` |
| n_channels | int | EEG channels stored (routed EOG/ECG/EMG are not counted) | `25` |
| sites | str | pipe-separated positive sites in channel order (10-10 names, aliases normalized) | `FP1\|FP2\|...` |
| record_path | str | repo-relative path of the per-record container; `.pkl` in rows written before the migration, resolved to the `.npz` sibling by moveatlas.records.prefer_npz | `datasets/eeg/.../canonical_eeg/<source>__<subject>__<task>.pkl` |

Written by: build_canonical_eeg.py and build_canonical_sensefog.py (both
merge into the existing manifest).

Record dict (configs/canonical_eeg.yaml), as observed:

| field | type / shape | meaning |
|---|---|---|
| signal | float32 [n_frames, n_channels] | as-recorded EEG, one column per channel, no software re-referencing |
| channels | list of dict {site, ref, kind} | montage made explicit per channel; `ref` is a site, AVG, LE, LM or REF_COMMON_UNKNOWN; seizeit2 adds `placement` |
| bad_channels | list, optional | declared-bad channels (OpenNeuro sources); the family's honesty mechanism together with the finite fraction |
| fps | float | native rate |
| unit | str | `uV` on every record |
| unit_scale | float | factor applied at ingestion (1.0, or 0.1 for sensefog whose header stored 0.1 uV units) |
| signal_kind | str, optional | `as_recorded` (sensefog) |
| filters | dict {hp_hz, lp_hz, notch_hz [, prefilter_verbatim]} | documented filters, None values when unknown |
| subject_ns, task, source | str | ids |
| n_frames | int | samples |
| label | int8 [n_frames] or None | eval-only dense label (FoG, seizure marks) |
| label_def | dict, optional | label value legend (seizeit2) |
| events | list of dict, optional | source event table (seizeit2 seizure events; sensefog markers) |
| montage, placement_scheme | str, optional | seizeit2 behind-the-ear descriptors |

## 4. EMG: datasets/_canonical_emg_manifest.csv

Header: `source,subject_ns,task,fps,n_frames,n_channels,kinds,record_path`

Example rows:

```
multimodal_fog,multimodal_fog:p005,task_1,500.0,127644,5,ecg|emg|eog,datasets/imu/multimodal_fog/processed/canonical_emg/multimodal_fog__multimodal_fog_p005__task_1.pkl
multimodal_fog,multimodal_fog:p008,OFF_1/task_1,500.0,228047,5,ecg|emg|eog,datasets/imu/multimodal_fog/processed/canonical_emg/multimodal_fog__multimodal_fog_p008__OFF_1_task_1.pkl
multimodal_fog,multimodal_fog:p005,task_2,500.0,10501,5,ecg|emg|eog,datasets/imu/multimodal_fog/processed/canonical_emg/multimodal_fog__multimodal_fog_p005__task_2.pkl
```

| column | type | meaning | example |
|---|---|---|---|
| source | str | dataset name (`semg_walking`, `cap_sleep_chin`, `seizeit2_emg` are aliases) | `gait120` |
| subject_ns | str | namespaced subject id | `gait120:S001` |
| task | str | task / trial | `level_walking_trial01` |
| fps | float | native sampling rate | `2000.0` |
| n_frames | int | samples | `5540` |
| n_channels | int | channels stored (EMG plus co-recorded aux) | `12` |
| kinds | str | pipe-separated distinct channel kinds present | `ecg\|emg\|eog` |
| record_path | str | repo-relative container path (see EEG) | `datasets/emg/gait120/processed/canonical_emg/...pkl` |

Written by: build_canonical_emg.py, build_canonical_eeg.py and
build_canonical_sensefog.py (chin / co-recorded EMG routed out of PSG and
EEG files), ingest_stroke_gait_analogs.py, ingest_cervical_motion.py,
build_canonical_drummer.py.

Record dict (configs/canonical_emg.yaml), as observed:

| field | type / shape | meaning |
|---|---|---|
| signal | float32 [n_frames, n_channels] | as-recorded values, one column per channel |
| channels | list of dict {kind, muscle, side, placement, resolved, ...} | variable channel table; `kind` in emg / ecg / eog / aux / unresolved_emg_ecg; `resolved` False = identity uncertain; some sources add `unit_in_header`, `electrode` |
| fps | float | native rate |
| unit | str | `mV`, `uV`, `uV_assumed` or `unknown`: what is proven, never guessed |
| unit_scale | float | factor applied at ingestion (1.0; 1000.0 for gait120 V -> mV; 0.1 for sensefog) |
| signal_kind | str | `raw`, `bandpassed`, `raw_per_header`, `filtered_remove_mean`, `as_recorded`, `rms_envelope_as_recorded` |
| filters | dict, None or str | {hp_hz, lp_hz, notch_hz} when documented; None (gait120, stroke_gait) or a free-text statement (drummer_tremor_model) |
| subject_ns, task, source | str | ids |
| n_frames | int | samples |
| label | ndarray or None | eval-only dense label (int8 FoG / seizure, int16 ninapro restimulus); absent on gait120 and drummer records |
| label_def, events, gait_events, notes, aux_streams | optional | source legends, event tables, 100 Hz mocap step indices (gait120), amplitude flags, footswitch / analog side streams (stroke_gait) |

## 5. Force: datasets/_canonical_force_manifest.csv

Header: `source,subject_ns,task,fps,n_frames`

Example rows:

```
physionet_gaitpdb,gaitpdb:GaCo01,GaCo01_01,100.0,12119
physionet_gaitpdb,gaitpdb:GaCo02,GaCo02_01,100.0,12119
physionet_gaitpdb,gaitpdb:GaCo02,GaCo02_02,100.0,12119
```

| column | type | meaning | example |
|---|---|---|---|
| source | str | dataset name | `gaitrec` |
| subject_ns | str | namespaced subject id | `gaitpdb:GaCo01` |
| task | str | walk / trial id | `GaCo01_01` |
| fps | float | native sampling rate | `100.0`, `300.0` |
| n_frames | int | samples | `12119` |

Written by: build_canonical_force.py, plus the gaitrec and stroke_gait
analog ingest scripts that append rows with the same header.

Record dict (configs/canonical_force.yaml), as observed:

| field | type / shape | meaning |
|---|---|---|
| force | float32 [n_frames, 2, 9] | feet (L, R) x [8 canonical insole positions + per-foot total], Newtons; absent sensors zero |
| sensor_mask | bool [2, 9] | which positions are real per foot (totals-only sources mask the 8 positions) |
| fps | float | native rate |
| subject_ns, task, source | str | ids |
| n_frames | int | samples |

No label field is stored on any force record opened.

## 6. Silhouette: datasets/_canonical_silhouette_manifest.csv

Header: `source,subject_ns,cohort,severity,sequence,fps,n_frames,n_detected,scale_px`

Example rows:

```
koa_pd_nm,koa_KOA_EL_001,knee_osteoarthritis,early,01,50.0,428,428,679.5
koa_pd_nm,koa_KOA_MD_001,knee_osteoarthritis,moderate,01,30.3,168,168,673.4
koa_pd_nm,koa_KOA_SV_001,knee_osteoarthritis,severe,01,50.0,777,777,664.2
```

| column | type | meaning | example |
|---|---|---|---|
| source | str | dataset name (`cody_external` is the alias of cody_3) | `koa_pd_nm` |
| subject_ns | str | namespaced subject id (underscore form) | `koa_KOA_EL_001`, `cody_ext_ds1_P28` |
| cohort | str | diagnosis group, eval-only label | `knee_osteoarthritis`, `hyperkinetic_external` |
| severity | str | clinical grade, eval-only; empty when the source has none | `early`, blank |
| sequence | str | walk / video id within the subject | `01`, `20250324_144251` |
| fps | float | native frame rate derived from the exporter's time column | `50.0`, `30.3` |
| n_frames | int | frames | `428` |
| n_detected | int | frames where the subject was segmented (sum of detect_mask) | `428` |
| scale_px | float | per-recording normalization scale, pixels (median major axis) | `679.5` |

Written by: build_canonical_silhouette.py.

Record dict (configs/canonical_silhouette.yaml), as observed:

| field | type / shape | meaning |
|---|---|---|
| contour | float32 [n_frames, 64, 2] | arc-length resampled outline, centred, y flipped up, divided by `scale` |
| scalars | float32 [n_frames, 8] | area, perimeter, solidity, extent, aspect_ratio, orientation_deg, major_axis, minor_axis (size channels normalized by scale) |
| detect_mask | bool [n_frames] | per-frame detection; the family's honesty mechanism |
| scalar_mask | bool [8] | which scalar channels are present |
| fps | float | native rate |
| scale | float | normalization scale in pixels |
| dim | int | 2 |
| modality | str | `silhouette` |
| subject_ns, cohort, severity, sequence, source | str | ids and eval-only labels |
| n_frames | int | frames |
| labels, label_raters, label_phenoms | optional | cody_external only: int8 [n_raters, n_phenomena] multi-rater phenomenology matrix with its rater and phenomenon lists |

## Cross-check against configs/canonical_*.yaml: disagreements to settle

1. IMU storage is compact, the config is dense. canonical_imu.yaml
   declares `signal (T, 14, 9)` + `location_mask (14,)`; records carry
   `signal [T, n_locations, 9]` + `location_ids [n_locations]` and no
   `location_mask`. Same information, different layout and names; the
   config comment should be updated to the compact form.
2. Pose mask names differ from the config. canonical_skeleton.yaml names
   `coordinate_mask` and `joint_presence_mask`; records carry `coord_mask`
   and `joint_mask`, and add `valid_mask [T, 15]`, which the config only
   mentions in a source note (modys DLC likelihood) and never declares.
3. EMG vocabularies have grown past the config. `unit` includes
   `uV_assumed` (config: mV | uV | unknown); `signal_kind` includes
   `raw_per_header`, `filtered_remove_mean`, `as_recorded`,
   `rms_envelope_as_recorded` (config: raw | bandpassed | envelope |
   rectified); `filters` is a dict, None or a free-text string (config:
   dict or null).
4. EEG extras are undeclared: `bad_channels`, `signal_kind`,
   `unit_scale` != 1.0 (sensefog), `events`, `label_def`, `montage`,
   `placement_scheme`, and a `placement` key inside channel dicts.
5. Silhouette subject ids use underscores (`koa_KOA_EL_001`), every other
   family uses the colon namespace; and cody_external records add
   `labels` / `label_raters` / `label_phenoms` the config does not list.
6. fps is None on li_taati, modys, remap_open pose records and on
   hd_accel_jnet IMU records (the configs mark these as unknown, so this
   is consistent, but consumers must treat fps as nullable in pose and
   IMU; the hour totals in Figure 2 exclude such records and say so).
7. IMU `label` dtype is not fixed (float64 / int64 across sources) while
   EEG labels are int8; the contracts state no label dtype.
8. Force records carry no label field although canonical_force.yaml lists
   `labels(optional)`; the manifest carries no cohort column either, so
   gaitpdb / gaitndd / gaitrec group membership currently lives only in
   the subject_ns prefix.
