# -*- coding: utf-8 -*-
"""The registry snapshot bundled with the package must be the registry
(LAUNCH_PLAN 1.7, handoff 23 s9: the copy under moveatlas/data/ lagged
docs/ by three days and shipped six phrases the cleaned registry no longer
had; the leak scan looked at the two files with different eyes). When this
tree carries docs/ (the working tree, the public tree), the two must be
byte-identical; a pip-installed package has no docs/ and skips."""
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
DOCS = os.path.join(REPO, "docs")
DATA = os.path.join(REPO, "moveatlas", "data")


@pytest.mark.parametrize("name", ["datasets_index.csv", "license_matrix.csv"])
def test_bundled_snapshot_equals_docs(name):
    src = os.path.join(DOCS, name)
    if not os.path.exists(src):
        pytest.skip("no docs/ here: an installed package")
    dst = os.path.join(DATA, name)
    assert os.path.exists(dst), f"{name} is not bundled"
    # compared as CSV, not as bytes: the public tree rewrites docs/ through
    # a DictWriter (quoting one field differently) and byte-copies the
    # snapshot; the rows are what must agree
    import csv
    with open(src, newline="", encoding="utf-8") as f:
        a = list(csv.DictReader(f))
    with open(dst, newline="", encoding="utf-8") as f:
        b = list(csv.DictReader(f))
    assert a == b, (f"moveatlas/data/{name} differs from docs/{name} "
                    f"({len(a)} vs {len(b)} rows): refresh the snapshot "
                    "(build_public_release copies it; so does "
                    "`cp docs/... moveatlas/data/`) and bump SNAPSHOT.json")


def test_snapshot_json_counts_match_the_files():
    import csv
    import json
    p = os.path.join(DATA, "SNAPSHOT.json")
    if not os.path.exists(p):
        pytest.skip("no SNAPSHOT.json")
    snap = json.load(open(p, encoding="utf-8"))
    rows = list(csv.DictReader(open(os.path.join(DATA, "datasets_index.csv"),
                                    encoding="utf-8", newline="")))
    assert snap.get("datasets_index_rows") == len(rows)
