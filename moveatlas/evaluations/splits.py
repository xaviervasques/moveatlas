# -*- coding: utf-8 -*-
"""Patient-level split primitives (pure numpy, no sklearn dependency)."""
import numpy as np


def cross_patient_folds(metadata, n_splits=5, seed=0):
    """Yield (train_idx, test_idx) over metadata rows, grouped by
    subject_ns so no subject straddles a fold. Deterministic under `seed`.
    """
    subjects = metadata["subject_ns"].to_numpy()
    uniq = np.unique(subjects)
    if len(uniq) < n_splits:
        raise ValueError(f"{len(uniq)} subjects cannot fill {n_splits} "
                         "patient-level folds")
    rng = np.random.default_rng(seed)
    order = rng.permutation(uniq)
    folds = np.array_split(order, n_splits)
    idx = np.arange(len(subjects))
    for f in folds:
        test = np.isin(subjects, f)
        yield idx[~test], idx[test]
