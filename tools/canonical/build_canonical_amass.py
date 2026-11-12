"""Ingest AMASS into the canonical skeleton (healthy 3D base).

Computes the 3D positions of the 22 SMPL body joints of each motion by forward kinematics of
the AMASS SMPL+H model in body_models/smplh (the joint path of smplx.lbs: shape blend, joint
regressor, rigid transform chain; no mesh), converts AMASS z-up -> y-up (to match the other 3D
sources), maps SMPL 22 -> canonical 15, normalizes (root-center on pelvis, scale by the median
pelvis-to-neck length) and writes one moveatlas-record/1 shard per sub-dataset, records in the
order of the archive members. Native fps is kept per sample (no decimation): the SMPL+H release
files (*_poses.npz) state it as mocap_framerate, the MoSh++ stage-II files (*_stageii.npz) as
mocap_frame_rate; builds before 2026-10-05 read only the first key, so the 2,914 stage-II records
of GRAB, SOMA, CNRS and WEIZMANN were written with fps None (fill them with --fill-fps).

CPU only. The first build (July 2026, Mac) ran through human_body_prior on Apple MPS until MPS
hung; the script was then forced to CPU and resumed, and the resume kept the shards already
written: ACCAD, BMLhandball and BMLmovi, the first three archives in sorted order. In those
three shards every forward pass of more than 65,536 joint rotations (52 per frame, so more
than 1,260 frames) came back as a skeleton whose bones change length: the 404 records of
1,261 frames or more. They were rebuilt with --only (CHANGELOG). Every record is now checked
for rigid bones before it is written, and a failed check stops the run.

Needs torch and numpy (no human_body_prior, no smplx). Run from the repository root with
PYTHONDONTWRITEBYTECODE=1:
    python build_canonical_amass.py
        build every archive that has no shard yet (resumable per shard)
    python build_canonical_amass.py --only ACCAD BMLhandball BMLmovi
        rebuild existing shards in place: same records, same order, same metadata; a record
        whose recomputed coords differ from the stored ones by more than 1e-4 is replaced
        (coords and scale), the others are kept as stored; the replaced records are listed in
        _paris_logs/amass_rebuild_<date>.csv; the manifest is not rewritten. A stored record
        whose fps is None while its file states a rate stops the run, unless:
    python build_canonical_amass.py --only CNRS WEIZMANN --fill-fps
        as --only, and such a record takes the rate its file states (every other field is
        checked as before); the empty fps cells of its rows in the AMASS manifest and in
        datasets/_canonical_manifest.csv are filled (each row seen once, with the record's
        n_frames; the line ending is kept and no other line changes), shard by shard: the
        manifest texts are checked before the shard is saved and written after it (each
        through a .part file and os.replace). A run stopped between a saved shard and its
        manifests is resumed by the same command (with --fill-fps): a record that already
        holds its stated rate fills an fps cell of its amass row that is still empty, under
        the same n_frames check, and leaves a filled cell as it is.
"""
import argparse
import csv
import datetime as dt
import glob
import io
import os
import sys
import tarfile

import numpy as np
import torch

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
from moveatlas import records  # noqa: E402

RAW = os.path.join(REPO, "datasets/socle/amass/raw")
PROC = os.path.join(REPO, "datasets/socle/amass/processed")
OUT = os.path.join(PROC, "canonical")
MANIFEST = os.path.join(PROC, "canonical_manifest.csv")
POOLED = os.path.join(REPO, "datasets/_canonical_manifest.csv")
CHUNK = 4000                       # frames per forward pass (CPU: no batch limit)
RIGID_TOL = 1e-4                   # largest relative spread of a bone length over frames
KEEP_TOL = 1e-4                    # --only: a stored record within this of the recomputation is kept

# canonical 15 <- SMPL 22 joint indices (SMPL order verified)
SEL = [0, 12, 15, 16, 17, 18, 19, 20, 21, 1, 2, 4, 5, 7, 8]
ROOT_I, NECK_I = 0, 1              # positions of pelvis, neck in canonical order
META_KEYS = ("source", "subject_ns", "take", "dim", "fps", "n_frames", "modality")
# the capture rate of a motion file: SMPL+H release files (*_poses.npz), MoSh++ stage-II files
# (*_stageii.npz)
FPS_KEYS = ("mocap_framerate", "mocap_frame_rate")


class NotRigid(RuntimeError):
    """A skeleton whose bones change length over frames: never written, the run stops."""


def load_models():
    models = {}
    for g in ("male", "female", "neutral"):
        m = np.load(os.path.join(REPO, f"body_models/smplh/{g}/model.npz"), encoding="latin1")
        models[g] = {
            "v_template": torch.tensor(m["v_template"][None], dtype=torch.float32),
            "shapedirs": torch.tensor(m["shapedirs"][:, :, :16], dtype=torch.float32),
            "J_regressor": torch.tensor(np.asarray(m["J_regressor"]), dtype=torch.float32),
            "parents": torch.tensor(m["kintree_table"][0].astype(np.int64)),
        }
    return models


