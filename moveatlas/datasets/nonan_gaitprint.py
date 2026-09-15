# -*- coding: utf-8 -*-
"""NONAN GaitPrint adapters: two cohorts, two datasets, one protocol.

Subject IDs collide across the cohorts (S009/S013/S019 exist in both with
different content), which is exactly why they are SEPARATE datasets with
separate namespaces (``nonan_gaitprint:`` vs ``nonan_gaitprint_young:``),
per the 2026-08-28 acquisition decision.

Records: canonical IMU contract (14-location grid), one pkl per subject
holding that subject's trial records, produced by ingest_nonan.py.
"""
import os

from moveatlas.datasets.base import BaseDataset, load_pickle


class _NonanBase(BaseDataset):
    modalities = ("imu",)
    _reldir = None

    def _load(self, store, subjects, modality):
        # per-subject shards let a subjects filter skip whole files: asking
        # for 3 subjects reads 3 pkl, not the cohort's ~25 GB
        wanted = None
        if subjects:
            wanted = {s.split(":", 1)[-1] for s in subjects}
        records, rows = [], []
        for p in store.glob_dir(self._reldir):
            import os
            stem = os.path.basename(p)[:-4]
            if wanted is not None and stem not in wanted:
                continue
            recs = load_pickle(p)
            for r in recs:
                if subjects and r["subject_ns"] not in subjects:
                    continue
                records.append(r)
                rows.append([self.code, r["subject_ns"], r["task"], "imu",
                             r["n_frames"], r["fps"]])
        return records, rows


class NonanGaitprint(_NonanBase):
    """Healthy older adults (41 subjects, 16-IMU Noraxon, 200 Hz)."""
    code = "nonan_gaitprint"
    _reldir = "datasets/imu/nonan_gaitprint/processed/canonical"


class NonanGaitprintYoung(_NonanBase):
    """Healthy young adults (35 subjects, same protocol, CC0)."""
    code = "nonan_gaitprint_young"
    _reldir = "datasets/imu/nonan_gaitprint_young/processed/canonical"
