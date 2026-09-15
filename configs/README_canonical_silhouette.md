# Canonical silhouette contract

`configs/canonical_silhouette.yaml`. A third pose-family modality, alongside the
15-joint skeleton (`canonical_skeleton.yaml`) and the two signal contracts
(`canonical_imu.yaml`, `canonical_force.yaml`).

## Why a separate contract

SAM3 segments the body and emits a dense **silhouette outline**, not joint positions.
There are no reliable keypoints to fold into the 15-joint skeleton, but the outline's
shape dynamics carry hyperkinetic movement (chorea, dystonia, whole-body tremor). So the
SAM3 stream gets its own contract instead of being forced into the keypoint schema.

The same SAM3 exporter (`*_sam3_timeseries.xlsx`) produced both the koa_pd_nm videos and
the CODY external cohorts, so one contract and one reader
(`build_canonical_silhouette.py`) serve both.

## What is stored (per recording = one video)

| field | shape | meaning |
|-------|-------|---------|
| `contour` | (T, 64, 2) f32 | resampled silhouette outline, normalized |
| `scalars` | (T, 8) f32 | shape descriptors (below) |
| `detect_mask` | (T,) bool | subject segmented this frame |
| `scalar_mask` | (8,) bool | which scalar channels present |
| `fps` | float | native rate of this recording (no global resample) |
| `scale` | float | per-recording normalization scale (px) |
| `dim` | int | 2 (image plane; no depth) |
| `subject_ns`, `cohort`, `severity`, `sequence`, `source` | | metadata / labels |

Owner decision (2026-07-16): keep the **64-point contour + 8 shape scalars**. SAM3 also
emits a 12x8 interior grid; it is dropped (~50% NaN, view/size dependent, redundant with
the contour).

Scalars (fixed order): `area, perimeter, solidity, extent, aspect_ratio, orientation_deg,
major_axis, minor_axis`. The size-dependent ones (area, perimeter, major/minor axis) are
divided by the per-recording scale (area by scale^2) so they are camera-distance invariant;
the dimensionless ones are stored raw.

## Normalization (mirrors the 2D pose contract)

1. center on the per-frame centroid,
2. flip image-y (y grows downward in image space) so up is positive,
3. scale by S = median over detected frames of the major-axis length (person height, px),
4. undetected frames -> zeros, `detect_mask = False`.

## Caveat

The 64 contour points are arc-length resampled from a consistent start, but point-to-point
correspondence across frames is **approximate** (the resampling start can drift a point or
two). Treat the contour as an ordered set, not tracked landmarks.

## Ingested

| source | recordings | subjects | notes |
|--------|-----------|----------|-------|
| koa_pd_nm | 190 | 96 | KOA 50 + PD 16 + NM 30; key `koa_<COH>_<SEV>_<num>` |
| cody_external | 36 | 34 | dataset_1/2/3; key `cody_ext_ds<d>_P<xx>`; 2 rated |

Output: `datasets/pose/<source|cody_3>/processed/canonical_silhouette.pkl` +
`datasets/_canonical_silhouette_manifest.csv` (source of truth for splits).
Labels (cohort, severity, CODY multi-rater phenomenology) are for evaluation only, never
pretraining.
