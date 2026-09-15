# Why 19 datasets sit on disk without a canonical ingestion

Written 2026-08-23, after opening every one of them. The catalogue reports 19
datasets as `telecharge_brut` (raw on disk, nothing processed), which reads like a
backlog of 19 ingesters to write. It is not. Only three of them are signal a
contract could hold, and two of those are already moving.

The distinction that matters: **the canonical contracts store SIGNAL.** A table of
per-window means and kurtosis, a spreadsheet of cadence and stride length, or a
list of YouTube URLs with bounding boxes are all legitimate research artefacts and
none of them are signal. Forcing them into a signal contract would put derived
quantities where a model expects measurements.

---

## 1. Real signal, work genuinely remaining (3)

| Dataset | State | What is needed |
|---|---|---|
| **capture24** | being ingested 2026-08-23 | Was sampled at 0.6 percent by v1 (10 minutes per subject). Full ingestion in progress: ~4,200 h, 151 subjects. |
| **ltmm** | download paused at 3.2 of 22.3 GB | Finish the download, then write the ingester. PhysioNet long-term movement monitoring. |
| **hubu_fis_fingertap** | 10.8 GB on disk, verified | 234 finger-tapping clips. Needs pose extraction before anything canonical exists, which is a project rather than a script. |

## 2. Annotation index, not data (1)

**gavd**  -  the archive holds `GAVD_Clinical_Annotations_*.csv`: sequence id, frame
number, camera view, gait pattern, a bounding box, and a **YouTube URL**. There
are no pose coordinates anywhere in it. Using it means downloading third-party
video and running pose estimation, which raises exactly the identifiability
question already ruled on for other YouTube-hosted clinical video. The bundled
`.pkl` copies are pandas frames from an old version and no longer load
(`pandas.core.indexes.numeric` was removed); the CSVs are the usable form.

Treat as: **pending a governance decision**, not pending an ingester.

## 3. Derived quantities and aux tables, correctly outside the signal contracts (15)

None of these should get a canonical ingestion. Each is listed with what it
actually contains, so the question does not get reopened.

| Dataset | What is actually in the file |
|---|---|
| **alameda_tremor** | 4,151 rows of per-window tremor FEATURES: magnitude mean, std, variance, median, IQR, skewness, kurtosis. No raw accelerometry. |
| **ataxie_kinect_dib** | 51 participants x 13 aggregate gait parameters (cadence, speed, stride length, base width, stance/swing phase) plus the SARA score. One row per participant. |
| **gaitdb** | Stride-INTERVAL series only, 15 subjects (young / old / PD), two columns of time and interval. The `.hea` files declare zero signals and the bundled `gait-data.tar.gz` contains the same 15 `.txt` files. The raw force never shipped. |
| **park_fingertap** | Extracted features only, as the catalogue already noted. |
| **chop_gma_features** | Feature and split tables plus two pickled AutoML models. De-identified features, not video. |
| **ilg_ataxia_tables** | Nine `.docx` aggregate tables (INAS plus Tab A-H). |
| **panelapp** | Two gene-panel TSVs. |
| **cdystonia** | TWSTRS scores, SPSS `.sav`. |
| **nqmitcsxpd** | Keystroke timing (M11). |
| **tappy_keystroke** | Keystroke timing (M11). |
| **uci_parkinson_voix** | 195 voice phonation feature vectors; fine-tuning only. |
| **kaggle_spiral** | Spiral and wave DRAWINGS as images (M11), not a motion trace. |
| **hpo** | The ontology itself. Already consumed by `build_hpo_movement_map.py`. |
| **visionmd** | A tool, not a corpus. The catalogue already records that it does not feed the model. |
| **fog_turning_filho** | Not actually un-ingested: 106 canonical records exist under `datasets/imu/fog_turning_filho/processed/`. The card and raw sit under `pose/`, which is the documented split-folder case. |

---

## Consequence for the catalogue

`telecharge_brut` currently conflates "waiting for an ingester" with "will never
have one, by design". The status is derived from whether a `processed/` directory
has files, so it cannot tell those apart on its own. Until the catalogue grows a
richer status, this file is the authority on which is which.

The honest count is therefore: **two ingesters left to write** (ltmm, and hubu_fis
after pose extraction), one governance decision (gavd), and fifteen datasets that
are already in their correct final form as aux material.
