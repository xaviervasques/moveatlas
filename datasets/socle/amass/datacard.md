# Data card: AMASS (healthy-motion base)

- Modality: mocap (SMPL-X / SMPL+H body parameters, .npz per motion)
- Source / URL: https://amass.is.tue.mpg.de (Max Planck IS), per-sub-dataset EULA
- License: non-commercial research (per sub-dataset license, MPI)
- Access: account + EULA accepted by owner (2026-07-10)
- Status: raw_downloaded (24 sub-datasets as .tar.bz2, ~31 GB, integrity-checked)
- Number of subjects: ~344 (aggregate over the full AMASS corpus; per-sub-dataset
  counts vary, to be confirmed per sub-base after extraction)
- Disorders covered: HEALTHY movement only (pretraining base). No pathology.
- Frequency / resolution: mocap-derived, high frame rate; SMPL-X/SMPL+H params
- Sub-datasets present (24) : ACCAD, BMLhandball, BMLmovi, BMLrub, CMU, CNRS, DFaust,
  DanceDB, EKUT, EyesJapanDataset, GRAB, HDM05, HUMAN4D, HumanEva, KIT, MoSh, PosePrior,
  SFU, SOMA, SSM, TCDHands, TotalCapture, Transitions, WEIZMANN.
- Specifics:
  - Postural / non-locomotor diversity: this is the priority-1 healthy base that the
    locomotor-only corpus was missing (Handoff 3). Conditions generalization to dystonia.
  - GRAB (grab.is.tue.mpg.de) is stored here in AMASS SMPL-X format; it also feeds the
    Motion-X mocap pipeline (see socle/motion_x).
  - To USE the data (not just store it) the SMPL+H and DMPL body models are required
    (mano.is.tue.mpg.de, smpl.is.tue.mpg.de). The project already has SMPL_NEUTRAL.

## Retrieval notes
Downloaded by the owner via the AMASS website (SMPL-X G per sub-dataset), staged in
`temporary/`, filed into `raw/` on 2026-07-10. Integrity of all 24 archives verified
with `tar -tjf` (see `datasets/_amass_integrity.log`).

## Processing
(pending) Extract each .tar.bz2, load SMPL-X/SMPL+H .npz, map to the canonical skeleton
(`configs/canonical_skeleton.yaml`). Keep per-sub-dataset provenance for the site probe.
Healthy base: pretraining only, no phenotype labels.
