# -*- coding: utf-8 -*-
"""Van Criekinge stroke gait adapter (50 stroke + 138 able-bodied, CC0).

Full-body Plug-in Gait mocap at native 100 Hz, mapped to the canonical
15-joint skeleton by measured geometry (configs pig_vancriekinge). Every
record carries the eval-only cohort label (1 stroke, 0 able-bodied) and
its group attribute; 737 records / 188 subjects since the 2026-08-28
prefixed-labels recovery.
"""
from moveatlas.datasets.base import BaseDataset, load_pickle


class StrokeGaitVanCriekinge(BaseDataset):
    code = "stroke_gait_vancriekinge"
    modalities = ("pose",)

    def _load(self, store, subjects, modality):
        recs = load_pickle(store.path(
            "datasets/pose/stroke_gait_vancriekinge/processed/canonical.pkl"))
        records, rows = [], []
        for r in recs:
            if subjects and r["subject_ns"] not in subjects:
                continue
            records.append(r)
            rows.append([self.code, r["subject_ns"], r["take"], "pose",
                         r["n_frames"], r["fps"]])
        return records, rows
