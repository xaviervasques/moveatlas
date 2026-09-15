# -*- coding: utf-8 -*-
"""CrossPatientEvaluation: the first concrete evaluation.

Folds are patient-level (a subject never straddles a split); the score is
balanced accuracy, robust to the class imbalance most clinical datasets
carry (e.g. 50 stroke vs 138 able-bodied). Per-fold scores are returned
so the analysis layer can meta-analyze; nothing is pooled across
datasets here by design.

scikit-learn is an optional dependency (the ``bench`` extra): it is
imported when ``evaluate`` runs, not when the module loads.
"""
import numpy as np
import pandas as pd

_SKLEARN_HINT = "install scikit-learn: pip install 'moveatlas[bench]'"


def _sklearn():
    try:
        from sklearn.base import clone
        from sklearn.metrics import balanced_accuracy_score
    except ImportError as e:
        raise ImportError(_SKLEARN_HINT) from e
    return clone, balanced_accuracy_score


class CrossPatientEvaluation:
    def __init__(self, n_splits=5, seed=0):
        self.n_splits = n_splits
        self.seed = seed

    def evaluate(self, paradigm, dataset, pipelines, subjects=None,
                 modality=None):
        clone, balanced_accuracy_score = _sklearn()
        records, _ = dataset.get_data(subjects=subjects, modality=modality)
        X, y, groups = paradigm.get_data(records)
        rows = []
        uniq = np.unique(groups)
        rng = np.random.default_rng(self.seed)
        order = rng.permutation(uniq)
        folds = np.array_split(order, self.n_splits)
        idx = np.arange(len(y))
        for k, fold_subjects in enumerate(folds):
            test = np.isin(groups, fold_subjects)
            tr, te = idx[~test], idx[test]
            if len(np.unique(y[tr])) < 2 or len(te) == 0:
                continue
            for name, pipe in pipelines.items():
                model = clone(pipe)
                model.fit([X[i] for i in tr], y[tr])
                pred = model.predict([X[i] for i in te])
                rows.append({
                    "dataset": dataset.code, "evaluation": "CrossPatient",
                    "fold": k, "pipeline": name,
                    "score": balanced_accuracy_score(y[te], pred),
                    "n_train_subj": len(uniq) - len(fold_subjects),
                    "n_test_subj": len(fold_subjects),
                    "n_windows": len(te)})
        return pd.DataFrame(rows)
