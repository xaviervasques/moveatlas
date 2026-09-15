# -*- coding: utf-8 -*-
"""Gait120 adapter: the multimodal pilot (one dataset, several streams).

Streams on disk today: EMG (canonical_emg records, 12 named right-leg
muscles at 2000 Hz, stored in mV). The joint-angle .mot and MotionCapture
trees await their own ingestion pass; when they land, this adapter gains
modality 'pose' with NO new dataset identity (one dataset, one card, one
DOI: docs/MoveAtlas_PLATFORM_DESIGN.md section 8).
"""
from moveatlas.datasets.base import BaseDataset, load_pickle


class Gait120(BaseDataset):
    code = "gait120"
    modalities = ("emg",)

    def _load(self, store, subjects, modality):
        # record ids embed the subject; a subjects filter skips whole files
        wanted = None
        if subjects:
            wanted = {s.split(":", 1)[-1] for s in subjects}
        records, rows = [], []
        for p in store.glob_dir("datasets/emg/gait120/processed/canonical_emg"):
            if wanted is not None:
                import os
                stem = os.path.basename(p)
                if not any(f"gait120_{w}__" in stem for w in wanted):
                    continue
            r = load_pickle(p)
            if subjects and r["subject_ns"] not in subjects:
                continue
            records.append(r)
            rows.append([self.code, r["subject_ns"], r["task"], "emg",
                         r["n_frames"], r["fps"]])
        return records, rows
