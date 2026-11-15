# CMU Graphics Lab Motion Capture Database (C3D)

- dataset: cmu_mocap
- family: pose  (physical path: datasets/pose/cmu_mocap)
- MoveAtlas cells: C1; M1
- population: healthy performers (actors, dancers, athletes and lab members) in 109 subject folders; a folder is a capture session, not a verified person
- n_subjects: 109
- signal: 3D marker trajectories, 41-marker Vicon full-body set (41 to 674 points per file with unlabelled and virtual points), C3D
- conditions: healthy; everyday actions, locomotion, sport, dance, two-person interaction
- marker set: 41-marker Vicon full body (LFHD..RTOE, Plug-in Gait names), labels prefixed by an actor name
- license: CMU Graphics Lab Motion Capture Database terms (mocap.cs.cmu.edu, read at fetch 2026-11-12): free for all uses; may be copied, modified or redistributed without permission (FAQ); may not be resold directly, even in converted form (home page). Not a Creative Commons licence. No NC condition (commercial use is allowed; only resale of the data itself is excluded) and no ND condition (modification and conversion are allowed): open under the program's definition, with the no-resale sentence carried into any release ; redistribution: yes (no direct resale of the data, even converted; the no-resale sentence travels with any copy)
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only cmu_mocap; C3D zips only)
- link: http://mocap.cs.cmu.edu/
- DOI: none (the host issues none)
- citation: CMU Graphics Lab Motion Capture Database, http://mocap.cs.cmu.edu/ (no DOI)
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 5 files; CANONICAL 2026-11-12 (ingest_open_mocap.py, joint map open_cmu_vicon41): 2533 3D pose records / 109 subjects / 10.94 h at native rates (120 Hz x 1978, 60 Hz x 555); measured body axis +z x 2494, +x x 19, +y x 9, -x x 4, -y x 4, -z x 3; 0 calibration or static trials skipped, 4 refused or unreadable, 85 with a joint unresolved in that file; 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 22 / 22 / 22 / 22 / 21; no subject in two folds; same persons and takes as AMASS's CMU subset (same_person_as on the records)
- sampling rate per file: 120 Hz x 1978, 60 Hz x 555 (records of the canonical build; per-sample fps, never resampled); inventory headers: C3D 120 Hz x 1873, 60 Hz x 522
- splits: 5 subject-level folds (cross_patient_folds, seed 0; datasets/_subject_folds_open_mocap.csv), subjects per fold 22 / 22 / 22 / 22 / 21; no subject in two folds
- known issues (2026-11-12):
  - A subject folder is a capture session: one performer may appear in several folders, and a take can hold two actors (one record per actor, both under the folder). Splits by folder cannot promise person-disjointness across folders.
  - 13 pairs of subject folders hold byte-identical C3D file sets (SHA-256 of every file; 335 files in the second folder of the pairs): 018 and 019, 020 and 021, 022 and 023, 033 and 034, 060 and 061, 063 and 064, 070 and 073, 074 and 084, 077 and 139, 083 and 122, 091 and 105, 093 and 103, 106 and 141. The records of the second folder repeat those of the first (405 records, 1.20 h of the 10.94 h). In datasets/_subject_folds_open_mocap.csv, 11 of the 13 pairs fall in two different folds, so the folds of this source are not take-disjoint. Count each take once, and keep each pair in one fold.
  - The persons and takes are those of AMASS's CMU subset (held in MoveAtlas as amass, namespace amass:CMU:CMU_<n>). Single-actor records carry same_person_as (and same_take_as when the AMASS take exists): one person, two packagings. In MD_FM the AMASS CMU persons sit on the training side, so the lockbox is not touched, but a training pool must not count a take twice.
  - The laboratory vertical is +z. The measured body axis (field up_axis) departs from it on takes performed lying, swimming or upside down (the swimming takes of folders 125 and 126, for instance) and on takes with gross marker errors.
  - The host publishes no checksum: sizes from Content-Length, and the zip CRC32 checked at extraction.
  - Actor label prefixes (sometimes a performer's name) are stripped at ingestion and never propagated.
  - Not fetched: allavi.zip (video of the performers) and allasfamc.zip (skeleton fits of the same takes).

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (5 files, subjects counted 109).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

ingest_open_mocap.py --only cmu_mocap (readers in mocap_readers.py; joint map open_cmu_vicon41 in configs/canonical_skeleton.yaml): shards processed/canonical/<source>_<subject>.npz (moveatlas-record/1), processed/ingest_audit.csv (one row per file: skipped, refused or built, with the pelvis validity and the measured up axis), rows in datasets/_canonical_manifest.csv. Then ingest_open_mocap.py --folds.
