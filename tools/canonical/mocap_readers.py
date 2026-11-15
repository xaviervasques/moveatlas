# -*- coding: utf-8 -*-
"""Minimal readers for the motion-capture file formats of the open mocap lot (2026-11-12).

numpy only (no ezc3d, no third-party parser): the PC has none, and the lot needs four formats.
Every reader returns the native sampling rate it found IN THE FILE, never a default:

- read_c3d(path): C3D point data (Intel, DEC and MIPS processors; integer or float storage).
  Rate: the POINT:RATE parameter, else the header's frame rate. Units: POINT:UNITS. Labels:
  POINT:LABELS, then LABELS2, LABELS3... for files with more than 255 points. A point whose
  residual word is negative, or whose three coordinates are exactly zero, is missing (NaN).
  The analog block of each frame is skipped, never decoded.
- read_bvh(path) and bvh_positions(bvh): a BVH hierarchy and its motion; the world position of
  every joint by forward kinematics (rotation channels applied in the order the file lists
  them). Rate: 1 / Frame Time.
- read_qualisys_tsv(path): a Qualisys Track Manager 3D export (FREQUENCY, MARKER_NAMES, then
  X Y Z per marker per row). Rate: the FREQUENCY line.
- read_dflow_mocap_txt(path, markers): the D-Flow "mocap" text export of Moore et al. (tab
  separated, a TimeStamp column in seconds, <marker>.PosX/.PosY/.PosZ columns). It has no rate
  field: the rate is MEASURED as 1 / median TimeStamp step and reported with the step spread,
  so the caller can state it as measured.

Nothing here resamples, filters or fills a gap.
"""
import io
import os
import re

import numpy as np

# ---------------------------------------------------------------- C3D
_PROC = {84: "intel", 85: "dec", 86: "mips"}


def _dec_floats(b):
    """DEC (VAX F) 32-bit floats from raw bytes: swap the 16-bit words, read as IEEE little
    endian, divide by 4 (the exponent bias differs by 2)."""
    a = np.frombuffer(b, dtype=np.uint8).reshape(-1, 4)[:, [2, 3, 0, 1]].copy()
    return a.view("<f4").ravel() / 4.0


class _C3DBytes:
    def __init__(self, data, proc):
        self.d, self.proc = data, proc
        self.ie = ">" if proc == "mips" else "<"

    def i16(self, off, n=1, unsigned=False):
        dt = np.dtype(self.ie + ("u2" if unsigned else "i2"))
        return np.frombuffer(self.d, dtype=dt, count=n, offset=off)

    def f32(self, off, n=1):
        if self.proc == "dec":
            return _dec_floats(self.d[off:off + 4 * n])
        return np.frombuffer(self.d, dtype=np.dtype(self.ie + "f4"), count=n, offset=off).astype(float)


def _s8(b):
    """A byte read as a signed 8-bit integer."""
    return b - 256 if b > 127 else b


