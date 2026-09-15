# -*- coding: utf-8 -*-
"""stroke_gait_vancriekinge analog pass: EMG + ground-reaction forces.

Written to docs/INGEST_STROKE_ANALOGS_SCOPING.md (2026-09-02): three
analog regimes measured from the recorded labels of the pose pass.

EMG: named-muscle channels only. Alias table (side = leading L/R,
trailing digits = electrode variants on one muscle): ERS erector
spinae, RF rectus femoris, VL vastus lateralis, ST semitendinosus,
BF/BIF biceps femoris, TA/TIA tibialis anterior, GAS gastrocnemius
(head NOT specified by the labels, so the canonical name stays
'gastrocnemius'). Footswitch* rides as aux. Anonymous channels
(Voltage.NN, Raw.Pin NN, bare numbers) are REFUSED and audited, never
guessed. Units from ANALOG:UNITS: V -> mV (x1000); mV kept; anything
else stored with unit 'unknown' and flagged. Records go to
processed/canonical_emg/ per the build_canonical_emg layout, source id
stays stroke_gait_vancriekinge, subject_ns IDENTICAL to the pose pass
so multimodal pairing sees the same people.

FORCE: 4 plates x (F,M) at 1000 Hz, type-2 platforms, corners in the
lab frame. Plate-to-foot assignment is its own audited step: a plate
counts as struck when |Fz| exceeds 20 N for >= 0.2 s; the striking
foot is the ankle marker (LTIO/RTIO, lab mm, 100 Hz upsampled by
index) whose mean xy during the loaded window lies closest to the
plate center, accepted only within 500 mm AND 1.5x closer than the
other foot; anything else refuses that plate, and a trial with zero
cleanly assigned plates yields no force record (audited). The
canonical record is gaitndd-style totals-only: per-foot |Fz| sum of
assigned plates in N at native 1000 Hz, sensor_mask lights only the
'total' position. Full 24-channel plate arrays (Fx/Fy/Fz/Mx/My/Mz x4)
are preserved per trial under processed/aux_force/.

Usage: python ingest_stroke_gait_analogs.py [--repo PATH] [--limit N]
"""
import argparse
import csv
import os
import pickle
import re
import tempfile
import zipfile

import numpy as np

MUSCLES = {
    "ERS": "erector_spinae", "RF": "rectus_femoris",
    "VL": "vastus_lateralis", "ST": "semitendinosus",
    "BF": "biceps_femoris", "BIF": "biceps_femoris",
    "TA": "tibialis_anterior", "TIA": "tibialis_anterior",
    "GAS": "gastrocnemius",
}
PLATE_RE = re.compile(r"^[FM][xyz]([1-4])$")
FZ_THRESH_N = 20.0
FZ_MIN_S = 0.2
ASSIGN_MAX_MM = 500.0
ASSIGN_RATIO = 1.5


def sanitize(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(s))


def read_c3d_full(zf, name):
    import ezc3d
    with tempfile.NamedTemporaryFile(suffix=".c3d", delete=False) as t:
        t.write(zf.read(name))
        p = t.name
    try:
        c = ezc3d.c3d(p)
    finally:
        os.unlink(p)
    par = c["parameters"]
    pts_labels = [x.strip() for x in par["POINT"]["LABELS"]["value"]]
    pts_labels = [l.split(":", 1)[-1] for l in pts_labels]
    pts = np.transpose(c["data"]["points"][:3], (2, 1, 0)).astype(float)
    pts[pts == 0.0] = np.nan
    ana_labels = [x.strip() for x in par["ANALOG"]["LABELS"]["value"]] \
        if "ANALOG" in par else []
    ana_units = [x.strip() for x in par["ANALOG"].get(
        "UNITS", {}).get("value", [])] if "ANALOG" in par else []
    ana_rate = float(np.asarray(par["ANALOG"]["RATE"]["value"]).ravel()[0]) \
        if "ANALOG" in par else 0.0
    sig = c["data"]["analogs"][0].T if "ANALOG" in par else None  # (T, C)
    corners = None
    if "FORCE_PLATFORM" in par and "CORNERS" in par["FORCE_PLATFORM"]:
        arr = np.asarray(par["FORCE_PLATFORM"]["CORNERS"]["value"],
                         dtype=float)
        if arr.size:
            corners = arr.reshape(3, 4, -1)
    return pts_labels, pts, ana_labels, ana_units, ana_rate, sig, corners


