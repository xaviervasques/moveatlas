# Canonical skeleton: design note

Companion to `configs/canonical_skeleton.yaml`. Date: 2026-07-10.

Designed from the real joint sets of the processed datasets and validated against them
by `scripts/validate_canonical_skeleton.py` (all three sources resolve the 15 canonical
joints, 0 missing).

## The 15-joint canonical set

Anatomical INTERSECTION shared across the three current keypoint sources:

    pelvis(root), neck, head,
    left/right shoulder, elbow, wrist,
    left/right hip, knee, ankle

Why 15 and not more or fewer:
- The strict body intersection is the 12 limb joints (shoulder/elbow/wrist/hip/knee/
  ankle, both sides), present natively in all three sources.
- `head` and `pelvis` are added because every source can supply them (directly or by a
  documented derivation), and they are needed for orientation and root-centering.
- `neck` is added for the torso reference segment; CODY/COCO lacks a neck joint, so it
  is derived as the shoulder midpoint (flagged, not invented in 3D).
- SMPL extras (spine1-3, collars, feet, hands), Li/Taati `face`, and COCO eyes/ears are
  dropped from the canonical set. They stay in raw/processed and can be revisited if a
  future source justifies a richer skeleton.

## How each source maps (validated on real samples)

| canonical   | SMPL/CARE-PD (3D) | Li/Taati (2D)        | CODY COCO-17 (2D)              |
|-------------|-------------------|----------------------|--------------------------------|
| pelvis      | pelvis            | midpoint(Lhip,Rhip)  | midpoint(left_hip,right_hip)   |
| neck        | neck              | neck                 | midpoint(l/r shoulder)         |
| head        | head              | head                 | proxy: nose                    |
| shoulders.. | direct            | Lsho/Rsho            | direct                         |
| elbows..    | direct            | Lelb/Relb            | direct                         |
| wrists..    | direct            | Lwri/Rwri            | direct                         |
| hips..      | direct            | Lhip/Rhip            | direct                         |
| knees..     | direct            | Lkne/Rkne            | direct                         |
| ankles..    | direct            | Lank/Rank            | direct                         |

## Decisions applied (tranched in Handoff 3, section 4)

- **No 2D->3D lifting.** Native dimensionality is kept; each sample carries a `dim`
  flag (2 or 3), stored as `(T, 15, 3)` with the z-channel masked for 2D samples, plus
  a joint-presence mask for derived/proxy joints and a learned modality embedding.
  Lifting would fabricate depth and bias the embedding.
- **No global fps decimation.** fps is a per-sample attribute. A myoclonic jerk lasts
  20-100 ms; decimating to 25-30 fps erases it. CODY is ~33 fps (measured); CARE-PD and
  Li/Taati fps are per-record (CARE-PD stores an `fps` field, currently unset).
- **Normalization order**: root-center on pelvis, flip image-y to up for 2D sources,
  scale by torso length (pelvis-neck), optional Procrustes for 3D (CARE-PD already
  orientation-canonical, reuse).

## Labels

CODY's 8 phenomenology labels (Dystonia, Tremor, Myoclonus, Chorea, Tics, Athetosis,
Ballismus, Stereotypie) never enter pretraining; they are for fine-tuning and the
phenotype probe of the evaluation protocol.

## What this unlocks

With the mapping fixed and validated, the next ingestion step can emit canonical
`(T, 15, C)` tensors + masks + per-sample (dim, fps, modality, provenance) for CARE-PD,
Li/Taati, and CODY, then extend the same declarative pattern to the IMU and healthy-base
sources. Splits stay at PATIENT level on namespaced ids.
