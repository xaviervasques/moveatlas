# -*- coding: utf-8 -*-
"""build_canonical_amass.py, corpus-free: the joint forward kinematics keeps every bone length,
whatever the number of frames in one pass (the first build ran on Apple MPS, where passes of
more than 65,536 joint rotations came back non-rigid), and the rigidity check refuses a
stretched skeleton. A synthetic body stands in for the SMPL+H model (not in the repository)."""
import importlib.util
import os

import numpy as np
import pytest

torch = pytest.importorskip("torch")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


def _builder():
    for d in ("", os.path.join("tools", "canonical")):
        p = os.path.join(REPO, d, "build_canonical_amass.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("build_canonical_amass", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    pytest.skip("build_canonical_amass.py is not in this tree")


PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19] + \
          [20] * 15 + [21] * 15


def _body(seed=0, V=60):
    g = torch.Generator().manual_seed(seed)
    Jr = torch.rand(52, V, generator=g)
    return {"v_template": torch.randn(1, V, 3, generator=g),
            "shapedirs": 0.01 * torch.randn(V, 3, 16, generator=g),
            "J_regressor": Jr / Jr.sum(1, keepdim=True),
            "parents": torch.tensor(PARENTS)}


def _bone_spread(J):
    d = np.linalg.norm(J[:, 1:22] - J[:, PARENTS[1:22]], axis=-1)
    return float(((d.max(0) - d.min(0)) / d.mean(0)).max())


def test_rodrigues_gives_rotations_past_65536():
    b = _builder()
    v = torch.randn(70000, 3, generator=torch.Generator().manual_seed(1))
    R = b.rodrigues(v)
    eye = torch.eye(3).expand_as(R)
    assert torch.allclose(R @ R.transpose(1, 2), eye, atol=1e-5)
    assert torch.allclose(torch.linalg.det(R), torch.ones(len(R)), atol=1e-5)


def test_one_pass_of_1261_frames_is_rigid_and_equals_frame_by_frame():
    b = _builder()
    m, T = _body(), 1261                         # 1261 x 52 = 65,572 rotations in one pass
    g = torch.Generator().manual_seed(2)
    pose, trans = torch.randn(T, 156, generator=g), torch.randn(T, 3, generator=g)
    betas = torch.randn(1, 16, generator=g).repeat(T, 1)
    with torch.no_grad():
        J = b.posed_joints(m, pose, betas, trans)[:, :22].numpy()
        J1 = np.concatenate([b.posed_joints(m, pose[i:i + 1], betas[i:i + 1], trans[i:i + 1])[:, :22].numpy()
                             for i in range(0, T, 97)])
    assert _bone_spread(J) < 1e-4
    assert np.abs(J[::97] - J1).max() < 1e-4


def test_rigidity_check_refuses_a_stretched_skeleton():
    b = _builder()
    m = _body()
    with torch.no_grad():
        J = b.posed_joints(m, torch.zeros(10, 156), torch.zeros(10, 16), torch.zeros(10, 3))[:, :22].numpy()
    b.check_rigid(J, np.array(PARENTS), "rest")          # rigid: no error
    J[5, 4] += 0.2                                       # the left knee of frame 5 moves off its bone
    with pytest.raises(RuntimeError):
        b.check_rigid(J, np.array(PARENTS), "stretched")


def _npz(T=6, stageii=False, fps=120.0, seed=3):
    """An AMASS-like motion file: SMPL+H release keys (poses (T, 156), mocap_framerate) or
    MoSh++ stage-II keys (poses (T, 165), mocap_frame_rate, surface_model_type); fps None
    leaves the rate out. Returned as the bytes of the .npz."""
    import io
    rng = np.random.default_rng(seed)
    d = {"poses": 0.3 * rng.standard_normal((T, 165 if stageii else 156)),
         "trans": rng.standard_normal((T, 3)), "betas": rng.standard_normal(16),
         "gender": np.array("male")}
    if stageii:
        d["surface_model_type"] = np.array("smplx")
    if fps is not None:
        d["mocap_frame_rate" if stageii else "mocap_framerate"] = np.array(fps)
    buf = io.BytesIO()
    np.savez(buf, **d)
    return buf.getvalue()


def _load(data):
    import io
    return np.load(io.BytesIO(data), allow_pickle=True)


def test_frame_rate_reads_both_keys():
    b = _builder()
    assert b.frame_rate(_load(_npz(fps=120.0))) == 120.0                 # *_poses.npz
    assert b.frame_rate(_load(_npz(stageii=True, fps=60.0))) == 60.0     # *_stageii.npz
    assert b.frame_rate(_load(_npz(fps=None))) is None
    models = {g: _body() for g in ("male", "female", "neutral")}
    J, fps = b.joints_for(_load(_npz(stageii=True, fps=60.0)), models, "stageii")
    assert fps == 60.0 and J.shape == (6, 22, 3)


