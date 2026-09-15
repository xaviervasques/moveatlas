# -*- coding: utf-8 -*-
"""Public surface of the package and its version pin."""
import os
import re

import pytest

import moveatlas

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYPROJECT = os.path.join(ROOT, "pyproject.toml")


def _pyproject_version():
    try:
        import tomllib                         # Python 3.11+
    except ImportError:                        # 3.9 / 3.10 fallback
        try:
            import tomli as tomllib
        except ImportError:
            tomllib = None
    if tomllib is not None:
        with open(PYPROJECT, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    with open(PYPROJECT, encoding="utf-8") as f:
        text = f.read()
    project = text.split("[project]", 1)[1].split("\n[", 1)[0]
    m = re.search(r'^version\s*=\s*"([^"]+)"', project, re.M)
    assert m, "no version in [project]"
    return m.group(1)


def test_public_names_exposed():
    for name in ("__version__", "list_datasets", "dataset_info", "dataset",
                 "to_frame", "viz"):
        assert hasattr(moveatlas, name), name
        assert name in moveatlas.__all__
    assert callable(moveatlas.list_datasets)
    assert callable(moveatlas.dataset)
    assert callable(moveatlas.to_frame)


def test_version_matches_pyproject():
    assert isinstance(moveatlas.__version__, str)
    assert moveatlas.__version__ == _pyproject_version()


def test_version_is_pep440_like():
    assert re.match(r"^\d+\.\d+\.\d+([a-z]+\d+|\.dev\d+)?$",
                    moveatlas.__version__), moveatlas.__version__


def test_generic_dataset_resolves_from_registry():
    rows = moveatlas.list_datasets()
    ds = moveatlas.dataset(rows[0]["id"])
    assert ds.code == rows[0]["id"]
    assert ds.access_case == rows[0]["access_case"]
    assert ds.title == rows[0]["title"]
    assert rows[0]["id"] in repr(ds)


def test_barrier_dataset_refuses_bytes_without_network(tmp_path,
                                                        monkeypatch):
    from moveatlas.datasets.base import AccessError
    monkeypatch.setenv("MOVEATLAS_CACHE", str(tmp_path / "cache"))
    barrier = moveatlas.list_datasets(case="barrier")
    if not barrier:
        pytest.skip("registry carries no barrier-tier id")
    ds = moveatlas.dataset(barrier[0]["id"])
    with pytest.raises(AccessError, match="documented access barrier"):
        ds.get_data()


def test_unknown_dataset_id_raises_with_known_ids():
    with pytest.raises(KeyError, match="unknown dataset"):
        moveatlas.dataset("no_such_dataset_xyz")
