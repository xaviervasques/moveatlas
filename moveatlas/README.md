# moveatlas

MoveAtlas is the open atlas of human movement data: one Python API over
the movement-disorders corpus, 170 catalogued datasets across six modality
families (pose, IMU, EMG, force, silhouette, EEG), harmonized into
canonical contracts, with patient-level evaluation splits.

The design deliberately follows MOABB (moabb.neurotechx.com), the
reproducibility framework for BCI, credited here as the model.

Install with `pip install moveatlas` (add `[bench]` for the scikit-learn
baseline pipelines). Records are self-describing `.npz` containers with a
`meta.json` member; no pickle.

```python
import moveatlas

moveatlas.list_datasets()                  # the full catalogue with access cases
ds = moveatlas.dataset("nonan_gaitprint")  # a hosted CC-BY dataset
records, meta = ds.get_data()          # canonical records + metadata frame
```

Access cases surfaced by `get_data()`:

- `hosted`: served from MoveAtlas's own records (local store today; Zenodo/HF
  after the public launch), sha256-verified;
- `recipe`: fetched from the original host by our ingestion recipe;
- `local_only`: private or licence-held data read from a local path;
- `barrier`: raises an informative error carrying the documented access
  route.

Any ingested id loads, not only the six with a dedicated adapter:
`moveatlas.dataset(code).get_data(subjects=..., modality=...)` discovers
the canonical containers under the dataset's `processed/` directory
(`canonical_eeg/`, `canonical_emg/`, `canonical.npz`, `canonical_imu.npz`,
`canonical_force.npz`, `canonical_silhouette.npz`, `canonical/*.npz`
shards), reads the modality from each record's keys, and returns the
metadata frame `[dataset, subject_ns, task, modality, n_frames, fps]`.
`ds.modalities` reports what is on disk; a recipe id nothing ingested
names the script to run. Without the repository, records come from the
published Zenodo deposits into `~/.moveatlas/records` (or
`MOVEATLAS_CACHE`): downloads resume, retry, print progress for large
files (`MOVEATLAS_QUIET=1` silences them) and fail offline with
`moveatlas.store.OfflineError`. With both a repository and a records
table, a path missing locally is fetched from the deposit.

License: BSD-3-Clause. Nothing in this package redistributes data whose
licence forbids it; see each dataset's card.
