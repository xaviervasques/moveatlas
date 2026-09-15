# -*- coding: utf-8 -*-
"""Evaluation splits. The house rule is absolute: splits are PATIENT-LEVEL,
a subject never appears on both sides of a split (Handoff rules; the
clinical generalization axes are WithinVisit / CrossVisit / CrossPatient /
CrossDataset, MOABB's Within/CrossSession/CrossSubject transposed)."""
from moveatlas.evaluations.splits import cross_patient_folds
from moveatlas.evaluations.evaluation import CrossPatientEvaluation

__all__ = ["cross_patient_folds", "CrossPatientEvaluation"]
