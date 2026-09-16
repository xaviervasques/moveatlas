# The privacy gate: no byte leaves without passing it

Owner mandate 2026-08-28: before anything is published, a paranoid cleanup
and audit pass. This document is that pass, made systematic. Rule zero:
**a release that has not passed the gate does not ship, whatever the
deadline.** The gate is enforced twice: by a human read of this checklist
and by the automated linter (`release_lint.py`), and BOTH must pass.

## 1. What may never appear in any public artifact

- Raw video of any PATIENT, from any source (CODY 05_external_videos and
  every patient capture; koa_pd_nm videos; any clinical video).
- Any render where a patient remains visible, including segmentation
  OVERLAYS and SIDEBYSIDE composites (`*_sam3_overlay.mp4`,
  `*_sam3_sidebyside.mp4`).
- Anything from a source whose licence does not allow redistribution
  (every registry row whose redistribution column does not start with
  "yes": 92 of the 169 catalogued datasets on 2026-09-17) or that is
  ND-restricted (CARE-PD harmonized tensors).
- Identifiers: names, dates of birth, addresses, faces, voices, hospital
  ids. Subject ids in releases are our namespaced pseudonyms only.
- Credentials or tokens of any kind, including in notebooks, logs and
  git history of the export repo.

## 2. What is allowed, by explicit rule

- CODY: keypoints, per-frame labels, PURE segmentation masks
  (`*_sam3_mask.mp4`) and timeseries (`*_sam3_timeseries.xlsx`);
  CONTROL raw videos (and only controls).
- Canonical records of the redistributable sources (77 on 2026-09-17,
  54 of them served by a published record), each under the licence its
  source states (moveatlas/data/zenodo_records.json lists the records),
  with its citation attached.
- All documentation, contracts, tools, manifests, checksums.

## 3. The audit steps (run in order, record the outcome)

1. **Inventory diff**: the release tree is built by ALLOWLIST (patterns in
   release_lint.py), never by blocklist. Anything not matched is refused by
   default. The linter prints every refused path; a human reads that list.
2. **Suffix partition check (CODY)**: no file under a cody path unless it
   matches the allowed suffixes; count masks == count timeseries per
   subject as a cross-check.
3. **Licence gate**: every dataset directory in the release must map to a
   host_copy_ok_with_attribution row of license_matrix.csv. pointer_only
   and private rows must have ZERO data files in the tree.
4. **Content sampling**: open N random files per class and LOOK (a video
   labeled mask that shows a face fails the whole gate); check video
   streams of every shipped .mp4 (masks are binary/grayscale; a natural-
   image histogram fails).
5. **Metadata scrub**: strip EXIF/creation metadata from shipped media;
   verify xlsx/csv column names carry no hospital identifiers.
6. **Manifest + checksums**: the release ships a sha256 manifest of itself;
   the gate re-verifies it after the scrub.
7. **Second pair of eyes**: the owner signs off on the linter report
   before any upload. The report is committed alongside the release tag.

## 4. Standing paranoia rules

- The export/moveatlas_repo tree (site + docs) must contain NO data files at
  all, ever; the linter runs on it too.
- Nothing in _paris_logs/, Downloads/, or scratch dirs is ever part of a
  release.
- When in doubt about a single file: it stays out, and the doubt is
  recorded in the datacard. Exclusion is reversible; a leak is not.
