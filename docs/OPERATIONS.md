# Operations: the standing truths a new session needs

Extracted 2026-09-08 from the handoff chain and the 360 review. Every
rule cites the section it was taken from (H8 s6 = KINEFM_HANDOFF_8.md
section 6, and so on; R360 = docs/REVIEW_360_2026-09-07.md). The
handoffs are working notes and evolve; this file is the distilled
version. When the two disagree, the LATEST handoff wins and this file
is the one to fix.

## 1. The two machines

- PC (Windows 11): repo at `<repo>` (disk migrated
  2026-09-02, H15 s6; verified after the copy with git fsck + 6/6
  sha256 spot-checks, H16 header). Env vars `MOVEATLAS_REPO` and
  `KINEFM_REPO` point at that root at User scope; fetchers, generators
  and the registry resolve through them (H15 s6 step 3, H16 header).
  Stdlib + numpy scripts run under
  `<python>` (3.12, numpy 2.4; H20 s1,
  README "Machine notes"). The venv `<venv>`
  (numpy pandas pyyaml wfdb mne scipy openpyxl awscli h5py requests)
  is the fetch/ingest environment of the Paris sessions (H8 s6); the
  `<obsolete-env>` env named in RUN1.ps1 no longer exists (H20
  s1). The torch/RTX environment question is open (H20 s1).
- Mac: the same disk mounted at `<external-volume>` (H19 header;
  `<external-volume>` in older files is the PRE-migration mount and is
  stale). Venv `/Users/xavi/.venvs/kinefm`, python 3.12, created in
  H15 (H15 header, H15 s7). The Sphinx stack (sphinx 9, pydata theme,
  gallery, myst, design, copybutton, matplotlib) lives in that Mac venv
  ONLY; the site build is a Mac task (H19 s7c, H19 s13 point 3, H21
  s5). Known conflict there: awscli pins docutils<=0.19, sphinx 9
  installed 0.22 (H19 s7c).
- The disk is exFAT (the Windows/Mac shuttle, H15 s6 step 1) with
  1 MiB clusters (H21 s1): container granularity and .git size both
  follow from that. exFAT timestamps carry a 3 h skew between the two
  machines: never date events from file mtimes across machines (H8
  s6). Hot-unplug is the enemy: run `stop_before_eject.sh` (fix its
  hardcoded mount first) before ejecting on the Mac (H15 header).
- Windows Update can reboot the PC mid-fetch (H8 s5): every fetcher is
  resumable by design; `_paris_logs/keep_awake.ps1` keeps the machine
  up without changing settings; pausing updates is an owner click.

## 2. `datasets/auxdata/`: the reserved-name rule, and its end

RESOLVED 2026-09-11 by renaming the family. It is recorded here because
the symptoms return for any path a filesystem dislikes, and because the
handoff chain up to H22 describes the corpus under the old name.

