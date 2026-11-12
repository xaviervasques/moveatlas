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
  - Body model (2026-11-12): SMPL+H, MANO/SMPL+H licence of the Max Planck Institute for Intelligent Systems
    (non-commercial research, education and artistic projects only; the model, and animations made with it, may not
    be made available in any form without MPI's written permission). Internal use only: each user downloads the
    model from mano.is.tue.mpg.de and accepts that licence (its LICENSE.txt comes with the download), and
    build_canonical_amass.py reads that copy from body_models/smplh/<gender>/model.npz, outside the repository.
    Nothing computed with it ships: the canonical AMASS records stay pointer_only, and build_public_release.py
    refuses a shipped file that is a body-model file, carries its arrays, or states an output made with it.
    docs/license_matrix.csv has no row for it, since its rows are datasets.
- known issues (2026-09-28, 2026-09-29, 2026-10-05, 2026-11-10): 404 of the 17,154 canonical records (242 in BMLhandball, 124 in BMLmovi and 38 in ACCAD, each at least 1,261 frames long) were not rigid skeletons in the shards built before 2026-09-29 (a bone length varied by more than 5 percent over the frames); joints recomputed from the source SMPL+H parameters differed from these 404 and reproduced the rigid records checked to 1e-4 torso units, so the fault was in the build, not the source. The three shards were rebuilt on 2026-09-29 by build_canonical_amass.py, which now refuses a skeleton whose bones change length: the 404 records are rigid (0 of the 17,154 records fail the 5 percent test), their order, frame counts and frame rates and both manifests are unchanged, and the other 21 subsets were not rebuilt. Anything computed from these takes before 2026-09-29 used non-rigid joints. The 2,914 records built from MoSh++ stage-II files (takes ending in _stageii.npz: every record of GRAB (1,340), SOMA (69), CNRS (79) and WEIZMANN (1,426)) were built with fps None and an empty fps cell in the manifests: these files state their rate under mocap_frame_rate (120 in every CNRS and WEIZMANN file), a key the builder reads only since 2026-10-05. The 79 CNRS and 1,426 WEIZMANN records carry 120.0, in their records and in both manifests, since 2026-11-10 (build_canonical_amass.py --only CNRS WEIZMANN --fill-fps, coordinates unchanged); the 1,409 GRAB and SOMA records still have fps None. CNRS and WEIZMANN are SMPL-X fits (surface_model_type smplx in every file; poses of 165 values per frame in the SMPL-X order root, body, jaw, eyes, hands), and the builder computed their joints with the SMPL+H model: the root and 21 body joint rotations are those of the fit, but the rest skeleton comes from the SMPL+H template and shape space driven by SMPL-X shape coefficients, so the bone proportions and joint offsets of these 1,505 records are not those of the fitted bodies; leave them out where body proportions matter. The two subsets stay in the canonical pool, flagged by this sentence, until they are built with the SMPL-X body model, which the repository does not hold. The builder skips every archive member whose file name contains "shape" or "neutral", a filter meant for the per-subject shape files that also leaves out 800 motions: 796 WEIZMANN S-shaped walks (*SShape*_stageii.npz, SMPL-X fits) and 4 DanceDB dances (*Neutral*_poses.npz); the 17,154 records hold none of them. They are to be added at the next release, with the SMPL-X build.

## Retrieval notes
Downloaded by the owner via the AMASS website (SMPL-X G per sub-dataset), staged in
`temporary/`, filed into `raw/` on 2026-07-10. Integrity of all 24 archives verified
with `tar -tjf` (see `datasets/_amass_integrity.log`).

## Processing
(pending) Extract each .tar.bz2, load SMPL-X/SMPL+H .npz, map to the canonical skeleton
(`configs/canonical_skeleton.yaml`). Keep per-sub-dataset provenance for the site probe.
Healthy base: pretraining only, no phenotype labels.
Rigidity check 2026-09-28: 404 records failed a 5 percent bone-length test (per subset: ACCAD 38, BMLhandball 242, BMLmovi 124). Rebuilt on 2026-09-29 with `build_canonical_amass.py --only ACCAD BMLhandball BMLmovi` on CPU: the 404 records were replaced, the other 2,298 records of the three shards are equal, the 21 other shards and both manifests are byte-identical, and 0 records fail the test. The three shards as built before are kept outside the repository, in `../_superseded/amass_canonical_mps_2026-07/`; the rebuild log is `_paris_logs/amass_rebuild_2026-09-29.csv` (not tracked).
Frame rates 2026-10-05: `build_canonical_amass.py` reads `mocap_frame_rate` (stage-II files) as well as `mocap_framerate`. The 2,914 stage-II records keep fps None until `build_canonical_amass.py --only GRAB SOMA CNRS WEIZMANN --fill-fps` is run, which gives each record the rate its file states and fills its cells in both manifests.
Frame rates 2026-11-10: `build_canonical_amass.py --only CNRS WEIZMANN --fill-fps` gave the 79 CNRS and 1,426 WEIZMANN records 120.0 and filled their 1,505 cells in both manifests; 0 records were replaced (every recomputed skeleton equals the stored one within 1e-4) and no other manifest line changed. The 1,409 GRAB and SOMA records keep fps None until `--only GRAB SOMA --fill-fps` is run. The shards and manifests as they were before are kept outside the repository, in `../_container_backup_20261110/amass/`.
