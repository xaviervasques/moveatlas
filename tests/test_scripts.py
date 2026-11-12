# -*- coding: utf-8 -*-
"""The three riskiest root scripts, pinned (LAUNCH_PLAN 1.3): the gate that
decides whether records are correct (validate_canonical.py), the pass that
produces the paper's record counts (mask_statistics.py), and the uploader's
offline paths (upload_zenodo.py). Corpus-free: every check runs on synthetic
records in a temporary repository. Each script is loaded from wherever this
tree keeps it (the root of the working tree, tools/<role>/ in the public
tree) and skipped when absent."""
import argparse
import csv
import importlib.util
import io
import json
import os
import zipfile

import numpy as np
import pytest

from moveatlas import records

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


def _load_script(name, *dirs):
    for d in ("",) + dirs:
        p = os.path.join(REPO, d, name) if d else os.path.join(REPO, name)
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location(name[:-3], p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    pytest.skip(f"{name} is not in this tree")


@pytest.fixture(scope="module")
def vc():
    return _load_script("validate_canonical.py")


@pytest.fixture(scope="module")
def ms():
    return _load_script("mask_statistics.py")


@pytest.fixture(scope="module")
def bcf():
    return _load_script("build_canonical_force.py", "tools/canonical")


def _imu(T=100, L=1, nan_at=None, zeros=False, acc_scale=1.0):
    sig = (np.random.rand(T, L, 9).astype(np.float32) * 0.5 + 0.7) * acc_scale
    sig[:, :, 3:6] = 30.0     # gyro deg/s, in band
    if zeros:
        sig[:] = 0.0
    if nan_at is not None:
        sig[nan_at] = np.nan
    cmask = np.zeros((L, 9), bool)
    cmask[:, :6] = True
    return {"signal": sig, "channel_mask": cmask,
            "location_ids": np.arange(L), "fps": 100.0, "n_frames": T,
            "subject_ns": "toy:s1", "task": "walk", "source": "toy"}


def _emg(T=200, C=2, unit="mV", scale=0.2):
    return {"signal": (np.random.rand(T, C).astype(np.float32) - 0.5) * scale,
            "channels": [{"kind": "emg", "site": f"m{i}"} for i in range(C)],
            "unit": unit, "fps": 2000.0, "n_frames": T,
            "subject_ns": "toy:s1", "task": "t", "source": "toy"}


# -- validate_canonical.check_record -------------------------------------------

def test_check_record_clean_imu_has_no_findings(vc):
    rep = vc.Report()
    vc.check_record(_imu(), vc.FAMILIES["imu"], "imu", "r", rep)
    assert rep.errors == [] and rep.warnings == []


def test_check_record_flags_frame_count_and_missing_array(vc):
    rep = vc.Report()
    r = _imu()
    r["n_frames"] = 99
    vc.check_record(r, vc.FAMILIES["imu"], "imu", "r", rep)
    assert any("n_frames says 99" in e for e in rep.errors)
    rep = vc.Report()
    vc.check_record({"fps": 1.0}, vc.FAMILIES["imu"], "imu", "r", rep)
    assert any("no 'signal' array" in e for e in rep.errors)


def test_check_record_nan_is_an_error_only_in_present_channels(vc):
    rep = vc.Report()
    r = _imu()
    r["signal"][5, 0, 0] = np.nan             # acc_x, present
    vc.check_record(r, vc.FAMILIES["imu"], "imu", "r", rep)
    assert any("marks PRESENT" in e for e in rep.errors)
    rep = vc.Report()
    r = _imu()
    r["signal"][5, 0, 7] = np.nan             # mag_y, absent
    vc.check_record(r, vc.FAMILIES["imu"], "imu", "r", rep)
    assert rep.errors == [] and any("already marks absent" in w for w in rep.warnings)


def test_check_record_all_zero_needs_a_mask_that_says_so(vc):
    rep = vc.Report()
    vc.check_record(_imu(zeros=True), vc.FAMILIES["imu"], "imu", "r", rep)
    assert any("NO mask marks it absent" in e for e in rep.errors)
    rep = vc.Report()
    r = _imu(zeros=True)
    r["channel_mask"][:] = False
    vc.check_record(r, vc.FAMILIES["imu"], "imu", "r", rep)
    assert rep.errors == [] and any("correctly says so" in w for w in rep.warnings)


def test_check_record_imu_amplitude_band_per_channel_kind(vc):
    rep = vc.Report()
    vc.check_record(_imu(acc_scale=100.0), vc.FAMILIES["imu"], "imu", "r", rep)
    assert any("acc p99" in w and "outside" in w for w in rep.warnings)
    assert not any("gyro p99" in w for w in rep.warnings)


def test_check_record_emg_units_the_contract_allows(vc):
    cfg = vc.FAMILIES["emg"]
    rep = vc.Report()
    vc.check_record(_emg(unit="uV", scale=200.0), cfg, "emg", "r", rep)
    assert rep.warnings == [], rep.warnings      # uV allowed, band judged in uV
    rep = vc.Report()
    vc.check_record(_emg(unit="unknown"), cfg, "emg", "r", rep)
    assert not any("not one the contract allows" in w for w in rep.warnings)
    rep = vc.Report()
    vc.check_record(_emg(unit="V"), cfg, "emg", "r", rep)
    assert any("unit 'V' is not one the contract allows" in w for w in rep.warnings)
    rep = vc.Report()
    r = _emg()
    r["channels"] = r["channels"][:1]
    vc.check_record(r, cfg, "emg", "r", rep)
    assert any("channel entries" in e for e in rep.errors)


# -- validate_canonical.validate_family on a temporary repository --------------

def _eeg_rec(T=50, C=3, subject="toy:s1"):
    return {"signal": np.random.rand(T, C).astype(np.float32) * 20,
            "channels": [{"site": f"C{i}", "kind": "eeg"} for i in range(C)],
            "unit": "uV", "fps": 250.0, "n_frames": T,
            "subject_ns": subject, "task": "rest", "source": "toy"}


def _write_eeg_repo(tmp_path, rows, files):
    ds = tmp_path / "datasets"
    d = ds / "eeg" / "toy" / "processed" / "canonical_eeg"
    d.mkdir(parents=True)
    for name, rec in files.items():
        records.save(str(d / name), rec)
    with open(ds / "_canonical_eeg_manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "task", "fps", "n_frames",
                    "n_channels", "sites", "record_path"])
        w.writerows(rows)
    return str(tmp_path)


