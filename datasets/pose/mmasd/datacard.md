# MMASD (ASD therapy movement derivatives)

- dataset: mmasd
- family: pose  (physical path: datasets/pose/mmasd)
- MoveAtlas cells: A5 proxy (stereotypies), D5; M1, M4
- population: 32 children with ASD, >100 h therapy video as privacy-preserving derivatives; ADOS-2 scores
- n_subjects: 32
- age: school-age children
- signal: optical flow JPGs + 2D skeleton (OpenPose 25) + 3D skeleton (ROMP 71), 1,315 samples, 11 activities
- license: not specified by the authors for the DATA (the GitHub repo carries an Apache-2.0 badge, which covers the repo, not necessarily the Drive payload) ; redistribution: no, DECIDED 2026-08-28: unspecified licence = pointer; the never-sent licence email stays in the barriers file
- access: direct download via Google Drive link (no form)
- status (2026-08-22): DOWNLOADED 2026-08-28 (owner risk call: INTERNAL training only, never in any release tree): 7.1 GB via gdown from the README's Drive folder, all 5 zips integrity-tested (optical_flow 481,176 entries; 2D_openpose 256,379; ROMP 2D/3D/3D-71 312,773 each) + ADOS_rating.xlsx + README. Ingestion is its own future pass: needs OpenPose-25 and ROMP-71 joint maps in the skeleton contract
- link: https://github.com/Li-Jicheng/MMASD-A-Multimodal-Dataset-for-Autism-Intervention-Analysis
- notes: best available substitute for the empty stereotypies cell alongside ethics-gated SSBD/AV-ASD; derivatives only, no raw video
