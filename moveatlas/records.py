# -*- coding: utf-8 -*-
"""The MoveAtlas record container ("moveatlas-record/1"): no pickle.

A record is a dict of numpy arrays plus plain metadata (str, int, float,
bool, None, lists and dicts of those). On disk it is ONE zip file with
the .npz extension so numpy users can open it directly:

    <name>.npz
        meta.json            {"format": "moveatlas-record/1",
                              "kind": "record" | "list",
                              "meta": {...}           (kind record)
                              "records": [{...}, ...] (kind list),
                              each dict carrying "_arrays": [names]}
        signal.npy           one .npy member per array (kind record)
        r000012/signal.npy   arrays of record 12      (kind list)

Why this shape: pickle.load on a downloaded file is arbitrary code
execution, and a public corpus cannot ask strangers to do that. .npy
members are numpy's own format (np.load reads them, np.lib.format
documents them); meta.json is inspectable with any text tool. The
container granularity stays what the ingestion produced (one file per
record for eeg/emg, one per dataset or shard for imu/force/silhouette/
pose) because the corpus volume has 1 MiB allocation units - splitting
300k pose records into files would multiply disk use by a large factor.

API
    save(path, rec_or_list)        write a container (kind by type)
    load(path)                     dict or list, arrays as numpy
    iter_load(path)                the records one at a time
    load_any(path)                 .npz via load(); .pkl via pickle with
                                   a DeprecationWarning (transition only)
    prefer_npz(path)               the .npz sibling of a .pkl path when it
                                   exists, else the path unchanged
    equal(a, b)                    strict round-trip equality (dtype,
                                   shape, values incl. NaN; metadata after
                                   JSON normalization)
"""
import io
import json
import os
import pickle
import warnings
import zipfile

import numpy as np

FORMAT = "moveatlas-record/1"
META = "meta.json"


# ------------------------------------------------------------- normalization
TOKEN = "$npy"


def _tokenize(v, path, arrays, where):
    """Plain-Python view of a value: every ndarray, at any depth, is
    lifted into `arrays` under its dotted path and replaced by the token
    {"$npy": path} (top-level arrays keep plain member names, e.g.
    signal.npy; nested ones read streams.0.signal.npy). Refuses what
    JSON cannot hold."""
    if isinstance(v, np.ndarray):
        if v.dtype == object:
            raise TypeError(f"{where}: object arrays are not allowed")
        arrays[path] = v
        return {TOKEN: path}
    if isinstance(v, np.generic):
        v = v.item()
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple)):
        return [_tokenize(x, f"{path}.{i}", arrays, f"{where}[{i}]")
                for i, x in enumerate(v)]
    if isinstance(v, dict):
        if TOKEN in v:
            raise TypeError(f"{where}: the key {TOKEN!r} is reserved")
        return {str(k): _tokenize(x, f"{path}.{k}", arrays, f"{where}.{k}")
                for k, x in v.items()}
    raise TypeError(f"{where}: value of type {type(v).__name__} is neither "
                    "an ndarray nor JSON-representable; the record contract "
                    "does not allow it")


def _split(rec, where="record"):
    arrays, meta = {}, {}
    for k, v in rec.items():
        meta[str(k)] = _tokenize(v, str(k), arrays, f"{where}.{k}")
    meta["_arrays"] = sorted(arrays)
    return arrays, meta


def _detokenize(v, zf, prefix):
    if isinstance(v, dict):
        if set(v) == {TOKEN}:
            return _read_npy(zf, f"{prefix}{v[TOKEN]}.npy")
        return {k: _detokenize(x, zf, prefix) for k, x in v.items()}
    if isinstance(v, list):
        return [_detokenize(x, zf, prefix) for x in v]
    return v


# every member carries this timestamp, so writing the same records twice
# gives the same bytes (a recipe run can be checked against the corpus by
# checksum; zipfile otherwise stamps the wall-clock minute, 2026-09-17)
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def _writestr(zf, name, data):
    info = zipfile.ZipInfo(name, date_time=_ZIP_EPOCH)
    info.compress_type = zf.compression
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def _write_npy(zf, name, arr):
    buf = io.BytesIO()
    np.lib.format.write_array(buf, np.ascontiguousarray(arr),
                              allow_pickle=False)
    _writestr(zf, name, buf.getvalue())


def _read_npy(zf, name):
    with zf.open(name) as f:
        return np.lib.format.read_array(io.BytesIO(f.read()),
                                        allow_pickle=False)