def classify(label):
    """-> ('plate', k) | ('emg', side, muscle, electrode) |
    ('aux', name) | ('anonymous', label) | ('unrecognized', label)"""
    core = label.split(":", 1)[-1]
    core = core.split(".", 1)[-1] if "." in core else core
    core = core.strip()
    m = PLATE_RE.match(core)
    if m:
        return ("plate", int(m.group(1)), label)
    if core.lower().startswith("footswitch"):
        return ("aux", core, label)
    if re.fullmatch(r"\d+", core) or "pin" in core.lower():
        return ("anonymous", core, label)
    m = re.fullmatch(r"([LR])([A-Za-z]+?)(\d*)", core)
    if m:
        side, code, elec = m.group(1), m.group(2).upper(), m.group(3)
        if code in MUSCLES:
            return ("emg", side, MUSCLES[code], elec, label)
    return ("unrecognized", core, label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get(
        "MOVEATLAS_REPO", os.environ.get(
            "KINEFM_REPO", os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    base = os.path.join(args.repo, "datasets", "pose",
                        "stroke_gait_vancriekinge")
    rawd = os.path.join(base, "raw")
    emg_dir = os.path.join(base, "processed", "canonical_emg")
    auxf_dir = os.path.join(base, "processed", "aux_force")
    os.makedirs(emg_dir, exist_ok=True)
    os.makedirs(auxf_dir, exist_ok=True)

    emg_manifest, force_recs, force_manifest, audit = [], [], [], []
    stats = {"emg_records": 0, "anon_refused_trials": 0,
             "force_records": 0, "force_refused": 0, "read_fail": 0}
    zips = sorted(f for f in os.listdir(rawd)
                  if f.lower().endswith(".zip") and not f.startswith("._")
                  and "timenormalized" not in f.lower())
    for zn in zips:
        z = zipfile.ZipFile(os.path.join(rawd, zn))
        low = zn.lower()
        if "healthy" in low or "ablebodied" in low:
            group = "able_bodied"
        elif "stroke" in low:
            group = "stroke"
        else:
            continue
        c3ds = sorted(n for n in z.namelist()
                      if n.lower().endswith(".c3d")
                      and "cal" not in os.path.basename(n).lower())
        if args.limit:
            c3ds = c3ds[:args.limit]
        print(f"{zn}: {len(c3ds)} C3D ({group})", flush=True)
        for name in c3ds:
            parts = name.split("/")
            subj_dir = parts[-2] if len(parts) >= 2 else ""
            m = re.search(r"(\d+)", subj_dir)
            if not m:
                continue
            ns = f"stroke_gait:{group}:S{int(m.group(1)):03d}"
            trial = re.sub(r"[^A-Za-z0-9]+", "_",
                           os.path.basename(name)[:-4]).strip("_")
            task = f"gait_{trial}"
            try:
                (pl, pts, al, au, arate, sig,
                 corners) = read_c3d_full(z, name)
            except Exception as e:
                stats["read_fail"] += 1
                audit.append([zn, name, ns, "READ FAIL", str(e)[:120]])
                continue
            if sig is None or not al:
                audit.append([zn, name, ns, "no analogs", ""])
                continue
            units = au + [""] * (len(al) - len(au))

            plates, emg_idx, aux_idx, anon, unrec = {}, [], [], [], []
            for ci, lab in enumerate(al):
                k = classify(lab)
                if k[0] == "plate":
                    plates.setdefault(k[1], {})[
                        k[2].split(":", 1)[-1].split(".")[-1][:2]] = ci
                elif k[0] == "emg":
                    emg_idx.append((ci, k[1], k[2], k[3]))
                elif k[0] == "aux":
                    aux_idx.append((ci, k[1]))
                elif k[0] == "anonymous":
                    anon.append(k[1])
                else:
                    unrec.append(k[1])

            # ------------------------------------------------ EMG record
            notes = []
            if emg_idx:
                cols, chans = [], []
                for ci, side, muscle, elec in emg_idx:
                    u = units[ci]
                    x = sig[:, ci].astype(np.float32)
                    if u.upper() == "V":
                        x = x * 1e3
                        unit_out = "mV"
                    elif u.lower() == "mv":
                        unit_out = "mV"
                    else:
                        unit_out = "unknown"
                        notes.append(f"{al[ci]}: unit {u!r} kept, "
                                     "flagged unknown")
                    cols.append(x)
                    ch = {"kind": "emg", "muscle": muscle, "side": side,
                          "resolved": True}
                    if elec:
                        ch["electrode"] = elec
                    chans.append((ch, unit_out))
                unit_set = {u for _, u in chans}
                unit_field = "mV" if unit_set == {"mV"} else "unknown"
                stack_ = np.stack(cols, axis=1)
                p99 = float(np.percentile(np.abs(stack_), 99))
                if not (1e-4 <= p99 <= 5.0):
                    notes.append(
                        f"AMPLITUDE FLAG: p99 {p99:.3g} mV vs a surface"
                        "-EMG range of ~0.0001-5 mV; the declared V is "
                        "likely amplifier-output volts (gain "
                        "undeclared) or mislabeled mV - both imply an "
                        "electrode-referred ~x1000 smaller signal. NOT "
                        "rescaled; electrode-referred scale UNRESOLVED")
                rec = {"signal": stack_,
                       "channels": [c for c, _ in chans],
                       "fps": arate, "unit": unit_field,
                       "unit_scale": 1.0, "signal_kind": "raw",
                       "filters": None, "subject_ns": ns, "task": task,
                       "source": "stroke_gait_vancriekinge",
                       "n_frames": int(sig.shape[0]), "label": None,
                       "notes": "; ".join(n for n in notes
                                          if "AMPLITUDE" in n) or None}
                if aux_idx:
                    rec["aux_streams"] = [
                        {"label": al[ci], "kind": "footswitch",
                         "unit": units[ci] or "unknown", "fps": arate,
                         "signal": sig[:, ci].astype(np.float32)}
                        for ci, _ in aux_idx]
                rid = sanitize(f"stroke_gait_vancriekinge__{ns}__{task}")
                with open(os.path.join(emg_dir, rid + ".pkl"),
                          "wb") as f:
                    pickle.dump(rec, f)
                rel = ("datasets/pose/stroke_gait_vancriekinge/"
                       f"processed/canonical_emg/{rid}.pkl")
                muscles = len({(c['muscle'], c['side'])
                               for c, _ in chans})
                emg_manifest.append(
                    ["stroke_gait_vancriekinge", ns, task, arate,
                     rec["n_frames"], len(chans),
                     "emg" + ("|aux" if aux_idx else ""), rel])
                stats["emg_records"] += 1
            if anon:
                stats["anon_refused_trials"] += 1
                notes.append(f"REFUSED {len(anon)} anonymous channels")
            if unrec:
                notes.append("unrecognized: "
                             + "|".join(sorted(set(unrec))[:6]))

            # ---------------------------------------------- force record
            fnote = ""
            if plates and corners is not None and \
                    all("Fz" in d for d in plates.values()):
                try:
                    la = pl.index("LTIO")
                    ra = pl.index("RTIO")
                except ValueError:
                    la = ra = None
                if la is not None:
                    Tana = sig.shape[0]
                    Tpts = pts.shape[0]
                    ratio = max(1, round(arate / 100.0))
                    centers = corners.mean(axis=1).T  # (nplate, 3)
                    footL = np.zeros(Tana, np.float32)
                    footR = np.zeros(Tana, np.float32)
                    gotL = gotR = False
                    refused_plates = []
                    for k, d in sorted(plates.items()):
                        fz = np.abs(sig[:, d["Fz"]])
                        loaded = fz > FZ_THRESH_N
                        if loaded.sum() < FZ_MIN_S * arate:
                            continue
                        w = np.where(loaded)[0]
                        pidx = np.clip(w // ratio, 0, Tpts - 1)
                        cxy = centers[k - 1][:2]
                        dl = np.nanmean(np.linalg.norm(
                            pts[pidx, la, :2] - cxy, axis=1))
                        dr = np.nanmean(np.linalg.norm(
                            pts[pidx, ra, :2] - cxy, axis=1))
                        if np.isnan(dl) or np.isnan(dr):
                            refused_plates.append(f"P{k}:no-marker")
                            continue
                        near, far, tgtL = (dl, dr, True) if dl < dr \
                            else (dr, dl, False)
                        if near > ASSIGN_MAX_MM or \
                                far < ASSIGN_RATIO * near:
                            refused_plates.append(
                                f"P{k}:ambiguous({near:.0f}/{far:.0f})")
                            continue
                        if tgtL:
                            footL += fz.astype(np.float32)
                            gotL = True
                        else:
                            footR += fz.astype(np.float32)
                            gotR = True
                    if gotL or gotR:
                        NPOS = 9
                        force = np.zeros((Tana, 2, NPOS), np.float32)
                        force[:, 0, 8] = footL
                        force[:, 1, 8] = footR
                        mask = np.zeros((2, NPOS), bool)
                        mask[0, 8] = gotL
                        mask[1, 8] = gotR
                        force_recs.append(
                            {"force": force, "sensor_mask": mask,
                             "fps": arate, "subject_ns": ns,
                             "task": task,
                             "source": "stroke_gait_vancriekinge",
                             "n_frames": int(Tana)})
                        force_manifest.append(
                            ["stroke_gait_vancriekinge", ns, task,
                             arate, int(Tana)])
                        stats["force_records"] += 1
                        fnote = (f"force L={gotL} R={gotR}"
                                 + (f" refused {refused_plates}"
                                    if refused_plates else ""))
                    else:
                        stats["force_refused"] += 1
                        fnote = f"force REFUSED: {refused_plates}"
                    # full plate arrays preserved
                    cols = sorted((k, ax, d[ax]) for k, d in
                                  plates.items() for ax in d)
                    auxr = {"subject_ns": ns, "task": task,
                            "fps": arate,
                            "labels": [f"{ax}{k}" for k, ax, _ in cols],
                            "signal": sig[:, [ci for _, _, ci in cols]]
                            .astype(np.float32),
                            "plate_centers_mm": centers}
                    with open(os.path.join(
                            auxf_dir, sanitize(f"{ns}__{task}")
                            + ".pkl"), "wb") as f:
                        pickle.dump(auxr, f)
            audit.append([zn, name, ns,
                          f"emg={len(emg_idx)} anon={len(anon)}",
                          ("; ".join(notes + ([fnote] if fnote else [])))
                          [:300]])

    print(stats)
    # manifest merges: replace any prior stroke_gait rows, append new
    def merge(path, header, rows):
        old = []
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                r = list(csv.reader(f))
            old = [x for x in r[1:]
                   if x and x[0] != "stroke_gait_vancriekinge"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(old + rows)
        print(f"{os.path.basename(path)}: {len(old) + len(rows)} rows "
              f"(+{len(rows)})")

    ds = os.path.join(args.repo, "datasets")
    merge(os.path.join(ds, "_canonical_emg_manifest.csv"),
          ["source", "subject_ns", "task", "fps", "n_frames",
           "n_channels", "kinds", "record_path"], emg_manifest)
    merge(os.path.join(ds, "_canonical_force_manifest.csv"),
          ["source", "subject_ns", "task", "fps", "n_frames"],
          force_manifest)
    with open(os.path.join(base, "processed", "canonical_force.pkl"),
              "wb") as f:
        pickle.dump(force_recs, f)
    with open(os.path.join(base, "processed",
                           "analogs_ingest_audit.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["zip", "file", "subject_ns", "counts", "notes"])
        w.writerows(audit)
    print("done.")


if __name__ == "__main__":
    main()
