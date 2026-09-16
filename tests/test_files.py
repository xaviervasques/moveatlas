# -*- coding: utf-8 -*-
"""ds.files() and ds.path(): every dataset exposes what it holds, and a
hosted record that carries tables rather than canonical records says so
instead of sending a stranger to an ingestion script (LAUNCH_PLAN 1.1).
Corpus-free: a temporary local store stands in for the repository."""
import os

import numpy as np
import pytest

import moveatlas
from moveatlas import records


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """The suite is corpus-free AND network-free: with the records table
    empty the store never asks Zenodo for a listing (CI failed on
    2026-09-16 when a test reached a record during a Zenodo 504)."""
    from moveatlas import store as store_mod
    monkeypatch.setattr(store_mod, "_records_table", lambda: {})


@pytest.fixture
def toy_store(tmp_path, monkeypatch):
    """A local store with alameda_tremor holding one raw table and
    tremordb holding a non-canonical .npz plus two tables (the real
    shapes of those two published records)."""
    root = tmp_path / "store"
    a = root / "datasets" / "imu" / "alameda_tremor"
    (a / "raw").mkdir(parents=True)
    (a / "raw" / "ALAMEDA_PD_tremor_dataset.csv").write_text("id,x\n1,2\n")
    (a / "downloads.sha256").write_text("ab  ALAMEDA_PD_tremor_dataset.csv  8\n")
    t = root / "datasets" / "imu" / "tremordb" / "processed"
    t.mkdir(parents=True)
    (t / "tremordb_subject_table.csv").write_text("subject\ng2\n")
    (t / "tremordb_ingest_audit.csv").write_text("file,status\nx,ok\n")
    records.save(str(t / "tremordb_velocity.npz"),
                 [{"signal": np.zeros((10, 1), np.float32), "kind": "laser",
                   "subject_ns": "tremordb:g2", "task": "r15ofh", "fps": 100.0,
                   "source": "tremordb", "n_frames": 10, "unit": "mm/s"}])
    monkeypatch.setenv("MOVEATLAS_REPO", str(root))
    return root


def test_files_lists_everything_under_the_registry_path(toy_store):
    ds = moveatlas.dataset("tremordb")
    names = [os.path.basename(f) for f in ds.files()]
    assert names == ["tremordb_ingest_audit.csv", "tremordb_subject_table.csv",
                     "tremordb_velocity.npz"]
    assert all(f.startswith("datasets/imu/tremordb/") for f in ds.files())
    a = moveatlas.dataset("alameda_tremor")
    assert [os.path.basename(f) for f in a.files()] == \
        ["downloads.sha256", "ALAMEDA_PD_tremor_dataset.csv"] or \
        sorted(os.path.basename(f) for f in a.files()) == \
        ["ALAMEDA_PD_tremor_dataset.csv", "downloads.sha256"]


def test_path_serves_a_local_file_by_name_or_relpath(toy_store):
    ds = moveatlas.dataset("tremordb")
    p = ds.path("tremordb_velocity.npz")
    assert os.path.isfile(p)
    assert records.load(p)[0]["unit"] == "mm/s"
    p2 = ds.path("datasets/imu/tremordb/processed/tremordb_subject_table.csv")
    assert open(p2).read().startswith("subject")
    with pytest.raises(FileNotFoundError, match="holds: "):
        ds.path("nothing.csv")


def test_hosted_table_record_says_what_it_holds(toy_store):
    ds = moveatlas.dataset("alameda_tremor")
    with pytest.raises(FileNotFoundError) as e:
        ds.get_data()
    msg = str(e.value)
    assert "holds files, not canonical records" in msg
    assert "ALAMEDA_PD_tremor_dataset.csv" in msg
    assert "ds.path(" in msg and "pandas" in msg
    assert "ingestion recipe" not in msg
    ds2 = moveatlas.dataset("tremordb")
    with pytest.raises(FileNotFoundError, match="tremordb_velocity.npz"):
        ds2.get_data()


def test_barrier_dataset_lists_no_files_and_still_raises_the_route(toy_store):
    ds = moveatlas.dataset("tuh_eeg")
    assert ds.files() == []
    with pytest.raises(Exception, match="documented access barrier"):
        ds.get_data()


def test_empty_hosted_dataset_keeps_the_ingestion_message(toy_store):
    # hosted in the registry, nothing on this machine, and no record
    # listing (the store's table is empty here, see _offline): the old
    # message, naming the ingestion recipe, is what remains
    ds = moveatlas.dataset("fog_star")      # a hosted id on the generic adapter
    assert ds.files() == []
    with pytest.raises(FileNotFoundError, match="hosted but no canonical"):
        ds.get_data()
