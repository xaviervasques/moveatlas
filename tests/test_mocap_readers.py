# -*- coding: utf-8 -*-
"""mocap_readers.py and the mapping rules of ingest_open_mocap.py, corpus-free: every file is
written here, in tmp_path, from known values, and read back. The C3D writer below follows the
format (512-byte blocks, a parameter section, then the frames) for the three processor types the
open lot holds: Intel and DEC with integer or float storage."""
import importlib.util
import os
import struct

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


def _load(name, needs_configs=False):
    for d in ("", os.path.join("tools", "canonical")):
        p = os.path.join(REPO, d, name)
        if os.path.exists(p):
            # the ingester reads configs/ beside it and imports build_canonical as a sibling,
            # which holds in the working tree; the public tree ships it under tools/canonical/
            # (the same skip as test_scripts.py's build_canonical test)
            if needs_configs and not os.path.exists(
                    os.path.join(os.path.dirname(p), "configs", "canonical_skeleton.yaml")):
                pytest.skip(f"{name} reads configs/ beside it; they are not there")
            spec = importlib.util.spec_from_file_location(name[:-3], p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    pytest.skip(f"{name} is not in this tree")


mr = _load("mocap_readers.py")


# ---------------------------------------------------------------- a minimal C3D writer
def _f32(v, proc):
    b = struct.pack("<f", v * (4.0 if proc == "dec" else 1.0))
    return b[2:4] + b[0:2] if proc == "dec" else b


def _param(name, gid, dtype, dims, data, last=False):
    body = bytes([dtype & 0xFF, len(dims)]) + bytes(dims) + data + b"\x00"
    off = 0 if last else 2 + len(body)
    return bytes([len(name), gid & 0xFF]) + name.encode() + struct.pack("<h", off) + body


def c3d_bytes(labels, pts, rate, proc="intel", storage="float", units="mm", resid=None):
    T, N, _ = pts.shape
    scale = -1.0 if storage == "float" else 0.5
    L = max(len(x) for x in labels)
    lab = b"".join(x.ljust(L).encode() for x in labels)
    params = (bytes([5, 0xFF]) + b"POINT" + struct.pack("<h", 3) + b"\x00"
              + _param("USED", 1, 2, [], struct.pack("<h", N))
              + _param("RATE", 1, 4, [], _f32(rate, proc))
              + _param("SCALE", 1, 4, [], _f32(scale, proc))
              + _param("UNITS", 1, -1, [len(units)], units.encode())
              + _param("LABELS", 1, -1, [L, N], lab, last=True))
    nblocks = (4 + len(params)) // 512 + 1
    psec = bytes([1, 0x50, nblocks, {"intel": 84, "dec": 85}[proc]]) + params
    psec = psec.ljust(nblocks * 512, b"\x00")
    dstart = 2 + nblocks
    head = bytearray(512)
    head[0], head[1] = 2, 0x50
    head[2:4] = struct.pack("<H", N)
    head[4:6] = struct.pack("<H", 0)
    head[6:8] = struct.pack("<H", 1)
    head[8:10] = struct.pack("<H", T)
    head[12:16] = _f32(scale, proc)
    head[16:18] = struct.pack("<H", dstart)
    head[20:24] = _f32(rate, proc)
    data = bytearray()
    for t in range(T):
        for j in range(N):
            r = 1.0 if resid is None else resid[t, j]
            vals = list(pts[t, j]) + [r]
            if storage == "float":
                data += b"".join(_f32(float(v), proc) for v in vals)
            else:
                data += struct.pack("<4h", *[int(round(v / abs(scale))) for v in vals[:3]], int(r))
    return bytes(head) + psec + bytes(data)


@pytest.mark.parametrize("proc,storage", [("intel", "float"), ("intel", "int"), ("dec", "float"), ("dec", "int")])
def test_c3d_points_labels_rate_units(tmp_path, proc, storage):
    rng = np.random.default_rng(0)
    pts = np.round(rng.uniform(-900, 1800, size=(7, 3, 3)) * 2) / 2      # on the int grid (scale 0.5)
    resid = np.ones((7, 3))
    resid[2, 1] = -1                                                        # a missing sample
    p = tmp_path / "t.c3d"
    p.write_bytes(c3d_bytes(["LASI", "RASI", "SACR"], pts, 150.0, proc, storage, "mm", resid))
    c = mr.read_c3d(str(p))
    assert c["processor"] == proc and c["storage"] == storage
    assert c["labels"] == ["LASI", "RASI", "SACR"]
    assert c["rate"] == 150.0 and c["rate_source"] == "POINT:RATE" and c["header_rate"] == 150.0
    assert c["units"] == "mm" and c["n_frames"] == 7 and c["frames_short"] == 0
    got = c["points"]
    assert np.isnan(got[2, 1]).all()
    ok = np.ones((7, 3), bool)
    ok[2, 1] = False
    assert np.allclose(got[ok], pts[ok], atol=1e-3)


def test_c3d_header_only_and_truncated_file(tmp_path):
    pts = np.ones((10, 2, 3))
    b = c3d_bytes(["A", "B"], pts, 100.0)
    p = tmp_path / "t.c3d"
    p.write_bytes(b[:-2 * 16 * 3])                     # the last three frames cut off
    c = mr.read_c3d(str(p), header_only=True)
    assert "points" not in c and c["rate"] == 100.0
    c = mr.read_c3d(str(p))
    assert c["n_frames"] == 7 and c["frames_short"] == 3 and c["points"].shape == (7, 2, 3)


def test_c3d_all_zero_point_is_missing_and_not_a_c3d_refused(tmp_path):
    pts = np.ones((3, 1, 3))
    pts[1] = 0.0
    p = tmp_path / "z.c3d"
    p.write_bytes(c3d_bytes(["A"], pts, 60.0))
    assert np.isnan(mr.read_c3d(str(p))["points"][1, 0]).all()
    q = tmp_path / "bad.c3d"
    q.write_bytes(b"\x00" * 1024)
    with pytest.raises(ValueError, match="not a C3D"):
        mr.read_c3d(str(q))


# ---------------------------------------------------------------- BVH
BVH = """HIERARCHY
ROOT Hips
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT Spine
  {
    OFFSET 0 10 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 5 0
    }
  }
}
MOTION
Frames: 2
Frame Time: 0.01
1 2 3 0 0 0 0 0 0
0 0 0 90 0 0 0 0 0
"""


def test_bvh_forward_kinematics_rate_and_end_site(tmp_path):
    p = tmp_path / "a.bvh"
    p.write_text(BVH, encoding="utf-8")
    b = mr.read_bvh(str(p))
    assert b["rate"] == pytest.approx(100.0) and b["frames_declared"] == 2
    pos, names = mr.bvh_positions(b)
    assert names == ["Hips", "Spine", "Spine_End"]
    assert np.allclose(pos[0], [[1, 2, 3], [1, 12, 3], [1, 17, 3]])
    # frame 2: the root turned 90 degrees about z, so +y offsets point to -x
    assert np.allclose(pos[1], [[0, 0, 0], [-10, 0, 0], [-15, 0, 0]], atol=1e-9)


def test_bvh_channel_count_mismatch_refused(tmp_path):
    p = tmp_path / "b.bvh"
    p.write_text(BVH.replace("1 2 3 0 0 0 0 0 0", "1 2 3 0 0 0 0 0"), encoding="utf-8")
    with pytest.raises(ValueError):
        mr.read_bvh(str(p))


# ---------------------------------------------------------------- Qualisys TSV and D-Flow text
def test_qualisys_tsv(tmp_path):
    lines = ["NO_OF_FRAMES\t3", "NO_OF_CAMERAS\t12", "NO_OF_MARKERS\t2", "FREQUENCY\t240",
             "NO_OF_ANALOG\t0", "ANALOG_FREQUENCY\t0", "DESCRIPTION--", "TIME_STAMP--", "DATA_INCLUDED\t3D",
             "MARKER_NAMES\tHead\tToe",
             "1.0\t2.0\t3.0\t4.0\t5.0\t6.0", "0\t0\t0\t4.5\t5.5\t6.5", "1.5\t2.5\t3.5\t4.0\t5.0\t6.0"]
    p = tmp_path / "Subject1_e0001.tsv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    q = mr.read_qualisys_tsv(str(p))
    assert q["rate"] == 240.0 and q["labels"] == ["Head", "Toe"] and q["n_frames"] == 3
    assert q["points"].shape == (3, 2, 3)
    assert np.isnan(q["points"][1, 0]).all() and np.allclose(q["points"][1, 1], [4.5, 5.5, 6.5])


def test_dflow_text_rate_is_measured(tmp_path):
    t = np.arange(6) * 0.01 + 100.0
    rows = ["TimeStamp\tFrameNumber\tLASIS.PosX\tLASIS.PosY\tLASIS.PosZ\tFP1.ForX"]
    for k, ti in enumerate(t):
        rows.append(f"{ti:.4f}\t{k}\t{k}\t1\t2\t9")
    p = tmp_path / "mocap-001.txt"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    r = mr.read_dflow_mocap_txt(str(p), ["LASIS", "RASIS"])
    assert r["rate"] == pytest.approx(100.0, rel=1e-3) and r["labels_present"] == ["LASIS"]
    assert np.isnan(r["points"][:, 1]).all() and r["points"][3, 0, 0] == 3


# ---------------------------------------------------------------- mapping rules of the ingester
def test_rules_centroid_first_of_absent_and_up_axis():
    io_ = _load("ingest_open_mocap.py", needs_configs=True)
    T = 4
    names = ["A", "B", "C"]
    pts = np.zeros((T, 3, 3))
    pts[:, 0] = [0, 0, 0]
    pts[:, 1] = [2, 0, 0]
    pts[:, 2] = [1, 3, 0]
    pts[1, 2] = np.nan
    idx = {n: i for i, n in enumerate(names)}
    v, kind = io_.resolve({"centroid": ["A", "B", "C"]}, idx, pts)
    assert kind == "centroid" and np.allclose(v[0], [1, 1, 0]) and np.isnan(v[1]).all()
    v, kind = io_.resolve({"first_of": [{"proxy": "Z"}, {"midpoint": ["A", "B"]}]}, idx, pts)
    assert kind == "midpoint" and np.allclose(v[0], [1, 0, 0])
    v, kind = io_.resolve({"first_of": [{"proxy": "Z"}, {"absent": "lower set"}]}, idx, pts)
    assert v is None and kind == "absent"
    assert io_.resolve({"proxy": "Z"}, idx, pts) == (None, "missing")
    canon = np.full((T, 15, 3), np.nan)
    canon[:, io_.J["pelvis"]] = [0, 0, 1.0]
    canon[:, io_.J["neck"]] = [0.02, 0.01, 1.5]
    assert io_.measure_up(canon)[0] == "+z"
    canon[:, io_.J["neck"]] = np.nan
    canon[:, io_.J["left_ankle"]] = [0, 0.9, 0]
    canon[:, io_.J["right_ankle"]] = [0, 0.9, 1.9]
    assert io_.measure_up(canon)[0] == "-y"


def test_every_open_joint_map_covers_the_15_joints():
    io_ = _load("ingest_open_mocap.py", needs_configs=True)
    for src, key in io_.CFG["open_mocap_sources"].items():
        jmap = io_.CFG["sources"][key]["joint_map"]
        assert set(jmap) == set(io_.CANON), (src, sorted(set(io_.CANON) ^ set(jmap)))
        assert src in io_.SOURCES