def _write_archive(path, members):
    import io
    import tarfile
    with tarfile.open(path, "w:bz2") as t:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))


def _bytes(*paths):
    out = {}
    for p in paths:
        with open(p, "rb") as f:
            out[p] = f.read()
    return out


def _subset(tmp_path, monkeypatch, members=None):
    """A subset SUB as a build that missed the stage-II key left it: a tar.bz2 of two stage-II
    files and one release file, its shard with fps None on the stage-II records, an AMASS
    manifest with CRLF and a pooled manifest with LF and a row of another source. Returns the
    builder (its paths moved into tmp_path), the models, the stored records and the shard path."""
    b = _builder()
    from moveatlas import records
    for k, v in {"REPO": tmp_path, "RAW": tmp_path / "raw", "OUT": tmp_path / "canonical",
                 "MANIFEST": tmp_path / "canonical_manifest.csv",
                 "POOLED": tmp_path / "_canonical_manifest.csv"}.items():
        monkeypatch.setattr(b, k, str(v))
    os.makedirs(b.RAW)
    os.makedirs(b.OUT)
    members = members or [("SUB/p1/a_stageii.npz", _npz(stageii=True, fps=60.0, seed=4)),
                          ("SUB/p1/b_poses.npz", _npz(fps=120.0, seed=5)),
                          ("SUB/p1/c_stageii.npz", _npz(T=7, stageii=True, fps=60.0, seed=6))]
    _write_archive(os.path.join(b.RAW, "SUB.tar.bz2"), members)
    models = {g: _body() for g in ("male", "female", "neutral")}
    old = []
    for name, data in members:                   # the shard as a build that missed the stage-II key
        J, fps = b.joints_for(_load(data), models, name)
        old.append(b.make_record(b.ns_of("SUB", name), name, J[:, b.SEL, :],
                                 None if "stageii" in name else fps))
    shard = os.path.join(b.OUT, "amass_SUB.npz")
    records.save(shard, old)
    head = "source,subject_ns,take,dim,fps,n_frames,modality"
    lines = [f"amass,{r['subject_ns']},{r['take']},3,{r['fps'] or ''},{r['n_frames']},3d_meter" for r in old]
    other = "remap_open,remap:p01,turn_1,2,,50,2d_pixel"
    with open(b.MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join([head] + lines) + "\r\n")
    with open(b.POOLED, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join([head, other] + lines) + "\n")
    return b, models, old, shard


def test_rebuild_fills_stated_frame_rates_only_with_fill_fps(tmp_path, monkeypatch):
    b, models, old, shard = _subset(tmp_path, monkeypatch)
    from moveatlas import records
    before = _bytes(shard, b.MANIFEST, b.POOLED)

    with pytest.raises(SystemExit, match="--fill-fps"):        # the default refuses, writes nothing
        b.rebuild(["SUB"], models)
    assert _bytes(*before) == before

    b.rebuild(["SUB"], models, fill_fps=True)
    new = records.load(shard)
    assert [r["fps"] for r in new] == [60.0, 120.0, 60.0]
    for o, n in zip(old, new):
        assert records.equal({k: v for k, v in n.items() if k != "fps"},
                             {k: v for k, v in o.items() if k != "fps"})
    for p, eol in ((b.MANIFEST, b"\r\n"), (b.POOLED, b"\n")):
        a, z = before[p].split(eol), _bytes(p)[p].split(eol)
        assert len(a) == len(z)
        changed = [(x, y) for x, y in zip(a, z) if x != y]
        assert len(changed) == 2 and all(b"stageii" in y and b",60.0," in y for _, y in changed)
        assert all(x.replace(b",3,,", b",3,60.0,") == y for x, y in changed)

    with pytest.raises(SystemExit, match="not empty"):          # a filled cell is never filled again
        b.fill_manifest_fps(b.POOLED, {(old[0]["subject_ns"], old[0]["take"]): (6, 60.0)})
    after = _bytes(b.MANIFEST, b.POOLED)
    b.rebuild(["SUB"], models, fill_fps=True)    # a second run has nothing to fill
    assert [r["fps"] for r in records.load(shard)] == [60.0, 120.0, 60.0]
    assert _bytes(*after) == after
    assert not [x for x in os.listdir(tmp_path) if x.endswith(".part")]


