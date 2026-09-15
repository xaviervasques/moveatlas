# Chambers infant pose estimates + normative video metadata

- dataset: infant_pose_chambers
- family: pose  (physical path: datasets/pose/infant_pose_chambers)
- MoveAtlas cells: C2; M1
- population: pose estimates for the 94-infant evaluation set + domain-adapted infant OpenPose model + normative YouTube metadata (85 infants)
- n_subjects: 94 + 85 meta
- signal: 2D pose estimate tables + model + video metadata CSV
- license: CC BY 4.0 (confirmed via the figshare API at fetch 2026-09-01; UNDECIDED resolved) ; redistribution: yes
- access: figshare + GitHub direct download
- status (2026-08-22): DOWNLOADED AND INGESTED 2026-09-01 (owner GO): all 12 files md5 MATCHED, then 116 canonical pose records / 104 infants (85 YouTube normative with age_in_weeks + 31 clinical trials from 19 CHOP infants with sex, ages and BINS risk as eval-only attributes). New chambers_coco18 joint map added to configs/canonical_skeleton.yaml (pelvis=midpoint hips, neck direct, head=proxy nose, eyes/ears dropped); missing detections -> valid_mask False. The first REAL (non-synthetic) open infant pose in the corpus
- link: https://doi.org/10.6084/m9.figshare.8161430
