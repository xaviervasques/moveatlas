# -*- coding: utf-8 -*-
"""Manifest-free loading of any ingested dataset from what sits on disk.

The dedicated adapters know their layout by heart. Every other id is
loaded from the record containers its ingestion left under
<registry path>/processed/, discovered through the store interface
(store.list_dir, so a RemoteStore discovers from its record manifest and
downloads only what the filters keep):

    canonical_eeg/<source>__<subject>__<task>.npz   one record per file
    canonical_emg/<source>__<subject>__<task>.npz   one record per file
    canonical.npz              the pose records of the dataset (a list)
    canonical_imu.npz          the IMU records (a list)
    canonical_force.npz        the force records (a list)
    canonical_silhouette.npz   the silhouette records (a list)
    canonical/<shard>.npz      per-subject / per-collection shards (lists;
                               pose, IMU or force depending on the dataset)

Legacy .pkl containers are read through records.load_any (with its
DeprecationWarning) only where no .npz exists.

The modality of a record is read from its keys, never from a file name:
coords -> pose, location_ids -> imu, channels with a site -> eeg, channels
with a muscle / kind -> emg, force -> force, contour -> silhouette.

Metadata-row contract (one row per record, the evaluation layer's input):
[dataset id, subject_ns, task (or take / sequence), modality, n_frames, fps].
"""
import json
import os
import zipfile

from moveatlas import records

# per-dataset containers: file name -> modality
NAMED = {
    "canonical.npz": "pose",
    "canonical_imu.npz": "imu",
    "canonical_force.npz": "force",
    "canonical_silhouette.npz": "silhouette",
}
# per-record and shard directories: name -> modality (None: read a shard)
DIRS = {
    "canonical_eeg": "eeg",
    "canonical_emg": "emg",
    "canonical": None,
}
MODALITIES = ("pose", "imu", "eeg", "emg", "force", "silhouette")
_MAIN_ARRAY = {"pose": "coords", "imu": "signal", "eeg": "signal",
               "emg": "signal", "force": "force", "silhouette": "contour"}


class Container:
    """One record container on disk: its store-relative path, the
    modality its name announces (None for canonical/ shards) and whether
    its file name may encode a subject (per-record files and shards)."""

    __slots__ = ("relpath", "hint", "sharded")

    def __init__(self, relpath, hint, sharded):
        self.relpath, self.hint, self.sharded = relpath, hint, sharded

    def __repr__(self):
        return f"Container({self.relpath!r}, {self.hint!r}, {self.sharded})"


# ------------------------------------------------------------ modality
def modality_of(rec, hint=None):
    """The canonical family of a record from its keys; `hint` is the
    container's announcement, used when the keys do not decide."""
    if "coords" in rec:
        return "pose"
    if "location_ids" in rec:
        return "imu"
    if "force" in rec:
        return "force"
    if "contour" in rec:
        return "silhouette"
    ch = rec.get("channels")
    if isinstance(ch, (list, tuple)) and ch and isinstance(ch[0], dict):
        first = ch[0]
        if "site" in first:
            return "eeg"
        if "muscle" in first or "kind" in first:
            return "emg"
        return hint or "eeg"
    if "signal" in rec and hint in ("eeg", "emg", "imu"):
        return hint
    return hint


def peek_modality(local_path, hint=None):
    """The modality of the first record of a container, read from its
    meta.json only (no array is decoded); a legacy .pkl is loaded."""
    if zipfile.is_zipfile(local_path):
        with zipfile.ZipFile(local_path) as zf:
            if records.META in zf.namelist():
                header = json.loads(zf.read(records.META).decode("utf-8"))
                if header.get("kind") == "record":
                    meta = header.get("meta", {})
                else:
                    recs = header.get("records") or [{}]
                    meta = recs[0]
                return modality_of(meta, hint)
    recs = records.load_any(local_path)
    if isinstance(recs, dict):
        return modality_of(recs, hint)
    return modality_of(recs[0], hint) if recs else hint


# ----------------------------------------------------------- discovery
def _record_files(children):
    """The record files among list_dir() children: .npz first, legacy
    .pkl only when a directory holds no .npz at all."""
    files = [c for c in children if not c.endswith("/")]
    for suf in (".npz", ".pkl"):
        hits = sorted(c for c in files if c.endswith(suf))
        if hits:
            return hits
    return []


def processed_dir(path):
    return path.replace("\\", "/").rstrip("/") + "/processed"


