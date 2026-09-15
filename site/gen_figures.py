# -*- coding: utf-8 -*-
"""Generate the site's REAL figures and corpus statistics.

Everything is computed from the canonical manifests and real records on
disk; nothing is invented (owner rule, 2026-08-28). Styling follows the
validated dataviz palette (categorical slots in fixed order, thin marks,
recessive axes, direct labels, one hue per magnitude panel). Every
figure is emitted twice: a light variant (name.png) and a dark variant
(name_dark.png), paired in the .rst sources with the pydata theme's
only-light / only-dark classes.

Outputs (site/source/_static/):
  catalogue_glance{,_dark}.png       the FULL catalogue: 12 modality lanes
  corpus_overview{,_dark}.png        hours + records per harmonized family
  sample_pose{,_dark}.png            real gait skeleton strip
  sample_signals{,_dark}.png         real EMG + IMU snippets
  modality_mosaic{,_dark}.png        six families, six real records
  modality_{imu,emg,eeg,force,silhouette}{,_dark}.png
  duration_distributions{,_dark}.png per-family record-duration histograms
  taxonomy_coverage{,_dark}.png      datasets per taxonomy cell, named
plus site/source/_generated/corpus_stats.html (per-family statistics)
and site/source/_generated/hero_stats.html (landing stat band).
Run from the repo root; the sphinx build does not run this automatically.
"""
import csv
import glob
import sys
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from moveatlas import records  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(REPO, "site", "source", "_static")
GEN = os.path.join(REPO, "site", "source", "_generated")
os.makedirs(STATIC, exist_ok=True)
os.makedirs(GEN, exist_ok=True)

# ------------------------------------------------------------------ style
# Validated reference palette (dataviz skill), both modes. The dark
# column is the same hues stepped for the dark surface, not a new set.
THEMES = {
    "light": dict(
        suffix="",
        S=("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
           "#008300"),
        INK="#0b0b0b", INK2="#52514e", MUTED="#898781",
        GRID="#e1e0d9", BASE="#c3c2b7", SURFACE="#fcfcfb"),
    "dark": dict(
        suffix="_dark",
        S=("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181",
           "#008300"),
        INK="#ffffff", INK2="#c3c2b7", MUTED="#898781",
        GRID="#2c2c2a", BASE="#383835", SURFACE="#1a1a19"),
}


def apply_theme(T):
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "figure.facecolor": T["SURFACE"], "axes.facecolor": T["SURFACE"],
        "savefig.facecolor": T["SURFACE"],
        "axes.edgecolor": T["BASE"], "axes.labelcolor": T["INK2"],
        "xtick.color": T["MUTED"], "ytick.color": T["MUTED"],
        "axes.titlecolor": T["INK"], "text.color": T["INK2"],
        "axes.titlesize": 10, "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def despine(ax, left=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if left:
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)


def save(fig, name, T):
    fig.savefig(os.path.join(STATIC, name + T["suffix"] + ".png"),
                dpi=150, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"  {name}{T['suffix']}.png")


# ------------------------------------------------------------- manifests
def read_manifest(name):
    with open(os.path.join(REPO, "datasets", name), newline="",
              encoding="utf-8") as f:
        return list(csv.DictReader(f))


# manifest source ids that differ from the registry id they belong to
SOURCE_ALIAS = {
    "semg_walking": "physionet_semg_walking",
    "cervical_motion": "cervical_motion_multiplanar",
    "modys": "modys_video",
    "ntu": "ntu_rgbd",
    "cody": "cody_1",
    "cody_external": "cody_3",
    "cap_sleep_chin": "cap_sleep",
    "seizeit2_emg": "seizeit2",
    "weargait": "weargait_pd",
}


def read_family(*names):
    """Read a family's manifests, counting each dataset ONCE.

    The main family manifests already contain the datasets that also
    keep a dedicated manifest file (verified 2026-08-31: capture24,
    ltmm, pads, pd_biostamprc21, sixmwt_lifespan, multimodal_fog in
    IMU; cervical_motion in EMG; identical row sets in both files).
    Reading main + dedicated therefore double-counted 27,147 records;
    a source seen in an earlier file is skipped in later files.
    Row-level dedupe would be WRONG: identical rows inside one file are
    real distinct records (equal-length wear segments).
    Source ids are rewritten onto registry ids via SOURCE_ALIAS."""
    seen_sources, out = set(), []
    for name in names:
        rows = read_manifest(name)
        for r in rows:
            r["source"] = SOURCE_ALIAS.get(r["source"], r["source"])
        fresh = {r["source"] for r in rows} - seen_sources
        out += [r for r in rows if r["source"] in fresh]
        seen_sources |= fresh
    return out


def stats_from(rows):
    hours = sum(float(r["n_frames"]) / float(r["fps"]) / 3600
                for r in rows if float(r.get("fps") or 0) > 0)
    return {"records": len(rows),
            "subjects": len({r["subject_ns"] for r in rows}),
            "datasets": len({r["source"] for r in rows}),
            "hours": hours}


