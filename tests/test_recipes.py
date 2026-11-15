# -*- coding: utf-8 -*-
"""The recipe tier as library calls: moveatlas.fetch / ingest / recipe,
the user store, the transports' journal and verification, and the IMU
contract writer. Corpus-free and network-free: the transports are
exercised on local files and a stub API."""
import csv
import hashlib
import io
import json
import os
import zipfile

import numpy as np
import pytest

import moveatlas
from moveatlas import recipes
from moveatlas.recipes import imu, transports
from moveatlas import records


# -- recipe(): the three answers --------------------------------------------

def test_recipe_kinds():
    r = recipes.recipe("fog_turning_filho")
    assert r.kind == "library" and r.fetch_fn and r.ingest_fn
    assert "moveatlas.fetch('fog_turning_filho')" in r.describe()
    s = recipes.recipe("ninapro")
    assert s.kind == "script" and "build_canonical_emg.py" in s.ingest_cmd
    with pytest.raises(recipes.NoRecipe, match="hosted"):
        recipes.recipe("modys_video")
    with pytest.raises(recipes.NoRecipe, match="barrier"):
        recipes.recipe("tuh_eeg")
    with pytest.raises(KeyError):
        recipes.recipe("no_such_dataset")


def test_script_recipe_raises_with_the_commands():
    with pytest.raises(recipes.RecipeIsScript) as e:
        moveatlas.fetch("ninapro")
    msg = str(e.value)
    assert "fetch_p2_lot.py --only ninapro" in msg
    assert "git clone https://github.com/xaviervasques/moveatlas" in msg
    with pytest.raises(recipes.RecipeIsScript, match="build_canonical_emg"):
        moveatlas.ingest("ninapro")


def test_uncurated_recipe_points_at_the_card():
    # a recipe-tier id with no curated entry still answers, honestly
    rows = [r for r in moveatlas.list_datasets(case="recipe")
            if r["id"] not in recipes._LIBRARY and r["id"] not in recipes._SCRIPTS]
    assert rows, "the registry has uncurated recipe ids"
    r = recipes.recipe(rows[0]["id"])
    assert r.kind == "script"
    assert "datacard.md" in r.fetch_cmd


def test_public_api_exports():
    for name in ("fetch", "ingest", "recipe", "store_root"):
        assert name in moveatlas.__all__
        assert callable(getattr(moveatlas, name))


# -- the user store ------------------------------------------------------------

def test_store_root_is_the_user_store_outside_a_source_tree(tmp_path, monkeypatch):
    from moveatlas import store as store_mod
    monkeypatch.delenv("MOVEATLAS_REPO", raising=False)
    monkeypatch.setenv("MOVEATLAS_STORE", str(tmp_path / "s"))
    fake = tmp_path / "site-packages" / "moveatlas"
    fake.mkdir(parents=True)
    monkeypatch.setattr(store_mod, "__file__", str(fake / "store.py"))
    assert recipes.store_root() == str(tmp_path / "s")
    assert (tmp_path / "s" / "datasets").is_dir()


# -- transports: journal, verification, resume ---------------------------------

def test_journal_appends_once(tmp_path):
    root = str(tmp_path)
    transports.journal(root, "datasets/imu/toy", "a.zip", 3, "ab" * 32)
    transports.journal(root, "datasets/imu/toy", "a.zip", 3, "ab" * 32)
    transports.journal(root, "datasets/imu/toy", "b.csv", 5, "cd" * 32)
    j = transports.journaled(root, "datasets/imu/toy")
    assert j == {"a.zip": ("ab" * 32, 3), "b.csv": ("cd" * 32, 5)}
    text = (tmp_path / "datasets" / "imu" / "toy" / "downloads.sha256").read_text()
    assert text.count("a.zip") == 1


