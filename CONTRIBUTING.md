# Contributing to MoveAtlas

The most valuable contributions are corrections to what the catalogue claims.

## Reporting a wrong fact

Open an issue naming the dataset id and the field. The fields most likely to
be wrong, in order:

1. **Licence.** The registry records the licence as read at the source on a
   dated verification. Sources change: a deposit is relicensed, withdrawn, or
   its landing page contradicts its metadata. If you find a disagreement,
   include the URL and what you read there today.
2. **Access route.** A barrier dataset carries the route its owner documents.
   If the route changed, or you obtained the data by a route we record as
   closed, say how.
3. **Taxonomy cells.** Cells are adjudicated, not inferred. If a dataset is
   filed under the wrong phenotype, say which cell and why.
4. **Subject counts and demographics.** The registry states what the source
   states. Where the source is silent, the table says "not reported by
   source" and that is deliberate.

## Adding a dataset

Open an issue first with the DOI or landing page, the licence, and whether
redistribution is permitted. The inclusion rule is broad: any human movement
signal or a movement-relevant biological lane, under any licence, because the
licence is recorded rather than filtered on. What we will not do is
redistribute data whose licence forbids it.

## Code

- The test suite runs without the corpus: `python -m pytest -q`.
- Style: English, no em-dashes, LF line endings, standard library first.
- A builder must refuse rather than guess. If a source does not declare a
  unit, a sampling rate or a channel identity, the record stores `unknown`
  and the ingest audit counts the refusal. Pull requests that infer a missing
  declaration will be asked to remove the inference.
- Run the three gates before proposing a release-affecting change.

## What we cannot accept

Data files. The repository carries code, cards and indexes; the corpus lives
in its Zenodo records.