FAMILIES = {
    "pose": read_family("_canonical_manifest.csv",
                        "_canonical_manifest_vidimu.csv",
                        "_canonical_manifest_infant_pose_chambers.csv"),
    "imu": read_family(
        "_canonical_imu_manifest.csv",
        "_canonical_imu_manifest_capture24.csv",
        "_canonical_imu_manifest_ltmm.csv",
        "_canonical_imu_manifest_multimodal_fog.csv",
        "_canonical_imu_manifest_pads.csv",
        "_canonical_imu_manifest_pd_biostamprc21.csv",
        "_canonical_imu_manifest_sixmwt_lifespan.csv",
        "_canonical_imu_manifest_goodwin_smm.csv"),
    "emg": read_family("_canonical_emg_manifest.csv",
                       "_canonical_emg_manifest_cervical_motion.csv"),
    "eeg": read_family("_canonical_eeg_manifest.csv"),
    "force": read_family("_canonical_force_manifest.csv"),
    "silhouette": read_family("_canonical_silhouette_manifest.csv"),
}
STATS = {fam: stats_from(rows) for fam, rows in FAMILIES.items()}
fams = list(STATS)

# ------------------------------------------------------------- registry
import sys as _sys
_sys.path.insert(0, REPO)
os.environ.setdefault("MOVEATLAS_REPO", REPO)
import moveatlas as _mv

REGISTRY = _mv.list_datasets()

# The 12 modality lanes of the catalogue. The first six are the
# harmonized signal families; the rest are catalogued with cards and
# access routes, not harmonized signal (yet).
LANES = [
    ("M1", "Pose & video", "pose"),
    ("M2", "Wearable IMU", "imu"),
    ("M5", "EMG", "emg"),
    ("M6", "EEG", "eeg"),
    ("M3", "Force & pressure", "force"),
    ("M4", "Silhouette", "silhouette"),
    ("M7", "LFP / ECoG (invasive)", None),
    ("M8", "MRI & imaging", None),
    ("M9", "Genetics", None),
    ("M10", "Histology & transcriptomics", None),
    ("M11", "Voice, writing & typing", None),
    ("M12", "Clinical scales", None),
]
LANE_COUNT = {}
for r in REGISTRY:
    for m in set(re.findall(r"M\d+", r["moveatlas_cells"])):
        LANE_COUNT[m] = LANE_COUNT.get(m, 0) + 1

# ------------------------------------------------------- real records
EDGES = [(0, 1), (1, 2), (1, 3), (1, 4), (3, 5), (5, 7), (4, 6), (6, 8),
         (0, 9), (0, 10), (9, 11), (11, 13), (10, 12), (12, 14)]
# The corpus moved from pickle to the moveatlas-record/1 container on
# 2026-09-08; load_any reads either, preferring the .npz sibling.
def _rec(*parts):
    return records.load_any(os.path.join(REPO, *parts))


pose_recs = _rec("datasets", "pose", "stroke_gait_vancriekinge",
                 "processed", "canonical.npz")
able = next(r for r in pose_recs if r["group"] == "able_bodied"
            and r["n_frames"] > 300)
stro = next(r for r in pose_recs if r["group"] == "stroke"
            and r["n_frames"] > 300)

emg = records.load_any(sorted(glob.glob(os.path.join(
    REPO, "datasets", "emg", "gait120", "processed", "canonical_emg",
    "*S001__level_walking_trial01.npz")))[0])
imu = _rec("datasets", "imu", "nonan_gaitprint", "processed", "canonical",
           "S102.npz")[0]
eeg = _rec("datasets", "eeg", "pd_walking_eeg_ds007526", "processed",
           "canonical_eeg",
           "pd_walking_eeg_ds007526__pd_walking_eeg_ds007526_sub-001__rest.npz")
force = _rec("datasets", "imu", "physionet_gaitpdb", "processed",
             "canonical_force.npz")[0]
sil = _rec("datasets", "pose", "koa_pd_nm", "processed",
           "canonical_silhouette.npz")[0]

# taxonomy cells (names from the portal's canonical mapping)
CELL_NAME = {
    "A1": "Tremor", "A2": "Myoclonus", "A3": "Tics", "A4": "Dystonia",
    "A5": "Stereotypies", "A6": "Athetosis", "A7": "Chorea",
    "A8": "Ballismus",
    "B1": "Rigidity", "B2": "Bradykinesia", "B3": "Hypokinesia",
    "B4": "Akinesia", "B5": "Freezing of gait",
    "C1": "Normal adult movement", "C2": "Infant development",
    "C3": "Aging",
    "D1": "Epilepsy", "D2": "Ataxia", "D3": "Pyramidal syndromes",
    "D4": "Neuropathies", "D5": "Neurodevelopmental",
    "D6": "Sleep disorders", "D7": "Functional movement disorders",
    "E1": "Endocrine", "E2": "Metabolic", "E3": "Diabetes-related",
    "E4": "Musculoskeletal", "E5": "Dermatologic", "E6": "Iatrogenic",
    "E7": "Psychiatric",
}
MOD_NAME = {
    "M1": "Pose / video", "M2": "Inertial (IMU)", "M3": "Plantar force",
    "M4": "Silhouette", "M5": "EMG", "M6": "EEG", "M7": "LFP / ECoG",
    "M8": "Imaging", "M9": "Genetics", "M10": "Histology / transcr.",
    "M11": "Voice / writing", "M12": "Clinical scales",
}
CELLCOUNT = {}
for r in REGISTRY:
    for c in set(re.findall(r"[A-E]\d+|M\d+", r["moveatlas_cells"])):
        CELLCOUNT[c] = CELLCOUNT.get(c, 0) + 1

