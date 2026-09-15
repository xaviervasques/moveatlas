# -*- coding: utf-8 -*-
"""Shared fixtures. The suite never touches the corpus under datasets/ nor
the network: every file it needs is written under tmp_path."""
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:                     # run from a bare git archive
    sys.path.insert(0, _ROOT)


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point the remote-store cache at tmp_path so no test writes to
    ~/.moveatlas."""
    cache = tmp_path / "cache"
    monkeypatch.setenv("MOVEATLAS_CACHE", str(cache))
    return cache
