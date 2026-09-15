# -*- coding: utf-8 -*-
"""The manifest-free generic loader (moveatlas.datasets.generic) and
GenericDataset over a tiny fake repository written with records.save:
one dataset per on-disk layout (per-record eeg dir, per-dataset
canonical_imu.npz + canonical_force.npz lists, a pose shard dir), a fake
registry, and the remote path against a fake record manifest. Corpus-free,
network-free."""
import hashlib
import io
import json
import os
import pickle
import urllib.error
import urllib.request

import numpy as np
import pytest

from moveatlas import records
from moveatlas import store as store_mod
from moveatlas.datasets import base as base_mod
from moveatlas.datasets import generic
from moveatlas.datasets.base import AccessError, GenericDataset, recipe_of
from moveatlas.store import LocalStore, RemoteStore


# -- fake records, one per family --------------------------------------------

def eeg_rec(subj, task, n):
    return {"signal": np.zeros((n, 2), np.float32),
            "channels": [{"site": "C3", "ref": "AVG", "kind": "eeg"},
                         {"site": "C4", "ref": "AVG", "kind": "eeg"}],
            "fps": 500.0, "unit": "uV", "unit_scale": 1.0,
            "filters": {"hp_hz": None, "lp_hz": None, "notch_hz": None},
            "subject_ns": subj, "task": task, "source": "toy_eeg",
            "n_frames": n, "label": None}


def emg_rec(subj, task, n):
    return {"signal": np.zeros((n, 1), np.float32),
            "channels": [{"kind": "emg", "muscle": "TA", "side": "R"}],
            "fps": 2000.0, "unit": "mV", "subject_ns": subj, "task": task,
            "source": "toy_emg", "n_frames": n}


def imu_rec(subj, task, n):
    return {"signal": np.zeros((n, 1, 9), np.float32),
            "location_ids": np.array([2]),
            "channel_mask": np.ones((1, 9), bool), "fps": 100.0,
            "subject_ns": subj, "task": task, "source": "toy_multi",
            "n_frames": n, "label": None}


def force_rec(subj, task, n):
    return {"force": np.zeros((n, 2, 9), np.float32),
            "sensor_mask": np.ones((2, 9), bool), "fps": 100.0,
            "subject_ns": subj, "task": task, "source": "toy_multi",
            "n_frames": n}


def pose_rec(subj, take, n, fps=30.0):
    return {"coords": np.zeros((n, 15, 3), np.float32),
            "coord_mask": np.ones(3, bool), "joint_mask": np.ones(15, bool),
            "valid_mask": np.ones((n, 15), bool), "dim": 3, "fps": fps,
            "modality": "3d_meter", "source": "toy_pose",
            "subject_ns": subj, "take": take, "n_frames": n, "scale": 1.0}


def silhouette_rec(subj, seq, n):
    return {"contour": np.zeros((n, 64, 2), np.float32),
            "scalars": np.zeros((n, 8), np.float32),
            "detect_mask": np.ones(n, bool), "scalar_mask": np.ones(8, bool),
            "fps": 50.0, "scale": 600.0, "dim": 2, "modality": "silhouette",
            "subject_ns": subj, "cohort": "control", "severity": "",
            "sequence": seq, "source": "toy_sil", "n_frames": n}


def _row(code, family, case, **kw):
    r = {"id": code, "family": family, "path": f"datasets/{family}/{code}",
         "title": f"Toy {code}", "license": "CC0", "moveatlas_cells": "A1",
         "access": "direct_download", "status": "INGESTED v1",
         "access_case": case}
    r.update(kw)
    return r


REGISTRY = {
    "toy_eeg": _row("toy_eeg", "eeg", "hosted"),
    "toy_multi": _row("toy_multi", "imu", "hosted"),
    "toy_pose": _row("toy_pose", "pose", "hosted"),
    "toy_mixed_shards": _row("toy_mixed_shards", "pose", "hosted"),
    "toy_legacy": _row("toy_legacy", "imu", "recipe"),
    "toy_sil": _row("toy_sil", "pose", "recipe",
                    access="direct_download (ingest_toy_sil.py)"),
    "toy_recipe": _row(
        "toy_recipe", "auxdata", "recipe",
        access="direct_download (ingest_toy.py --only toy_recipe, tower)",
        status="raw on disk"),
    "toy_hosted_empty": _row("toy_hosted_empty", "imu", "hosted",
                             status="INGESTED by build_toy.py"),
    "toy_barrier": _row("toy_barrier", "imu", "barrier",
                        access="email the PI", status="DOCUMENTED BARRIER"),
}

