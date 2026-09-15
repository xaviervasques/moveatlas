# -*- coding: utf-8 -*-
"""Statistical feature baselines (the LogVariance+LDA tradition MOABB's
2024 study showed is still a hard floor to beat).

scikit-learn is an optional dependency (the ``bench`` extra). The module
imports without it: ``StatFeatures`` falls back to plain-object bases and
``baseline_pipelines()`` raises an informative ImportError.
"""
import numpy as np

_SKLEARN_HINT = "install scikit-learn: pip install 'moveatlas[bench]'"


def _estimator_bases():
    """sklearn's estimator mixins when available, else plain bases so the
    class statement below still executes."""
    try:
        from sklearn.base import BaseEstimator, TransformerMixin
    except ImportError:
        return (object,)
    return (BaseEstimator, TransformerMixin)


class StatFeatures(*_estimator_bases()):
    """Per-channel summary statistics over each window: log-variance,
    RMS, mean absolute delta (a crude velocity), range. NaN-safe: the
    pose contract encodes missing joints as zeros with masks, and IMU
    dropouts as zeros, so plain stats stay finite."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        out = []
        for w in X:
            w = np.asarray(w, np.float32)
            var = np.log(np.var(w, axis=0) + 1e-12)
            rms = np.sqrt(np.mean(w * w, axis=0) + 1e-12)
            vel = np.mean(np.abs(np.diff(w, axis=0)), axis=0)
            rng = np.max(w, axis=0) - np.min(w, axis=0)
            out.append(np.concatenate([var, rms, vel, rng]))
        return np.asarray(out, np.float32)


def baseline_pipelines():
    """The v0 pipeline set: a chance reference and two classic floors."""
    try:
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.dummy import DummyClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as e:
        raise ImportError(_SKLEARN_HINT) from e
    return {
        "chance (majority)": Pipeline([
            ("dummy", DummyClassifier(strategy="most_frequent"))]),
        "StatFeatures + LDA": Pipeline([
            ("feat", StatFeatures()), ("scale", StandardScaler()),
            ("clf", LinearDiscriminantAnalysis())]),
        "StatFeatures + LogReg": Pipeline([
            ("feat", StatFeatures()), ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000))]),
    }
