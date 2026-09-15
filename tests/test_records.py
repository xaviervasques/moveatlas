# -*- coding: utf-8 -*-
"""The moveatlas-record/1 container: round trip, refusals, and the
equality function that decided 520 GB of pickles could be deleted.

records.equal() is the only thing that stood between the corpus and a
silent corruption during the 2026-09-08 migration: every .npz was
compared against the pickle it replaced, and only an equal verdict
allowed the pickle to be removed. A function with that much authority
gets adversarial tests: it must say False for differences that a naive
implementation would miss (dtype, shape, NaN, nested arrays, key sets,
numeric type changes) and True only for a genuine round trip.
"""
import io
import json
import os
import zipfile

import numpy as np
import pytest

from moveatlas import records


# --------------------------------------------------------------- fixtures
def eeg_record():
    rng = np.random.default_rng(0)
    return {
        "signal": rng.standard_normal((64, 3)).astype(np.float32),
        "channels": [{"site": "C3", "ref": "PZ", "kind": "eeg"},
                     {"site": "C4", "ref": "PZ", "kind": "eeg"},
                     {"site": "CZ", "ref": "PZ", "kind": "eeg"}],
        "fps": 300.0, "unit": "uV", "unit_scale": 1.0,
        "filters": {"hp_hz": None, "lp_hz": 100.0, "notch_hz": 50},
        "subject_ns": "src:S01", "task": "walk", "source": "src",
        "n_frames": 64, "label": np.zeros(64, np.int8),
    }


def imu_record():
    return {
        "signal": np.arange(2 * 3 * 9, dtype=np.float32).reshape(2, 3, 9),
        "location_ids": np.array([0, 4, 9], np.int64),
        "channel_mask": np.ones((3, 9), bool),
        "fps": 60.0, "subject_ns": "src:S02", "task": "t", "source": "src",
        "n_frames": 2, "label": None,
    }


ALL = {"eeg": eeg_record, "imu": imu_record}


# ------------------------------------------------------------- round trip
@pytest.mark.parametrize("name", sorted(ALL))
def test_round_trip_is_equal(tmp_path, name):
    rec = ALL[name]()
    p = str(tmp_path / f"{name}.npz")
    records.save(p, rec)
    back = records.load(p)
    assert records.equal(rec, back)
    for k, v in rec.items():
        if isinstance(v, np.ndarray):
            assert back[k].dtype == v.dtype
            assert back[k].shape == v.shape
            np.testing.assert_array_equal(back[k], v)


def test_round_trip_list(tmp_path):
    recs = [eeg_record(), imu_record()]
    p = str(tmp_path / "list.npz")
    records.save(p, recs)
    back = records.load(p)
    assert isinstance(back, list) and len(back) == 2
    assert records.equal(recs, back)


def test_nan_survives_and_compares_equal(tmp_path):
    rec = eeg_record()
    rec["signal"][3, 1] = np.nan
    rec["fps"] = float("nan")
    p = str(tmp_path / "nan.npz")
    records.save(p, rec)
    back = records.load(p)
    assert np.isnan(back["signal"][3, 1])
    assert records.equal(rec, back)


def test_nested_arrays_at_any_depth(tmp_path):
    rec = {"meta": {"streams": [{"x": np.arange(3), "name": "a"},
                                {"x": np.arange(4) * 1.5, "name": "b"}]},
           "top": np.eye(2), "n": 2}
    p = str(tmp_path / "nested.npz")
    records.save(p, rec)
    back = records.load(p)
    assert records.equal(rec, back)
    np.testing.assert_array_equal(back["meta"]["streams"][1]["x"],
                                  np.arange(4) * 1.5)


def test_empty_array_and_empty_containers(tmp_path):
    rec = {"signal": np.zeros((0, 3), np.float32), "channels": [],
           "meta": {}, "n_frames": 0}
    p = str(tmp_path / "empty.npz")
    records.save(p, rec)
    back = records.load(p)
    assert records.equal(rec, back)
    assert back["signal"].shape == (0, 3)


def test_unicode_metadata(tmp_path):
    rec = {"signal": np.zeros(2), "note": "sujet a droite, 30 degres",
           "muscle": "gastrocnemius", "cle": {"accentue": "e acute"}}
    p = str(tmp_path / "uni.npz")
    records.save(p, rec)
    assert records.equal(rec, records.load(p))


# ---------------------------------------------------------------- refusals
def test_object_array_is_refused(tmp_path):
    rec = {"bad": np.array([{"a": 1}, "b"], dtype=object)}
    with pytest.raises(TypeError, match="object arrays"):
        records.save(str(tmp_path / "o.npz"), rec)


def test_non_json_value_is_refused(tmp_path):
    rec = {"signal": np.zeros(2), "bad": {1, 2, 3}}
    with pytest.raises(TypeError):
        records.save(str(tmp_path / "s.npz"), rec)


def test_reserved_token_key_is_refused(tmp_path):
    rec = {"signal": np.zeros(2), "meta": {records.TOKEN: "x"}}
    with pytest.raises(TypeError, match="reserved"):
        records.save(str(tmp_path / "t.npz"), rec)