EEG_DIR = "datasets/eeg/toy_eeg/processed/canonical_eeg"
EEG_FILES = {
    "toy_eeg__toy_eeg_s01__task_1.npz": eeg_rec("toy_eeg:s01", "task_1", 40),
    "toy_eeg__toy_eeg_s01__task_2.npz": eeg_rec("toy_eeg:s01", "task_2", 30),
    "toy_eeg__toy_eeg_s02__task_1.npz": eeg_rec("toy_eeg:s02", "task_1", 20),
}


def _save(root, relpath, obj):
    p = os.path.join(str(root), *relpath.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    records.save(p, obj)
    return p


def write_repo(root):
    for name, rec in EEG_FILES.items():
        _save(root, f"{EEG_DIR}/{name}", rec)
    _save(root, "datasets/imu/toy_multi/processed/canonical_imu.npz",
          [imu_rec("toy_multi:s01", "walk", 100),
           imu_rec("toy_multi:s02", "walk", 120)])
    _save(root, "datasets/imu/toy_multi/processed/canonical_force.npz",
          [force_rec("toy_multi:s01", "walk", 100)])
    _save(root, "datasets/pose/toy_pose/processed/canonical/S01.npz",
          [pose_rec("toy_pose:S01", "t1", 10), pose_rec("toy_pose:S01", "t2", 12)])
    _save(root, "datasets/pose/toy_pose/processed/canonical/S02.npz",
          [pose_rec("toy_pose:S02", "t1", 14, fps=None)])
    # shards whose names say nothing about subjects
    _save(root, "datasets/pose/toy_mixed_shards/processed/canonical/part0.npz",
          [pose_rec("toy_mixed_shards:A", "t1", 5),
           pose_rec("toy_mixed_shards:B", "t1", 6)])
    _save(root, "datasets/pose/toy_mixed_shards/processed/canonical/part1.npz",
          [pose_rec("toy_mixed_shards:C", "t1", 7)])
    _save(root, "datasets/pose/toy_sil/processed/canonical_silhouette.npz",
          [silhouette_rec("toy_sil_P1", "01", 9)])
    # a pre-migration dataset: only the pickle exists
    p = os.path.join(str(root), "datasets", "imu", "toy_legacy", "processed",
                     "canonical_imu.pkl")
    os.makedirs(os.path.dirname(p))
    with open(p, "wb") as f:
        pickle.dump([imu_rec("toy_legacy:s01", "run", 50)], f)
    # hosted id whose processed/ holds nothing canonical
    os.makedirs(os.path.join(str(root), "datasets", "imu", "toy_hosted_empty",
                             "processed"))


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    write_repo(root)
    monkeypatch.setattr(base_mod, "dataset_info",
                        lambda code: dict(REGISTRY[code]))
    monkeypatch.setattr(base_mod, "open_store",
                        lambda: LocalStore(root=str(root)))
    return root


@pytest.fixture
def load_counter(monkeypatch):
    """Count the containers the loader actually opens."""
    opened = []
    real = generic.records.load_any

    def counting(path):
        opened.append(os.path.basename(path))
        return real(path)
    monkeypatch.setattr(generic.records, "load_any", counting)
    return opened


COLUMNS = ["dataset", "subject_ns", "task", "modality", "n_frames", "fps"]


# -- per-record eeg directory --------------------------------------------------

def test_eeg_per_record_dir(repo):
    ds = GenericDataset("toy_eeg")
    assert ds.modalities == ("eeg",)
    recs, meta = ds.get_data()
    assert list(meta.columns) == COLUMNS
    assert len(recs) == 3
    assert meta["dataset"].tolist() == ["toy_eeg"] * 3
    assert meta["modality"].tolist() == ["eeg"] * 3
    assert meta["subject_ns"].tolist() == ["toy_eeg:s01", "toy_eeg:s01",
                                           "toy_eeg:s02"]
    assert meta["task"].tolist() == ["task_1", "task_2", "task_1"]
    assert meta["n_frames"].tolist() == [40, 30, 20]
    assert meta["fps"].tolist() == [500.0] * 3
    assert recs[0]["signal"].shape == (40, 2)


def test_subjects_filter_skips_files_by_name(repo, load_counter):
    recs, meta = GenericDataset("toy_eeg").get_data(subjects=["toy_eeg:s02"])
    assert meta["subject_ns"].tolist() == ["toy_eeg:s02"]
    assert load_counter == ["toy_eeg__toy_eeg_s02__task_1.npz"]


def test_unknown_subject_yields_an_empty_frame(repo):
    recs, meta = GenericDataset("toy_eeg").get_data(subjects=["toy_eeg:s99"])
    assert recs == [] and len(meta) == 0 and list(meta.columns) == COLUMNS


# -- per-dataset lists: two named containers, the modality filter -------------

def test_multimodal_named_containers(repo, load_counter):
    ds = GenericDataset("toy_multi")
    assert ds.modalities == ("imu", "force")
    recs, meta = ds.get_data()
    assert meta["modality"].tolist() == ["imu", "imu", "force"]
    assert meta["n_frames"].tolist() == [100, 120, 100]
    load_counter.clear()
    recs, meta = ds.get_data(modality="force")
    assert meta["modality"].tolist() == ["force"]
    assert load_counter == ["canonical_force.npz"]     # imu file skipped
    recs, meta = ds.get_data(subjects=["toy_multi:s02"])
    assert meta["subject_ns"].tolist() == ["toy_multi:s02"]
    assert meta["modality"].tolist() == ["imu"]
    with pytest.raises(ValueError, match="carries \\('imu', 'force'\\)"):
        ds.get_data(modality="eeg")


# -- shard directories ----------------------------------------------------------

def test_pose_shards_skip_whole_files_on_the_subjects_filter(repo,
                                                             load_counter):
    ds = GenericDataset("toy_pose")
    assert ds.modalities == ("pose",)
    recs, meta = ds.get_data()
    assert meta["task"].tolist() == ["t1", "t2", "t1"]      # take -> task
    assert meta["modality"].tolist() == ["pose"] * 3
    assert meta["fps"].tolist()[:2] == [30.0, 30.0]
    assert np.isnan(meta["fps"].tolist()[2])            # nullable fps
    load_counter.clear()
    recs, meta = ds.get_data(subjects=["toy_pose:S02"])
    assert meta["subject_ns"].tolist() == ["toy_pose:S02"]
    assert load_counter == ["S02.npz"]


def test_shards_not_named_after_subjects_fall_back_to_record_filtering(
        repo, load_counter):
    ds = GenericDataset("toy_mixed_shards")
    recs, meta = ds.get_data(subjects=["toy_mixed_shards:C"])
    assert meta["subject_ns"].tolist() == ["toy_mixed_shards:C"]
    assert sorted(load_counter) == ["part0.npz", "part1.npz"]


def test_silhouette_sequence_is_the_task_column(repo):
    ds = GenericDataset("toy_sil")
    assert ds.modalities == ("silhouette",)
    recs, meta = ds.get_data()
    assert meta.iloc[0].tolist() == ["toy_sil", "toy_sil_P1", "01",
                                     "silhouette", 9, 50.0]


# -- legacy pickle fallback ----------------------------------------------------

def test_legacy_pkl_is_read_only_as_a_fallback(repo):
    ds = GenericDataset("toy_legacy")
    with pytest.warns(DeprecationWarning, match="legacy pickle"):
        recs, meta = ds.get_data()
    assert meta["modality"].tolist() == ["imu"]
    assert meta["task"].tolist() == ["run"]
    # once the .npz sibling exists the pickle is ignored
    _save(repo, "datasets/imu/toy_legacy/processed/canonical_imu.npz",
          [imu_rec("toy_legacy:s01", "run", 50),
           imu_rec("toy_legacy:s02", "run", 51)])
    recs, meta = ds.get_data()
    assert len(recs) == 2


# -- access cases and messages ------------------------------------------------

def test_recipe_id_not_ingested_names_the_script_and_the_card(repo):
    ds = GenericDataset("toy_recipe")
    assert ds.modalities == ()
    with pytest.raises(FileNotFoundError) as exc:
        ds.get_data()
    msg = str(exc.value)
    assert "not ingested on this machine" in msg
    assert "run ingest_toy.py --only toy_recipe" in msg
    assert "datasets/auxdata/toy_recipe/datacard.md" in msg
    # a modality request cannot hide the real problem
    with pytest.raises(FileNotFoundError, match="not ingested"):
        ds.get_data(modality="imu")


def test_hosted_id_with_nothing_canonical_says_so(repo):
    with pytest.raises(FileNotFoundError) as exc:
        GenericDataset("toy_hosted_empty").get_data()
    msg = str(exc.value)
    assert "no canonical container" in msg
    assert "run build_toy.py" in msg
    assert "datasets/imu/toy_hosted_empty/datacard.md" in msg


def test_barrier_id_raises_the_documented_route(repo):
    ds = GenericDataset("toy_barrier")
    assert ds.modalities == ()
    with pytest.raises(AccessError, match="documented access barrier"):
        ds.get_data()
    with pytest.raises(AccessError, match="email the PI"):
        ds.get_data(modality="imu")


def test_recipe_of_falls_back_to_the_card():
    assert recipe_of(REGISTRY["toy_recipe"]) == \
        "ingest_toy.py --only toy_recipe"
    assert recipe_of(REGISTRY["toy_hosted_empty"]) == "build_toy.py"
    assert recipe_of(REGISTRY["toy_eeg"]) == \
        "the ingestion recipe named in datasets/eeg/toy_eeg/datacard.md"


# -- unit level ----------------------------------------------------------------

def test_modality_is_read_from_the_record_keys():
    assert generic.modality_of(eeg_rec("a:1", "t", 3)) == "eeg"
    assert generic.modality_of(emg_rec("a:1", "t", 3)) == "emg"
    assert generic.modality_of(imu_rec("a:1", "t", 3)) == "imu"
    assert generic.modality_of(force_rec("a:1", "t", 3)) == "force"
    assert generic.modality_of(pose_rec("a:1", "t", 3)) == "pose"
    assert generic.modality_of(silhouette_rec("a_1", "01", 3)) == "silhouette"
    assert generic.modality_of({"signal": np.zeros(3)}, "emg") == "emg"
    assert generic.modality_of({"x": 1}) is None


def test_peek_modality_reads_only_the_header(tmp_path):
    p = _save(tmp_path, "datasets/pose/x/processed/canonical/S1.npz",
              [pose_rec("x:S1", "t", 4)])
    assert generic.peek_modality(p) == "pose"
    p = _save(tmp_path, "datasets/eeg/x/processed/canonical_eeg/r.npz",
              eeg_rec("x:1", "t", 4))
    assert generic.peek_modality(p) == "eeg"


@pytest.mark.parametrize("token, subject, hit", [
    ("S01", "toy:S01", True),
    ("S01", "toy:S010", False),
    ("toy_S01", "toy:S01", True),
    ("amass_ACCAD", "amass:ACCAD:Female1_c3d", True),
    ("amass_CMU", "amass:ACCAD:Female1_c3d", False),
    ("0", "care_pd:3DGait:0", True),
    ("koa_KOA_EL_001", "koa_KOA_EL_001", True),
    ("part0", "toy:A", False),
])
def test_name_matches(token, subject, hit):
    assert generic.name_matches(token, subject) is hit


def test_discover_lists_containers_in_a_stable_order(repo):
    s = LocalStore(root=str(repo))
    found = generic.discover(s, "datasets/imu/toy_multi")
    assert [(c.relpath.rsplit("/", 1)[1], c.hint, c.sharded) for c in found] \
        == [("canonical_imu.npz", "imu", False),
            ("canonical_force.npz", "force", False)]
    found = generic.discover(s, "datasets/eeg/toy_eeg")
    assert [c.hint for c in found] == ["eeg"] * 3
    assert all(c.sharded for c in found)
    assert found[0].relpath == f"{EEG_DIR}/toy_eeg__toy_eeg_s01__task_1.npz"
    assert generic.discover(s, "datasets/imu/nowhere") == []


def test_row_of_derives_n_frames_from_the_main_array():
    r = pose_rec("x:1", "t", 7)
    del r["n_frames"]
    assert generic.row_of("x", r, "pose") == ["x", "x:1", "t", "pose", 7, 30.0]


# -- the remote path: discovery from the record manifest ----------------------

def _sha(data):
    return hashlib.sha256(data).hexdigest()


def fake_record(monkeypatch, blobs, record=777):
    """A fake Zenodo record serving `blobs` (relpath -> bytes) in the
    direct layout; returns the list of urls opened."""
    calls = []
    man = ["path,bytes,sha256,record_name"]
    files = {}
    for rel, data in blobs.items():
        key = rel.replace("/", "__")
        man.append(f"{rel},{len(data)},{_sha(data)},{key}")
        files[key] = data
    files["files.csv"] = ("\n".join(man) + "\n").encode("utf-8")
    base = "https://files.fake/"

    def urlopen(req, timeout=None):
        url = req.full_url if isinstance(req, urllib.request.Request) else req
        calls.append(url)
        if url == f"https://zenodo.org/api/records/{record}":
            payload = {"files": [{"key": k, "size": len(v),
                                  "links": {"self": base + k}}
                                 for k, v in files.items()]}
            return io.BytesIO(json.dumps(payload).encode("utf-8"))
        key = url[len(base):]
        if url.startswith(base) and key in files:
            return io.BytesIO(files[key])
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(store_mod.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(store_mod.time, "sleep", lambda s: None)
    return calls


def test_remote_store_discovers_from_the_manifest(tmp_path, monkeypatch,
                                                  load_counter):
    src = tmp_path / "src"
    write_repo(src)
    blobs = {}
    for name in EEG_FILES:
        rel = f"{EEG_DIR}/{name}"
        with open(os.path.join(str(src), *rel.split("/")), "rb") as f:
            blobs[rel] = f.read()
    blobs["datasets/eeg/toy_eeg/README.md"] = b"# not a record"
    calls = fake_record(monkeypatch, blobs)
    remote = RemoteStore(cache=str(tmp_path / "cache"),
                         table={"toy_eeg": {"record": 777}})
    monkeypatch.setattr(base_mod, "dataset_info",
                        lambda code: dict(REGISTRY[code]))
    monkeypatch.setattr(base_mod, "open_store", lambda: remote)
    ds = GenericDataset("toy_eeg")
    assert ds.modalities == ("eeg",)
    assert len(calls) == 2                  # api listing + manifest only
    recs, meta = ds.get_data(subjects=["toy_eeg:s02"])
    assert meta["subject_ns"].tolist() == ["toy_eeg:s02"]
    assert meta["n_frames"].tolist() == [20]
    assert load_counter == ["toy_eeg__toy_eeg_s02__task_1.npz"]
    downloaded = [u for u in calls if u.startswith("https://files.fake/")
                  and u.endswith(".npz")]
    assert len(downloaded) == 1 and downloaded[0].endswith("s02__task_1.npz")
    recs, meta = ds.get_data()
    assert len(recs) == 3
    assert sum(u.endswith(".npz") for u in calls) == 3   # s02 was cached


def test_remote_store_without_a_record_reads_as_not_ingested(tmp_path,
                                                             monkeypatch):
    remote = RemoteStore(cache=str(tmp_path / "cache"), table={})
    monkeypatch.setattr(base_mod, "dataset_info",
                        lambda code: dict(REGISTRY[code]))
    monkeypatch.setattr(base_mod, "open_store", lambda: remote)
    ds = GenericDataset("toy_recipe")
    assert ds.modalities == ()
    with pytest.raises(FileNotFoundError, match="not ingested on this"):
        ds.get_data()
    with pytest.raises(FileNotFoundError) as exc:
        GenericDataset("toy_eeg").get_data()
    assert "no published MoveAtlas record" in str(exc.value)
    assert "datasets/eeg/toy_eeg/datacard.md" in str(exc.value)
