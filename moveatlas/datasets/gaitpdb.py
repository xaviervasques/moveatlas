# -*- coding: utf-8 -*-
"""PhysioNet gaitpdb adapter (gait in Parkinson, VGRF insoles).

Vertical ground-reaction forces from 8 insole sensors + the per-foot
total at 100 Hz, three studies pooled by PhysioNet (Ga/Ju/Si prefixes).
The cohort is encoded in the subject id by the SOURCE itself: 'Co' =
control, 'Pt' = Parkinson patient; the adapter exposes it as an
eval-only 'group' the honest way (read from the id, documented, never
guessed from the signal).
"""
from moveatlas.datasets.base import BaseDataset, load_pickle


def cohort_of(subject_ns):
    """'gaitpdb:GaPt07' -> 'parkinson'; 'gaitpdb:SiCo12' -> 'control'."""
    sid = subject_ns.split(":", 1)[-1]
    if "Pt" in sid:
        return "parkinson"
    if "Co" in sid:
        return "control"
    return "unknown"


class PhysionetGaitpdb(BaseDataset):
    code = "physionet_gaitpdb"
    modalities = ("force",)

    def _load(self, store, subjects, modality):
        recs = load_pickle(store.path(
            "datasets/imu/physionet_gaitpdb/processed/canonical_force.pkl"))
        records, rows = [], []
        for r in recs:
            if subjects and r["subject_ns"] not in subjects:
                continue
            records.append(r)
            rows.append([self.code, r["subject_ns"], r["task"], "force",
                         r["n_frames"], r["fps"]])
        return records, rows