def discover(store, path):
    """The record containers under <path>/processed/ as Container objects
    (per-dataset files first, then the per-record and shard directories).
    [] when nothing is there; a RemoteStore without a record for the
    dataset raises FileNotFoundError."""
    base = processed_dir(path)
    children = store.list_dir(base)
    names = {c[len(base) + 1:] for c in children}
    found = []
    for fname, hint in NAMED.items():
        if fname in names:
            found.append(Container(f"{base}/{fname}", hint, False))
        elif fname[:-4] + ".pkl" in names:
            found.append(Container(f"{base}/{fname[:-4]}.pkl", hint, False))
    for dname, hint in DIRS.items():
        if dname + "/" in names:
            for f in _record_files(store.list_dir(f"{base}/{dname}")):
                found.append(Container(f, hint, True))
    return found


def _resolve_hints(store, found):
    """Fill the None hints (canonical/ shards) by peeking one shard per
    directory; the other shards of that directory get the same answer."""
    seen = {}
    for c in found:
        if c.hint is not None:
            continue
        d = c.relpath.rsplit("/", 1)[0]
        if d not in seen:
            seen[d] = peek_modality(store.path(c.relpath))
        c.hint = seen[d]
    return found


def modalities_on_disk(store, path):
    """The modalities a dataset carries, from its containers on disk
    (a canonical/ shard directory costs one shard header read)."""
    found = _resolve_hints(store, discover(store, path))
    return tuple(m for m in MODALITIES if any(c.hint == m for c in found))


# -------------------------------------------------------------- filters
def _subject_token(relpath):
    """The part of a file name that may name a subject: the middle of a
    <source>__<subject>__<task> per-record name, else the whole stem."""
    stem = os.path.splitext(os.path.basename(relpath))[0]
    parts = stem.split("__")
    return parts[1] if len(parts) >= 2 else stem


def name_matches(token, subject_ns):
    """True when a file-name token plausibly encodes subject_ns: the full
    id, its ':'->'_' form, its tail after the first or last namespace
    separator, or a prefix of the '_' form ending at a separator (amass
    shards are per collection: amass_ACCAD vs amass:ACCAD:<subject>).
    Over-matching is harmless (records are filtered afterwards); the
    caller falls back to reading everything when nothing matches."""
    flat = subject_ns.replace(":", "_")
    forms = {subject_ns, flat, subject_ns.split(":", 1)[-1],
             subject_ns.rsplit(":", 1)[-1]}
    if token in forms:
        return True
    return flat.startswith(token + "_")


def select(found, subjects=None, modality=None):
    """Apply the filters at the container level: drop containers whose
    announced modality is not the requested one, and, when the names of
    the sharded containers encode subjects, keep only the wanted ones.
    Returns the containers still worth opening."""
    if modality:
        found = [c for c in found if c.hint in (None, modality)]
    if subjects:
        wanted = list(subjects)
        keep = [c for c in found if c.sharded and any(
            name_matches(_subject_token(c.relpath), s) for s in wanted)]
        if keep:
            keepset = {c.relpath for c in keep}
            found = [c for c in found
                     if not c.sharded or c.relpath in keepset]
        # else: the names do not encode subjects; read and filter records
    return found


# ---------------------------------------------------------------- rows
def _n_frames(rec, modality):
    n = rec.get("n_frames")
    if n is not None:
        return int(n)
    arr = rec.get(_MAIN_ARRAY.get(modality, ""))
    return int(len(arr)) if arr is not None and hasattr(arr, "__len__") \
        else None


def row_of(code, rec, modality):
    """[dataset, subject_ns, task-or-take, modality, n_frames, fps]."""
    task = rec.get("task")
    if task is None:
        task = rec.get("take")
    if task is None:
        task = rec.get("sequence")
    return [code, rec.get("subject_ns"), task, modality,
            _n_frames(rec, modality), rec.get("fps")]


def load(store, code, path, subjects=None, modality=None, found=None):
    """(records, rows) for a dataset from its containers on disk.
    `found` is the discover() result when the caller already has it."""
    if found is None:
        found = discover(store, path)
    if modality and any(c.hint is None for c in found):
        _resolve_hints(store, found)
    wanted = set(subjects) if subjects else None
    out_records, rows = [], []
    for c in select(found, subjects, modality):
        recs = records.load_any(store.path(c.relpath))
        if isinstance(recs, dict):
            recs = [recs]
        for r in recs:
            if wanted is not None and r.get("subject_ns") not in wanted:
                continue
            m = modality_of(r, c.hint)
            if modality and m != modality:
                continue
            out_records.append(r)
            rows.append(row_of(code, r, m))
    return out_records, rows