def _run(vc, repo, full=True):
    rep = vc.Report()
    args = argparse.Namespace(full=full, sample=3)
    vc.validate_family(repo, "eeg", vc.FAMILIES["eeg"], args, rep)
    return rep


def test_validate_family_clean(vc, tmp_path):
    rel = "datasets/eeg/toy/processed/canonical_eeg/toy__s1__rest.npz"
    repo = _write_eeg_repo(tmp_path, [["toy", "toy:s1", "rest", 250, 50, 3, "C0|C1|C2", rel]],
                           {"toy__s1__rest.npz": _eeg_rec()})
    rep = _run(vc, repo)
    assert rep.errors == [], rep.errors
    assert any("opened 1 record" in n for n in rep.info)


def test_validate_family_backslash_path_is_missing_on_posix(vc, tmp_path):
    """The 2026-09-08 defect: a manifest written on Windows carried
    backslashes; the gate passed there and failed here. It must FAIL
    here, loudly, and the same rows with forward slashes must pass."""
    if os.sep == "\\":
        pytest.skip("backslashes resolve on Windows; the guard is test_manifests")
    bad = "datasets\\eeg\\toy\\processed\\canonical_eeg\\toy__s1__rest.npz"
    repo = _write_eeg_repo(tmp_path, [["toy", "toy:s1", "rest", 250, 50, 3, "C0", bad]],
                           {"toy__s1__rest.npz": _eeg_rec()})
    rep = _run(vc, repo)
    assert any("missing file" in e for e in rep.errors)
    assert any("NOT in the manifest" in e for e in rep.errors)


