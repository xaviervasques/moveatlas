# Data card: NTU RGB+D 120 (3D skeletons, healthy-motion base)

- Modality: 3D skeleton (Kinect v2, 25 joints per body, up to 2 bodies)
- Source / URL: ROSE Lab, NTU (rose1.ntu.edu.sg/dataset/actionRecognition)
- License: academic research only, non-commercial (Release Agreement)
- Access: ROSE portal login, request approved 2026-07-12 (30-day window)
- Status: raw_downloaded (3D SKELETONS ONLY; RGB/depth/IR deliberately NOT downloaded)
- Number of subjects: 106 (full NTU RGB+D 120; the S001-S017 part on disk has 40)
- Disorders covered: HEALTHY movement only (120 daily/action classes). No pathology.
- Frequency / resolution: Kinect v2 ~30 fps, 3D joints in meters, y up
- Contenu present :
  - raw/nturgbd_skeletons_s001_to_s017.zip  (56880 .skeleton, NTU-60 part, ~5.8 GB)
  - raw/nturgbd_skeletons_s018_to_s032.zip  (57600 .skeleton, NTU-120 extra; re-zipped
    from the owner's extracted download to reclaim disk, verified before deletion)
  - raw/NTU_RGBD_samples_with_missing_skeletons.txt   (302 samples to exclude)
  - raw/NTU_RGBD120_samples_with_missing_skeletons.txt (537 samples to exclude)
  - docs/ : the two reference papers (CVPR2016, TPAMI2020)
  - Total 114480 samples across 120 classes, 32 camera setups.
- Specifics:
  - Filename code SxxxCxxxPxxxRxxxAxxx = Setup, Camera, Person(subject), Replication,
    Action. Subject = P###; use it for subject-level splits.
  - The two missing-skeleton lists MUST be applied to drop corrupt/empty samples.
  - Postural + action diversity (non-locomotor); priority-1 healthy base of Handoff 3.
  - RGB video / depth / IR (hundreds of GB) intentionally excluded: out of scope,
    identifiable, and disk-prohibitive. Skeletons are exactly what the FM needs.

## Retrieval notes
Downloaded by the owner via the ROSE portal (3D skeletons category), staged in
temporary/, filed 2026-07-13. The S018-S032 part arrived extracted (113 GB of text);
re-compressed to a zip in raw/ to reclaim ~108 GB, after verifying the archive.

## Processing
(pending) Ingest to the canonical skeleton via the ntu_kinect25 mapping in
configs/canonical_skeleton.yaml (NTU 25 joints -> canonical 15, all direct, 3D meters).
Apply the missing-skeleton exclusion lists. Healthy base: pretraining only, no labels.