def rodrigues(v):
    """smplx.lbs.batch_rodrigues: (N, 3) axis-angle -> (N, 3, 3) rotation matrices."""
    angle = torch.norm(v + 1e-8, dim=1, keepdim=True)
    d = v / angle
    cos = torch.cos(angle)[:, :, None]
    sin = torch.sin(angle)[:, :, None]
    rx, ry, rz = torch.split(d, 1, dim=1)
    z = torch.zeros_like(rx)
    K = torch.cat([z, -rz, ry, rz, z, -rx, -ry, rx, z], dim=1).view(-1, 3, 3)
    return torch.eye(3, dtype=v.dtype)[None] + sin * K + (1 - cos) * torch.bmm(K, K)


def posed_joints(m, pose, betas, trans):
    """The joint path of smplx.lbs for the 52 SMPL+H joints, plus the translation:
    pose (B, 156) axis-angle, betas (B, 16), trans (B, 3) -> (B, 52, 3) in the AMASS world."""
    B = pose.shape[0]
    v_shaped = m["v_template"] + torch.einsum("bl,mkl->bmk", betas, m["shapedirs"])
    J = torch.einsum("bik,ji->bjk", v_shaped, m["J_regressor"])
    R = rodrigues(pose.reshape(-1, 3)).view(B, -1, 3, 3)
    par = m["parents"]
    rel = J.clone()
    rel[:, 1:] -= J[:, par[1:]]
    T = torch.zeros(B, J.shape[1], 4, 4, dtype=J.dtype)
    T[..., :3, :3] = R
    T[..., :3, 3] = rel
    T[..., 3, 3] = 1
    chain = [T[:, 0]]
    for i in range(1, J.shape[1]):
        chain.append(torch.matmul(chain[int(par[i])], T[:, i]))
    return torch.stack(chain, 1)[:, :, :3, 3] + trans[:, None]


def check_rigid(J, parents, what):
    """J (T, 22, 3) m: refuse a skeleton whose bones change length over frames (forward
    kinematics keeps every bone length; float32 leaves about 1e-6)."""
    d = np.linalg.norm(J[:, 1:22] - J[:, parents[1:22]], axis=-1)
    spread = float(((d.max(0) - d.min(0)) / np.maximum(d.mean(0), 1e-9)).max())
    if spread > RIGID_TOL:
        raise NotRigid(f"{what}: a bone length varies by {spread:.3g} over frames")


def frame_rate(npz):
    """The rate a motion file states (the first of FPS_KEYS it carries), or None."""
    for k in FPS_KEYS:
        if k in npz:
            return float(npz[k])
    return None


def joints_for(npz, models, what=""):
    poses = npz["poses"]
    if poses.ndim != 2 or poses.shape[1] < 156:
        return None, None
    T = poses.shape[0]
    g = npz["gender"].item()
    g = g.decode() if isinstance(g, bytes) else str(g)
    g = g if g in models else "neutral"
    m = models[g]
    betas = np.zeros((16,), np.float32)
    b = npz["betas"][:16]
    betas[:len(b)] = b
    trans = npz["trans"].astype(np.float32)
    fps = frame_rate(npz)
    out = []
    with torch.no_grad():
        for s in range(0, T, CHUNK):
            e = min(s + CHUNK, T)
            p = torch.tensor(poses[s:e, :156], dtype=torch.float32)
            tr = torch.tensor(trans[s:e], dtype=torch.float32)
            be = torch.tensor(betas).unsqueeze(0).repeat(e - s, 1)
            out.append(posed_joints(m, p, be, tr)[:, :22].numpy())
    J = np.concatenate(out, 0)                             # (T,22,3) z-up
    check_rigid(J, m["parents"].numpy(), what)
    J = np.stack([J[..., 0], J[..., 2], -J[..., 1]], -1)   # z-up -> y-up
    return J, fps


def normalize(canon):
    c = canon.astype(float) - canon[:, ROOT_I:ROOT_I + 1, :]
    torso = np.linalg.norm(c[:, NECK_I] - c[:, ROOT_I], axis=-1)
    good = torso[np.isfinite(torso) & (torso > 1e-6)]
    scale = float(np.median(good)) if good.size else 1.0
    return (c / scale).astype(np.float32), scale


