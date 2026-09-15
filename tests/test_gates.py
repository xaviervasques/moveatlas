# -*- coding: utf-8 -*-
"""The project's guarantees, tested as guarantees.

Two of them silently did not hold until 2026-09-09:

- the release lint exited 0 on a directory that did not exist, so a typo
  in the path looked exactly like a clean release;
- the remote store skipped sha256 verification when a manifest cell was
  empty, so a record with a lost digest served arbitrary downloaded bytes
  as if they had been checked.

A gate that cannot fail is not a gate, so both failure modes are pinned
here. These tests need no corpus and no network.
"""
import io
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The pipeline scripts sit at the root of the working tree and under
# tools/<group>/ in the generated public tree, so a test that hard-codes
# the root passes here and fails there. It did: five of these failed
# inside the built tree while the handoff recorded the whole suite as
# passing in it, because the claim had been asserted and not run.
TOOL_DIRS = ["", "tools/release", "tools/registry", "tools/canonical",
             "tools/fetch", "tools/ingest"]


def tool(name):
    """The path to a pipeline script, wherever this tree keeps it."""
    for d in TOOL_DIRS:
        p = os.path.join(REPO, d, name) if d else os.path.join(REPO, name)
        if os.path.exists(p):
            return p
    raise AssertionError(
        f"{name} is in neither the root nor tools/ of {REPO}; if it was "
        "renamed or dropped, this test must be updated with it rather "
        "than quietly skipped")


def importable(name):
    """Put the directory holding a pipeline script on sys.path."""
    d = os.path.dirname(tool(name))
    if d not in sys.path:
        sys.path.insert(0, d)


# ------------------------------------------------------------ release lint
def run_lint(path):
    return subprocess.run(
        [sys.executable, os.path.join(REPO, "release_lint.py"), str(path)],
        capture_output=True, text=True, cwd=REPO)


def test_release_lint_fails_on_a_missing_directory(tmp_path):
    r = run_lint(tmp_path / "does-not-exist")
    assert r.returncode != 0, "a missing release tree must not pass the gate"
    assert "No such release directory" in r.stdout


def test_release_lint_fails_on_an_empty_directory(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    r = run_lint(empty)
    assert r.returncode != 0, "an empty release tree must not pass the gate"
    assert "nothing to certify" in r.stdout


# -------------------------------------------------------------- the store
def make_remote(tmp_path, sha, payload=b"hello"):
    """A RemoteStore whose single manifest row carries `sha`, wired to a
    fetch that writes `payload`. No network."""
    from moveatlas import store as store_mod
    rel = "datasets/imu/demo/processed/canonical_imu.npz"
    s = store_mod.RemoteStore(cache=str(tmp_path / "cache"),
                              table={"demo": {"record": "1", "doi": "d"}})
    s._manifest["demo"] = {rel: {"path": rel, "bytes": str(len(payload)),
                                 "sha256": sha, "record_name": "flat.npz"}}

    def fake_fetch(did, key, dest, size=None):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(payload)
        return dest

    s._fetch_record_file = fake_fetch
    return s, rel


def test_store_refuses_a_manifest_row_with_no_sha256(tmp_path):
    s, rel = make_remote(tmp_path, sha="")
    with pytest.raises(IOError, match="no sha256"):
        s.path(rel)


def test_store_removes_the_file_it_refused(tmp_path):
    s, rel = make_remote(tmp_path, sha="")
    dest = os.path.join(s.cache, *rel.split("/"))
    with pytest.raises(IOError):
        s.path(rel)
    assert not os.path.exists(dest), "unverified bytes must not stay cached"


def test_store_still_refuses_a_wrong_digest(tmp_path):
    s, rel = make_remote(tmp_path, sha="0" * 64)
    with pytest.raises(IOError, match="sha256 mismatch"):
        s.path(rel)


def test_store_accepts_a_matching_digest(tmp_path):
    import hashlib
    payload = b"hello"
    good = hashlib.sha256(payload).hexdigest()
    s, rel = make_remote(tmp_path, sha=good, payload=payload)
    p = s.path(rel)
    assert os.path.exists(p)
    with open(p, "rb") as f:
        assert f.read() == payload


# ------------------------------------------- the staging redistribution bar
def test_staging_refuses_a_forbidden_licence():
    """build_zenodo_staging re-states the redistribution condition instead
    of trusting the access-case classifier, because a deposit cannot be
    withdrawn once published."""
    src = io.open(tool("build_zenodo_staging.py"), encoding="utf-8").read()
    assert "REFUSED to stage" in src
    assert 'redist.startswith("yes")' in src


def test_staging_refuses_pickles_by_content():
    """A source can ship a pickle under any name: two protocol-4 pickles
    named by bare OSF ids reached a draft before this rule existed."""
    importable("build_zenodo_staging.py")
    from build_zenodo_staging import is_pickle
    import pickle
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "no_extension_at_all")
        with open(p, "wb") as f:
            pickle.dump({"a": 1}, f, protocol=4)
        assert is_pickle(p)
        q = os.path.join(d, "plain.csv")
        with open(q, "wb") as f:
            f.write(b"a,b\n1,2\n")
        assert not is_pickle(q)


def test_staging_withholds_media_pending_a_decision():
    src = io.open(tool("build_zenodo_staging.py"), encoding="utf-8").read()
    assert "MEDIA_EXT" in src and "include_media.txt" in src


# --------------------------------------------------- what a record publishes
def test_licence_sentence_keeps_the_version_and_drops_the_trail():
    """The registry licence column is an evidence trail written for us.
    A record publishes the licence, not the adjudication; and a version
    number must survive, which a naive split at the first period does
    not ("CC BY 4.0" became "CC BY 4" on 18 records)."""
    importable("build_zenodo_staging.py")
    from build_zenodo_staging import licence_sentence as ls
    assert ls("CC BY 4.0. DISCREPANCY RESOLVED 2026-08-23 and it was "
              "ours: the CC BY-NC-ND belongs to the ARTICLE") == "CC BY 4.0"
    assert ls("CC0 1.0 (Dryad, re-verified at fetch)") == "CC0 1.0"
    assert ls("etalab 2.0 (VERIFIED at fetch 2026-09-05)") == "etalab 2.0"
    assert ls("ODC-By 1.0; see the deposit") == "ODC-By 1.0"
    assert ls("MIT (LICENSE file in the repo, read 2026-08-28)") == "MIT"
    assert ls("") == "see the source record"
    for bad in ("DISCREPANCY", "SETTLED", "verified", "owner"):
        assert bad not in ls("CC BY 4.0. SETTLED 2026-08-25 by the owner "
                             "after a verified read")


def test_licence_ids_are_the_checked_vocabulary_spellings():
    """Every id this table emits was resolved against Zenodo's licence
    vocabulary on 2026-09-09. cc-zero and odc-by are the legacy
    deposition spellings and answer 404 there."""
    importable("build_zenodo_staging.py")
    from build_zenodo_staging import LICENSE_IDS, license_id
    emitted = {lid for _, lid in LICENSE_IDS if lid}
    assert "cc-zero" not in emitted and "odc-by" not in emitted
    assert license_id("CC0 (Dryad)") == "cc0-1.0"
    assert license_id("ODC-By 1.0") == "odc-by-1.0"
    # an open source with no formal instrument is not relabelled
    assert license_id("PhysioNet open") == "other-open"
    assert license_id("UCI open") == "other-open"
    # and a licence that forbids redistribution maps to nothing
    assert license_id("CC BY-NC-ND 4.0, SETTLED 2026-08-25") is None
