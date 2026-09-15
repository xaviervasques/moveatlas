# -*- coding: utf-8 -*-
"""Baseline pipelines: sklearn estimators over windowed canonical data.

Featurizers turn variable-length (T, C) windows into fixed vectors; the
classifier is any sklearn estimator. Deep pipelines and foundation-model
embeddings enter later through the same interface.
"""
from moveatlas.pipelines.features import StatFeatures, baseline_pipelines

__all__ = ["StatFeatures", "baseline_pipelines"]