def test_save_refuses_a_non_record(tmp_path):
    with pytest.raises(TypeError):
        records.save(str(tmp_path / "x.npz"), "not a record")
    with pytest.raises(TypeError):
        records.save(str(tmp_path / "y.npz"), [eeg_record(), "not a dict"])


def test_load_refuses_a_foreign_npz(tmp_path):
    p = str(tmp_path / "foreign.npz")
    np.savez(p, a=np.arange(3))
    with pytest.raises(ValueError, match="not a .* container"):
        records.load(p)


def test_load_refuses_an_unknown_format_tag(tmp_path):
    p = str(tmp_path / "future.npz")
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(records.META, json.dumps(
            {"format": "moveatlas-record/99", "kind": "record", "meta": {}}))
    with pytest.raises(ValueError, match="unknown format"):
        records.load(p)


def test_truncated_container_is_detected(tmp_path):
    """meta.json is written last, so a truncated write has no header."""
    good = str(tmp_path / "good.npz")
    records.save(good, eeg_record())
    with zipfile.ZipFile(good) as z:
        names = z.namelist()
    assert names[-1] == records.META, "the header must be the last member"
    cut = str(tmp_path / "cut.npz")
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(cut, "w") as dst:
        for n in names:
            if n != records.META:
                dst.writestr(n, src.read(n))
    assert not records.is_container(cut)
    with pytest.raises(ValueError):
        records.load(cut)


# ----------------------------------------------------------------- equal()
def test_equal_detects_dtype_change():
    a = {"x": np.arange(4, dtype=np.float32)}
    b = {"x": np.arange(4, dtype=np.float64)}
    assert not records.equal(a, b)


def test_equal_detects_shape_change():
    assert not records.equal({"x": np.zeros((2, 3))}, {"x": np.zeros((3, 2))})


def test_equal_detects_value_change():
    a = {"x": np.arange(4.0)}
    b = {"x": np.arange(4.0)}
    b["x"][2] = 99
    assert not records.equal(a, b)


def test_equal_detects_missing_and_extra_keys():
    assert not records.equal({"a": 1, "b": 2}, {"a": 1})
    assert not records.equal({"a": 1}, {"a": 1, "b": 2})


def test_equal_detects_array_versus_scalar():
    assert not records.equal({"x": np.zeros(1)}, {"x": 0.0})


def test_equal_detects_nested_difference():
    a = {"m": {"s": [{"x": np.arange(3)}]}}
    b = {"m": {"s": [{"x": np.arange(3) + 1}]}}
    assert not records.equal(a, b)


def test_equal_list_length_and_type():
    assert not records.equal([eeg_record()], [eeg_record(), eeg_record()])
    assert not records.equal(eeg_record(), [eeg_record()])


def test_equal_accepts_the_normalization_save_applies():
    """save() turns tuples into lists and numpy scalars into Python ones;
    equal() must not call that a difference, or the migration would have
    refused every record it correctly converted."""
    a = {"t": (1, 2, 3), "n": np.float32(2.5), "i": np.int64(7)}
    b = {"t": [1, 2, 3], "n": 2.5, "i": 7}
    assert records.equal(a, b)


def test_equal_is_not_fooled_by_close_floats():
    a = {"x": np.array([1.0], np.float64)}
    b = {"x": np.array([1.0 + 1e-12], np.float64)}
    assert not records.equal(a, b)


# ------------------------------------------------------- transition readers
def test_prefer_npz_and_load_any(tmp_path):
    rec = eeg_record()
    npz = tmp_path / "r.npz"
    pkl = tmp_path / "r.pkl"
    records.save(str(npz), rec)
    pkl.write_bytes(b"not really a pickle")
    assert records.prefer_npz(str(pkl)) == str(npz)
    assert records.equal(records.load_any(str(pkl)), rec)


def test_load_any_warns_on_a_legacy_pickle(tmp_path):
    import pickle
    p = tmp_path / "legacy.pkl"
    p.write_bytes(pickle.dumps({"signal": np.zeros(3), "n_frames": 3}))
    with pytest.deprecated_call():
        got = records.load_any(str(p))
    assert got["n_frames"] == 3


def test_prefer_npz_leaves_other_paths_alone(tmp_path):
    assert records.prefer_npz("x.txt") == "x.txt"
    missing = str(tmp_path / "gone.pkl")
    assert records.prefer_npz(missing) == missing


# -------------------------------------------------------- numpy readability
def test_a_stranger_can_read_it_with_numpy_alone(tmp_path):
    """The reason the format exists: no code executes on load."""
    p = str(tmp_path / "plain.npz")
    records.save(p, eeg_record())
    with np.load(p) as z:
        # numpy strips the .npy suffix when it lists members
        assert "signal" in z.files
        assert z["signal"].shape == (64, 3)
    with zipfile.ZipFile(p) as z:
        header = json.loads(z.read(records.META))
    assert header["format"] == records.FORMAT
    assert header["kind"] == "record"


def test_no_partial_file_survives_a_failed_save(tmp_path):
    bad = {"x": np.zeros(2), "nope": {1, 2}}
    p = tmp_path / "fail.npz"
    with pytest.raises(TypeError):
        records.save(str(p), bad)
    assert not p.exists()
    assert not (tmp_path / "fail.npz.part").exists()