# human-readable ticks for log10-seconds axes
DUR_TICKS = [(0.1, "0.1 s"), (1, "1 s"), (10, "10 s"), (60, "1 min"),
             (600, "10 min"), (3600, "1 h"), (36000, "10 h")]


# ================================================================ figures
def fig_catalogue_glance(T):
    """The whole catalogue: datasets per modality lane + harmonized hours."""
    S1, S2 = T["S"][0], T["S"][1]
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(9.6, 4.0), gridspec_kw={"width_ratios": [1.45, 1]})

    labels = [name for _, name, _ in LANES]
    counts = [LANE_COUNT.get(code, 0) for code, _, _ in LANES]
    colors = [S1 if fam else S2 for _, _, fam in LANES]
    y = np.arange(len(LANES))[::-1]
    axL.barh(y, counts, height=0.62, color=colors, zorder=3)
    axL.set_yticks(y)
    axL.set_yticklabels(labels, fontsize=8)
    for yy, v in zip(y, counts):
        axL.text(v + 0.5, yy, str(v), va="center", fontsize=8,
                 color=T["INK"])
    axL.set_xlim(0, max(counts) * 1.14)
    axL.xaxis.grid(True, color=T["GRID"], lw=0.7, zorder=0)
    axL.set_axisbelow(True)
    axL.set_xlabel("datasets in the catalogue (a set counts in every "
                   "lane it covers)")
    despine(axL, left=True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (S1, S2)]
    leg = axL.legend(handles, ["harmonized family", "catalogued lane"],
                     fontsize=7.5, frameon=False, loc="lower right",
                     handlelength=1.1, handleheight=1.1)
    for txt in leg.get_texts():
        txt.set_color(T["INK2"])

    hfams = [(name, fam) for _, name, fam in LANES if fam]
    hours = [max(STATS[fam]["hours"], 0.5) for _, fam in hfams]
    y2 = np.arange(len(hfams))[::-1]
    axR.hlines(y2, 0.4, hours, color=T["GRID"], lw=1.4, zorder=2)
    axR.scatter(hours, y2, s=42, color=S1, zorder=3)
    for yy, v, (_, fam) in zip(y2, hours, hfams):
        real = STATS[fam]["hours"]
        axR.text(v * 1.45, yy, f"{real:,.0f} h", va="center", fontsize=8,
                 color=T["INK"])
    axR.set_xscale("log")
    axR.set_yticks(y2)
    axR.set_yticklabels([name for name, _ in hfams], fontsize=8)
    ticks = [(10, "10 h"), (100, "100 h"), (1000, "1,000 h"),
             (10000, "10,000 h")]
    axR.set_xticks([t for t, _ in ticks])
    axR.set_xticklabels([s for _, s in ticks])
    axR.set_xlim(0.4, max(hours) * 12)
    axR.xaxis.grid(True, color=T["GRID"], lw=0.7, zorder=0)
    axR.set_axisbelow(True)
    axR.set_xlabel("hours of harmonized signal")
    axR.tick_params(axis="x", which="minor", bottom=False)
    despine(axR, left=True)

    fig.suptitle(f"{len(REGISTRY)} datasets across 12 modality lanes; "
                 "six families carry harmonized signal today",
                 fontsize=11, color=T["INK"], x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "catalogue_glance", T)