def test_download_url_verifies_and_skips_complete(tmp_path, monkeypatch):
    payload = b"movement data " * 1000
    md5 = hashlib.md5(payload).hexdigest()
    src = tmp_path / "src.bin"
    src.write_bytes(payload)
    # as_uri(), not "file://" + path: on Windows the latter reads "C:" as a host name, and
    # urllib then asks the resolver about it (a network call, about 300 s per test here)
    url = src.as_uri()
    dest = str(tmp_path / "raw" / "src.bin")
    os.makedirs(os.path.dirname(dest))
    n, sha = transports.download_url(url, dest, size=len(payload), md5=md5)
    assert n == len(payload) and sha == hashlib.sha256(payload).hexdigest()
    assert not os.path.exists(dest + ".part")
    # complete file: not touched again (the source may even be gone)
    src.unlink()
    n2, sha2 = transports.download_url(url, dest, size=len(payload), md5=md5)
    assert (n2, sha2) == (n, sha)
    # wrong checksum: refused, nothing left behind
    src.write_bytes(payload)
    with pytest.raises(transports.FetchError, match="md5"):
        transports.download_url(url, str(tmp_path / "raw" / "other.bin"),
                                size=len(payload), md5="0" * 32)
    assert not os.path.exists(str(tmp_path / "raw" / "other.bin"))


def test_figshare_article_uses_api_listing_and_journal(tmp_path, monkeypatch):
    payload = b"1\t0.0\t0.1\t0.2\t0.9\t1.0\t2.0\n" * 10
    src = tmp_path / "IMU.zip"
    src.write_bytes(payload)
    listing = {"title": "toy article", "license": {"name": "CC BY 4.0"},
               "files": [{"name": "IMU.zip", "size": len(payload),
                          "computed_md5": hashlib.md5(payload).hexdigest(),
                          "download_url": src.as_uri()},
                         {"name": "Videos.zip", "size": 5, "computed_md5": "x",
                          "download_url": "file:///nowhere"}]}
    monkeypatch.setattr(transports, "api_json", lambda url, tries=5: listing)
    # curl is not needed for a file:// source in the test: route through urllib
    monkeypatch.setattr(transports, "curl_download", transports.download_url)
    out = transports.figshare_article(str(tmp_path), "datasets/pose/toy", 1,
                                      only=["IMU.zip"])
    assert [o[0] for o in out] == ["IMU.zip"]
    assert (tmp_path / "datasets" / "pose" / "toy" / "raw" / "IMU.zip").exists()
    assert "IMU.zip" in transports.journaled(str(tmp_path), "datasets/pose/toy")
    with pytest.raises(transports.FetchError, match="no file selected"):
        transports.figshare_article(str(tmp_path), "datasets/pose/toy", 1,
                                    only=["absent"])


# -- the IMU contract writer -----------------------------------------------------

def test_make_record_validity_rules():
    T = 50
    acc = np.random.rand(T)
    dead = np.full(T, np.nan)
    dropout = np.random.rand(T)
    dropout[10:20] = np.nan
    rec = imu.make_record({"lower_back": {"acc_x": acc, "acc_y": dropout,
                                          "gyro_x": dead},
                           "wrist_L": {"acc_x": dead}},
                          128.0, "toy:s1", "walk", "toy")
    # wrist_L had only a dead channel: dropped; gyro_x dead: masked off
    assert rec["signal"].shape == (T, 1, 9)
    assert list(rec["location_ids"]) == [imu.LOC_I["lower_back"]]
    assert rec["channel_mask"][0, imu.CH_I["acc_x"]]
    assert rec["channel_mask"][0, imu.CH_I["acc_y"]]
    assert not rec["channel_mask"][0, imu.CH_I["gyro_x"]]
    assert np.isfinite(rec["signal"]).all()
    assert rec["sample_valid"].shape == (T, 1)
    assert not rec["sample_valid"][10:20, 0].any() and rec["sample_valid"][:10, 0].all()
    assert 0 < rec["dropout_fraction"] < 1
    assert rec["n_frames"] == T and rec["fps"] == 128.0


def test_imu_save_writes_container_and_manifest(tmp_path):
    root = str(tmp_path)
    rec = imu.make_record({"lower_back": {"acc_x": np.ones(8)}}, 100.0,
                          "toy:s1", "t1", "toy")
    out = imu.save(root, "toy", [rec])
    assert out.endswith(os.path.join("datasets", "imu", "toy", "processed",
                                     "canonical_imu.npz"))
    back = records.load(out)
    assert len(back) == 1 and back[0]["subject_ns"] == "toy:s1"
    m = list(csv.DictReader(open(os.path.join(os.path.dirname(out), "manifest.csv"))))
    assert m[0]["source"] == "toy" and m[0]["locations"] == "lower_back"
    # with a central manifest present (an ingestion machine): merged, not clobbered
    central = tmp_path / "datasets" / "_canonical_imu_manifest.csv"
    central.write_text("source,subject_ns,task,fps,n_frames,locations\n"
                       "other,o:1,t,100,8,trunk\n"
                       "toy,stale:1,t,100,8,trunk\n", encoding="utf-8")
    imu.save(root, "toy", [rec])
    rows = list(csv.DictReader(open(central)))
    assert [r["source"] for r in rows] == ["other", "toy"]
    assert rows[1]["subject_ns"] == "toy:s1"


