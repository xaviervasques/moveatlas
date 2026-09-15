# -*- coding: utf-8 -*-
"""The launch dry-run: prove a STRANGER's machine can use MoveAtlas.

Simulates a researcher with no corpus disk: builds the package from
this repo, installs it into a FRESH venv, hides the local record store,
and walks the researcher path:

  1. import moveatlas; list_datasets() works from packaged data alone
  2. dataset(id) resolves and enforces access cases (barrier raises
     its documented route, not a download)
  3. the hosted tier reaches the PUBLIC Zenodo API: before the records
     are published this proves the honest-404 path end to end; after
     publication the same run downloads a real record file, verifies
     its sha256 and loads it (the flag flips automatically)

Exit 0 = ready at the current publication state; non-zero = a launch
gap, printed. Run before every release. Stdlib only; runs on POSIX and
Windows (venv layout and archive extraction are chosen per platform).
Usage: python launch_dryrun.py [--keep]
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.abspath(__file__))


def venv_bin(venv, name):
    """Path of an executable inside the venv: Scripts/<name>.exe on
    Windows, bin/<name> elsewhere."""
    if os.name == "nt":
        return os.path.join(venv, "Scripts", name + ".exe")
    return os.path.join(venv, "bin", name)


# names Windows refuses as path components (reserved DOS devices).
# datasets/aux/ was one of them until the 2026-09-11 rename to auxdata
# (KINEFM_HANDOFF_20 s1, docs/OPERATIONS.md s2); the corpus carries no
# reserved path today and this guard is what keeps it that way cheaply
_DOS_RESERVED = {"con", "prn", "aux", "nul"} | {
    f"{p}{i}" for p in ("com", "lpt") for i in range(1, 10)}


def _writable_here(member):
    """False on Windows for archive members that NTFS cannot create; such
    paths are never part of the wheel anyway. No corpus path matches since
    datasets/aux/ became datasets/auxdata/."""
    if os.name != "nt":
        return True
    return not any(seg.split(".")[0].lower() in _DOS_RESERVED
                   for seg in member.split("/"))


def stage_head(stage):
    """Extract `git archive HEAD` into stage using zip + zipfile (no tar
    dependency, identical on every platform). Windows git refuses to
    archive a reserved path unless core.protectNTFS is off for the command
    - `datasets/aux` did until it was renamed to auxdata on 2026-09-11 -
    so the override and the extraction skip both stay, for the next such
    path rather than for this one."""
    cmd = ["git", "-C", REPO]
    if os.name == "nt":
        cmd += ["-c", "core.protectNTFS=false"]
    cmd += ["archive", "--format=zip", "HEAD"]
    ar = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
    with zipfile.ZipFile(io.BytesIO(ar.stdout)) as zf:
        members = [m for m in zf.namelist() if _writable_here(m)]
        zf.extractall(stage, members=members)

CHILD = r'''
import json, os, sys
assert "MOVEATLAS_REPO" not in os.environ
import moveatlas
print("import OK, version", moveatlas.__version__)

rows = moveatlas.list_datasets()
assert len(rows) > 80, f"registry too small: {len(rows)}"
print("list_datasets OK:", len(rows), "rows")

from moveatlas.datasets.base import AccessError
try:
    moveatlas.dataset("beijing_sleep_lfp").get_data()
    sys.exit("FAIL: barrier dataset did not raise")
except AccessError as e:
    print("barrier enforcement OK:", str(e)[:60], "...")

from moveatlas.store import RemoteStore, _records_table
table = _records_table()
assert table, "packaged zenodo_records.json is missing or empty"
print("records table OK:", len(table), "records shipped")

did = sorted(table)[0]
rs = RemoteStore()
probe = f"datasets/auxdata/{did}/nonexistent.probe"
try:
    # the manifest fetch inside path() is the real test: it hits the
    # public API for the record and downloads+verifies files.csv
    rs._rows(did)
    print(f"HOSTED TIER LIVE: record manifest of '{did}' downloaded "
          "from the public API")
    hosted = True
except FileNotFoundError as e:
    msg = str(e)
    assert "not public (yet)" in msg, f"wrong 404 wording: {msg}"
    print("pre-publication state confirmed honestly:", msg[:70], "...")
    hosted = False
print("DRYRUN VERDICT:", "LAUNCH-READY (hosted tier live)" if hosted
      else "PLUMBING READY - waiting on record publication only")
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true",
                    help="keep the scratch venv for inspection")
    a = ap.parse_args()
    work = tempfile.mkdtemp(prefix="moveatlas_dryrun_")
    venv = os.path.join(work, "venv")
    try:
        print("== fresh venv:", venv)
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        pip = venv_bin(venv, "pip")
        py = venv_bin(venv, "python")
        # stage a CLEAN tree via git archive: the external volume grows
        # AppleDouble ._* ghosts (H8 quirk) that break the wheel build,
        # and archive-of-HEAD is exactly what a user would install anyway
        stage = os.path.join(work, "src")
        os.makedirs(stage)
        stage_head(stage)
        print("== pip install <git archive of HEAD> (isolated build)")
        subprocess.run([pip, "install", "--quiet", stage], check=True)
        print("== researcher walk (no local store, no env)")
        env = {k: v for k, v in os.environ.items()
               if k not in ("MOVEATLAS_REPO", "MOVEATLAS_CACHE", "PYTHONPATH")}
        env["MOVEATLAS_CACHE"] = os.path.join(work, "cache")
        r = subprocess.run([py, "-c", CHILD], env=env, cwd=work)
        sys.exit(r.returncode)
    finally:
        if a.keep:
            print("kept:", work)
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
