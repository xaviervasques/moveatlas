# -*- coding: utf-8 -*-
"""Base dataset classes: identity, access-case enforcement, data access.

A MoveAtlas dataset is ONE identity (one code, one card, one DOI, one
download) however many modality streams it carries. get_data() returns
(records, metadata): records are dicts in the canonical contract of their
family (configs/canonical_*.yaml); metadata is a pandas DataFrame with at
least [dataset, subject_ns, task, modality, n_frames, fps], the contract
with the evaluation layer.
"""
import os
import re

import pandas as pd

from moveatlas import records
from moveatlas.datasets import generic
from moveatlas.registry import dataset_info
from moveatlas.store import open_store


class AccessError(RuntimeError):
    """Raised when a dataset's access case forbids automated download."""


class BaseDataset:
    """Subclasses set `code` and implement `_load(store, subjects,
    modality)` returning (records, metadata_rows)."""

    code = None
    modalities = ()

    def __init__(self):
        self.info = dataset_info(self.code)
        self.access_case = self.info["access_case"]

    # -- identity ----------------------------------------------------
    @property
    def title(self):
        return self.info["title"]

    @property
    def license(self):
        return self.info["license"]

    @property
    def taxonomy_cells(self):
        return [c.strip() for c in self.info["moveatlas_cells"].split(";")]

    def __repr__(self):
        return (f"<{type(self).__name__} '{self.code}' "
                f"[{self.access_case}] {self.title!r}>")

    # -- the dataset's files, canonical or not ---------------------------
    def files(self):
        """Store-relative paths of every file this dataset holds: what is
        on this machine under its registry path, plus, for a hosted
        dataset, what its published record lists (nothing is downloaded
        to list). Many hosted records hold tables, archives or documents
        rather than canonical records; this is how you see them."""
        if self.access_case in ("barrier", "local_only", "tool"):
            return []
        store = open_store()
        base = self.info["path"].replace("\\", "/").rstrip("/")
        out, stack = [], [base]
        while stack:
            d = stack.pop()
            try:
                children = store.list_dir(d)
            except FileNotFoundError:
                children = []
            for c in children:
                if c.endswith("/"):
                    stack.append(c.rstrip("/"))
                elif not os.path.basename(c).startswith("._"):
                    out.append(c)
        return sorted(set(out))

    def path(self, name):
        """A local path to one of the dataset's files, by file name or
        store-relative path: served from this machine when it is there,
        else downloaded from the published record and sha256-verified.
        Read a table with pandas, an archive with zipfile, an .npz
        container with moveatlas.records.load()."""
        name = name.replace("\\", "/")
        files = self.files()
        hits = [f for f in files if f == name or f.endswith("/" + name)]
        if not hits:
            known = ", ".join(os.path.basename(f) for f in files[:12])
            raise FileNotFoundError(
                f"'{self.code}' has no file named {name!r}; it holds: "
                f"{known or 'nothing on this machine or in a record'}")
        if len(hits) > 1:
            raise ValueError(f"{name!r} is ambiguous in '{self.code}': "
                             f"{hits}; give the store-relative path")
        return open_store().path(hits[0])

    # -- data --------------------------------------------------------
    def get_data(self, subjects=None, modality=None):
        """Return (records, metadata). `subjects` filters on subject_ns;
        `modality` filters multimodal datasets to one stream."""
        known = self.modalities
        if modality is not None and known and modality not in known:
            raise ValueError(f"{self.code} carries {known}, "
                             f"not '{modality}'")
        store = open_store()
        records, rows = self._load(store, subjects, modality)
        meta = pd.DataFrame(rows, columns=["dataset", "subject_ns", "task",
                                           "modality", "n_frames", "fps"])
        return records, meta

    def _load(self, store, subjects, modality):
        raise NotImplementedError


_RECIPE = re.compile(r"[\w\-]+\.py(?: --[\w\-]+(?: [\w\-]+)?)*")


