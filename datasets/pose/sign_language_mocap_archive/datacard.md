# Sign Language Mocap Archive (Studio Galt): catalogue snapshot

- dataset: sign_language_mocap_archive
- family: pose  (physical path: datasets/pose/sign_language_mocap_archive)
- MoveAtlas cells: C1; M1 (catalogue only)
- population: one signer (dataset description)
- n_subjects: 1
- signal: catalogue and documentation of an archive of about 2,700 ASL motions (inertial suit and gloves, FBX); this snapshot holds no motion file
- conditions: healthy signer; American Sign Language
- marker set: none in this snapshot
- license: CC BY 4.0 applied: the Zenodo snapshot 24149408 states CC BY 4.0, the GitHub repository states CC0-1.0 (read at fetch 2026-11-12); the stricter, attribution-requiring CC BY 4.0 is applied ; redistribution: yes (with attribution, CC BY 4.0 applied)
- tier: host_copy_ok_with_attribution (portal tier 1); access case recipe until a MoveAtlas record is published
- access: direct_download (fetch_open_mocap.py fetch --only sign_language_mocap_archive)
- link: https://doi.org/10.5281/zenodo.24149408
- DOI: 10.5281/zenodo.24149408
- citation: Sign Language Mocap Archive (Zenodo 24149408, snapshot 2026-11-11), doi 10.5281/zenodo.24149408
- status (2026-11-12): DOWNLOADED 2026-11-12 (fetch_open_mocap.py, MoveAtlas 3994070): 1 files; METADATA ONLY: catalogue snapshot, no motion file, no canonical record
- sampling rate per file: none stated in the files
- splits: no canonical records, no folds
- known issues (2026-11-12):
  - METADATA ONLY: the deposit is the catalogue, documentation and tooling of the archive; it holds no motion file, so there is no canonical record and no split. Signs would be chosen from the catalogue and fetched separately.
  - The archive's 39 .py files and its .blend file are never run or opened; its 43 images stay inside the zip.

## Retrieval notes

fetch_open_mocap.py (2026-11-12, MoveAtlas 3994070): fetch_manifest.json, fetch_log.json and downloads.sha256 in this folder; licence text in raw/licence.txt; raw/ is gitignored. Inventory: MD_FM reports/open_mocap/fetched.md (1 files, subjects counted None).
Every extracted file is untrusted data: no script, notebook, .blend file or git hook inside an archive is run or imported.

## Processing

None in this pass (see status).