# One manifest edited before a --fill-fps run: (manifest, edit of its text, refusal message).
# The amass row of the first stored record reads amass,amass:SUB:SUB_p1,SUB/p1/a_stageii.npz,3,,6,3d_meter
_A = "amass:SUB:SUB_p1,SUB/p1/a_stageii.npz"
_REFUSALS = {
    "cell already filled": ("MANIFEST", lambda t: t.replace(f"{_A},3,,6,", f"{_A},3,60.0,6,"), "not empty"),
    "n_frames differs":("POOLED", lambda t: t.replace(f"{_A},3,,6,", f"{_A},3,,5,"), "n_frames"),
    "duplicate row": ("MANIFEST", lambda t: t + t.split("\r\n")[1] + "\r\n", "two rows"),
    "no row": ("POOLED", lambda t: "\n".join(x for x in t.split("\n") if _A not in x), "no row"),
    "row under another source only": ("POOLED", lambda t: t.replace(f"amass,{_A}", f"remap_open,{_A}"), "no row"),
    "round trip changes another line": ("POOLED", lambda t: t.replace("remap_open,", '"remap_open",'), "round trip"),
    "round trip changes the line count": ("MANIFEST", lambda t: t[:-2], "round trip"),
}


@pytest.mark.parametrize("case", sorted(_REFUSALS))
def test_fill_fps_refusals_write_nothing(tmp_path, monkeypatch, case):
    b, models, old, shard = _subset(tmp_path, monkeypatch)
    which, edit, match = _REFUSALS[case]
    p = getattr(b, which)
    with open(p, encoding="utf-8", newline="") as f:
        txt = f.read()
    assert edit(txt) != txt
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(edit(txt))
    before = _bytes(shard, b.MANIFEST, b.POOLED)
    with pytest.raises(SystemExit, match=match):
        b.rebuild(["SUB"], models, fill_fps=True)
    assert _bytes(*before) == before             # refused before the shard is saved


@pytest.mark.parametrize("rate", [0.0, float("nan")])
def test_fill_fps_refuses_a_rate_that_is_not_finite_and_positive(tmp_path, monkeypatch, rate):
    members = [("SUB/p1/a_stageii.npz", _npz(stageii=True, fps=rate, seed=4)),
               ("SUB/p1/b_poses.npz", _npz(fps=120.0, seed=5))]
    b, models, old, shard = _subset(tmp_path, monkeypatch, members)
    before = _bytes(shard, b.MANIFEST, b.POOLED)
    with pytest.raises(SystemExit, match="states fps"):
        b.rebuild(["SUB"], models, fill_fps=True)
    assert _bytes(*before) == before


def test_fill_fps_leaves_a_row_of_another_source_with_the_same_key(tmp_path, monkeypatch):
    b, models, old, shard = _subset(tmp_path, monkeypatch)
    twin = f"remap_open,{_A},3,,6,3d_meter"
    with open(b.POOLED, encoding="utf-8", newline="") as f:
        txt = f.read()
    head, rest = txt.split("\n", 1)
    with open(b.POOLED, "w", encoding="utf-8", newline="") as f:
        f.write(f"{head}\n{twin}\n{rest}")       # before the amass row
    b.rebuild(["SUB"], models, fill_fps=True)
    with open(b.POOLED, encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    assert lines[1] == twin
    assert f"amass,{_A},3,60.0,6,3d_meter" in lines


def test_fill_fps_resumes_a_run_stopped_before_its_manifests(tmp_path, monkeypatch):
    b, models, old, shard = _subset(tmp_path, monkeypatch)
    from moveatlas import records
    stale = _bytes(b.MANIFEST, b.POOLED)
    b.rebuild(["SUB"], models, fill_fps=True)
    done = _bytes(b.MANIFEST, b.POOLED)
    # stopped after the shard was saved: before both manifests, or between the two
    for lost in ((b.MANIFEST, b.POOLED), (b.POOLED,)):
        for p in lost:
            with open(p, "wb") as f:
                f.write(stale[p])
        b.rebuild(["SUB"], models)               # without the flag: no error, nothing caught up
        assert all(_bytes(p)[p] == stale[p] for p in lost)
        b.rebuild(["SUB"], models, fill_fps=True)
        assert _bytes(b.MANIFEST, b.POOLED) == done
        assert [r["fps"] for r in records.load(shard)] == [60.0, 120.0, 60.0]
    txt = stale[b.POOLED].decode("utf-8")                           # a caught-up row is checked too
    dup = txt + next(x for x in txt.split("\n") if _A in x) + "\n"
    for bad, match in ((txt.replace(f"{_A},3,,6,", f"{_A},3,,5,"), "n_frames"), (dup, "two rows")):
        with open(b.POOLED, "w", encoding="utf-8", newline="") as f:
            f.write(bad)
        before = _bytes(b.MANIFEST, b.POOLED)
        with pytest.raises(SystemExit, match=match):
            b.rebuild(["SUB"], models, fill_fps=True)
        assert _bytes(b.MANIFEST, b.POOLED) == before