def test_validate_family_orphan_and_identity(vc, tmp_path):
    rel = "datasets/eeg/toy/processed/canonical_eeg/toy__s1__rest.npz"
    repo = _write_eeg_repo(
        tmp_path,
        [["toy", "toy:s1", "rest", 250, 50, 3, "C0", rel],
         ["other", "toy:s1", "rest", 250, 50, 3, "C0", rel],      # same subject, two sources
         ["toy", "s2", "rest", 250, 50, 3, "C0", rel]],           # not namespaced
        {"toy__s1__rest.npz": _eeg_rec(), "toy__s9__rest.npz": _eeg_rec(subject="toy:s9")})
    rep = _run(vc, repo)
    assert any("claimed by BOTH" in e for e in rep.errors)
    assert any("1 record file(s) on disk are NOT in the manifest" in e for e in rep.errors)
    assert any("not namespaced" in w for w in rep.warnings)


def test_validate_family_no_manifest_is_a_note_not_an_error(vc, tmp_path):
    rep = _run(vc, str(tmp_path))
    assert rep.errors == [] and any("no manifest" in n for n in rep.info)


# -- mask_statistics --------------------------------------------------------------

def test_rec_family_and_usability(ms):
    imu = _imu()
    assert ms.rec_family(imu) == "imu"
    assert ms.usability(imu, "imu") == 1.0
    imu["sample_valid"] = np.zeros((100, 1), bool)
    imu["sample_valid"][:25] = True
    assert abs(ms.usability(imu, "imu") - 0.25) < 1e-9
    eeg = _eeg_rec()
    assert ms.rec_family(eeg) == "eeg"
    eeg["bad_channels"] = ["C0"]
    assert abs(ms.usability(eeg, "eeg") - 2 / 3) < 1e-9
    emg = _emg()
    assert ms.rec_family(emg) == "emg" and ms.usability(emg, "emg") == 1.0
    pose = {"coords": np.zeros((10, 15, 2)), "valid_mask": np.array([True] * 5 + [False] * 5)}
    assert ms.rec_family(pose) == "pose" and ms.usability(pose, "pose") == 0.5
    assert ms.rec_family({"x": 1}) is None
    assert ms.usability({"coords": 1}, "pose") is None   # no mask: None, never a guess
    force = {"force": np.ones((10, 2, 9), np.float32), "sensor_mask": np.ones((2, 9), bool)}
    assert ms.rec_family(force) == "force" and ms.usability(force, "force") == 1.0
    force["sample_valid"] = np.ones((10, 2), bool)
    force["sample_valid"][:5, 0] = False
    assert abs(ms.usability(force, "force") - 0.75) < 1e-9


def test_force_make_record_marks_dropouts(bcf):
    tmask = np.zeros(9, bool)
    tmask[8] = True                                    # totals only
    footL = np.zeros((5, 9))
    footR = np.zeros((5, 9))
    footL[:, 8] = [np.nan, np.nan, 10, 20, 30]
    footR[:, 8] = [np.nan, 5, 5, 5, 5]
    rec = bcf.make_record(footL, footR, tmask, tmask, 100.0, "toy:S1", "walk", "toy")
    assert np.isfinite(rec["force"]).all() and rec["force"][0, 0, 8] == 0
    assert rec["force"][:, 0, 8].tolist() == [0, 0, 10, 20, 30]
    assert rec["sample_valid"].tolist() == [[False, False], [False, True], [True, True],
                                            [True, True], [True, True]]
    assert rec["dropout_fraction"] == pytest.approx(0.3)
    footL[:, 8] = 1.0
    footR[:, 8] = 1.0
    clean = bcf.make_record(footL, footR, tmask, tmask, 100.0, "toy:S1", "walk", "toy")
    assert "sample_valid" not in clean and "dropout_fraction" not in clean


