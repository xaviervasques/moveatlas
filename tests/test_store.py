# -*- coding: utf-8 -*-
"""LocalStore, RemoteStore (against a fake Zenodo API), HybridStore and
open_store. No network: urllib.request.urlopen is replaced for the remote
tests, time.sleep is recorded instead of waited."""
import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import zipfile

import pytest

from moveatlas import store as store_mod
from moveatlas.store import (HybridStore, LocalStore, OfflineError,
                             RemoteStore, open_store, sha256_of)

TABLE = {"toy": {"record": 4242, "doi": "10.5281/zenodo.4242"}}
REL = "datasets/imu/toy/processed/canonical/S001.npz"
PAYLOAD = b"toy record bytes, any content will do"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _manifest(rows, last_col):
    """files.csv text in one of the two upload_zenodo.py layouts:
    last_col is 'record_name' (direct) or 'zip_part' (bundled)."""
    out = [f"path,bytes,sha256,{last_col}"]
    for path, data, extra in rows:
        out.append(f"{path},{len(data)},{_sha(data)},{extra}")
    return ("\n".join(out) + "\n").encode("utf-8")


class _FakeResponse(io.BytesIO):
    """Enough of an HTTP response for json.load and chunked .read(n)."""
    status = 200
    headers = {}


class _Log(list):
    """The urls opened, in order, plus the Range headers seen and the
    sleeps the retry loop asked for."""

    def __init__(self):
        super().__init__()
        self.ranges = []
        self.sleeps = []


