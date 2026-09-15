# MoveAtlas / KineFM: the pipeline, calling the root scripts IN PLACE.
# Order and rules: docs/OPERATIONS.md s4. Script list: INDEX.md.
#
#   make PY=<python> validate
#
# PY defaults to whatever "python" resolves to. Nothing here publishes,
# deletes or needs a token except "upload", which only prints the
# instruction. `make` is not on the PC's Git Bash PATH; the recipes are
# plain commands and can be pasted.

PY ?= python
RELEASE ?= export/moveatlas_repo

.PHONY: help fetch canonical convert validate maskstats stage bundle upload records site test lint docx

help:
	@echo "targets: fetch canonical convert validate maskstats stage bundle upload records site test lint docx"
	@echo "PY=$(PY)  RELEASE=$(RELEASE)"

# 1. acquisition: one fetcher per host, run by hand per dataset (they
#    take dataset-specific arguments; see each docstring)
fetch:
	@echo "fetchers (run one at a time, from the repo root, see INDEX.md):"
	@ls fetch_*.py pads_mirror.py verify_dandi_local.py

# 2. harmonization: the builders that take no per-dataset argument;
#    the ingest_*.py family is dataset-specific and is listed only
canonical:
	$(PY) build_canonical.py
	$(PY) build_canonical_imu.py
	$(PY) build_canonical_force.py
	$(PY) build_canonical_emg.py
	$(PY) build_canonical_eeg.py
	$(PY) build_canonical_silhouette.py
	@echo "dataset-specific ingesters, run by hand:"; ls ingest_*.py

# 3. pickle -> moveatlas-record/1 (until every builder writes npz)
convert:
	$(PY) convert_records_to_npz.py --workers 12

# 4. gate 1
validate:
	$(PY) validate_canonical.py

# 5. exhaustive validity-mask numbers (disk quiet)
maskstats:
	$(PY) mask_statistics.py --cap 0

# 6. Zenodo staging with sha256
stage:
	$(PY) build_zenodo_staging.py --hash

# 7a. bundle zips for the deposits
bundle:
	$(PY) upload_zenodo.py --bundle

# 7b. the token session (owner): printed, not run
upload:
	@echo "owner token session - not run by make:"
	@echo "  PowerShell:  \$$env:ZENODO_TOKEN = \"...\"   (scopes deposit:write + deposit:actions)"
	@echo "  bash:        export ZENODO_TOKEN=..."
	@echo "  then:        $(PY) upload_zenodo.py --dry-run && $(PY) upload_zenodo.py"
	@echo "  drafts only; the owner publishes from zenodo.org/uploads; rotate the token after the campaign (docs/OPERATIONS.md s9)"

# 9. dataset id -> Zenodo record table shipped with the package
records:
	$(PY) build_records_table.py

# 11. site regeneration (stdlib part; the Sphinx build is a Mac task)
site:
	$(PY) gen_datacards.py
	$(PY) site/gen_dataset_pages.py
	$(PY) build_portal.py

test:
	$(PY) -m pytest -q

# gate 2 usage (needs a release dir: make lint RELEASE=path)
lint:
	$(PY) release_lint.py --help

docx:
	$(PY) paper/build_docx.py
