# -*- coding: utf-8 -*-
"""The canonical manifests as the gate reads them (LAUNCH_PLAN 1.2).

On 2026-09-08 a Windows session wrote 3,021 EEG and EMG manifest rows
with backslash record paths; validate_canonical.py passed there and
failed on the Mac for three days before anyone saw it (handoff 23 s5).
These tests run wherever the manifests are (the working tree; the
public tree ships none, so they skip there) and refuse a backslash, a
path outside datasets/, or a row without a record path."""
import csv
import glob
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
MANIFESTS = sorted(glob.glob(os.path.join(REPO, "datasets", "_canonical_*_manifest.csv")))


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.skipif(not MANIFESTS, reason="no canonical manifests here (public tree)")
@pytest.mark.parametrize("path", MANIFESTS, ids=[os.path.basename(m) for m in MANIFESTS])
def test_record_paths_are_portable(path):
    rows = _rows(path)
    assert rows, f"{os.path.basename(path)} is empty"
    if "record_path" not in rows[0]:
        pytest.skip("this manifest carries no record_path column")
    bad_sep = [r["record_path"] for r in rows if "\\" in r["record_path"]]
    assert not bad_sep, (f"{len(bad_sep)} backslash record paths in "
                         f"{os.path.basename(path)}; first: {bad_sep[0]}")
    empty = [i for i, r in enumerate(rows, 2) if not r["record_path"].strip()]
    assert not empty, f"rows without a record path: {empty[:5]}"
    outside = [r["record_path"] for r in rows
               if not r["record_path"].startswith("datasets/")]
    assert not outside, f"record paths outside datasets/: {outside[:3]}"
    absolute = [r["record_path"] for r in rows
                if os.path.isabs(r["record_path"]) or ":" in r["record_path"][:3]]
    assert not absolute, f"absolute record paths: {absolute[:3]}"


def test_builders_normalise_record_paths():
    """The three builders that emit record_path must write forward
    slashes explicitly, so a Windows run cannot reintroduce the defect."""
    for name in ("build_canonical_eeg.py", "build_canonical_emg.py",
                 "build_canonical_sensefog.py"):
        p = os.path.join(REPO, name)
        if not os.path.exists(p):
            p = os.path.join(REPO, "tools", "canonical", name)   # the public tree
        if not os.path.exists(p):
            pytest.skip(f"{name} not shipped here")
        src = open(p, encoding="utf-8").read()
        raw = src.count("os.path.relpath(")
        normalised = src.count('.replace("\\\\", "/")')
        assert normalised >= raw, (f"{name}: {raw} relpath() calls, "
                                   f"{normalised} normalised")