def recipe_of(info):
    """The ingestion script the registry row names (access, then status),
    with its flags when they follow it; a pointer to the card otherwise."""
    for field in ("access", "status"):
        m = _RECIPE.search(info.get(field) or "")
        if m:
            return m.group(0)
    return f"the ingestion recipe named in {info['path']}/datacard.md"


class GenericDataset(BaseDataset):
    """Registry-backed adapter for every catalogued id without a dedicated
    class. Hosted and recipe ids load from whatever their ingestion left
    under <path>/processed/ (moveatlas.datasets.generic); asking a barrier
    id for bytes raises the documented route instead of pretending, and a
    recipe id nothing ingested says which script to run."""

    def __init__(self, code):
        self.code = code
        self._modalities = None
        super().__init__()

    @property
    def modalities(self):
        """The modalities found on disk (or in the published record),
        computed once; () for barrier / local_only ids and when nothing
        is ingested."""
        if self._modalities is None:
            if self.access_case in ("barrier", "local_only", "tool"):
                self._modalities = ()
            else:
                try:
                    self._modalities = generic.modalities_on_disk(
                        open_store(), self.info["path"])
                except FileNotFoundError:
                    self._modalities = ()
        return self._modalities

    def _not_ingested(self, reason=""):
        i = self.info
        recipe = recipe_of(i)
        card = f"{i['path']}/datacard.md"
        if self.access_case == "recipe":
            return FileNotFoundError(
                f"'{self.code}' is not ingested on this machine: run "
                f"{recipe}. Access: {i['access']}. Status: {i['status']}. "
                f"Card: {card}")
        # hosted, but the record holds no canonical container. Nineteen
        # of the 53 published records are like that (tables, archives,
        # documents, a non-canonical .npz): say what is there and how to
        # read it, instead of sending a stranger to an ingestion script
        # (finding of 2026-09-15, LAUNCH_PLAN 1.1)
        try:
            names = [os.path.basename(f) for f in self.files()
                     if not f.endswith("downloads.sha256")]
        except Exception:      # listing must never mask the real message
            names = []
        if names:
            shown = ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")
            return FileNotFoundError(
                f"'{self.code}' holds files, not canonical records: {shown}. "
                f"ds.path('<name>') returns a local, verified path to one "
                f"(downloaded from the record when needed); read a table with "
                f"pandas, an archive with zipfile, an .npz container with "
                f"moveatlas.records.load(). Card: {card}")
        return FileNotFoundError(
            f"'{self.code}' is hosted but no canonical container is under "
            f"{i['path']}/processed/ in this store{reason}. If this machine "
            f"never ingested it, run {recipe}. Card: {card}")

    def _load(self, store, subjects, modality):
        i = self.info
        if self.access_case == "barrier":
            raise AccessError(
                f"'{self.code}' is a documented access barrier, not a "
                f"download. Route on record: {i['access']}. Status: "
                f"{i['status']}. Card: {i['path']}/datacard.md")
        if self.access_case == "tool":
            raise AccessError(
                f"'{self.code}' is software catalogued for reference, not a "
                f"dataset: nothing downloads. Code: {i['link']}. "
                f"Card: {i['path']}/datacard.md")
        if self.access_case == "local_only":
            raise AccessError(
                f"'{self.code}' is private-tier data; point a dedicated "
                "adapter at a local copy (LocalStore path), nothing "
                "downloads")
        try:
            found = generic.discover(store, i["path"])
        except FileNotFoundError as e:
            raise self._not_ingested(f" ({e})") from e
        if not found:
            raise self._not_ingested()
        return generic.load(store, self.code, i["path"], subjects, modality,
                            found=found)


def load_record(path):
    """Read a record container: the moveatlas-record/1 .npz natively; a
    legacy .pkl through the transition reader (DeprecationWarning). The
    .npz sibling of a .pkl path wins when it exists."""
    return records.load_any(path)


# kept for the adapters written before the format migration
load_pickle = load_record
