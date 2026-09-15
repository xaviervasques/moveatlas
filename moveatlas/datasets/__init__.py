# -*- coding: utf-8 -*-
"""Dataset adapters. One module per dataset; `dataset(code)` is the factory.

Dedicated adapters: nonan_gaitprint (hosted, CC BY), nonan_gaitprint_young
(hosted, CC0), gait120 (hosted, CC BY, multimodal: EMG stream implemented),
cody_3 (the program's own cohort), stroke_gait_vancriekinge and
physionet_gaitpdb. Every other catalogued id resolves to GenericDataset,
which loads whatever its ingestion left under <path>/processed/ through
the manifest-free loader (moveatlas.datasets.generic) and enforces the
access case honestly (a barrier id raises with its documented route, a
recipe id nothing ingested names the script to run).
"""
from moveatlas.datasets.base import BaseDataset, GenericDataset
from moveatlas.datasets.nonan_gaitprint import NonanGaitprint, NonanGaitprintYoung
from moveatlas.datasets.gait120 import Gait120
from moveatlas.datasets.cody import Cody
from moveatlas.datasets.stroke_gait import StrokeGaitVanCriekinge
from moveatlas.datasets.gaitpdb import PhysionetGaitpdb

_ADAPTERS = {
    "nonan_gaitprint": NonanGaitprint,
    "nonan_gaitprint_young": NonanGaitprintYoung,
    "gait120": Gait120,
    "cody_3": Cody,
    "stroke_gait_vancriekinge": StrokeGaitVanCriekinge,
    "physionet_gaitpdb": PhysionetGaitpdb,
}


def dataset(code):
    """Factory: the dedicated adapter when one exists, else the generic
    registry-backed adapter for the catalogued id."""
    cls = _ADAPTERS.get(code)
    return cls() if cls else GenericDataset(code)


__all__ = ["dataset", "BaseDataset", "GenericDataset", "NonanGaitprint",
           "NonanGaitprintYoung", "Gait120", "Cody",
           "StrokeGaitVanCriekinge", "PhysionetGaitpdb"]
