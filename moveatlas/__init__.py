# -*- coding: utf-8 -*-
"""MoveAtlas: the open atlas of movement data, human and animal.

One API over the movement-disorders corpus. Design credit: MOABB
(moabb.neurotechx.com), whose Dataset/Paradigm/Evaluation decomposition
this package transposes to movement data (docs/MoveAtlas_PLATFORM_DESIGN.md).

    import moveatlas
    moveatlas.list_datasets()                        # the catalogue
    recs, meta = moveatlas.dataset("modys_video").get_data()   # hosted
    moveatlas.fetch("fog_turning_filho")             # recipe: origin download
    moveatlas.ingest("fog_turning_filho")            # recipe: harmonize
    moveatlas.recipe("ninapro")                      # what a recipe needs
"""
from moveatlas.registry import list_datasets, dataset_info
from moveatlas.datasets import dataset
from moveatlas.frames import to_frame
from moveatlas.recipes import fetch, ingest, recipe, store_root
from moveatlas import viz

__version__ = "0.1.0.dev0"
__all__ = ["list_datasets", "dataset_info", "dataset", "to_frame",
           "fetch", "ingest", "recipe", "store_root", "viz", "__version__"]