The family was `datasets/aux/`, and `aux` is a reserved DOS device name.
Git on Windows could not open any path under it ("could not open ... No
such file or directory" on files that exist), while Python and PowerShell
handled those paths fine (H8 s6). It showed phantom "M" rows there (7 in
H8 s6, 22 in H20 s1), could not hash the files, could not set index flags
on them, refused them in `git archive`, and would have failed a Windows
`git clone` of any published repository carrying them at checkout. That
last consequence is why the public tree already renamed the family on the
way out, and why six Zenodo records froze the old path into immutable
file names before the decision could be taken.

`auxdata` is not reserved. Ordinary git works on that family on both
machines now: `git add datasets/auxdata` is the normal route, `git status`
tells the truth there, `git archive` needs no override, and a Windows
clone checks out. `aux_status.py` is kept as the honest way to ask what
under the family differs from HEAD and from the INDEX, which `git status`
alone cannot show, but it is no longer the only route that works.

Two things the rename did not undo:

- `build_access_log.py` must still not run on Windows (it reads mtimes
  the PC reports differently), and
- the six Zenodo records staged before 2026-09-11 carry file names built
  from `datasets/aux/`; they were re-staged and re-uploaded to match.

## 3. Line endings: `core.autocrlf=input` and the LF rule

- Every text file is LF. `core.autocrlf=input` is set repo-locally on
  the PC clone (H20 s1, README); `.gitattributes` at the root now
  carries the same policy so it travels with the repo (R360 s6).
- Python on Windows writes CRLF unless told not to: gen_datacards.py
  once rewrote all cards in CRLF (H8 s6). Any writer script must open
  with `newline="\n"` and use `csv.writer(..., lineterminator="\n")`
  (H8 s6, H15 s7 "Writers must still emit LF").
- A CRLF stash from 2026-09-03 is still parked on the PC clone (H20
  s1, H19 s13 point 2); leave it alone.
- `open()` reads cp1252 on Windows: pass `encoding="utf-8"`
  explicitly everywhere (the seizeit2 citation was lost to this once,
  H8 s6).

## 4. Pipeline order

Taken from README "Pipeline order", H21 s1-s2 and H19 s13. Run from the
repo root; every step is idempotent and resumable.

1. `fetch_*.py` / `ingest_*.py`: acquire raw data from the origin host
   with a sha256-journaled, resumable download; licence read at fetch
   time, never at catalogue time (README; memory rule "verify at
   fetch").
2. `build_canonical_*.py` / `ingest_*.py`: harmonize into the contracts
   under `configs/`, writing the per-family manifests in `datasets/`.
3. `convert_records_to_npz.py`: builders other than build_canonical_eeg
   still write pickle; run the converter after any ingestion until each
   builder is switched to `moveatlas.records.save` (H21 s1, list in
   docs/RECORD_FORMAT.md).
4. `validate_canonical.py` (gate 1, see s5).
5. `mask_statistics.py --cap 0`: the exhaustive validity-mask numbers
   the paper reports (H15 s1, H20 s3); run with the disk quiet.
6. `build_zenodo_staging.py --hash`: `export/zenodo_staging/<id>/`
   (metadata.json, files.csv, provenance.html prepended; H21 s2).
7. `upload_zenodo.py --bundle` then `upload_zenodo.py`: DRAFT deposits
   only, stale draft files removed, resumable through
   `export/zenodo_staging/_uploaded.json` (H15 s7, H21 s2).
8. The owner publishes from zenodo.org/uploads (H19 s7b). The code
   never publishes and never touches a published record (H21 s2).
9. `build_records_table.py`: `moveatlas/data/zenodo_records.json`,
   shipped with the package (README, H19 s9).
10. `launch_dryrun.py` (gate 3) must say LAUNCH-READY (H19 s9).
11. Site regeneration: `gen_datacards.py`, `site/gen_dataset_pages.py`,
    `build_portal.py` (stdlib, run anywhere; H19 s13 point 3), then the
    Sphinx build on the Mac (H21 s5).

## 5. The three gates

All three before any release; each exits non-zero on a gap (README
"The three gates"):

- `validate_canonical.py`: contract conformity of the harmonized
  records (full pass or sampled).
- `release_lint.py <release_dir> [--scidata]`: the automated half of
  the privacy and licence gate (docs/PRIVACY_GATE.md); anything not
  allowed by `docs/license_matrix.csv` is refused; `*.pkl` is no longer
  allowlisted (H21 s1).
- `launch_dryrun.py`: builds the package from a clean `git archive` of
  HEAD, installs it into a fresh venv with the local store hidden, and
  walks a stranger's path (README, H19 s9).

Tests: `<python> -m pytest -q` (105
corpus-free tests, CI on ubuntu x 3.9/3.11/3.13; H21 s4).

## 6. The record format

`moveatlas-record/1`: one ZIP per container with extension `.npz`, a
`meta.json` header, one `.npy` member per array at any depth (token
`{"$npy": path}` in the metadata), readable with numpy alone; spec in
docs/RECORD_FORMAT.md, implementation moveatlas/records.py (H21 s1).
Container granularity is unchanged from the pickle era (per record for
eeg/emg, per dataset or shard elsewhere) because of the 1 MiB clusters
(H21 s1). The 519.7 GB of superseded pickles are still on disk; their
deletion (`convert_records_to_npz.py --workers 12 --delete-pkl`) is an
owner GO (H21 s1, s9).

## 7. The access log

`datasets/_access_log_manual.csv` is human-owned and gets every new
row by hand on the PC; `build_access_log.py` rebuilds the output csv
and must NOT run on Windows: its stat pass would degrade every aux
dossier row (H20 s1, README). The rebuild is a Mac task (H20 s1, H21
s9 point 5).

## 8. AppleDouble ghosts

macOS writes `._*` sidecars for every file on the exFAT volume. They
crash sphinx-gallery (utf-8 decode) and the in-place wheel build
(H19 s9); they land in `.git` as `._pack-*` and produce "non-monotonic
index" noise, and `find .git -name "._*" -delete` is always safe (H15
s1). Sphinx excludes them (`exclude_patterns = ["._*", "**/._*"]`, H15
s1). The review counted 2,260 in the tree: `dot_clean` from the Mac and
`COPYFILE_DISABLE=1` in the Mac shell (R360 s6, H21 s9 point 5). A venv
created ON the volume is unusable for the same reason (H6/H7, cited by
H8 s6): venvs live on the machines' own disks.

## 9. Token hygiene

- The Zenodo token is passed only through the environment
  (`export ZENODO_TOKEN=...` on the Mac, `$env:ZENODO_TOKEN = "..."`
  on the PC; scopes deposit:write + deposit:actions; H15 s3, H17 s4,
  H18). upload_zenodo.py reads it from the env and never writes it to
  disk; download_synapse.py does the same with SYNAPSE_AUTH_TOKEN.
- The token transited a session in clear during the 2026-09-04
  campaign: rotate it at zenodo.org/account/settings/applications after
  each campaign (H19 s7b); the GitHub OAuth grant is queued for
  rotation too (H19 s13 point 4, H21 s9 point 4).
- Tokens do not travel between machines: the PC needs the owner's
  token again for every token session (H19 s13 point 4).

## 10. Where logs go

`_paris_logs/` at the repo root (gitignored) holds every fetch log,
retry script, campaign log and conversion journal, on the disk itself
so they travel with it (H8 s9, H19 s13 point 5, H21 s1). Session
handoffs are `KINEFM_HANDOFF_N.md` at the root (history, not
documentation; README); `CHANGELOG.md` is the dated summary.

## 11. Standing owner rules that touch operations

English repo, no em-dashes (use " - "); commit messages long,
lowercase, descriptive, with no attribution trailer of any kind (restated
H19 s7); no git state changes unless asked; nothing is
published by the code (README); no number typed by hand into a table
(paper/build_*.py docstrings); "not reported by source" rather than a
filled gap (H20 s7c).