def make_record(ns, take, canon, fps):
    coords, scale = normalize(canon)
    return {"coords": coords, "coord_mask": np.array([True, True, True]),
            "joint_mask": np.ones(15, bool), "valid_mask": np.ones(coords.shape[:2], bool),
            "dim": 3, "fps": fps, "modality": "3d_meter", "source": "amass",
            "subject_ns": ns, "take": take, "n_frames": int(coords.shape[0]),
            "scale": scale}


def ns_of(sub, member):
    """subject_ns of an archive member (tar names always use '/')."""
    return f"amass:{sub}:{os.path.dirname(member).replace('/', '_')}"


def motions(tb):
    """(member name, loaded npz) for every motion file of an archive, in archive order, read
    in memory (nothing is extracted to disk)."""
    with tarfile.open(tb, "r:bz2") as t:
        for info in t:
            b = os.path.basename(info.name)
            if not info.isfile() or not b.endswith(".npz") or b.startswith("._") \
                    or "shape" in b.lower() or "neutral" in b.lower():
                continue
            yield info.name, np.load(io.BytesIO(t.extractfile(info).read()), allow_pickle=True)


def write_manifest():
    """The full manifest, rebuilt from every shard on disk (sorted shards, record order)."""
    rows = []
    for sp in sorted(glob.glob(os.path.join(OUT, "amass_*.npz"))):
        if os.path.basename(sp).startswith("._"):
            continue
        for r in records.iter_load(sp):
            rows.append([r["source"], r["subject_ns"], r["take"], 3,
                         r["fps"] or "", r["n_frames"], "3d_meter"])
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "subject_ns", "take", "dim", "fps", "n_frames", "modality"])
        w.writerows(rows)
    return len(rows)


def build_all(models):
    os.makedirs(OUT, exist_ok=True)
    total, bad = 0, 0
    for tb in sorted(glob.glob(os.path.join(RAW, "*.tar.bz2"))):
        sub = os.path.basename(tb)[:-len(".tar.bz2")]
        path = os.path.join(OUT, f"amass_{sub}.npz")
        if os.path.exists(path):
            print(f"  {sub}: shard exists, skip (resume; rebuild it with --only {sub})", flush=True)
            continue
        shard = []
        for name, npz in motions(tb):
            if "poses" not in npz:
                continue
            try:
                J, fps = joints_for(npz, models, name)
            except NotRigid:
                raise                      # a non-rigid skeleton stops the run
            except Exception:
                bad += 1
                continue
            if J is None:
                bad += 1
                continue
            shard.append(make_record(ns_of(sub, name), name, J[:, SEL, :], fps))
        if shard:
            records.save(path, shard)
        total += len(shard)
        print(f"  {sub}: {len(shard)} motions (running total {total})", flush=True)
    n = write_manifest()
    print(f"\nAMASS canonical: {n} motions in the manifest, {bad} bad this run")


def fill_manifest_fps(path, fills, pending=None):
    """The text of the manifest at `path` with the empty fps cell of the amass row of each
    (subject_ns, take) of `fills` ({key: (n_frames, fps)}) set to str(fps), or None when no line
    changes. Refused (SystemExit, nothing returned) unless each key of `fills` has exactly one
    amass row, with an empty fps cell and the record's n_frames. `pending` (same form: records
    that already hold their stated rate) fills only an amass row whose fps cell is still empty,
    under the same row and n_frames checks, and leaves its filled rows as they are: the catch-up
    of a run stopped between a saved shard and its manifests. The csv round trip must keep the
    line count and the line ending (read from the first line) and change exactly the filled
    lines."""
    pending = pending or {}
    with open(path, encoding="utf-8", newline="") as f:
        txt = f.read()
    eol = "\r\n" if txt.split("\n", 1)[0].endswith("\r") else "\n"
    rows = list(csv.reader(io.StringIO(txt, newline="")))
    head = rows[0] if rows else []
    cols = ("source", "subject_ns", "take", "fps", "n_frames")
    if any(c not in head for c in cols):
        raise SystemExit(f"{path}: the columns {cols} are not all in the header")
    ci = {c: head.index(c) for c in cols}
    seen, caught = set(), set()
    for r in rows[1:]:
        if not r or r[ci["source"]] != "amass":
            continue
        key = (r[ci["subject_ns"]], r[ci["take"]])
        if key in fills:
            n, fps = fills[key]
            if key in seen:
                raise SystemExit(f"{path}: {key} has two rows")
            if r[ci["fps"]] != "":
                raise SystemExit(f"{path}: {key} has fps {r[ci['fps']]!r}, not empty")
            done = seen
        elif key in pending and r[ci["fps"]] == "":
            n, fps = pending[key]
            if key in caught:
                raise SystemExit(f"{path}: {key} has two rows")
            done = caught
        else:
            continue
        if int(r[ci["n_frames"]]) != n:
            raise SystemExit(f"{path}: {key} has n_frames {r[ci['n_frames']]}, the record {n}")
        done.add(key)
        r[ci["fps"]] = str(fps)
    if seen != set(fills):
        raise SystemExit(f"{path}: {len(set(fills) - seen)} filled records have no row")
    if not seen and not caught:
        return None
    buf = io.StringIO(newline="")
    csv.writer(buf, lineterminator=eol).writerows(rows)
    out = buf.getvalue()
    a, b = txt.split(eol), out.split(eol)
    if len(a) != len(b) or sum(x != y for x, y in zip(a, b)) != len(seen) + len(caught):
        raise SystemExit(f"{path}: the csv round trip would change other lines")
    return out