def fake_zenodo(monkeypatch, files, record=4242, status=None,
                api="https://zenodo.org/api", honor_range=True,
                file_status=None, offline=False):
    """Replace urllib.request.urlopen: the record endpoint lists `files`
    (key -> bytes) or fails with HTTP `status` (an int: always; a list:
    one code per call, None meaning success); file links serve bytes,
    honouring a Range header (206) unless honor_range is False, and can
    fail per call through `file_status` the same way. offline=True makes
    every call raise URLError."""
    log = _Log()
    file_base = "https://files.fake/"
    api_codes = list(status) if isinstance(status, (list, tuple)) else None
    file_codes = list(file_status) if file_status else None

    def urlopen(req, timeout=None):
        if isinstance(req, urllib.request.Request):
            url, rng = req.full_url, req.get_header("Range")
        else:
            url, rng = req, None
        log.append(url)
        log.ranges.append(rng)
        if offline:
            raise urllib.error.URLError("simulated: name resolution failed")
        if url == f"{api}/records/{record}":
            code = api_codes.pop(0) if api_codes else status
            if code:
                raise urllib.error.HTTPError(url, code, "simulated",
                                             None, None)
            payload = {"files": [{"key": k, "size": len(v),
                                  "links": {"self": file_base + k}}
                                 for k, v in files.items()]}
            return _FakeResponse(json.dumps(payload).encode("utf-8"))
        if url.startswith(file_base) and url[len(file_base):] in files:
            if file_codes:
                code = file_codes.pop(0)
                if code:
                    raise urllib.error.HTTPError(url, code, "simulated",
                                                 None, None)
            data = files[url[len(file_base):]]
            if rng and honor_range:
                start = int(rng.split("=", 1)[1].rstrip("-"))
                resp = _FakeResponse(data[start:])
                resp.status = 206
                return resp
            return _FakeResponse(data)
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(store_mod.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(store_mod.time, "sleep",
                        lambda s: log.sleeps.append(s))
    return log


# -- LocalStore -----------------------------------------------------------------

def test_local_store_missing_relpath_carries_the_ingestion_hint(tmp_path):
    s = LocalStore(root=str(tmp_path))
    rel = "datasets/imu/toy/processed/canonical/S001.npz"
    with pytest.raises(FileNotFoundError) as exc:
        s.path(rel)
    msg = str(exc.value)
    assert "record not in the local store" in msg
    assert rel in msg
    assert str(tmp_path) in msg
    assert "run its ingestion recipe first" in msg


def test_local_store_serves_existing_file(tmp_path):
    d = tmp_path / "datasets" / "imu" / "toy"
    d.mkdir(parents=True)
    (d / "S001.npz").write_bytes(PAYLOAD)
    s = LocalStore(root=str(tmp_path))
    p = s.path("datasets/imu/toy/S001.npz")
    assert os.path.exists(p)
    assert open(p, "rb").read() == PAYLOAD


def test_local_store_pkl_resolves_to_npz_sibling(tmp_path):
    d = tmp_path / "datasets" / "imu" / "toy"
    d.mkdir(parents=True)
    (d / "S001.npz").write_bytes(PAYLOAD)
    s = LocalStore(root=str(tmp_path))
    assert s.path("datasets/imu/toy/S001.pkl").endswith("S001.npz")
    # a legacy store with only the .pkl still answers the .pkl
    (d / "S002.pkl").write_bytes(b"legacy")
    assert s.path("datasets/imu/toy/S002.pkl").endswith("S002.pkl")


def test_local_store_glob_dir(tmp_path):
    d = tmp_path / "datasets" / "imu" / "toy"
    d.mkdir(parents=True)
    for name in ("b.npz", "a.npz", "._a.npz", "c.pkl", "notes.txt"):
        (d / name).write_bytes(b"x")
    s = LocalStore(root=str(tmp_path))
    hits = s.glob_dir("datasets/imu/toy")
    assert [os.path.basename(h) for h in hits] == ["a.npz", "b.npz"]
    assert [os.path.basename(h) for h in s.glob_dir("datasets/imu/toy",
                                                    suffix=".pkl")] == ["c.pkl"]
    assert s.glob_dir("datasets/imu/toy", suffix=".edf") == []
    with pytest.raises(FileNotFoundError, match="record directory not in"):
        s.glob_dir("datasets/imu/nowhere")


def test_local_store_glob_dir_falls_back_to_legacy_pkl(tmp_path):
    d = tmp_path / "datasets" / "imu" / "legacy"
    d.mkdir(parents=True)
    (d / "r.pkl").write_bytes(b"x")
    s = LocalStore(root=str(tmp_path))
    assert [os.path.basename(h) for h in s.glob_dir("datasets/imu/legacy")] \
        == ["r.pkl"]


def test_local_store_list_dir(tmp_path):
    d = tmp_path / "datasets" / "imu" / "toy" / "processed"
    (d / "canonical_eeg").mkdir(parents=True)
    (d / "canonical_imu.npz").write_bytes(b"x")
    (d / "._junk.npz").write_bytes(b"x")
    (d / "canonical_eeg" / "r1.npz").write_bytes(b"x")
    s = LocalStore(root=str(tmp_path))
    assert s.list_dir("datasets/imu/toy/processed") == [
        "datasets/imu/toy/processed/canonical_eeg/",
        "datasets/imu/toy/processed/canonical_imu.npz"]
    assert s.list_dir("datasets\\imu\\toy\\processed\\canonical_eeg/") == [
        "datasets/imu/toy/processed/canonical_eeg/r1.npz"]
    assert s.list_dir("datasets/imu/toy/nowhere") == []


def test_local_store_verify_manifest(tmp_path):
    d = tmp_path / "datasets" / "imu" / "toy"
    d.mkdir(parents=True)
    (d / "S001.npz").write_bytes(PAYLOAD)
    (d / "S002.npz").write_bytes(b"other")
    man = tmp_path / "manifest.csv"
    man.write_text("path,sha256\n"
                   f"datasets/imu/toy/S001.npz,{_sha(PAYLOAD).upper()}\n"
                   f"datasets/imu/toy/S002.npz,{_sha(b'not other')}\n",
                   encoding="utf-8")
    s = LocalStore(root=str(tmp_path))
    assert s.verify_manifest(str(man)) == ["datasets/imu/toy/S002.npz"]


def test_sha256_of_matches_hashlib(tmp_path):
    f = tmp_path / "blob.bin"
    f.write_bytes(PAYLOAD * 1000)
    assert sha256_of(str(f), chunk=64) == _sha(PAYLOAD * 1000)


# -- open_store / _repo_root ---------------------------------------------------

def test_repo_root_env_var_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("MOVEATLAS_REPO", str(tmp_path))
    assert store_mod._repo_root() == str(tmp_path)
    assert LocalStore().root == str(tmp_path)
    s = open_store()
    assert isinstance(s, LocalStore) and s.root == str(tmp_path)


def test_repo_root_autodetects_from_package_location(tmp_path, monkeypatch):
    monkeypatch.delenv("MOVEATLAS_REPO", raising=False)
    fake_pkg = tmp_path / "repo" / "moveatlas"
    fake_pkg.mkdir(parents=True)
    monkeypatch.setattr(store_mod, "__file__", str(fake_pkg / "store.py"))
    # no datasets/ beside the package: the USER store, created on demand
    # (since 2026-09-15 a fresh install has an empty store, never an error)
    monkeypatch.setenv("MOVEATLAS_STORE", str(tmp_path / "userstore"))
    assert store_mod._repo_root() == str(tmp_path / "userstore")
    assert (tmp_path / "userstore" / "datasets").is_dir()
    assert store_mod._repo_root(create=False) == str(tmp_path / "userstore")
    # a source tree that holds datasets/ wins over the user store
    (tmp_path / "repo" / "datasets").mkdir()
    assert store_mod._repo_root() == str(tmp_path / "repo")


def test_user_store_root_env_and_default(tmp_path, monkeypatch):
    monkeypatch.setenv("MOVEATLAS_STORE", str(tmp_path / "s"))
    assert store_mod.user_store_root() == str(tmp_path / "s")
    monkeypatch.delenv("MOVEATLAS_STORE", raising=False)
    assert store_mod.user_store_root().endswith(
        os.path.join(".moveatlas", "store"))


def test_open_store_prefers_local_when_repo_found(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "_repo_root", lambda: str(tmp_path))
    monkeypatch.setattr(store_mod, "_records_table", lambda: {})
    s = open_store()
    assert isinstance(s, LocalStore) and not isinstance(s, HybridStore)
    assert s.root == str(tmp_path)


def test_open_store_returns_hybrid_when_repo_and_table_exist(tmp_path,
                                                             monkeypatch,
                                                             isolated_cache):
    monkeypatch.setattr(store_mod, "_repo_root", lambda: str(tmp_path))
    monkeypatch.setattr(store_mod, "_records_table", lambda: dict(TABLE))
    s = open_store()
    assert isinstance(s, HybridStore) and isinstance(s, LocalStore)
    assert s.root == str(tmp_path)
    assert s.remote.table == TABLE
    assert s.remote.cache == str(isolated_cache)
    assert not isolated_cache.exists()        # nothing touched yet


def test_open_store_falls_back_to_remote(monkeypatch, isolated_cache):
    def no_repo():
        raise FileNotFoundError("no local corpus")
    monkeypatch.setattr(store_mod, "_repo_root", no_repo)
    s = open_store()
    assert isinstance(s, RemoteStore)
    assert s.cache == str(isolated_cache)
    assert isinstance(s.table, dict)
    assert not isolated_cache.exists()        # nothing touched yet


def test_remote_store_default_cache_under_home_when_env_unset(monkeypatch):
    monkeypatch.delenv("MOVEATLAS_CACHE", raising=False)
    s = RemoteStore(table={})
    assert s.cache == os.path.join(os.path.expanduser("~"), ".moveatlas",
                                   "records")


# -- RemoteStore: path resolution -----------------------------------------------

@pytest.mark.parametrize("relpath, did", [
    ("datasets/imu/daphnet/processed/canonical/x.npz", "daphnet"),
    ("datasets\\imu\\daphnet\\processed\\x.npz", "daphnet"),
    ("datasets/pose/toy/", "toy"),
    ("datasets/emg/gait120", "gait120"),
])
def test_dataset_of_parses_store_paths(relpath, did):
    assert RemoteStore._dataset_of(relpath) == did


@pytest.mark.parametrize("relpath", [
    "imu/daphnet/x.npz",
    "datasets/imu",
    "datasets",
    "x.npz",
    "",
    "records/imu/daphnet/x.npz",
    "/datasets/imu/daphnet/x.npz",
])
def test_dataset_of_rejects_other_shapes(relpath):
    with pytest.raises(FileNotFoundError, match="cannot map"):
        RemoteStore._dataset_of(relpath)


def test_record_id_unknown_dataset(tmp_path):
    s = RemoteStore(cache=str(tmp_path), table=TABLE)
    with pytest.raises(FileNotFoundError, match="no published MoveAtlas"):
        s.path("datasets/imu/unlisted/x.npz")
    assert s.has_record(REL) and s.has_record("toy")
    assert not s.has_record("datasets/imu/unlisted/x.npz")
    assert not s.has_record("not/a/store/path")


# -- RemoteStore: downloads against the fake API -------------------------------

def test_remote_resolves_direct_layout_and_verifies_sha256(tmp_path,
                                                            monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    cache = str(tmp_path / "cache")
    s = RemoteStore(cache=cache, table=TABLE)
    p = s.path(REL)
    assert p == os.path.join(cache, REL)
    assert open(p, "rb").read() == PAYLOAD
    assert sha256_of(p) == _sha(PAYLOAD)
    assert os.path.exists(os.path.join(cache, "toy", "_files.csv"))
    assert not os.path.exists(p + ".part")
    # api listing, manifest, record file: three requests, then cache hits
    assert len(calls) == 3
    assert calls.ranges == [None, None, None]     # nothing to resume
    assert calls.sleeps == []
    assert s.path(REL) == p
    assert len(calls) == 3


def test_remote_direct_layout_default_key_is_flattened_path(tmp_path,
                                                             monkeypatch):
    man = _manifest([(REL, PAYLOAD, "")], "record_name")
    key = REL.replace("/", "__")
    fake_zenodo(monkeypatch, {"files.csv": man, key: PAYLOAD})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD


def test_remote_corrupted_download_raises_ioerror(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man,
                              "S001.npz": b"corrupted bytes"})
    cache = str(tmp_path / "cache")
    s = RemoteStore(cache=cache, table=TABLE)
    with pytest.raises(IOError, match="sha256 mismatch"):
        s.path(REL)
    assert not os.path.exists(os.path.join(cache, REL))


def test_remote_stale_cached_file_is_refetched(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    cache = str(tmp_path / "cache")
    dest = os.path.join(cache, REL)
    os.makedirs(os.path.dirname(dest))
    with open(dest, "wb") as f:
        f.write(b"stale")
    s = RemoteStore(cache=cache, table=TABLE)
    assert s.path(REL) == dest
    assert open(dest, "rb").read() == PAYLOAD
    assert any(u.endswith("S001.npz") for u in calls)


def test_remote_bundled_layout_extracts_from_zip_part(tmp_path, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(REL, PAYLOAD)
        z.writestr("datasets/imu/toy/processed/canonical/S002.npz", b"two")
    # no zip_part_sha256 column: tolerated, the member sha256 still rules
    man = _manifest([(REL, PAYLOAD, "part-000.zip")], "zip_part")
    calls = fake_zenodo(monkeypatch, {"files.csv": man,
                                      "part-000.zip": buf.getvalue()})
    cache = str(tmp_path / "cache")
    s = RemoteStore(cache=cache, table=TABLE)
    p = s.path(REL)
    assert open(p, "rb").read() == PAYLOAD
    assert os.path.exists(os.path.join(cache, "toy", "_parts",
                                       "part-000.zip"))
    assert sum(u.endswith("part-000.zip") for u in calls) == 1


def _part_manifest(rows):
    """files.csv with the optional zip_part_sha256 column."""
    out = ["path,bytes,sha256,zip_part,zip_part_sha256"]
    for path, data, part, part_sha in rows:
        out.append(f"{path},{len(data)},{_sha(data)},{part},{part_sha}")
    return ("\n".join(out) + "\n").encode("utf-8")


def test_remote_zip_part_sha256_is_verified_before_extraction(tmp_path,
                                                              monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(REL, PAYLOAD)
    part = buf.getvalue()
    man = _part_manifest([(REL, PAYLOAD, "part-000.zip", _sha(part))])
    fake_zenodo(monkeypatch, {"files.csv": man, "part-000.zip": part})
    cache = str(tmp_path / "cache")
    s = RemoteStore(cache=cache, table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD
    zpath = os.path.join(cache, "toy", "_parts", "part-000.zip")
    assert zpath in s._verified_parts


def test_remote_zip_part_sha256_mismatch_refuses_to_extract(tmp_path,
                                                            monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(REL, PAYLOAD)
    part = buf.getvalue()
    man = _part_manifest([(REL, PAYLOAD, "part-000.zip", _sha(b"tampered"))])
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "part-000.zip": part})
    cache = str(tmp_path / "cache")
    s = RemoteStore(cache=cache, table=TABLE)
    with pytest.raises(IOError, match="sha256 mismatch for zip part"):
        s.path(REL)
    assert not os.path.exists(os.path.join(cache, "toy", "_parts",
                                           "part-000.zip"))
    assert not os.path.exists(os.path.join(cache, REL))
    assert sum(u.endswith("part-000.zip") for u in calls) == 1


def test_remote_stale_cached_zip_part_is_refetched_once(tmp_path,
                                                        monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(REL, PAYLOAD)
    part = buf.getvalue()
    man = _part_manifest([(REL, PAYLOAD, "part-000.zip", _sha(part))])
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "part-000.zip": part})
    cache = str(tmp_path / "cache")
    zpath = os.path.join(cache, "toy", "_parts", "part-000.zip")
    os.makedirs(os.path.dirname(zpath))
    with open(zpath, "wb") as f:
        f.write(b"truncated part from an older run")
    s = RemoteStore(cache=cache, table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD
    assert sum(u.endswith("part-000.zip") for u in calls) == 1
    assert sha256_of(zpath) == _sha(part)


def test_remote_unpublished_record_says_not_public_yet(tmp_path,
                                                       monkeypatch):
    calls = fake_zenodo(monkeypatch, {}, status=404)
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    with pytest.raises(FileNotFoundError, match=r"not public \(yet\)") as exc:
        s.path(REL)
    assert "4242" in str(exc.value) and "'toy'" in str(exc.value)
    assert isinstance(exc.value.__cause__, urllib.error.HTTPError)
    assert exc.value.__cause__.code == 404
    assert len(calls) == 1 and calls.sleeps == []      # 404 is never retried


def test_remote_other_http_errors_propagate_after_the_retries(tmp_path,
                                                              monkeypatch):
    calls = fake_zenodo(monkeypatch, {}, status=503)
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    with pytest.raises(urllib.error.HTTPError) as exc:
        s.path(REL)
    assert exc.value.code == 503
    assert len(calls) == 4                     # one try + three retries
    assert calls.sleeps == [5, 15, 45]


def test_remote_retries_a_503_then_succeeds(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD},
                        status=[503, None])
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD
    api = "https://zenodo.org/api/records/4242"
    assert calls.count(api) == 2
    assert calls.sleeps == [5]


def test_remote_retries_file_downloads_on_429_and_5xx(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD},
                        file_status=[500, 429, None])
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD
    assert calls.sleeps == [5, 15]
    assert sum(u.endswith("files.csv") for u in calls) == 3


def test_remote_404_on_a_file_is_not_retried(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD},
                        file_status=[404])
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    with pytest.raises(urllib.error.HTTPError) as exc:
        s.path(REL)
    assert exc.value.code == 404 and calls.sleeps == []


def test_remote_resume_sends_range_and_keeps_the_prefix(tmp_path,
                                                        monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    cache = str(tmp_path / "cache")
    dest = os.path.join(cache, REL)
    os.makedirs(os.path.dirname(dest))
    with open(dest + ".part", "wb") as f:
        f.write(PAYLOAD[:10])            # an interrupted earlier download
    s = RemoteStore(cache=cache, table=TABLE)
    assert s.path(REL) == dest
    assert open(dest, "rb").read() == PAYLOAD
    assert sha256_of(dest) == _sha(PAYLOAD)
    assert not os.path.exists(dest + ".part")
    ranges = dict(zip(calls, calls.ranges))
    assert ranges["https://files.fake/S001.npz"] == "bytes=10-"
    assert ranges["https://files.fake/files.csv"] is None


def test_remote_resume_restarts_when_the_server_ignores_the_range(
        tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD},
                        honor_range=False)
    cache = str(tmp_path / "cache")
    dest = os.path.join(cache, REL)
    os.makedirs(os.path.dirname(dest))
    with open(dest + ".part", "wb") as f:
        f.write(b"garbage prefix")
    s = RemoteStore(cache=cache, table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD
    assert "bytes=14-" in calls.ranges


def test_remote_resume_discards_a_part_longer_than_the_file(tmp_path,
                                                            monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    cache = str(tmp_path / "cache")
    dest = os.path.join(cache, REL)
    os.makedirs(os.path.dirname(dest))
    with open(dest + ".part", "wb") as f:
        f.write(PAYLOAD + b"overrun")
    s = RemoteStore(cache=cache, table=TABLE)
    assert open(s.path(REL), "rb").read() == PAYLOAD
    assert calls.ranges[-1] is None


def test_remote_offline_raises_offline_error(tmp_path, monkeypatch):
    calls = fake_zenodo(monkeypatch, {}, offline=True)
    cache = str(tmp_path / "cache")
    s = RemoteStore(cache=cache, table=TABLE)
    with pytest.raises(OfflineError) as exc:
        s.path(REL)
    msg = str(exc.value)
    assert isinstance(exc.value, FileNotFoundError)
    assert "network" in msg and cache in msg and "'toy'" in msg
    assert isinstance(exc.value.__cause__, urllib.error.URLError)
    assert calls.sleeps == [5, 15, 45]
    # a cached, verified file needs no network at all
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    os.makedirs(os.path.join(cache, "toy"))
    with open(os.path.join(cache, "toy", "_files.csv"), "wb") as f:
        f.write(man)
    dest = os.path.join(cache, REL)
    os.makedirs(os.path.dirname(dest))
    with open(dest, "wb") as f:
        f.write(PAYLOAD)
    assert RemoteStore(cache=cache, table=TABLE).path(REL) == dest


def test_remote_progress_lines_for_large_files_only(tmp_path, monkeypatch,
                                                    capsys):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    monkeypatch.delenv("MOVEATLAS_QUIET", raising=False)
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    s.path(REL)
    assert capsys.readouterr().err == ""          # 37 bytes: silent
    monkeypatch.setattr(store_mod._Progress, "THRESHOLD", 10)
    s = RemoteStore(cache=str(tmp_path / "cache2"), table=TABLE)
    s.path(REL)
    err = capsys.readouterr().err
    lines = [ln for ln in err.splitlines() if "S001.npz" in ln]
    assert lines[0].startswith("S001.npz: ")           # one line per file
    assert lines[-1].startswith("  S001.npz: 100%")
    assert len(lines) == 11                             # header + 10 steps
    monkeypatch.setenv("MOVEATLAS_QUIET", "1")
    s = RemoteStore(cache=str(tmp_path / "cache3"), table=TABLE)
    s.path(REL)
    assert capsys.readouterr().err == ""


def test_remote_path_not_in_manifest(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    with pytest.raises(FileNotFoundError, match="not in the record manifest"):
        s.path("datasets/imu/toy/processed/canonical/S999.npz")


def test_remote_file_missing_from_record(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    with pytest.raises(FileNotFoundError, match="has no file 'S001.npz'"):
        s.path(REL)


def test_remote_pkl_request_resolves_to_published_npz(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    assert s.resolve(REL[:-4] + ".pkl") == REL
    assert s.path(REL[:-4] + ".pkl").endswith("S001.npz")


def test_remote_glob_dir(tmp_path, monkeypatch):
    rel2 = "datasets/imu/toy/processed/canonical/S002.npz"
    man = _manifest([(REL, PAYLOAD, "S001.npz"), (rel2, b"two", "S002.npz"),
                     ("datasets/imu/toy/README.md", b"#", "README.md")],
                    "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD,
                              "S002.npz": b"two", "README.md": b"#"})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    hits = s.glob_dir("datasets/imu/toy/processed/canonical")
    assert [os.path.basename(h) for h in hits] == ["S001.npz", "S002.npz"]
    with pytest.raises(FileNotFoundError, match="holds nothing"):
        s.glob_dir("datasets/imu/toy/processed/canonical", suffix=".pkl")


def test_remote_list_dir_reads_the_manifest_without_downloading(tmp_path,
                                                                monkeypatch):
    rel2 = "datasets/imu/toy/processed/canonical/S002.npz"
    man = _manifest([(REL, PAYLOAD, "S001.npz"), (rel2, b"two", "S002.npz"),
                     ("datasets/imu/toy/processed/canonical_imu.npz", b"i",
                      "canonical_imu.npz"),
                     ("datasets/imu/toy/README.md", b"#", "README.md")],
                    "record_name")
    calls = fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD,
                                      "S002.npz": b"two", "README.md": b"#"})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    assert s.list_dir("datasets/imu/toy/processed") == [
        "datasets/imu/toy/processed/canonical/",
        "datasets/imu/toy/processed/canonical_imu.npz"]
    assert s.list_dir("datasets/imu/toy/processed/canonical/") == [REL, rel2]
    assert s.list_dir("datasets/imu/toy/nowhere") == []
    assert len(calls) == 2            # api listing + manifest, no record
    with pytest.raises(FileNotFoundError, match="no published MoveAtlas"):
        s.list_dir("datasets/imu/unlisted/processed")


def test_remote_verify_manifest(tmp_path, monkeypatch):
    man = _manifest([(REL, PAYLOAD, "S001.npz")], "record_name")
    fake_zenodo(monkeypatch, {"files.csv": man, "S001.npz": PAYLOAD})
    s = RemoteStore(cache=str(tmp_path / "cache"), table=TABLE)
    good = tmp_path / "good.csv"
    good.write_text(f"path,sha256\n{REL},{_sha(PAYLOAD)}\n", encoding="utf-8")
    assert s.verify_manifest(str(good)) == []
    bad = tmp_path / "bad.csv"
    bad.write_text(f"path,sha256\n{REL},{_sha(b'else')}\n", encoding="utf-8")
    assert s.verify_manifest(str(bad)) == [REL]


# -- HybridStore ----------------------------------------------------------------

def _hybrid(tmp_path, monkeypatch, extra_rows=()):
    """A local root holding S001 and a fake record holding S002 (and any
    extra rows); returns (store, root, cache, calls)."""
    root = tmp_path / "repo"
    d = root / "datasets" / "imu" / "toy" / "processed" / "canonical"
    d.mkdir(parents=True)
    (d / "S001.npz").write_bytes(b"local copy")
    rel2 = "datasets/imu/toy/processed/canonical/S002.npz"
    rows = [(rel2, b"two", "S002.npz")] + list(extra_rows)
    files = {"files.csv": _manifest(rows, "record_name")}
    files.update({extra: data for _, data, extra in rows})
    calls = fake_zenodo(monkeypatch, files)
    cache = str(tmp_path / "cache")
    s = HybridStore(root=str(root), remote=RemoteStore(cache=cache,
                                                       table=TABLE))
    return s, root, cache, calls


def test_hybrid_store_serves_local_first_then_the_record(tmp_path,
                                                         monkeypatch):
    s, root, cache, calls = _hybrid(tmp_path, monkeypatch)
    assert isinstance(s, LocalStore) and s.root == str(root)
    p1 = s.path("datasets/imu/toy/processed/canonical/S001.npz")
    assert p1.startswith(str(root)) and open(p1, "rb").read() == b"local copy"
    assert len(calls) == 0                     # local hit: no network
    rel2 = "datasets/imu/toy/processed/canonical/S002.npz"
    p2 = s.path(rel2)
    assert p2 == os.path.join(cache, rel2)
    assert open(p2, "rb").read() == b"two"
    assert len(calls) == 3


def test_hybrid_store_keeps_the_local_error_without_a_record(tmp_path,
                                                             monkeypatch):
    s, root, cache, calls = _hybrid(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError, match="record not in the local"):
        s.path("datasets/imu/unlisted/processed/canonical/S001.npz")
    with pytest.raises(FileNotFoundError, match="record not in the local"):
        s.path("not/a/store/path.npz")
    assert len(calls) == 0


def test_hybrid_store_glob_and_list_dir_fall_back_per_directory(tmp_path,
                                                                monkeypatch):
    extra = [("datasets/imu/toy/processed/canonical_emg/r1.npz", b"e",
              "r1.npz")]
    s, root, cache, calls = _hybrid(tmp_path, monkeypatch, extra)
    # the local directory exists and has files: local wins, no network
    hits = s.glob_dir("datasets/imu/toy/processed/canonical")
    assert [os.path.basename(h) for h in hits] == ["S001.npz"]
    assert s.list_dir("datasets/imu/toy/processed/canonical") == [
        "datasets/imu/toy/processed/canonical/S001.npz"]
    assert len(calls) == 0
    # a directory the local tree lacks comes from the record
    assert s.list_dir("datasets/imu/toy/processed/canonical_emg") == [
        "datasets/imu/toy/processed/canonical_emg/r1.npz"]
    hits = s.glob_dir("datasets/imu/toy/processed/canonical_emg")
    assert [os.path.basename(h) for h in hits] == ["r1.npz"]
    assert open(hits[0], "rb").read() == b"e"
    # and one nobody has stays a local error
    with pytest.raises(FileNotFoundError, match="record directory not in"):
        s.glob_dir("datasets/imu/unlisted/processed/canonical")
    assert s.list_dir("datasets/imu/unlisted/processed") == []