def test_iter_records_walks_every_container_kind_and_marks_sampling(ms, tmp_path):
    ds = tmp_path / "datasets"
    # one-big-container family
    d1 = ds / "imu" / "a" / "processed"
    d1.mkdir(parents=True)
    records.save(str(d1 / "canonical_imu.npz"), [_imu(), _imu()])
    # per-record family
    d2 = ds / "eeg" / "b" / "processed" / "canonical_eeg"
    d2.mkdir(parents=True)
    for i in range(3):
        records.save(str(d2 / f"b__s{i}__rest.npz"), _eeg_rec(subject=f"b:s{i}"))
    # shard directory (one list per subject)
    d3 = ds / "pose" / "c" / "processed" / "canonical"
    d3.mkdir(parents=True)
    for i in range(5):
        records.save(str(d3 / f"s{i}.npz"),
                     [{"coords": np.zeros((4, 15, 2)), "valid_mask": np.ones(4, bool),
                       "source": "c", "subject_ns": f"c:s{i}"}])
    (d3 / "._ghost.npz").write_bytes(b"not a container")
    got = list(ms.iter_records(str(tmp_path), cap_shards=0))
    fams = sorted(ms.rec_family(r) for r, _ in got)
    assert fams == ["eeg"] * 3 + ["imu"] * 2 + ["pose"] * 5
    assert all(sampled is False for _, sampled in got)
    # a shard cap below the shard count marks the pose records sampled
    got = list(ms.iter_records(str(tmp_path), cap_shards=2))
    pose_flags = {s for r, s in got if ms.rec_family(r) == "pose"}
    assert pose_flags == {True}
    assert sum(1 for r, _ in got if ms.rec_family(r) == "pose") == 2


# -- upload_zenodo: the offline paths ------------------------------------------

