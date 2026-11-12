# -*- coding: utf-8 -*-
"""to_frame on synthetic canonical records of every family: n rows, masks
honored as NaN (never zero), meaningful column names."""
import numpy as np
import pytest

from moveatlas.frames import (IMU_CHANNELS, IMU_LOCATIONS, POSE_JOINTS,
                              SIL_SCALARS, to_frame)

N = 50
FPS = 25.0


def _check_time_index(df, n, fps):
    assert len(df) == n
    assert df.index.name == "time_s"
    assert df.index[0] == 0.0
    assert df.index[1] == pytest.approx(1.0 / fps)
    assert df.index[-1] == pytest.approx((n - 1) / fps)


# -- pose ---------------------------------------------------------------------

def _pose_record(n=N, n_axes=3, coord_mask=None):
    rng = np.random.default_rng(0)
    coords = rng.normal(size=(n, 15, 3)).astype(np.float32) + 1.0
    valid = np.ones((n, 15), bool)
    valid[3:8, 5] = False                    # l_elbow missing on 5 frames
    valid[10, :] = False                     # one wholly empty frame
    coords[~valid] = 0.0                     # the contract stores zeros
    rec = {"coords": coords, "valid_mask": valid, "fps": FPS,
           "subject_ns": "toy:S1", "task": "walk"}
    if coord_mask is not None:
        rec["coord_mask"] = np.asarray(coord_mask, bool)
    return rec


def test_pose_frame_shape_and_columns():
    df = to_frame(_pose_record())
    _check_time_index(df, N, FPS)
    assert df.shape == (N, 45)
    assert list(df.columns.names) == ["joint", "axis"]
    assert list(df.columns.get_level_values("joint").unique()) == POSE_JOINTS
    assert ("l_elbow", "x") in df.columns
    assert ("pelvis", "z") in df.columns


def test_pose_masked_joints_are_nan_not_zero():
    df = to_frame(_pose_record())
    elbow = df["l_elbow"]
    assert elbow.iloc[3:8].isna().all().all()
    assert not elbow.iloc[:3].isna().any().any()
    assert df.iloc[10].isna().all()
    assert not df.iloc[11].isna().any()
    assert (df.iloc[11] != 0).all()
    assert df.isna().sum().sum() == 5 * 3 + 15 * 3


def test_pose_padded_2d_drops_z():
    df = to_frame(_pose_record(coord_mask=[True, True, False]))
    assert df.shape == (N, 30)
    assert set(df.columns.get_level_values("axis")) == {"x", "y"}


# -- emg ----------------------------------------------------------------------

def _emg_record(n=N):
    channels = [{"kind": "emg", "muscle": "tibialis_anterior", "side": "L"},
                {"kind": "emg", "muscle": "gastrocnemius", "side": "R"},
                {"kind": "ecg"}]
    sig = np.random.default_rng(1).normal(size=(n, len(channels)))
    return {"signal": sig.astype(np.float32), "channels": channels,
            "fps": FPS, "signal_kind": "raw", "unit": "mV",
            "subject_ns": "toy:S1"}


def test_emg_frame_named_by_muscle_and_side():
    df = to_frame(_emg_record())
    _check_time_index(df, N, FPS)
    assert df.shape == (N, 3)
    assert df.columns.name == "channel"
    assert list(df.columns) == ["tibialis_anterior_L", "gastrocnemius_R",
                                "ecg"]
    assert not df.isna().any().any()


# -- eeg ----------------------------------------------------------------------

def _eeg_record(n=N, dict_channels=True):
    sites = ["C3", "C4", "CZ"]
    if dict_channels:
        channels = [{"site": s, "ref": "AVG", "kind": "eeg"} for s in sites]
    else:
        channels = list(sites)
    sig = np.random.default_rng(2).normal(size=(n, len(sites)))
    return {"signal": sig.astype(np.float32), "channels": channels,
            "fps": FPS, "unit": "uV", "subject_ns": "toy:S1"}


def test_eeg_frame_from_site_list():
    df = to_frame(_eeg_record(dict_channels=False))
    _check_time_index(df, N, FPS)
    assert list(df.columns) == ["C3", "C4", "CZ"]
    assert df.columns.name == "channel"


def test_eeg_frame_from_canonical_channel_table_uses_sites():
    # fixed 2026-09-08: dict channels carrying a site are EEG and take it
    # as the column name; EMG dicts keep muscle_side(_electrode)
    df = to_frame(_eeg_record(dict_channels=True))
    assert len(df) == N
    assert list(df.columns) == ["C3", "C4", "CZ"]


def test_eeg_canonical_channel_table_keeps_row_count():
    # row count and values survive even while the names are wrong
    rec = _eeg_record(dict_channels=True)
    df = to_frame(rec)
    _check_time_index(df, N, FPS)
    assert df.shape == (N, 3)
    np.testing.assert_allclose(df.to_numpy(), rec["signal"], rtol=1e-6)


# -- imu ----------------------------------------------------------------------