# ------------------------------------------------------------------- write
def save(path, obj, compress=True):
    """Write a record (dict) or a list of records to `path` (.npz).

    Any iterable of dicts (a generator included) is written as a list,
    one record at a time, so a builder can stream a container larger
    than memory."""
    if isinstance(obj, dict):
        kind, items = "record", [obj]
    elif isinstance(obj, (list, tuple)):
        kind, items = "list", obj
    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        kind, items = "list", obj
    else:
        raise TypeError("save() takes a record dict or an iterable of them")
    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    tmp = path + ".part"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    header = {"format": FORMAT, "kind": kind}
    try:
        with zipfile.ZipFile(tmp, "w", compression=mode, allowZip64=True) as zf:
            if kind == "record":
                arrays, meta = _split(items[0])
                header["meta"] = meta
                for k, a in arrays.items():
                    _write_npy(zf, f"{k}.npy", a)
            else:
                metas = []
                for i, rec in enumerate(items):
                    if not isinstance(rec, dict):
                        raise TypeError(f"record {i} is not a dict")
                    arrays, meta = _split(rec, f"record[{i}]")
                    metas.append(meta)
                    for k, a in arrays.items():
                        _write_npy(zf, f"r{i:06d}/{k}.npy", a)
                header["records"] = metas
                header["n_records"] = len(metas)
            # meta.json LAST so a truncated write is detectable (no header)
            _writestr(zf, META, json.dumps(header, ensure_ascii=False,
                                           separators=(",", ":")))
    except BaseException:
        # a refused value (object array, non-JSON metadata) aborts the write
        # partway; leave no half-container behind for a later pass to find
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    os.replace(tmp, path)
    return path


# -------------------------------------------------------------------- read
def is_container(path):
    if not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as zf:
        return META in zf.namelist()


def _assemble(zf, meta, prefix):
    rec = {k: _detokenize(v, zf, prefix)
           for k, v in meta.items() if k != "_arrays"}
    # containers written by the first writer (2026-09-08 morning) listed
    # top-level arrays in _arrays without a token in the metadata
    for name in meta.get("_arrays", []):
        if name not in rec and "." not in name:
            rec[name] = _read_npy(zf, f"{prefix}{name}.npy")
    return rec


def load(path):
    """Read a container: a dict for kind 'record', a list for kind 'list'."""
    with zipfile.ZipFile(path) as zf:
        if META not in zf.namelist():
            raise ValueError(f"{path}: not a {FORMAT} container (no {META})")
        header = json.loads(zf.read(META).decode("utf-8"))
        if header.get("format") != FORMAT:
            raise ValueError(f"{path}: unknown format {header.get('format')!r}")
        if header["kind"] == "record":
            return _assemble(zf, header["meta"], "")
        return [_assemble(zf, m, f"r{i:06d}/")
                for i, m in enumerate(header["records"])]


def iter_load(path):
    """Yield the records of a container one at a time (a kind 'record'
    container yields its single record), so a container larger than
    memory can be read record by record."""
    with zipfile.ZipFile(path) as zf:
        if META not in zf.namelist():
            raise ValueError(f"{path}: not a {FORMAT} container (no {META})")
        header = json.loads(zf.read(META).decode("utf-8"))
        if header.get("format") != FORMAT:
            raise ValueError(f"{path}: unknown format {header.get('format')!r}")
        if header["kind"] == "record":
            yield _assemble(zf, header["meta"], "")
            return
        for i, m in enumerate(header["records"]):
            yield _assemble(zf, m, f"r{i:06d}/")


def prefer_npz(path):
    """The .npz sibling of a .pkl path when it exists (post-migration
    stores keep only the .npz; pre-migration stores only the .pkl)."""
    if path.endswith(".pkl"):
        alt = path[:-4] + ".npz"
        if os.path.exists(alt):
            return alt
    return path


def load_any(path):
    """Transition reader: .npz containers natively, legacy .pkl through
    pickle with a DeprecationWarning. New code should call load()."""
    path = prefer_npz(path)
    if path.endswith(".npz") or is_container(path):
        return load(path)
    warnings.warn(f"{os.path.basename(path)}: legacy pickle record; convert "
                  "with convert_records_to_npz.py (pickle is unsafe on "
                  "downloaded data)", DeprecationWarning, stacklevel=2)
    with open(path, "rb") as f:
        return pickle.load(f)


# ------------------------------------------------------------------ verify
def _same(a, b):
    """Value equality after the normalization save() applies: numpy
    scalars become Python scalars, tuples become lists; arrays compare by
    dtype, shape and values with NaN == NaN; NaN scalars are equal."""
    if isinstance(a, np.generic):
        a = a.item()
    if isinstance(b, np.generic):
        b = b.item()
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        if not (isinstance(a, np.ndarray) and isinstance(b, np.ndarray)):
            return False
        if a.dtype != b.dtype or a.shape != b.shape:
            return False
        return bool(np.array_equal(a, b, equal_nan=a.dtype.kind == "f"))
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        if not (isinstance(a, (list, tuple)) and isinstance(b, (list, tuple))):
            return False
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) or isinstance(b, dict):
        if not (isinstance(a, dict) and isinstance(b, dict)):
            return False
        if {str(k) for k in a} != {str(k) for k in b}:
            return False
        bb = {str(k): v for k, v in b.items()}
        return all(_same(v, bb[str(k)]) for k, v in a.items())
    if isinstance(a, float) and isinstance(b, float) \
            and np.isnan(a) and np.isnan(b):
        return True
    return a == b


def equal(a, b):
    """Strict round-trip equality of two records or two record lists."""
    if isinstance(a, list) or isinstance(b, list):
        if not (isinstance(a, list) and isinstance(b, list)) or len(a) != len(b):
            return False
        return all(equal(x, y) for x, y in zip(a, b))
    return _same(a, b)