@pytest.fixture
def staging(tmp_path, monkeypatch):
    """A temporary repository with two staged deposits: one clean, one
    with a missing file; plus a bundled one whose zip carries files.csv."""
    repo = tmp_path
    st = repo / "export" / "zenodo_staging"
    st.mkdir(parents=True)
    data = repo / "datasets" / "imu" / "ok" / "raw"
    data.mkdir(parents=True)
    (data / "a.csv").write_bytes(b"1,2,3\n" * 10)
    with open(st / "_plan.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "target", "record", "license", "n_files", "ok"])
        w.writerow(["ok", "zenodo", "", "cc-by-4.0", 1, "yes"])
        w.writerow(["gone", "zenodo", "", "cc-by-4.0", 1, "yes"])
        w.writerow(["hfset", "hf", "", "cc0", 1, "yes"])
    for did, path, nbytes in (("ok", "datasets\\imu\\ok\\raw\\a.csv", 60),
                              ("gone", "datasets/imu/gone/raw/b.csv", 5)):
        d = st / did
        d.mkdir()
        (d / "metadata.json").write_text(json.dumps({"metadata": {"title": did}}))
        with open(d / "files.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "bytes", "sha256"])
            w.writerow([path, nbytes, "ab" * 32])
    monkeypatch.setenv("MOVEATLAS_REPO", str(repo))
    return repo


def test_read_staging_normalises_paths_and_filters_targets(staging):
    uz = _load_script("upload_zenodo.py", "tools/release")
    got = {did: files for did, _meta, files in uz.read_staging()}
    assert set(got) == {"ok", "gone"}            # the hf row is not zenodo's
    rel, abspath, nbytes = got["ok"][0]
    assert rel == "datasets/imu/ok/raw/a.csv" and nbytes == 60
    assert abspath.endswith(os.path.join("imu", "ok", "raw", "a.csv"))
    only = {did for did, _m, _f in uz.read_staging(only={"gone"})}
    assert only == {"gone"}


def test_dry_run_reports_missing_files(staging, capsys):
    uz = _load_script("upload_zenodo.py", "tools/release")
    assert uz.dry_run(None) == 1
    out = capsys.readouterr().out
    assert "1 staged deposits clean, 1 with problems" in out
    assert "gone" in out and "1 missing" in out
    assert uz.dry_run({"ok"}) == 0


def test_bundle_is_current_compares_content_not_time(staging):
    uz = _load_script("upload_zenodo.py", "tools/release")
    d = staging / "export" / "zenodo_staging" / "ok"
    assert uz.bundle_is_current("ok") is False          # no bundle yet
    b = d / "bundle"
    b.mkdir()
    (b / "BUNDLED.ok").write_text("")
    with zipfile.ZipFile(b / "part1.zip", "w") as z:
        z.writestr("files.csv", "path,bytes,sha256,zip_part\n"
                   "datasets/imu/ok/raw/a.csv,60," + "ab" * 32 + ",part1.zip\n")
    assert uz.bundle_is_current("ok") is True           # same path + sha256
    with open(d / "files.csv", "w", newline="") as f:
        f.write("path,bytes,sha256\ndatasets/imu/ok/raw/a.csv,60," + "cd" * 32 + "\n")
    assert uz.bundle_is_current("ok") is False          # sha changed: rebuild


def test_hashes(staging):
    uz = _load_script("upload_zenodo.py", "tools/release")
    p = staging / "datasets" / "imu" / "ok" / "raw" / "a.csv"
    md5, sha = uz._hashes(str(p))
    import hashlib
    assert md5 == hashlib.md5(p.read_bytes()).hexdigest()
    assert sha == hashlib.sha256(p.read_bytes()).hexdigest()


# -- set_stated_fps.py and the build_canonical.py guard (2026-09-29) ----------

PROV = "30 fps stated by a toy data paper: nominal, not measured"


@pytest.fixture()
def ssf(monkeypatch, tmp_path):
    mod = _load_script("set_stated_fps.py", "tools/canonical")
    monkeypatch.setattr(mod, "REPO", str(tmp_path))
    return mod


def _pose(source, ns, take, T, fps=None):
    return {"coords": np.zeros((T, 15, 3), np.float32), "fps": fps, "source": source,
            "subject_ns": ns, "take": take, "n_frames": T, "dim": 2}


def _toy_repo(root, crlf_rows=True):
    """A list container of two sources, an LF pooled manifest and a CRLF per-source one."""
    recs = [_pose("toy", "toy:S1", "walk_1", 5), _pose("other", "other:S1", "walk_1", 6),
            _pose("toy", "toy:S2", "walk_1", 7), _pose("toy", "toy:S1", "sts_1", 8, 30.0)]
    records.save(str(root / "c.npz"), recs)
    head = ["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"]
    pooled = [head, ["toy", "toy:S1", "walk_1", "2", "", "5", "2d_pixel"],
              ["other", "other:S1", "walk_1", "2", "", "6", "2d_pixel"],
              ["toy", "toy:S1", "sts_1", "2", "30.0", "8", "2d_pixel"]]
    own = [head] + ([["toy", "toy:S2", "walk_1", "2", "", "7", "2d_pixel"]] if crlf_rows else [])
    for name, rows, eol in (("m_lf.csv", pooled, "\n"), ("m_crlf.csv", own, "\r\n")):
        with open(root / name, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, lineterminator=eol).writerows(rows)
    return ["c.npz", "m_lf.csv", "m_crlf.csv"]


def _state(root, names):
    import hashlib
    return {n: (hashlib.sha256((root / n).read_bytes()).hexdigest(),
                os.stat(root / n).st_mtime_ns) for n in names}


def _args(extra=()):
    return ["--container", "c.npz", "--manifest", "m_lf.csv", "--manifest", "m_crlf.csv",
            "--source", "toy", "--take-prefix", "walk_", "--fps", "30",
            "--provenance", PROV] + list(extra)


def test_set_stated_fps_patches_only_the_source_and_refuses_a_second_run(ssf, tmp_path):
    names = _toy_repo(tmp_path)
    before = _state(tmp_path, names)
    lf0 = (tmp_path / "m_lf.csv").read_bytes()
    crlf0 = (tmp_path / "m_crlf.csv").read_bytes()
    assert ssf.main(_args()) == 0                              # dry run
    assert _state(tmp_path, names) == before
    assert ssf.main(_args(["--yes"])) == 0
    recs = records.load(str(tmp_path / "c.npz"))
    assert [r["fps"] for r in recs] == [30.0, None, 30.0, 30.0]
    assert [r.get("fps_provenance") for r in recs] == [PROV, None, PROV, None]
    assert recs[0]["coords"].shape == (5, 15, 3) and recs[1]["n_frames"] == 6
    lf1 = (tmp_path / "m_lf.csv").read_bytes()
    crlf1 = (tmp_path / "m_crlf.csv").read_bytes()
    assert b"\r" not in lf1 and crlf1.count(b"\r\n") == 2      # line endings kept
    assert lf1 == lf0.replace(b"walk_1,2,,5,", b"walk_1,2,30.0,5,")
    assert crlf1 == crlf0.replace(b"walk_1,2,,7,", b"walk_1,2,30.0,7,")
    after = _state(tmp_path, names)
    with pytest.raises(SystemExit, match="already has fps"):
        ssf.main(_args(["--yes"]))
    assert _state(tmp_path, names) == after


def test_set_stated_fps_refuses_a_missing_manifest_row(ssf, tmp_path):
    names = _toy_repo(tmp_path, crlf_rows=False)
    before = _state(tmp_path, names)
    with pytest.raises(SystemExit, match="no manifest row"):
        ssf.main(_args(["--yes"]))
    assert _state(tmp_path, names) == before


def test_set_stated_fps_refuses_a_different_n_frames(ssf, tmp_path):
    names = _toy_repo(tmp_path)
    p = tmp_path / "m_lf.csv"
    p.write_bytes(p.read_bytes().replace(b"walk_1,2,,5,", b"walk_1,2,,9,"))
    before = _state(tmp_path, names)
    with pytest.raises(SystemExit, match="n_frames"):
        ssf.main(_args(["--yes"]))
    assert _state(tmp_path, names) == before


def test_set_stated_fps_take_prefix_leaves_other_takes_alone(ssf, tmp_path):
    _toy_repo(tmp_path)
    recs = records.load(str(tmp_path / "c.npz"))
    recs[3]["fps"] = None                                    # an sts_ take without a rate
    records.save(str(tmp_path / "c.npz"), recs)
    assert ssf.main(_args(["--yes"])) == 0
    recs = records.load(str(tmp_path / "c.npz"))
    assert recs[3]["fps"] is None and "fps_provenance" not in recs[3]
    assert "toy,toy:S1,sts_1,2,30.0,8" in (tmp_path / "m_lf.csv").read_text(encoding="utf-8")


def test_build_canonical_main_refuses_to_run(tmp_path, monkeypatch):
    for d in ("", "tools/canonical"):
        p = os.path.join(REPO, d, "build_canonical.py")
        if os.path.exists(p):
            break
    else:
        pytest.skip("build_canonical.py is not in this tree")
    if not os.path.exists(os.path.join(os.path.dirname(p), "configs", "canonical_skeleton.yaml")):
        pytest.skip("build_canonical.py reads configs/ beside it; they are not there")
    bc = _load_script("build_canonical.py", "tools/canonical")

    def called(*a, **k):
        raise AssertionError("an ingest function ran")

    for name in [n for n in dir(bc) if n.startswith("ingest_")]:
        monkeypatch.setattr(bc, name, called)
    monkeypatch.setattr(bc, "REPO", str(tmp_path))
    with pytest.raises(SystemExit, match="refuses to run"):
        bc.main()
    assert list(tmp_path.iterdir()) == []
