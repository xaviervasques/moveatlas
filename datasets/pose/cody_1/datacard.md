# Data card: CODY-1 (adult cohort)

- Modality: pose (COCO-17 keypoints 2D) + per-frame phenomenology labels
- Source / URL: non-public in-house data (owner). NOT a public dataset.
- License: private, not shareable in current form (identifiable source video)
- Access: local only; raw video never leaves the machine (sovereignty constraint)
- Version / retrieval date: provided 2026-07-10
- Status: processed (inventoried; canonical ingestion pending)
- UPDATE 2026-09-02: the derived release is PUBLIC on Zenodo since
  2026-09-01: CODY deposit, concept DOI 10.5281/zenodo.22232609
  (v1.0.0 = 10.5281/zenodo.22232610), CC BY 4.0, open access, verified
  on the record page 2026-09-02. The License/Access lines above
  describe the in-house SOURCE (raw patient video), which stays
  private; the deposit carries only de-identified derived data.
- UPDATE 2026-09-04 (v1.1.0 = 10.5281/zenodo.22275553, published,
  API-verified): archive names now carry study + extraction pipeline.
  What CODY-1 uses is dataset_0_labels_raw_cody_1_2_yolo.zip: the
  per-rater expert labels TOGETHER WITH the YOLOv8 COCO-17 keypoint
  time-series of the 25 adults (the earlier claim that the adult
  kinematics lived in the merged archives was wrong - those, and all
  *_cody_3_sam3 archives, are CODY-3 SAM3 products, a different
  extraction of the same subjects).
- Number of subjects: 25 (4 controls C1-C4 + 21 patients)
- Disorders covered: hyperkinetic (Dystonia, Tremor, Myoclonus, Chorea, Tics,
  Athetosis, Ballismus, Stereotypie), multi-label per frame
- Frequency / resolution: ~33 fps (dt=0.03s), keypoints in image PIXELS
- Specifics:
  - 125 real xlsx (134 AppleDouble ._* + 3 .DS_Store = macOS noise, excluded).
  - Two raters (dataset_dd, dataset_lc). Exam conditions in rest_posture_action
    (Rest / Posture / Action), French labels ("Repos" = rest).
  - Columns: time, 17 COCO keypoints x/y, per-keypoint *_distance, 8 ordinal
    phenomenology labels (e.g. Dystonia {0,1,2}).
  - REDUNDANCY: these 25 adults are the SAME subjects as cody_2/training and
    cody_3/01-03. Canonical source for the adult labeled cohort = cody_3.
    cody_1 is a flattened legacy export; do NOT ingest it as independent samples.

## Retrieval notes
Provided directly by the owner on the external disk. Not downloaded. See
`build_cody_manifest.py` and `datasets/pose/cody_1/processed/manifest.csv`.

## Processing
Inventoried by `build_cody_manifest.py` (2026-07-10). Namespaced subject registry:
`datasets/pose/_cody_registry.csv` (adult:* ids). Canonical-skeleton ingestion pending
(COCO-17 -> canonical mapping, `configs/canonical_skeleton.yaml`). Labels are for
fine-tuning and evaluation probes only, never for pretraining.
