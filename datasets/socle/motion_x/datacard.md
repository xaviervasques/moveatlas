# Data card: Motion-X++ (healthy-motion base)

- Modality: motion (SMPL-X whole-body params, keypoints, mesh) + text labels
- Source / URL: https://huggingface.co/datasets/YuhongZhang/Motion-Xplusplus
  (Motion-X++, NeurIPS 2023 lineage). Original toolkit/repo also kept (see below).
- License: non-commercial research (Motion-X license). HuggingFace copy is public /
  non-gated. Mocap subsets (AMASS/GRAB) keep their own MPI licenses.
- Access: public HuggingFace download (no EULA, no form); owner account VasquesXavier
- Status: raw_downloaded (47 GB motion + 488 MB text + 89 MB video, download clean,
  0 incomplete files, no LFS pointers)
- Number of subjects: unknown at subject level (dataset is clip/motion-indexed;
  ~15.6M poses / 81.1K clips across subsets)
- Disorders covered: HEALTHY movement only (pretraining base). No pathology.
- Contenu present (motion_x_plusplus/) :
  - motion/keypoints, motion/mesh_recovery (global + local), motion/motion_generation
    (joint, new_joint, new_joint_vecs, smplx322, root_body_pos_vel_hand_pos_vel)
  - text/pose_description, text/semantic_label
  - video/ (sample visualization GIFs only)
  - subsets seen: idea400 (self-recorded, covers NTU-RGBD120 actions), music, haa500,
    and others, each as .zip per representation.
- Specifics:
  - IDEA400 is Motion-X's licensed replacement for NTU-RGBD120 (400 daily actions).
  - The IDEA Research team does NOT redistribute original RGB video; only motion +
    text. Stays within scope (no identifiable video).
  - Also on disk: `Motion-X-main/` = the original GitHub toolkit (processing scripts,
    split index files). Useful for reconstructing the mocap subsets against AMASS/GRAB
    (already in socle/amass/raw) if the original Motion-X format is ever needed.

## Retrieval notes
Downloaded 2026-07-10 via `hf download YuhongZhang/Motion-Xplusplus --repo-type dataset
--local-dir datasets/socle/motion_x/raw/motion_x_plusplus`. Log:
`datasets/_motionx_download.log`. Resumable; re-run to complete if interrupted.

## Processing
(pending) Unzip the chosen representation (smplx322 or keypoints), map to the canonical
skeleton (`configs/canonical_skeleton.yaml`). Keep per-subset provenance for the site
probe. Healthy base: pretraining only, no phenotype labels.
