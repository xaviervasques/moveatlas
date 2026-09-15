# -*- coding: utf-8 -*-
"""CODY adapter: the program's own hyperkinetic cohort (hosted tier).

Raw patient video NEVER leaves the machine (owner mandate,
docs/PRIVACY_GATE.md); what this adapter reads is the canonical 2D-pose
derivative already ingested from cody_3, the canonical source for the
adult labeled cohort. Labels ride on the records and are EVAL-ONLY
(standing rule R1: never pretraining).

The publishable derived data is PUBLIC since 2026-09-01: the CODY Zenodo
deposit (concept DOI 10.5281/zenodo.22232609, CC BY 4.0), fetched and
md5-verified by fetch_cody_zenodo.py at the repo root. That flipped the
cody ids from local_only to hosted. This class stays the local,
full-cohort canonical view; a machine without the local records fetches
the deposit and runs the ingestion recipe.
"""
from moveatlas.datasets.base import BaseDataset, load_pickle


class Cody(BaseDataset):
    code = "cody_3"
    modalities = ("pose",)

    def _load(self, store, subjects, modality):
        recs = load_pickle(
            store.path("datasets/pose/cody_3/processed/canonical.pkl"))
        records, rows = [], []
        for r in recs:
            if subjects and r["subject_ns"] not in subjects:
                continue
            records.append(r)
            rows.append([self.code, r["subject_ns"], r["take"], "pose",
                         r["n_frames"], r["fps"]])
        return records, rows
