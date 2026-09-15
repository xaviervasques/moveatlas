# Data card: CODY-2 (pediatric / inference split)

- Modality: pose (COCO-17 keypoints 2D) + per-frame labels (training) ;
  keypoints without labels (inference, pediatric)
- Source / URL: non-public in-house data (owner). NOT a public dataset.
- License: private, not shareable in current form (identifiable source video)
- Access: local only; raw video never leaves the machine (sovereignty constraint)
- Version / retrieval date: provided 2026-07-10
- Status: processed (inventoried; canonical ingestion pending)
- UPDATE 2026-09-02: the derived release is PUBLIC on Zenodo since
  2026-09-01 (CODY deposit, 10.5281/zenodo.22232609, CC BY 4.0): the
  pediatric cohort ships as dataset_2 inside the datasets_1_2_3_*
  files (SAM3 timeseries + results). Raw video stays in-house; the
  License/Access lines above describe the in-house source.
- UPDATE 2026-09-04 (v1.1.0 = 10.5281/zenodo.22275553, published,
  API-verified): CODY-2's OWN pediatric YOLOv8 keypoints are now
  deposited too - dataset_2_timeseries_cody_2_yolo.zip (48 MB), the
  12 unlabeled pediatric COCO-17 time-series this study's inference
  actually consumes (v1.0.0 only carried the SAM3 extraction of
  dataset_2). CODY-2 is therefore genuinely reproducible from public
  data as of v1.1.0; the training-side labels + adult YOLO keypoints
  are dataset_0_labels_raw_cody_1_2_yolo.zip (shared with CODY-1).
- Number of subjects: training = 25 adults (redundant with cody_1/cody_3) ;
  inference = 12 pediatric subjects ("PEDIA")
- Disorders covered: same 8-label hyperkinetic scheme
- Frequency / resolution: ~33 fps, keypoints in image PIXELS
- Specifics:
  - 137 real xlsx (147 AppleDouble excluded). Split: training/ (dataset_dd, dataset_lc,
    dataset_action, dataset_posture, dataset_rest) and inference/dataset_2 (12 pediatric
    timeseries).
  - REDUNDANCY: training/ holds the SAME 25 adults as cody_1 and cody_3. Canonical
    source = cody_3. inference/dataset_2 (pediatric) is mirrored in cody_3 external
    dataset_2.
  - Pediatric inference subjects have NO per-frame labels here; their subject-level
    multi-rater diagnosis is in cody_3/dataset_inference.xlsx (sheet dataset_2).

## Retrieval notes
Provided directly by the owner. Not downloaded. See
`datasets/pose/cody_2/processed/manifest.csv`.

## Processing
Inventoried by `build_cody_manifest.py` (2026-07-10). Ingest pediatric subjects from
cody_3 external dataset_2 (video + SAM3) to avoid duplication. Labels for evaluation
only.
