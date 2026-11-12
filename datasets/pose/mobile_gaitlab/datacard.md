# Data card: mobile-gaitlab: video-derived gait keypoints of 1026 CP patients (Stanford/Gillette)

- Modality: family 'pose'
- Source / URL: https://github.com/stanfordnmbl/mobile-gaitlab
- License / access: data: CC BY-NC (4.0 in the SimTK DataCite record 10.18735/j0rz-0k12, 2.0 in the GitHub README), trajectories and labels on SimTK, raw clinical video not published; code: Apache 2.0 (GitHub stanfordnmbl/mobile-gaitlab); the demo video of the repository and its keypoints are Gillette material for testing only
- Version / retrieval date: catalogued 2026-09-05 (deep-dive sweep,
  pediatric/genetic-rare pass); the GitHub repository cloned 2026-09-06 (code, two model checkpoints, figure tables and a testing-only demo); the data NOT fetched
- Status (2026-09-28): CATALOGUED 2026-09-05 (deep-dive): OpenPose keypoint trajectories from 1792 clinical gait videos of 1026 patients + ground-truth labels (GDI, speed, cadence, knee flexion), published on SimTK (video-gait-v1.zip, 3.1 GB, doi 10.18735/j0rz-0k12) - the LARGEST CP video-derived signal release in existence (predominantly spastic; dyskinetic fraction not delineated). FETCH CANDIDATE: the data are not on disk. The shallow clone of the GitHub repository made 2026-09-06 (4167ee6, 462 files, 462 MB without .git) holds the code (Apache 2.0), two model checkpoints, figure CSVs and a Gillette demo licensed for testing only; the repository licence does not govern the data
- MoveAtlas cells: D3 (cerebral palsy); C1; M1
- population: 1,026 patients with cerebral palsy, 1,792 clinical gait videos (Kidzinski et al. 2020, Nat Commun, doi 10.1038/s41467-020-17807-z); none of their trajectories is on disk
- n_subjects: 1026 (source count; not held)

## Retrieval notes
RE-VERIFY at fetch. No-emails policy for application tiers.

## Processing
None. Catalogue-tier.