def _imu_record(n=N, with_sample_valid=True):
    L = 2
    location_ids = np.array([IMU_LOCATIONS.index("trunk"),
                             IMU_LOCATIONS.index("wrist_R")])
    channel_mask = np.zeros((L, 9), bool)
    channel_mask[0, :6] = True              # trunk: acc + gyr
    channel_mask[1, :3] = True              # wrist_R: acc only
    sig = np.random.default_rng(3).normal(size=(n, L, 9)).astype(np.float32)
    sig += 5.0                              # keep every real value non-zero
    sig[:, ~channel_mask] = 0.0
    rec = {"signal": sig, "channel_mask": channel_mask,
           "location_ids": location_ids,
           "location_mask": np.zeros(len(IMU_LOCATIONS), bool),
           "fps": FPS, "subject_ns": "toy:S1", "task": "walk"}
    rec["location_mask"][location_ids] = True
    if with_sample_valid:
        sv = np.ones((n, L), bool)
        sv[20:25, 0] = False                # trunk dropout
        sig[20:25, 0, :] = 0.0              # the contract stores zeros
        rec["sample_valid"] = sv
    return rec


def test_imu_frame_columns_are_instrumented_slots_only():
    df = to_frame(_imu_record())
    _check_time_index(df, N, FPS)
    assert list(df.columns.names) == ["location", "channel"]
    assert df.shape == (N, 9)
    assert list(df["trunk"].columns) == IMU_CHANNELS[:6]
    assert list(df["wrist_R"].columns) == IMU_CHANNELS[:3]
    assert ("trunk", "mag_x") not in df.columns
    assert ("wrist_R", "gyr_x") not in df.columns


def test_imu_dropouts_are_nan_not_zero():
    df = to_frame(_imu_record())
    assert df["trunk"].iloc[20:25].isna().all().all()
    assert not df["wrist_R"].iloc[20:25].isna().any().any()
    assert not df.iloc[:20].isna().any().any()
    assert (df.iloc[:20] != 0).all().all()
    assert df.isna().sum().sum() == 5 * 6


def test_imu_without_sample_valid_has_no_nan():
    df = to_frame(_imu_record(with_sample_valid=False))
    assert df.shape == (N, 9)
    assert not df.isna().any().any()


# -- force --------------------------------------------------------------------

def _force_record(n=N):
    S = 9                                    # s1..s8 + total
    force = np.abs(np.random.default_rng(4).normal(size=(n, 2, S))) + 1.0
    mask = np.ones((2, S), bool)
    mask[1, :8] = False                      # right foot: total only
    force[:, ~mask] = 0.0
    return {"force": force.astype(np.float32), "sensor_mask": mask,
            "fps": FPS, "subject_ns": "toy:S1", "task": "walk"}


def test_force_frame_columns_and_masks():
    df = to_frame(_force_record())
    _check_time_index(df, N, FPS)
    assert list(df.columns.names) == ["foot", "sensor"]
    assert df.shape == (N, 18)
    sensors = [f"s{i}" for i in range(1, 9)] + ["total"]
    assert list(df["left"].columns) == sensors
    assert list(df["right"].columns) == sensors
    assert not df["left"].isna().any().any()
    assert (df["left"] != 0).all().all()
    assert df["right"][[f"s{i}" for i in range(1, 9)]].isna().all().all()
    assert not df[("right", "total")].isna().any()
    assert df.isna().sum().sum() == N * 8


def test_force_sample_valid_becomes_nan():
    rec = _force_record()
    sv = np.ones((N, 2), bool)
    sv[:3, 0] = False
    rec["sample_valid"] = sv
    df = to_frame(rec)
    assert df["left"].iloc[:3].isna().all().all()
    assert not df[("left", "total")].iloc[3:].isna().any()
    assert not df[("right", "total")].isna().any()


# -- silhouette ---------------------------------------------------------------

def _silhouette_record(n=N):
    rng = np.random.default_rng(5)
    contour = rng.normal(size=(n, 64, 2)).astype(np.float32)
    scalars = np.abs(rng.normal(size=(n, 8))).astype(np.float32) + 0.5
    detect = np.ones(n, bool)
    detect[[0, 7, 8, 9]] = False
    contour[~detect] = 0.0                   # the contract stores zeros
    scalars[~detect] = 0.0
    return {"contour": contour, "scalars": scalars, "detect_mask": detect,
            "scalar_mask": np.ones(8, bool), "fps": FPS,
            "subject_ns": "toy:S1", "task": "walk"}


def test_silhouette_frame_scalars_and_detect_mask():
    df = to_frame(_silhouette_record())
    _check_time_index(df, N, FPS)
    assert df.shape == (N, 8)
    assert df.columns.name == "scalar"
    assert list(df.columns) == SIL_SCALARS
    assert df.iloc[[0, 7, 8, 9]].isna().all().all()
    assert not df.iloc[1:7].isna().any().any()
    assert (df.iloc[1:7] != 0).all().all()
    assert df.isna().sum().sum() == 4 * 8


# -- unknown layout ---------------------------------------------------------

def test_unrecognized_record_raises():
    with pytest.raises(ValueError, match="unrecognized canonical record"):
        to_frame({"fps": FPS, "subject_ns": "toy:S1"})
