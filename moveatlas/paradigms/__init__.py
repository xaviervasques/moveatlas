# -*- coding: utf-8 -*-
"""Paradigms: what a valid sample is, independently of any dataset
(MOABB's Paradigm layer transposed; docs/MOVEATLAS_PLATFORM_DESIGN.md
section 2). First concrete paradigm: FixedIntervalWindows. Clinical-task
paradigms (gait, tremor_rest, tapping...) with is_valid(dataset)
compatibility checks follow in P2."""
from moveatlas.paradigms.windows import FixedIntervalWindows

__all__ = ["FixedIntervalWindows"]