# -- the fog_turning recipe end to end, on a synthetic archive ----------------

def test_fog_turning_ingest_from_a_synthetic_archive(tmp_path):
    root = str(tmp_path)
    raw = tmp_path / "datasets" / "pose" / "fog_turning_filho" / "raw"
    raw.mkdir(parents=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        head = "Frame\tTime\tACC_ML\tACC_AP\tACC_SI\tGYR_ML\tGYR_AP\n"
        body = "".join(f"{i}\t{i / 128:.4f}\t0.01\t0.02\t0.98\t1.5\t-0.5\n"
                       for i in range(256))
        z.writestr("S01_turn1.txt", head + body)
        z.writestr("S02_turn1.txt", head + body)
        z.writestr("readme.pdf", b"not data")
    (raw / "IMU.zip").write_bytes(buf.getvalue())
    out, n = recipes.ingest("fog_turning_filho", root=root)
    assert n == 2
    back = records.load(out)
    assert {r["subject_ns"] for r in back} == {"fog_turning:S01", "fog_turning:S02"}
    assert back[0]["signal"].shape == (256, 1, 9)
    assert back[0]["fps"] == 128.0
    # written under the dataset's registry path, where the generic loader looks
    assert out.endswith(os.path.join("datasets", "pose", "fog_turning_filho",
                                     "processed", "canonical_imu.npz"))
    from moveatlas.store import LocalStore
    from moveatlas.datasets import generic
    found = generic.discover(LocalStore(root), "datasets/pose/fog_turning_filho")
    assert found


def test_fog_turning_ingest_without_fetch_says_so(tmp_path):
    with pytest.raises(FileNotFoundError, match="moveatlas.fetch"):
        recipes.ingest("fog_turning_filho", root=str(tmp_path))


# -- fog_star: a hosted dataset that the library can also rebuild from origin --

def test_hosted_dataset_may_have_a_library_recipe():
    r = recipes.recipe("fog_star")
    assert r.kind == "library"
    assert "get_data" in r.describe() and "moveatlas.fetch('fog_star')" in r.describe()


def test_fog_star_ingest_from_a_synthetic_csv(tmp_path):
    pd = pytest.importorskip("pandas")
    root = str(tmp_path)
    raw = tmp_path / "datasets" / "imu" / "fog_star" / "raw"
    raw.mkdir(parents=True)
    n = 120
    cols = {"subjectID": ["S1"] * n, "sessionID": [1] * n, "taskID": [2] * n,
            "fog": [0] * (n // 2) + [1] * (n // 2)}
    for src in ("ankleL", "ankleR", "back", "wrist"):
        for ax, v in (("x", 0.0), ("y", 0.0), ("z", 9.81)):   # m/s^2: converted
            cols[f"{src}_acc_{ax}"] = [v] * n
        for ax in "xyz":
            cols[f"{src}_gyro_{ax}"] = [0.5] * n
    pd.DataFrame(cols).to_csv(raw / "sensor_data.csv", index=False)
    out, k = recipes.ingest("fog_star", root=root)
    assert k == 1
    rec = records.load(out)[0]
    assert rec["subject_ns"] == "fog_star:S1" and rec["task"] == "s1_t2"
    assert rec["signal"].shape == (n, 4, 9)
    # m/s^2 recognised and converted to g
    assert abs(float(rec["signal"][0, 0, imu.CH_I["acc_z"]]) - 1.0) < 1e-3
    assert rec["label"].shape == (n,) and rec["label"].sum() == n // 2


def test_manual_download_message_names_url_path_and_checksum():
    e = transports.ManualDownload("https://h/x", "/store/raw/IMU.zip", 12, "ab" * 16)
    msg = str(e)
    assert "https://h/x" in msg and "/store/raw/IMU.zip" in msg
    assert "12 bytes" in msg and "md5 " + "ab" * 16 in msg
    assert isinstance(e, transports.FetchError)


# -- daphnet, hd_accel_jnet, monipar: the three more library recipes ---------

def test_five_library_recipes_are_registered():
    for did in ("fog_star", "fog_turning_filho", "daphnet", "hd_accel_jnet", "monipar"):
        r = recipes.recipe(did)
        assert r.kind == "library", did


def test_daphnet_ingest_from_a_synthetic_archive(tmp_path):
    root = str(tmp_path)
    raw = tmp_path / "datasets" / "imu" / "daphnet" / "raw"
    raw.mkdir(parents=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        # 11 columns: time, 9 accelerometer channels in mg, annotation
        lines = "\n".join(" ".join(str(v) for v in [i * 15] + [1000] * 9 + [1]) for i in range(64))
        z.writestr("dataset_fog_release/dataset/S01R01.txt", lines)
        z.writestr("dataset_fog_release/dataset/S02R01.txt", lines)
        z.writestr("dataset_fog_release/doc/readme.txt", "not data")
    (raw / "daphnet.zip").write_bytes(buf.getvalue())
    out, n = recipes.ingest("daphnet", root=root)
    assert n == 2
    rec = records.load(out)[0]
    assert rec["subject_ns"] == "daphnet:S01" and rec["fps"] == 64.0
    assert rec["signal"].shape == (64, 3, 9)                # ankle, thigh, trunk
    assert abs(float(rec["signal"][0, 0, imu.CH_I["acc_x"]]) - 1.0) < 1e-6   # mg -> g
    assert rec["label"].shape == (64,)


def test_hd_accel_ingest_from_synthetic_csvs(tmp_path):
    pd = pytest.importorskip("pandas")
    root = str(tmp_path)
    raw = tmp_path / "datasets" / "imu" / "hd_accel_jnet" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({"x": [0.1] * 20, "y": [0.2] * 20, "z": [0.9] * 20,
                  "label": [0] * 20}).to_csv(raw / "7.csv", index=False)
    pd.DataFrame({"id": [7], "age": [60]}).to_csv(raw / "metadata.csv", index=False)
    out, n = recipes.ingest("hd_accel_jnet", root=root)
    assert n == 1
    rec = records.load(out)[0]
    assert rec["subject_ns"] == "hd_accel:7" and rec["fps"] == 100.0
    assert rec["signal"].shape == (20, 1, 9)


def test_monipar_ingest_from_a_synthetic_mat(tmp_path):
    sio = pytest.importorskip("scipy.io")
    root = str(tmp_path)
    raw = tmp_path / "datasets" / "imu" / "monipar" / "raw"
    raw.mkdir(parents=True)
    t = np.arange(0, 2000, 20.0)                            # ms, 50 Hz
    cell = np.column_stack([t, np.full_like(t, 0.0), np.full_like(t, 0.0),
                            np.full_like(t, 9.81), np.zeros_like(t)])
    cells = np.empty((6, 8), dtype=object)
    for i in range(6):
        for j in range(8):
            cells[i, j] = cell if (i, j) != (0, 1) else np.zeros((3, 5))   # one too-short cell
    sio.savemat(str(raw / "MONIPAR_PD_SUPERVISED.mat"), {"SUPERVISED_RAWDATA": cells})
    out, n = recipes.ingest("monipar", root=root)
    assert n == 47
    rec = records.load(out)[0]
    assert rec["subject_ns"] == "monipar:sup_r0c0" and abs(rec["fps"] - 50.0) < 1e-6
    assert abs(float(rec["signal"][0, 0, imu.CH_I["acc_z"]]) - 1.0) < 1e-3   # m/s^2 -> g


def test_an_all_zero_channel_is_an_absent_sensor():
    import numpy as np
    from moveatlas.recipes import imu
    z = np.zeros(50)
    x = np.linspace(-1, 1, 50)
    rec = imu.make_record({"head": {"acc_x": z, "acc_y": z, "acc_z": z},
                           "trunk": {"acc_x": x, "acc_y": x, "acc_z": x + 1}},
                          100.0, "t:1", "t", "t")
    # the head wrote zeros throughout: dropped, like a never-finite sensor
    assert rec["location_ids"].tolist() == [imu.LOC_I["trunk"]]
    assert rec["channel_mask"][:, :3].all() and not rec["channel_mask"][:, 3:].any()
