# MoveAtlas

An access-audited catalogue of movement-disorder and healthy-movement data,
harmonized into six canonical signal families and served through one Python
API. MoveAtlas answers a practical question: which movement data actually
exist for a given phenotype and modality, which of it can a stranger obtain,
and in what shape.

- **170 catalogued datasets** (159 human, 11 animal), one
  data card each, licence verified at acquisition time with its date.
- **46 of them harmonized** into pose, inertial, force, surface EMG,
  EEG and silhouette records: **302,463 records** measured exhaustively.
- **Access is reported, not assumed**: every dataset carries one of four
  access cases and the package enforces it at load time.

## Install

```bash
pip install moveatlas          # add [bench] for the baseline pipelines
```

```python
import moveatlas

moveatlas.list_datasets()                   # the catalogue with access cases
ds = moveatlas.dataset("nonan_gaitprint")   # a hosted CC-BY dataset
records, meta = ds.get_data()               # canonical records + metadata
moveatlas.to_frame(records[0]).head()       # a tidy, named, masked frame

moveatlas.fetch("fog_star")                 # a recipe: fetched at its origin, journaled
moveatlas.ingest("fog_star")                # harmonized on your machine, same code as the corpus
moveatlas.recipe("ninapro")                 # what a recipe needs before you run it
```

Hosted datasets download on demand from their Zenodo record into a local
cache and are verified against the record's own sha256 manifest. Recipe
datasets are fetched from their origin host and harmonized into the store
(`~/.moveatlas/store`, or `$MOVEATLAS_STORE`). Nothing needs credentials.
The same verbs exist on the command line: `moveatlas list | info <id> |
fetch <id> | ingest <id> | where`. The site's *Getting started* and *User
guide* walk one complete example per access case.

## The four access cases

| case | what happens on `get_data()` |
|---|---|
| `hosted` | downloaded from the MoveAtlas record for that dataset, sha256-verified |
| `recipe` | fetched from the original host by the documented ingestion recipe |
| `barrier` | raises the documented access route; nothing is downloaded |
| `local_only` | read from a local path only; nothing is redistributed |

A barrier is a result, not a failure: the access-barrier casebook
(`docs/ACCESS_BARRIERS_CASES.md`) types thirteen ways open data turns out not
to be obtainable, and the absences ledger (`docs/hunt_confirmed_absences.md`)
records the phenotypes for which no open dataset exists at all.

## Layout

```
moveatlas/     the package: registry, record store, frames, splits, paradigms
datasets/      one data card and one acquisition journal per dataset
docs/          design documents, the generated indexes, the casebook
configs/       the six canonical contracts, one YAML per family
tools/         the pipeline: fetch, ingest, canonical, registry, release
site/          the documentation site sources
tests/         the corpus-free test suite
```

The three gates live at the root and each exits non-zero on a gap:
`validate_canonical.py` (contract conformity), `release_lint.py` (privacy and
licence), `launch_dryrun.py` (a stranger's install path). Those run here.

`tools/` is the provenance record, not a runnable pipeline. Every script is
the one that actually produced what this repository describes, but they read
and write `datasets/<family>/<id>/raw/` and `processed/`, which this tree
deliberately does not carry - the data lives in its Zenodo records - and they
resolve the repository root from their own location, which the grouping into
`tools/<role>/` changes. Read them as the method; to re-run one, place it at
the root of a tree that holds the corpus.

## Records

A record is a self-describing container: a zip with the `.npz` extension
holding one `.npy` member per array and a `meta.json` header, format
`moveatlas-record/1` (`docs/RECORD_FORMAT.md`). It opens with numpy alone and
executes no code on load. Native sampling rates and units are preserved;
where a source declares no unit, the record says `unknown` rather than
guessing, and every refusal is a counted row in a per-dataset ingest audit.

## Data, licences and citation

The harmonized records are deposited as one Zenodo record per dataset, each
with its own DOI; the mapping ships with the package
(`moveatlas/data/zenodo_records.json`). Each record is a derived work of its
source: **cite the source dataset as well as MoveAtlas**. Every data card
carries the source licence, its verification date and a BibTeX entry
(`docs/citations.bib`).

Code is BSD-3-Clause (`LICENSE`). Data is licensed per dataset. Datasets whose
licence forbids redistribution are never deposited; they are catalogued with
their access route and used in-house for evaluation only.

Software citation: `CITATION.cff`. The resource paper is in preparation; its
reference will be added here when the preprint is out.

## Contributing

Corrections to a data card, a licence reading or an access route are the most
valuable contributions: see `CONTRIBUTING.md`.
