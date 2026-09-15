# -*- coding: utf-8 -*-
"""FixedIntervalWindows: window counts and record boundaries."""
import numpy as np
import pytest

from moveatlas.paradigms.windows import FixedIntervalWindows


def _record(n, fps, value, subject, label=0, task="walk_trial01", kind="signal"):
    """A record whose every sample carries `value`, so a window that mixes
    records would show more than one distinct value."""
    if kind == "signal":                     # emg-like [n, c]
        data = np.full((n, 3), value, np.float32)
        rec = {"signal": data}
    elif kind == "imu":                      # imu-like [n, L, 9]
        data = np.full((n, 2, 9), value, np.float32)
        rec = {"signal": data}
    else:                                    # pose-like [n, 15, 3]
        data = np.full((n, 15, 3), value, np.float32)
        rec = {"coords": data}
    rec.update({"fps": fps, "subject_ns": subject, "label": label,
                "task": task})
    return rec


@pytest.mark.parametrize("n, fps, dur, stride, expected", [
    (100, 10.0, 2.0, 1.0, 9),        # w=20, s=10: (100-20)//10 + 1
    (100, 10.0, 2.0, 2.0, 5),        # non-overlapping
    (100, 10.0, 2.0, None, 5),       # stride defaults to duration
    (100, 10.0, 10.0, 1.0, 1),       # exactly one window
    (99, 10.0, 10.0, 1.0, 0),        # one sample short: nothing
    (100, 10.0, 0.1, 1.0, 0),        # w=1 < 2: skipped
    (1000, 100.0, 2.0, 0.5, 17),     # w=200, s=50: (1000-200)//50 + 1
    (1000, 30.0, 1.0, 1.0, 33),      # w=30, s=30: 1000//30
])
def test_window_count(n, fps, dur, stride, expected):
    par = FixedIntervalWindows(duration_s=dur, stride_s=stride)
    X, y, groups = par.get_data([_record(n, fps, 1.0, "toy:S1")])
    assert len(X) == expected
    assert len(y) == expected and len(groups) == expected
    w = int(round(dur * fps))
    for win in X:
        assert win.shape == (w, 3)


def test_windows_never_cross_record_boundaries():
    fps = 10.0
    recs = [_record(35, fps, 1.0, "toy:S1", label=0),
            _record(50, fps, 2.0, "toy:S2", label=1),
            _record(12, fps, 3.0, "toy:S3", label=0),   # shorter than w
            _record(20, fps, 4.0, "toy:S4", label=1)]   # exactly w
    par = FixedIntervalWindows(duration_s=2.0, stride_s=1.0)
    X, y, groups = par.get_data(recs)
    # 35 -> (35-20)//10+1 = 2; 50 -> 4; 12 -> 0; 20 -> 1
    assert len(X) == 2 + 4 + 0 + 1
    for win, g in zip(X, groups):
        vals = np.unique(win)
        assert len(vals) == 1, "a window mixed samples from two records"
        assert g == {1.0: "toy:S1", 2.0: "toy:S2", 4.0: "toy:S4"}[vals[0]]
    assert list(groups) == ["toy:S1"] * 2 + ["toy:S2"] * 4 + ["toy:S4"]
    assert list(y) == [0] * 2 + [1] * 4 + [1]
    assert "toy:S3" not in set(groups)


def test_windows_are_contiguous_slices():
    fps = 10.0
    rec = _record(60, fps, 0.0, "toy:S1")
    rec["signal"] = np.arange(60 * 3, dtype=np.float32).reshape(60, 3)
    par = FixedIntervalWindows(duration_s=2.0, stride_s=1.0)
    X, _, _ = par.get_data([rec])
    assert len(X) == 5
    for k, win in enumerate(X):
        start = k * 10
        np.testing.assert_array_equal(win, rec["signal"][start:start + 20])


def test_native_rates_differ_across_records():
    par = FixedIntervalWindows(duration_s=1.0)
    recs = [_record(100, 100.0, 1.0, "toy:S1"),
            _record(100, 50.0, 2.0, "toy:S2")]
    X, _, groups = par.get_data(recs)
    assert [w.shape[0] for w in X] == [100, 50, 50]
    assert list(groups) == ["toy:S1", "toy:S2", "toy:S2"]


def test_imu_and_pose_records_are_flattened():
    par = FixedIntervalWindows(duration_s=1.0)
    X_imu, _, _ = par.get_data([_record(30, 10.0, 1.0, "toy:S1", kind="imu")])
    assert len(X_imu) == 3 and X_imu[0].shape == (10, 18)
    X_pose, _, _ = par.get_data([_record(30, 10.0, 1.0, "toy:S1", kind="pose")])
    assert len(X_pose) == 3 and X_pose[0].shape == (10, 45)


def test_task_prefix_labels_strip_trial_suffix():
    par = FixedIntervalWindows(duration_s=1.0, label_from="task_prefix")
    recs = [_record(20, 10.0, 1.0, "toy:S1", task="slope_ascent_trial05"),
            _record(20, 10.0, 1.0, "toy:S2", task="level_walk")]
    for r in recs:
        del r["label"]
    _, y, _ = par.get_data(recs)
    assert list(y) == ["slope_ascent", "slope_ascent", "level_walk",
                       "level_walk"]


def test_record_label_required_when_label_from_record():
    rec = _record(20, 10.0, 1.0, "toy:S1")
    del rec["label"]
    with pytest.raises(ValueError, match="no eval label"):
        FixedIntervalWindows(duration_s=1.0).get_data([rec])


def test_record_without_signal_or_coords_raises():
    with pytest.raises(ValueError, match="neither 'signal' nor 'coords'"):
        FixedIntervalWindows().get_data([{"fps": 10.0, "subject_ns": "x",
                                          "label": 0}])


def test_invalid_label_source_rejected():
    with pytest.raises(ValueError):
        FixedIntervalWindows(label_from="guess")