def _c3d_params(buf, start):
    """{(group, parameter): value} of the parameter section starting at byte `start`."""
    d = buf.d
    groups, raw = {}, []
    p = start + 4
    while p + 2 <= len(d):
        nlen = _s8(d[p])
        gid = _s8(d[p + 1])
        if nlen == 0:
            break
        name = d[p + 2:p + 2 + abs(nlen)].decode("latin-1").strip().upper()
        q = p + 2 + abs(nlen)
        off = int(buf.i16(q)[0])
        if gid < 0:
            groups[-gid] = name
        else:
            dtype = _s8(d[q + 2])
            nd = d[q + 3]
            dims = list(d[q + 4:q + 4 + nd])
            v0 = q + 4 + nd
            count = int(np.prod(dims)) if dims else 1
            size = abs(dtype) * count
            raw.append((gid, name, dtype, dims, v0, size))
        if off == 0:
            break
        p = q + off
    out = {}
    for gid, name, dtype, dims, v0, size in raw:
        g = groups.get(gid, str(gid))
        if dtype == -1:
            chars = d[v0:v0 + size].decode("latin-1")
            if len(dims) <= 1:
                val = chars.strip()
            else:
                L = dims[0]
                if L == 0:
                    val = [""] * int(np.prod(dims[1:]))
                else:
                    val = [chars[i:i + L].strip() for i in range(0, len(chars), L)]
        elif dtype == 1:
            val = np.frombuffer(d, dtype=np.uint8, count=size, offset=v0).astype(int)
        elif dtype == 2:
            val = buf.i16(v0, size // 2).astype(int)
        elif dtype == 4:
            val = buf.f32(v0, size // 4)
        else:
            continue
        out[(g, name)] = val
    return out


def _scalar(v):
    if v is None:
        return None
    a = np.asarray(v).ravel()
    return a[0].item() if a.size else None


def read_c3d(path_or_bytes, header_only=False):
    """Read a C3D file. Returns a dict: labels (list), units (str), rate (float, from the file),
    rate_source ('POINT:RATE' or 'header'), header_rate, n_points, n_frames, first_frame,
    processor, storage ('float' or 'int'), points (T, N, 3) float with NaN where missing
    (absent when header_only), frames_short (int: declared frames missing at the end of a
    truncated file), params (the parsed parameter dict)."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        d = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, "rb") as f:
            d = f.read()
    if len(d) < 512 or d[1] != 0x50:
        raise ValueError("not a C3D file (byte 2 is not 0x50)")
    pblock = d[0]
    pstart = (pblock - 1) * 512
    proc = _PROC.get(d[pstart + 3])
    if proc is None:
        raise ValueError(f"unknown C3D processor type {d[pstart + 3]}")
    buf = _C3DBytes(d, proc)
    npts = int(buf.i16(2, unsigned=True)[0])
    n_analog = int(buf.i16(4, unsigned=True)[0])
    first = int(buf.i16(6, unsigned=True)[0])
    last = int(buf.i16(8, unsigned=True)[0])
    scale = float(buf.f32(12)[0])
    dstart = int(buf.i16(16, unsigned=True)[0])
    hrate = float(buf.f32(20)[0])
    params = _c3d_params(buf, pstart)
    used = _scalar(params.get(("POINT", "USED")))
    if used is not None and used < 0:
        used += 65536
    if used is not None and used != npts:
        npts = int(used)
    prate = _scalar(params.get(("POINT", "RATE")))
    rate, rsrc = (float(prate), "POINT:RATE") if prate and prate > 0 else (hrate, "header")
    pscale = _scalar(params.get(("POINT", "SCALE")))
    if pscale is not None and pscale != 0:
        scale = float(pscale)
    pds = _scalar(params.get(("POINT", "DATA_START")))
    if pds:
        dstart = int(pds) if pds > 0 else int(pds) + 65536
    labels = []
    for key in ["LABELS"] + [f"LABELS{i}" for i in range(2, 100)]:
        v = params.get(("POINT", key))
        if v is None:
            if key != "LABELS":
                break
            continue
        labels += [v] if isinstance(v, str) else list(v)
    labels = [x.strip("\x00 ") for x in labels]
    labels = labels[:npts] + [f"_unlabelled_{i}" for i in range(len(labels), npts)]
    units = params.get(("POINT", "UNITS"), "")
    units = units if isinstance(units, str) else (units[0] if units else "")
    nfr = last - first + 1
    pf = _scalar(params.get(("POINT", "FRAMES")))
    if pf is not None and pf < 0:
        pf += 65536
    if pf and pf > nfr:
        nfr = int(pf)
    trial = params.get(("TRIAL", "ACTUAL_END_FIELD"))
    if trial is not None and np.asarray(trial).size == 2:
        a = np.asarray(trial).astype(np.int64) & 0xFFFF
        end = int(a[0] + a[1] * 65536)
        ts = params.get(("TRIAL", "ACTUAL_START_FIELD"))
        if ts is not None and np.asarray(ts).size == 2:
            b = np.asarray(ts).astype(np.int64) & 0xFFFF
            start_f = int(b[0] + b[1] * 65536)
            if end - start_f + 1 > nfr:
                nfr = end - start_f + 1
    is_float = scale < 0
    width = 4 if is_float else 2
    per_frame = (4 * npts + n_analog) * width
    off0 = (dstart - 1) * 512
    avail = (len(d) - off0) // per_frame if per_frame else 0
    short = max(0, nfr - avail)
    nfr = min(nfr, avail)
    out = {"labels": labels, "units": str(units).strip("\x00 "), "rate": rate, "rate_source": rsrc,
           "header_rate": hrate, "n_points": npts, "n_frames": int(nfr), "first_frame": first,
           "processor": proc, "storage": "float" if is_float else "int", "frames_short": int(short),
           "params": params}
    if header_only or npts == 0:
        if not header_only:
            out["points"] = np.zeros((nfr, 0, 3))
        return out
    block = d[off0:off0 + nfr * per_frame]
    if is_float:
        if proc == "dec":
            vals = _dec_floats(block)
        else:
            vals = np.frombuffer(block, dtype=np.dtype(buf.ie + "f4")).astype(float)
        vals = vals.reshape(nfr, 4 * npts + n_analog)[:, :4 * npts].reshape(nfr, npts, 4)
        xyz = vals[..., :3].copy()
        resid = vals[..., 3]
    else:
        vals = np.frombuffer(block, dtype=np.dtype(buf.ie + "i2")).astype(float)
        vals = vals.reshape(nfr, 4 * npts + n_analog)[:, :4 * npts].reshape(nfr, npts, 4)
        xyz = vals[..., :3] * abs(scale)
        resid = vals[..., 3]
    bad = (resid < 0) | np.all(xyz == 0.0, axis=-1) | ~np.isfinite(xyz).all(axis=-1)
    xyz[bad] = np.nan
    out["points"] = xyz
    return out


# ---------------------------------------------------------------- BVH
def read_bvh(path_or_text):
    """Parse a BVH file. Returns a dict: names, parents, offsets (J, 3), channels (list of
    lists), frame_time, rate, motion (T, C) float."""
    if isinstance(path_or_text, str) and "\n" not in path_or_text and os.path.exists(path_or_text):
        with open(path_or_text, encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        text = path_or_text
    head, sep, motion = text.partition("MOTION")
    if not sep:
        raise ValueError("no MOTION section")
    toks = head.split()
    names, parents, offsets, channels = [], [], [], []
    stack, i, last = [], 0, None
    while i < len(toks):
        t = toks[i]
        if t in ("ROOT", "JOINT"):
            names.append(toks[i + 1])
            parents.append(stack[-1] if stack else -1)
            offsets.append([0.0, 0.0, 0.0])
            channels.append([])
            last = len(names) - 1
            i += 2
        elif t == "End":
            names.append(f"{names[stack[-1]]}_End")    # End Site: named after its parent joint
            parents.append(stack[-1])
            offsets.append([0.0, 0.0, 0.0])
            channels.append([])
            last = len(names) - 1
            i += 2
        elif t == "{":
            stack.append(last)
            i += 1
        elif t == "}":
            stack.pop()
            i += 1
        elif t == "OFFSET":
            offsets[last] = [float(x) for x in toks[i + 1:i + 4]]
            i += 4
        elif t == "CHANNELS":
            n = int(toks[i + 1])
            channels[last] = toks[i + 2:i + 2 + n]
            i += 2 + n
        else:
            i += 1
    lines = motion.strip().splitlines()
    nfr, ft, start = None, None, 0
    for k, ln in enumerate(lines[:4]):
        if ln.strip().lower().startswith("frames:"):
            nfr = int(ln.split(":")[1])
        elif ln.strip().lower().startswith("frame time:"):
            ft = float(ln.split(":")[1])
            start = k + 1
    if ft is None or ft <= 0:
        raise ValueError("no positive Frame Time line")
    rows = "\n".join(lines[start:])
    data = np.loadtxt(io.StringIO(rows), dtype=float, ndmin=2) if rows.strip() else np.zeros((0, 0))
    nch = sum(len(c) for c in channels)
    if data.size and data.shape[1] != nch:
        raise ValueError(f"motion rows have {data.shape[1]} values, the hierarchy {nch} channels")
    return {"names": names, "parents": parents, "offsets": np.array(offsets, dtype=float),
            "channels": channels, "frame_time": ft, "rate": 1.0 / ft,
            "frames_declared": nfr, "motion": data}


def _rot(axis, deg):
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    T = a.shape[0]
    R = np.zeros((T, 3, 3))
    if axis == "X":
        R[:, 0, 0] = 1; R[:, 1, 1] = c; R[:, 1, 2] = -s; R[:, 2, 1] = s; R[:, 2, 2] = c
    elif axis == "Y":
        R[:, 1, 1] = 1; R[:, 0, 0] = c; R[:, 0, 2] = s; R[:, 2, 0] = -s; R[:, 2, 2] = c
    else:
        R[:, 2, 2] = 1; R[:, 0, 0] = c; R[:, 0, 1] = -s; R[:, 1, 0] = s; R[:, 1, 1] = c
    return R


def bvh_positions(bvh):
    """World positions (T, J, 3) of every joint and End Site (named <parent>_End), and their names.
    A joint's local transform is its OFFSET (plus its position channels, when it has any),
    then its rotation channels composed in the order listed (R = R1 @ R2 @ R3)."""
    mot = bvh["motion"]
    T = mot.shape[0]
    J = len(bvh["names"])
    gR = [None] * J
    gp = [None] * J
    col = 0
    for j in range(J):
        chans = bvh["channels"][j]
        t = np.tile(bvh["offsets"][j], (T, 1))
        R = np.tile(np.eye(3), (T, 1, 1))
        for c in chans:
            v = mot[:, col]
            col += 1
            if c.endswith("position"):
                t[:, "XYZ".index(c[0])] += v
            elif c.endswith("rotation"):
                R = R @ _rot(c[0], v)
        p = bvh["parents"][j]
        if p < 0:
            gR[j], gp[j] = R, t
        else:
            gp[j] = gp[p] + np.einsum("tij,tj->ti", gR[p], t)
            gR[j] = gR[p] @ R
    return np.stack(gp, axis=1), list(bvh["names"])


# ---------------------------------------------------------------- Qualisys TSV
def read_qualisys_tsv(path, header_only=False):
    """Read a Qualisys Track Manager 3D TSV export. Returns a dict: rate (the FREQUENCY line),
    labels, n_frames (NO_OF_FRAMES), header (dict of the header lines), points (T, M, 3) in the
    file's unit (millimetres in QTM exports), NaN where a marker is missing (0 0 0 or empty)."""
    header, n_head = {}, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in f:
            parts = ln.rstrip("\r\n").split("\t")
            key = parts[0].strip()
            if re.fullmatch(r"[A-Z][A-Z_0-9]*(--)?", key):
                header[key] = parts[1:]
                n_head += 1
                continue
            break
    if "FREQUENCY" not in header or "MARKER_NAMES" not in header:
        raise ValueError("not a QTM 3D TSV (no FREQUENCY or MARKER_NAMES line)")
    rate = float(header["FREQUENCY"][0])
    labels = [x.strip() for x in header["MARKER_NAMES"] if x.strip()]
    nfr = int(header["NO_OF_FRAMES"][0]) if "NO_OF_FRAMES" in header else None
    out = {"rate": rate, "labels": labels, "n_frames": nfr, "header": header}
    if header_only:
        return out
    import pandas as pd
    df = pd.read_csv(path, sep="\t", skiprows=n_head, header=None, dtype=str, engine="c")
    first = df.iloc[0].astype(str).str.strip().tolist()
    if first and first[0].lower() == "frame":          # column-name line of newer QTM exports
        df = df.iloc[1:]
        ncol0 = 2 if len(first) > 1 and first[1].lower() == "time" else 1
    else:
        ncol0 = 0
    vals = df.iloc[:, ncol0:ncol0 + 3 * len(labels)].apply(pd.to_numeric, errors="coerce").to_numpy(float, copy=True)
    if vals.shape[1] != 3 * len(labels):
        raise ValueError(f"{vals.shape[1]} coordinate columns for {len(labels)} markers")
    pts = vals.reshape(vals.shape[0], len(labels), 3)
    pts[np.all(pts == 0.0, axis=-1)] = np.nan
    out["points"] = pts
    if nfr is None:
        out["n_frames"] = pts.shape[0]
    return out


# ---------------------------------------------------------------- D-Flow mocap text
def read_dflow_mocap_txt(path, markers):
    """Read the TimeStamp and the .PosX/.PosY/.PosZ columns of `markers` from a D-Flow mocap
    text export. Returns a dict: time (T,), points (T, M, 3) in the file's unit (metres in
    D-Flow), NaN where missing (all three exactly 0), rate (1 / median step), step_min,
    step_max, labels_present (the markers found), columns (every column name)."""
    import pandas as pd
    with open(path, encoding="utf-8", errors="replace") as f:
        cols = f.readline().rstrip("\r\n").split("\t")
    want = ["TimeStamp"]
    present = [m for m in markers if all(f"{m}.Pos{a}" in cols for a in "XYZ")]
    for m in present:
        want += [f"{m}.Pos{a}" for a in "XYZ"]
    df = pd.read_csv(path, sep="\t", usecols=want, dtype=float, engine="c")
    t = df["TimeStamp"].to_numpy(float, copy=True)
    pts = np.full((len(t), len(markers), 3), np.nan)
    for k, m in enumerate(markers):
        if m in present:
            pts[:, k, :] = df[[f"{m}.Pos{a}" for a in "XYZ"]].to_numpy(float, copy=True)
    pts[np.all(pts == 0.0, axis=-1)] = np.nan
    dt = np.diff(t)
    dt = dt[np.isfinite(dt) & (dt > 0)]
    med = float(np.median(dt)) if dt.size else float("nan")
    return {"time": t, "points": pts, "rate": 1.0 / med if dt.size else None,
            "step_min": float(dt.min()) if dt.size else None,
            "step_max": float(dt.max()) if dt.size else None,
            "labels_present": present, "columns": cols}