def fig_corpus_overview(T):
    """Hours + records per harmonized family (log dot plots)."""
    S1 = T["S"][0]
    hours = [max(STATS[f]["hours"], 0.5) for f in fams]
    recs = [STATS[f]["records"] for f in fams]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.0))
    tick_sets = (
        [(10, "10 h"), (100, "100 h"), (1000, "1,000 h"),
         (10000, "10,000 h")],
        [(1000, "1,000"), (10000, "10,000"), (100000, "100,000")])
    for ax, vals, reals, label, fmt, ticks in (
            (axes[0], hours, [STATS[f]["hours"] for f in fams],
             "hours of harmonized signal", "{:,.0f} h", tick_sets[0]),
            (axes[1], recs, recs, "canonical records", "{:,}",
             tick_sets[1])):
        y = np.arange(len(fams))[::-1]
        lo = min(vals) * 0.5
        ax.hlines(y, lo, vals, color=T["GRID"], lw=1.4, zorder=2)
        ax.scatter(vals, y, s=42, color=S1, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(fams)
        ax.set_xscale("log")
        ax.set_xticks([t for t, _ in ticks])
        ax.set_xticklabels([s for _, s in ticks])
        ax.tick_params(axis="x", which="minor", bottom=False)
        ax.set_xlabel(label)
        ax.xaxis.grid(True, color=T["GRID"], lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        despine(ax, left=True)
        for yy, v, real in zip(y, vals, reals):
            ax.text(v * 1.45, yy, fmt.format(real), va="center",
                    fontsize=8, color=T["INK"])
        ax.set_xlim(lo, max(vals) * 14)
    fig.suptitle("The harmonized corpus, measured from the canonical "
                 "manifests", fontsize=11, color=T["INK"], x=0.02,
                 ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "corpus_overview", T)


def draw_skel(ax, rec, fr, color, T):
    pts = rec["coords"][fr][:, [1, 2]]
    val = rec["valid_mask"][fr]
    for a, b in EDGES:
        if val[a] and val[b]:
            ax.plot(pts[[a, b], 0], pts[[a, b], 1], "-", lw=2.0,
                    color=color, solid_capstyle="round", zorder=2)
    ax.scatter(pts[val, 0], pts[val, 1], s=9, color=T["INK"], zorder=3)
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.55, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")


def fig_sample_pose(T):
    S1, S2 = T["S"][0], T["S"][1]
    fig, axes = plt.subplots(2, 6, figsize=(9.6, 4.3))
    fig.subplots_adjust(left=0.12)
    for row, (rec, label, color) in enumerate([(able, "able-bodied", S1),
                                               (stro, "stroke", S2)]):
        frames = np.linspace(50, rec["n_frames"] - 50, 6).astype(int)
        for col, fr in enumerate(frames):
            draw_skel(axes[row, col], rec, fr, color, T)
        # row label in the figure margin, never over the skeleton
        pos = axes[row, 0].get_position()
        fig.text(0.015, (pos.y0 + pos.y1) / 2, label, fontsize=9.5,
                 color=color, fontweight="bold", va="center")
    fig.suptitle("Two real gait sequences, canonical 15-joint skeletons "
                 "(stroke_gait_vancriekinge, 100 Hz optical mocap)",
                 fontsize=11, color=T["INK"], x=0.02, ha="left")
    save(fig, "sample_pose", T)


def style_trace(ax, title, T):
    ax.set_title(title, loc="left", fontsize=8.6, color=T["INK2"])
    ax.yaxis.grid(True, color=T["GRID"], lw=0.6)
    ax.set_axisbelow(True)
    despine(ax)


def panel_emg(ax, T):
    t = np.arange(emg["signal"].shape[0]) / emg["fps"]
    ax.plot(t, emg["signal"][:, 3] * 1e3, lw=0.5, color=T["S"][0])
    ax.set_ylabel("uV", fontsize=7.5)
    style_trace(ax, "EMG - tibialis anterior, walking (gait120, 2 kHz)", T)


def panel_imu(ax, T):
    sl = slice(0, int(15 * imu["fps"]))
    t = np.arange(imu["signal"].shape[0])[sl] / imu["fps"]
    ax.plot(t, imu["signal"][sl, 2, 0], lw=0.7, color=T["S"][0])
    ax.set_ylabel("g", fontsize=7.5)
    style_trace(ax, "IMU - lower-back vertical accel. (NONAN, 200 Hz)", T)


def panel_eeg(ax, T):
    fs = eeg["fps"]
    sl = slice(int(10 * fs), int(20 * fs))
    t = np.arange(eeg["signal"].shape[0])[sl] / fs
    for k in range(6):
        v = eeg["signal"][sl, k]
        v = (v - np.nanmean(v))
        ax.plot(t, v + k * 120, lw=0.5, color=T["S"][0])
    ax.set_yticks([])
    style_trace(ax, "EEG - 6 of 60 channels, rest (PD study, 250 Hz, uV)",
                T)
    ax.spines["left"].set_visible(False)


def panel_force(ax, T):
    fs = force["fps"]
    sl = slice(int(20 * fs), int(30 * fs))
    t = np.arange(force["force"].shape[0])[sl] / fs
    left = force["force"][sl, 0, 8]
    right = force["force"][sl, 1, 8]
    ax.plot(t, left, lw=0.9, color=T["S"][0])
    ax.plot(t, right, lw=0.9, color=T["S"][1])
    # direct labels at the trace ends instead of a legend box
    ax.text(t[-1] + 0.12, np.max(left[-int(fs):]), "left", fontsize=7.5,
            color=T["S"][0], va="center", fontweight="bold")
    ax.text(t[-1] + 0.12, np.min(right[-int(fs):]) + 60, "right",
            fontsize=7.5, color=T["S"][1], va="center",
            fontweight="bold")
    ax.set_xlim(t[0], t[-1] + 1.0)
    ax.set_ylabel("N", fontsize=7.5)
    style_trace(ax, "Force - vertical GRF, both feet (gaitpdb, 100 Hz)", T)


def panel_sil(ax, T):
    good = np.where(sil["detect_mask"])[0]
    mid = good[len(good) // 4: 3 * len(good) // 4]
    frames = mid[np.linspace(0, len(mid) - 1, 6).astype(int)]
    for i, fr in enumerate(frames):
        c = sil["contour"][fr].copy()
        c[:, 0] = c[:, 0] + i * 1.4
        ax.fill(c[:, 0], c[:, 1], color=T["S"][0], alpha=0.9, lw=0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Silhouette - 64-point contours (KOA-PD-NM, 50 fps)",
                 loc="left", fontsize=8.6, color=T["INK2"])


def panel_pose_mini(ax, T):
    draw_skel(ax, able, 200, T["S"][0], T)
    ax.set_title("Pose - 15-joint skeleton (stroke_gait, 100 Hz)",
                 loc="left", fontsize=8.6, color=T["INK2"])


def fig_sample_signals(T):
    fig, axes = plt.subplots(2, 1, figsize=(9.6, 4.4))
    panel_emg(axes[0], T)
    panel_imu(axes[1], T)
    axes[1].set_xlabel("time (s)", fontsize=7.5)
    fig.tight_layout()
    save(fig, "sample_signals", T)


def fig_mosaic(T):
    fig, axes = plt.subplots(3, 2, figsize=(9.6, 7.6))
    panel_pose_mini(axes[0, 0], T)
    panel_imu(axes[0, 1], T)
    panel_emg(axes[1, 0], T)
    panel_eeg(axes[1, 1], T)
    panel_force(axes[2, 0], T)
    panel_sil(axes[2, 1], T)
    axes[2, 0].set_xlabel("time (s)", fontsize=7.5)
    fig.suptitle("Six harmonized families, six real records", fontsize=12,
                 color=T["INK"], x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    save(fig, "modality_mosaic", T)


def fig_family_cards(T):
    """Small clean thumbnails for the landing family cards: one real
    record each, marks only, no chrome."""
    def bare(ax):
        ax.axis("off")

    def th_pose(ax):
        draw_skel(ax, able, 200, T["S"][0], T)

    def th_imu(ax):
        sl = slice(0, int(8 * imu["fps"]))
        ax.plot(np.arange(imu["signal"].shape[0])[sl] / imu["fps"],
                imu["signal"][sl, 2, 0], lw=0.8, color=T["S"][1])
        bare(ax)

    def th_emg(ax):
        t = np.arange(emg["signal"].shape[0]) / emg["fps"]
        ax.plot(t, emg["signal"][:, 3] * 1e3, lw=0.4, color=T["S"][2])
        bare(ax)

    def th_eeg(ax):
        fs = eeg["fps"]
        sl = slice(int(10 * fs), int(18 * fs))
        t = np.arange(eeg["signal"].shape[0])[sl] / fs
        for k in range(3):
            v = eeg["signal"][sl, k]
            ax.plot(t, v - np.nanmean(v) + k * 150, lw=0.5,
                    color=T["S"][3])
        bare(ax)

    def th_force(ax):
        fs = force["fps"]
        sl = slice(int(20 * fs), int(26 * fs))
        t = np.arange(force["force"].shape[0])[sl] / fs
        ax.plot(t, force["force"][sl, 0, 8], lw=0.9, color=T["S"][4])
        ax.plot(t, force["force"][sl, 1, 8], lw=0.9, color=T["S"][4],
                alpha=0.45)
        bare(ax)

    def th_sil(ax):
        good = np.where(sil["detect_mask"])[0]
        mid = good[len(good) // 4: 3 * len(good) // 4]
        frames = mid[np.linspace(0, len(mid) - 1, 4).astype(int)]
        for i, fr in enumerate(frames):
            c = sil["contour"][fr].copy()
            c[:, 0] = c[:, 0] + i * 1.4
            ax.fill(c[:, 0], c[:, 1], color=T["S"][5], alpha=0.9, lw=0)
        ax.set_aspect("equal")
        bare(ax)

    for name, th in (("card_pose", th_pose), ("card_imu", th_imu),
                     ("card_emg", th_emg), ("card_eeg", th_eeg),
                     ("card_force", th_force),
                     ("card_silhouette", th_sil)):
        fig, ax = plt.subplots(figsize=(3.6, 1.7))
        th(ax)
        fig.tight_layout(pad=0.4)
        save(fig, name, T)


def fig_modality_singles(T):
    for name, panel, size in (
            ("modality_imu", panel_imu, (9.6, 2.6)),
            ("modality_emg", panel_emg, (9.6, 2.6)),
            ("modality_eeg", panel_eeg, (9.6, 3.4)),
            ("modality_force", panel_force, (9.6, 2.6)),
            ("modality_silhouette", panel_sil, (9.6, 2.4))):
        fig, ax = plt.subplots(figsize=size)
        panel(ax, T)
        if name != "modality_silhouette":
            ax.set_xlabel("time (s)", fontsize=7.5)
        fig.tight_layout()
        save(fig, name, T)


def fig_durations(T):
    S1 = T["S"][0]
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.0))
    for ax, fam in zip(axes.ravel(), fams):
        rows = FAMILIES[fam]
        dur = np.array([float(r["n_frames"]) / float(r["fps"])
                        for r in rows if float(r.get("fps") or 0) > 0])
        logd = np.log10(dur[dur > 0])
        ax.hist(logd, bins=40, color=S1, zorder=3)
        ax.set_title(f"{fam}  (n = {len(dur):,})", loc="left", fontsize=9,
                     color=T["INK"])
        lo, hi = logd.min(), logd.max()
        ticks = [(np.log10(v), s) for v, s in DUR_TICKS
                 if lo - 0.3 <= np.log10(v) <= hi + 0.3]
        ax.set_xticks([t for t, _ in ticks])
        ax.set_xticklabels([s for _, s in ticks], fontsize=7)
        ax.set_xlabel("record duration (log scale)")
        ax.yaxis.grid(True, color=T["GRID"], lw=0.6)
        ax.set_axisbelow(True)
        despine(ax)
    fig.suptitle("Record-duration distributions per family",
                 fontsize=11, color=T["INK"], x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "duration_distributions", T)


def fig_taxonomy(T):
    """Small multiples per taxonomy axis, cells NAMED, no legend needed."""
    S = T["S"]
    AXIS_META = [
        ("A", "Hyperkinetic", S[1]), ("B", "Hypokinetic", S[2]),
        ("C", "Age-conditioned normal", S[3]),
        ("D", "Neurological comorbidity", S[4]),
        ("E", "Systemic comorbidity", S[5]),
        ("M", "Modality lanes", S[0]),
    ]
    MAXROWS = 12
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 6.8))
    for ax, (axis, title, color) in zip(axes.ravel(), AXIS_META):
        cells = sorted((c for c in CELLCOUNT if c[0] == axis
                        and (axis != "M" or c in MOD_NAME)),
                       key=lambda c: int(c[1:]))
        names = [MOD_NAME[c] if axis == "M" else CELL_NAME[c]
                 for c in cells]
        vals = [CELLCOUNT[c] for c in cells]
        y = np.arange(len(cells))[::-1] + (MAXROWS - len(cells))
        ax.barh(y, vals, height=0.62, color=color, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=7.6)
        for yy, v in zip(y, vals):
            ax.text(v + 0.5, yy, str(v), va="center", fontsize=7.4,
                    color=T["INK"])
        ax.set_ylim(-0.6, MAXROWS - 0.4)
        ax.set_xlim(0, 30)
        ax.set_title(f"{axis} · {title}", loc="left", fontsize=9,
                     color=T["INK"])
        ax.xaxis.grid(True, color=T["GRID"], lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        despine(ax, left=True)
        ax.tick_params(labelbottom=False, bottom=False)
    fig.suptitle("Taxonomy coverage: datasets per cell, across the 83 "
                 "catalogued datasets", fontsize=11, color=T["INK"],
                 x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "taxonomy_coverage", T)


# ================================================================ html
def write_stats_table():
    rows = ["<table class=\"table\"><thead><tr><th>Family</th><th>Datasets "
            "ingested</th><th>Subjects</th><th>Records</th><th>Hours</th>"
            "</tr></thead><tbody>"]
    tot = {"datasets": 0, "subjects": 0, "records": 0, "hours": 0.0}
    for fam in fams:
        s = STATS[fam]
        rows.append(f"<tr><td><b>{fam}</b></td><td>{s['datasets']}</td>"
                    f"<td>{s['subjects']:,}</td><td>{s['records']:,}</td>"
                    f"<td>{s['hours']:,.0f}</td></tr>")
        for k in tot:
            tot[k] += s[k]
    rows.append(f"<tr><td><b>total</b></td><td>{tot['datasets']}</td>"
                f"<td>{tot['subjects']:,}</td><td>{tot['records']:,}</td>"
                f"<td>{tot['hours']:,.0f}</td></tr>")
    rows.append("</tbody></table>")
    with open(os.path.join(GEN, "corpus_stats.html"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(rows))
    return tot


def write_hero_stats(tot):
    """Landing stat band; theme-aware via the pydata data-theme attribute."""
    tiles = [
        (f"{len(REGISTRY)}", "catalogued datasets"),
        (f"{tot['records']:,}", "harmonized records"),
        (f"{tot['subjects']:,}", "subjects"),
        (f"{tot['hours']:,.0f}", "hours of signal"),
    ]
    cells = "\n".join(
        f'<div class="ma-tile"><div class="ma-n">{n}</div>'
        f'<div class="ma-l">{l}</div></div>' for n, l in tiles)
    html = f'<div class="ma-band">\n{cells}\n</div>'
    with open(os.path.join(GEN, "hero_stats.html"), "w",
              encoding="utf-8") as f:
        f.write(html)


FAMILY_BLURB = {
    "pose": "3D mocap and video keypoints on one canonical 15-joint "
            "skeleton. Gait analysis, action recognition, clinical video.",
    "imu": "Wearable inertial sensing on a 14-location body grid; "
           "protocol trials and multi-day free living.",
    "emg": "Surface electromyography with named muscles, never guessed. "
           "Locomotion, tremor and sleep protocols.",
    "eeg": "Scalp EEG during movement and sleep; the invasive LFP/ECoG "
           "lane joins this contract at its own pass.",
    "force": "Ground-reaction forces from insoles and force plates; "
             "footstep-level records at native rates.",
    "silhouette": "Privacy-preserving 64-point body contours: the "
                  "publishable face of clinical video.",
}


def write_family_cards():
    """Landing family cards: real thumbnail, live counts, one-line use."""
    cards = []
    for fam in fams:
        s = STATS[fam]
        count = (f"{s['datasets']} datasets · {s['subjects']:,} subjects "
                 f"· {s['hours']:,.0f} h")
        cards.append(f"""<a class="ma-fcard" href="modalities.html#{fam}">
<img class="only-light" src="_static/card_{fam}.png" alt="{fam} sample">
<img class="only-dark" src="_static/card_{fam}_dark.png" alt="{fam} sample">
<div class="ma-fcard-body">
<div class="ma-fam ma-{fam}">{fam}</div>
<div class="ma-count">{count}</div>
<p>{FAMILY_BLURB[fam]}</p>
</div></a>""")
    html = ('<div class="ma-fgrid">\n' + "\n".join(cards) + "\n</div>")
    with open(os.path.join(GEN, "family_cards.html"), "w",
              encoding="utf-8") as f:
        f.write(html)


def write_provenance():
    """Chip row of the source hosts the catalogue draws from."""
    from urllib.parse import urlparse
    NAME = {
        "physionet.org": "PhysioNet", "openneuro.org": "OpenNeuro",
        "zenodo.org": "Zenodo", "figshare.com": "figshare",
        "kaggle.com": "Kaggle", "archive.ics.uci.edu": "UCI ML",
        "osf.io": "OSF", "github.com": "GitHub",
        "datadryad.org": "Dryad", "data.4tu.nl": "4TU.ResearchData",
        "data.mendeley.com": "Mendeley Data",
        "ieee-dataport.org": "IEEE DataPort",
        "springernature.figshare.com": "figshare",
        "wwwn.cdc.gov": "CDC NHANES", "cdn.intechopen.com": "IntechOpen",
        "panelapp.genomicsengland.co.uk": "Genomics England",
        "ncbi.nlm.nih.gov": "NCBI", "human.brain-map.org": "Allen Atlas",
        "portal.brain-map.org": "Allen Atlas",
        "cellxgene.cziscience.com": "CZ CELLxGENE",
        "hpo.jax.org": "HPO",
    }
    hosts = {}
    for r in REGISTRY:
        link = (r.get("link") or "").strip()
        if not link.startswith("http"):
            continue
        h = urlparse(link).netloc.lower().removeprefix("www.")
        label = NAME.get(h)
        if label:
            hosts[label] = hosts.get(label, 0) + 1
    chips = "".join(
        f'<span class="ma-chip">{n}</span>'
        for n, _ in sorted(hosts.items(), key=lambda kv: -kv[1]))
    html = ('<div class="ma-chips"><span class="ma-count-note">'
            'Sources include </span>' + chips + "</div>")
    with open(os.path.join(GEN, "provenance.html"), "w",
              encoding="utf-8") as f:
        f.write(html)


def write_synthesis_tables():
    """The reviewer tables: symptom x modality, context/comorbidity x
    modality (both from the registry, the operational truth), and
    subjects carrying several harmonized modalities (from the
    manifests)."""
    OPEN_CASES = {"hosted", "recipe"}
    lanes = [code for code, _, _ in LANES]
    lane_label = {code: name for code, name, _ in LANES}

    def matrix_rows(cell_codes):
        cnt = {}
        opn = {}
        for r in REGISTRY:
            found = set(re.findall(r"[A-E]\d+|M\d+", r["moveatlas_cells"]))
            for c in found & set(cell_codes):
                for m in found & set(lanes):
                    cnt[(c, m)] = cnt.get((c, m), 0) + 1
                    if r["access_case"] in OPEN_CASES:
                        opn[(c, m)] = opn.get((c, m), 0) + 1
        return cnt, opn

    def matrix_html(title, cell_codes, name):
        cnt, opn = matrix_rows(cell_codes)
        used = [m for m in lanes if any((c, m) in cnt
                                        for c in cell_codes)]
        out = [f"<p class=\"ma-count-note\">{title}: datasets per cell "
               "and modality lane; the parenthesized number is the "
               "open-access subset (hosted or recipe). Computed from "
               "the registry at build time.</p>",
               "<div style=\"overflow-x:auto\">",
               "<table class=\"table\"><thead><tr><th></th>"]
        out += [f"<th>{lane_label[m]}</th>" for m in used]
        out.append("<th>any lane</th></tr></thead><tbody>")
        for c in cell_codes:
            row_ids = [r["id"] for r in REGISTRY
                       if c in re.findall(r"[A-E]\d+",
                                          r["moveatlas_cells"])]
            if not row_ids:
                cells = "".join(f"<td></td>" for _ in used)
                out.append(f"<tr><td><b>{c} {CELL_NAME[c]}</b></td>"
                           f"{cells}<td>0</td></tr>")
                continue
            tds = []
            for m in used:
                n = cnt.get((c, m), 0)
                o = opn.get((c, m), 0)
                if not n:
                    tds.append("<td></td>")
                elif o == n:
                    tds.append(f"<td><b>{n}</b></td>")
                else:
                    tds.append(f"<td><b>{n}</b> <span class=\""
                               f"ma-count-note\">({o})</span></td>")
            out.append(f"<tr><td><b>{c} {CELL_NAME[c]}</b></td>"
                       f"{''.join(tds)}<td>{len(row_ids)}</td></tr>")
        out.append("</tbody></table></div>")
        with open(os.path.join(GEN, name), "w", encoding="utf-8") as f:
            f.write("\n".join(out))

    matrix_html("Target symptoms",
                ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8",
                 "B1", "B2", "B3", "B4", "B5"],
                "matrix_symptoms.html")
    matrix_html("Healthy context and comorbidities",
                ["C1", "C2", "C3", "D1", "D2", "D3", "D4", "D5", "D6",
                 "D7", "E1", "E2", "E3", "E4", "E5", "E6", "E7"],
                "matrix_context.html")

    # subjects with several harmonized modalities, from the manifests
    subs = {}
    for fam, rows in FAMILIES.items():
        for r in rows:
            ds = r["source"]
            subs.setdefault(ds, {}).setdefault(fam, set()).add(
                r["subject_ns"])
    out = ["<table class=\"table\"><thead><tr><th>Dataset</th>"
           "<th>Families</th><th>Subjects per family</th>"
           "<th>Subjects with 2+ modalities</th></tr></thead><tbody>"]
    total_paired = 0
    for ds in sorted(subs, key=lambda d: -len(subs[d])):
        fams = subs[ds]
        if len(fams) < 2:
            continue
        inter = set.intersection(*fams.values())
        total_paired += len(inter)
        per = ", ".join(f"{f} {len(s):,}" for f, s in sorted(fams.items()))
        out.append(f"<tr><td><b>{ds}</b></td>"
                   f"<td>{' + '.join(sorted(fams))}</td>"
                   f"<td>{per}</td><td><b>{len(inter):,}</b></td></tr>")
    out.append(f"<tr><td><b>total</b></td><td></td><td></td>"
               f"<td><b>{total_paired:,}</b></td></tr>")
    out.append("</tbody></table>")
    with open(os.path.join(GEN, "multimodal_subjects.html"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out))

    # intervention and state labels, from the curated evidence table
    ipath = os.path.join(REPO, "docs", "interventions.csv")
    out = ["<table class=\"table\"><thead><tr><th>Dataset</th>"
           "<th>Intervention</th><th>State labels available</th>"
           "<th>Evidence</th></tr></thead><tbody>"]
    with open(ipath, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(
                f"<tr><td><b>{r['dataset']}</b></td>"
                f"<td>{r['intervention']}</td>"
                f"<td>{r['states_available']}</td>"
                f"<td class=\"ma-count-note\">{r['evidence']}"
                f" [{r['verified']}]</td></tr>")
    out.append("</tbody></table>")
    with open(os.path.join(GEN, "interventions.html"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out))

    # demographics documentation coverage, from the registry age field
    ing = {r["source"] for rows_ in FAMILIES.values() for r in rows_}
    with_age = [r for r in REGISTRY if (r.get("age") or "").strip()]
    out = [f'<p class="ma-count-note">{len(with_age)} of '
           f'{len(REGISTRY)} catalogued datasets document ages in the '
           "registry (verbatim below); per-record demographics (sex, "
           "anthropometrics, clinical scores) ride inside the records "
           "where the source provides them.</p>",
           "<table class=\"table\"><thead><tr><th>Dataset</th>"
           "<th>Status</th><th>Ages (verbatim)</th></tr></thead><tbody>"]
    for r in sorted(with_age, key=lambda x: x["id"]):
        badge = ("harmonized" if r["id"] in ing else "catalogued")
        out.append(f"<tr><td><b>{r['id']}</b></td>"
                   f"<td><span class=\"ma-badge ma-{badge}\">{badge}"
                   f"</span></td><td>{r['age'][:90]}</td></tr>")
    out.append("</tbody></table>")
    with open(os.path.join(GEN, "demographics.html"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(out))


# ================================================================== run
tot = write_stats_table()
write_hero_stats(tot)
write_family_cards()
write_provenance()
write_synthesis_tables()
print("  corpus_stats + hero_stats + family_cards + provenance"
      " + synthesis html")

for theme in ("light", "dark"):
    T = THEMES[theme]
    apply_theme(T)
    fig_catalogue_glance(T)
    fig_corpus_overview(T)
    fig_family_cards(T)
    fig_sample_pose(T)
    fig_sample_signals(T)
    fig_mosaic(T)
    fig_modality_singles(T)
    fig_durations(T)
    fig_taxonomy(T)

print("done.")
for fam in fams:
    s = STATS[fam]
    print(f"  {fam:12s} {s['datasets']:3d} sets {s['subjects']:6,} subj "
          f"{s['records']:7,} rec {s['hours']:9,.1f} h")
