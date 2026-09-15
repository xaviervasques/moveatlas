# The MoveAtlas record container: moveatlas-record/1

Written 2026-09-08, the day the corpus left pickle. Reference
implementation: moveatlas/records.py (save, load, load_any, equal).
Migration tool: convert_records_to_npz.py (verified round trip, journal
in _paris_logs/npz_conversion_<date>.csv).

## Why

Every canonical record used to be a Python pickle. pickle.load on a
file a stranger downloaded is arbitrary code execution; a public
corpus cannot ask its users to do that, and a Scientific Data referee
from the computing side will say so. The replacement had to (1) hold
the same content byte-for-byte after a round trip, (2) be readable
without MoveAtlas (numpy alone), (3) keep the container granularity
the ingestion produced, because the corpus volume has 1 MiB
allocation units and 300,000 per-record files would multiply disk use.

## Shape

One ZIP file per container, extension .npz so numpy users can open it:

    <name>.npz
      meta.json                the header (below)
      signal.npy               one .npy member per array, kind "record"
      r000012/coords.npy       arrays of record 12, kind "list"
      streams.0.signal.npy     an array nested inside metadata

meta.json:

    {"format": "moveatlas-record/1",
     "kind": "record" | "list",
     "meta": {...}                       kind record
     "records": [{...}, ...],            kind list
     "n_records": N,                     kind list
    }

Each record dict is the canonical contract of its family
(configs/canonical_<family>.yaml, docs/MANIFEST_SCHEMA.md) with every
ndarray, at any depth, replaced by the token {"$npy": "<member path>"}
and written as a .npy member (np.lib.format, allow_pickle=False).
Top-level arrays keep plain member names (signal.npy); nested ones are
named by their dotted path (streams.0.signal.npy). The key "$npy" is
reserved. Scalars are plain JSON (numpy scalars are converted; tuples
become lists). A `_arrays` list of member paths is kept in each record
dict for inspection. meta.json is written LAST so a truncated file is
detectable (missing member).

Compression: deflate (zipfile.ZIP_DEFLATED); typical ratios observed
on 2026-09-08: IMU 10x (daphnet 222 MB -> 22 MB), force 3x, pose and
silhouette 1.2-1.7x, EEG 1.1-1.8x.

## Reading without MoveAtlas

    import json, zipfile, numpy as np
    z = zipfile.ZipFile("record.npz")
    header = json.loads(z.read("meta.json"))
    sig = np.load(z.open("signal.npy"))       # or np.load("record.npz")["signal"]

np.load("record.npz") lists every .npy member (and errors only if you
access "meta.json" through it - read that member with zipfile).

## Reading with MoveAtlas

    from moveatlas import records
    rec = records.load("record.npz")           # dict, arrays as numpy
    recs = records.load("canonical_imu.npz")   # list of dicts
    records.equal(a, b)                        # strict round-trip check

records.load_any(path) also accepts a legacy .pkl (DeprecationWarning)
and prefers the .npz sibling when it exists; LocalStore.path() and
RemoteStore.path() resolve a .pkl relpath to its .npz sibling the same
way, so adapters written before the migration keep working.

## Guarantees and refusals

- Round trip: convert_records_to_npz.py writes the .npz, reads it back
  and requires records.equal() against the pickle (dtype, shape,
  values incl. NaN; metadata after JSON normalization) before the
  pickle may be deleted (--delete-pkl); a mismatch keeps the pickle
  and is journaled.
- Object arrays are refused (TypeError) - none exist in the corpus.
- Values that are neither ndarray nor JSON (sets, custom classes) are
  refused; the contracts never used them.
- release_lint.py no longer allowlists *.pkl: a pickle in a release
  tree is a finding.

## What still writes pickle (to migrate at their next run)

build_canonical_imu.py, build_canonical_force.py,
build_canonical_silhouette.py, build_canonical*.py for pose
(amass/ntu/motionx/modys), the ingest_*.py that dump lists, and
build_canonical_drummer.py. build_canonical_eeg.py (and sensefog,
which imports its write_record) already write .npz. Until each is
switched, run convert_records_to_npz.py after an ingestion; the
readers accept both.
