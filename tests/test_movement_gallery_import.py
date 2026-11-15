# -*- coding: utf-8 -*-
"""site/gen_movement_gallery.py's refusals: the gallery it brings into the site is a public export of generated clips
only, under an open licence (CC BY 4.0 since the gallery was rebuilt on the open Anny body model), whose page matches
its manifest."""
import hashlib
import importlib.util
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


@pytest.fixture(scope="module")
def gmg():
    spec = importlib.util.spec_from_file_location("gen_movement_gallery",
                                                  os.path.join(REPO, "site", "gen_movement_gallery.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gallery(tmp_path, gmg, **over):
    page = b"<!doctype html><title>SYNTHETIC Movement gallery</title>"
    (tmp_path / gmg.PAGE).write_bytes(page)
    man = {"public": True, "clips": ["a0", "a1"], "provenance": {"a0": "generated", "a1": "generated"},
           "licence": "CC BY 4.0 (Creative Commons Attribution 4.0 International)",
           "page_sha256": hashlib.sha256(page).hexdigest()}
    man.update(over)
    (tmp_path / gmg.MANIFEST).write_text(json.dumps(man), encoding="utf-8")
    return str(tmp_path)


def test_an_open_generated_gallery_passes(gmg, tmp_path):
    assert gmg.check(_gallery(tmp_path, gmg))["clips"] == ["a0", "a1"]


@pytest.mark.parametrize("over", [
    {"public": False},
    {"provenance": {"a0": "generated"}},
    {"provenance": {"a0": "generated", "a1": "motion_capture"}},
    {"licence": "CC BY-NC 4.0 (Creative Commons Attribution-NonCommercial 4.0)"},
    {"licence": "CC BY 4.0 NC for the motion data"},
    {"licence": "LICENCE TO BE CHOSEN"},
    {"page_sha256": "0" * 64},
])
def test_the_refusals(gmg, tmp_path, over):
    with pytest.raises(SystemExit):
        gmg.check(_gallery(tmp_path, gmg, **over))