def rebuild(subsets, models, fill_fps=False):
    stamp = dt.date.today().isoformat()
    log = os.path.join(REPO, "_paris_logs", f"amass_rebuild_{stamp}.csv")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "a", newline="", encoding="utf-8") as lf:
        lw = csv.writer(lf, lineterminator="\n")
        if lf.tell() == 0:
            lw.writerow(["subset", "record", "take", "n_frames", "max_abs_change", "old_scale", "new_scale"])
        for sub in subsets:
            path = os.path.join(OUT, f"amass_{sub}.npz")
            old = records.load(path)
            index = {r["take"]: i for i, r in enumerate(old)}
            if len(index) != len(old):
                raise SystemExit(f"{sub}: duplicate takes in {path}")
            new, seen, rows, fills, pending = list(old), set(), [], {}, {}
            for name, npz in motions(os.path.join(RAW, f"{sub}.tar.bz2")):
                i = index.get(name)
                if i is None:
                    continue
                J, fps = joints_for(npz, models, name)
                rec = make_record(ns_of(sub, name), name, J[:, SEL, :], fps)
                fill = fill_fps and old[i]["fps"] is None and rec["fps"] is not None
                if fill and not (np.isfinite(rec["fps"]) and rec["fps"] > 0):
                    raise SystemExit(f"{sub} {name}: the file states fps {rec['fps']!r}")
                for k in META_KEYS:
                    if rec[k] != old[i][k] and not (k == "fps" and fill):
                        hint = " (a rate the stored record lacks: --fill-fps)" \
                            if k == "fps" and old[i][k] is None else ""
                        raise SystemExit(f"{sub} {name}: {k} {rec[k]!r} differs from the stored {old[i][k]!r}{hint}")
                seen.add(i)
                change = float(np.abs(rec["coords"].astype(np.float64) - old[i]["coords"]).max())
                if change > KEEP_TOL:
                    new[i] = rec
                    rows.append([sub, f"r{i:06d}", name, rec["n_frames"], f"{change:.6g}",
                                 old[i]["scale"], rec["scale"]])
                elif fill:
                    new[i] = dict(old[i], fps=rec["fps"])
                if fill:
                    fills[(old[i]["subject_ns"], name)] = (old[i]["n_frames"], rec["fps"])
                elif fill_fps and old[i]["fps"] is not None:
                    # holds its stated rate (checked above): a release file, or a record filled
                    # by an earlier run that stopped before its manifests were written
                    pending[(old[i]["subject_ns"], name)] = (old[i]["n_frames"], old[i]["fps"])
            if len(seen) != len(old):
                raise SystemExit(f"{sub}: {len(old) - len(seen)} stored takes are not in the archive")
            # the manifest texts are checked before the shard is written, and written after it
            texts = []
            if fills or pending:
                for m in (MANIFEST, POOLED):
                    txt = fill_manifest_fps(m, fills, pending)
                    if txt is not None:
                        texts.append((m, txt))
            records.save(path, new)            # atomic: .part then os.replace
            lw.writerows(rows)                 # logged only once the shard is saved
            lf.flush()
            for m, txt in texts:               # atomic too: a stop leaves a whole old or new file
                with open(m + ".part", "w", encoding="utf-8", newline="") as f:
                    f.write(txt)
                os.replace(m + ".part", m)
            filled = f", {len(fills)} frame rates filled, {len(texts)} manifests written" \
                if fill_fps else ""
            print(f"  {sub}: {len(rows)} of {len(old)} records replaced{filled}; log {log}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="+", metavar="SUBSET",
                    help="rebuild these existing shards in place (see the docstring)")
    ap.add_argument("--fill-fps", action="store_true",
                    help="with --only: a stored record without fps takes the rate its file "
                         "states, and its manifest rows are filled (see the docstring)")
    a = ap.parse_args()
    if a.fill_fps and not a.only:
        ap.error("--fill-fps needs --only")
    models = load_models()
    print("device: cpu", flush=True)
    if a.only:
        rebuild(a.only, models, fill_fps=a.fill_fps)
    else:
        build_all(models)


if __name__ == "__main__":
    main()
