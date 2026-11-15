# 3D-LEX v1.0: ASL and NGT sign lexicons, Vicon markers and FBX animation

- dataset: lex3d
- family: pose  (physical path: datasets/pose/lex3d)
- MoveAtlas cells: C1; M1
- population: sign language signers (ASL and NGT lexicons); 4 distinct signer names on the first line of the marker CSVs (names not copied)
- n_subjects: 4
- signal: Vicon marker trajectories (CSV, *_V3D_MarkerData.csv) and FBX skeletal animation, per sign
- conditions: healthy signers; isolated signs of two lexicons (ASL, NGT)
- marker set: 53-marker body set plus hand markers (ARIEL, head, trunk, arm and hand labels); CSV columns <marker><T-X|T-Y|T-Z>
- license: CC BY 4.0 (OSF cv276 node licence, read at fetch 2026-11-12) ; redistribution: yes
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only lex3d)
- link: https://osf.io/cv276/
- DOI: none (the host issues none)
- citation: 3D-LEX v1.0: 3D Lexicons for American Sign Language and Sign Language of the Netherlands (OSF cv276)
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 4 files; canonical build OPEN: the marker CSVs carry no rate (the FBX time settings are not read); 4 distinct signer names in the CSVs where the survey said 5
- sampling rate per file: none stated in the files
- splits: no canonical records, no folds
- known issues (2026-11-12):
  - The survey reported 5 signers; the marker CSVs name 4 distinct signers on their first line.
  - No canonical build: the marker CSVs hold a frame index and no time or rate field. The FBX files carry their own time settings, not read in this pass (MoveAtlas has no FBX reader). The rate is not guessed: open until it is read from the FBX or found stated by the source.
  - Not fetched: the GLB copies (duplicate of the FBX), the handshape parts (15.1 GB) and the face components.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (4 files, subjects counted 4).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

None in this pass (see status).
