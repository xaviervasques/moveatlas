# -*- coding: utf-8 -*-
"""Patient-level folds: no subject straddles a fold, every record tested
once, deterministic under a seed."""
import numpy as np
import pandas as pd
import pytest

from moveatlas.evaluations.splits import cross_patient_folds

N_SUBJECTS = 40


def _metadata(n_subjects=N_SUBJECTS):
    """Synthetic metadata frame: subject i owns 1 + (i % 3) records, so
    some subjects carry several rows."""
    rows = []
    for i in range(n_subjects):
        for k in range(1 + i % 3):
            rows.append({"dataset": "toy", "subject_ns": f"toy:S{i:03d}",
                         "task": f"walk_trial{k:02d}", "modality": "imu",
                         "n_frames": 100 + k, "fps": 100.0})
    return pd.DataFrame(rows)


@pytest.fixture
def meta():
    return _metadata()


def test_metadata_has_multi_record_subjects(meta):
    counts = meta["subject_ns"].value_counts()
    assert counts.max() > 1
    assert meta["subject_ns"].nunique() == N_SUBJECTS


@pytest.mark.parametrize("n_splits", [2, 5, 7])
def test_no_subject_in_both_train_and_test(meta, n_splits):
    subjects = meta["subject_ns"].to_numpy()
    folds = list(cross_patient_folds(meta, n_splits=n_splits, seed=0))
    assert len(folds) == n_splits
    for train, test in folds:
        assert len(train) and len(test)
        assert not (set(subjects[train]) & set(subjects[test]))
        assert not (set(train) & set(test))


@pytest.mark.parametrize("n_splits", [2, 5, 7])
def test_every_record_tested_exactly_once(meta, n_splits):
    folds = list(cross_patient_folds(meta, n_splits=n_splits, seed=0))
    tested = np.concatenate([test for _, test in folds])
    assert sorted(tested.tolist()) == list(range(len(meta)))
    for train, test in folds:
        assert sorted(np.concatenate([train, test]).tolist()) == \
            list(range(len(meta)))


def test_all_records_of_a_subject_share_a_fold(meta):
    subjects = meta["subject_ns"].to_numpy()
    for _, test in cross_patient_folds(meta, n_splits=5, seed=0):
        for s in set(subjects[test]):
            owned = np.where(subjects == s)[0]
            assert set(owned) <= set(test)


def test_deterministic_for_a_fixed_seed(meta):
    a = [(tr.tolist(), te.tolist())
         for tr, te in cross_patient_folds(meta, n_splits=5, seed=123)]
    b = [(tr.tolist(), te.tolist())
         for tr, te in cross_patient_folds(meta, n_splits=5, seed=123)]
    assert a == b
    c = [(tr.tolist(), te.tolist())
         for tr, te in cross_patient_folds(meta, n_splits=5, seed=124)]
    assert a != c


def test_folds_are_balanced_in_subjects(meta):
    subjects = meta["subject_ns"].to_numpy()
    sizes = [len(set(subjects[test]))
             for _, test in cross_patient_folds(meta, n_splits=5, seed=0)]
    assert sum(sizes) == N_SUBJECTS
    assert max(sizes) - min(sizes) <= 1


def test_index_order_does_not_matter(meta):
    shuffled = meta.sample(frac=1.0, random_state=7).reset_index(drop=True)
    subjects = shuffled["subject_ns"].to_numpy()
    for train, test in cross_patient_folds(shuffled, n_splits=5, seed=0):
        assert not (set(subjects[train]) & set(subjects[test]))


def test_too_few_subjects_raises():
    small = _metadata(3)
    with pytest.raises(ValueError, match="3 subjects cannot fill 5"):
        list(cross_patient_folds(small, n_splits=5, seed=0))


def test_exactly_enough_subjects_is_leave_one_subject_out():
    small = _metadata(5)
    subjects = small["subject_ns"].to_numpy()
    folds = list(cross_patient_folds(small, n_splits=5, seed=0))
    assert len(folds) == 5
    for _, test in folds:
        assert len(set(subjects[test])) == 1
