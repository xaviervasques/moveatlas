# -*- coding: utf-8 -*-
"""One-liner plotters for canonical objects (the nilearn pattern: each
domain object gets a sensible-defaults visualizer)::

  plot_skeleton(rec, frame, ax=None)   one pose frame as a stick figure
  plot_trace(rec, n_channels=6, ...)   any signal-bearing record, stacked

Both return the matplotlib Axes so callers can keep styling.
"""
import numpy as np


def _plt():
    # lazy on purpose: matplotlib is the 'examples' extra, not a core
    # dependency, and a bare `import moveatlas` must work without it
    # (caught by launch_dryrun.py on a fresh venv, 2026-09-04)
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "moveatlas.viz needs matplotlib: pip install "
            "'moveatlas[examples]' (or matplotlib alone)") from e
    return plt

SKELETON_EDGES = [(0, 1), (1, 2), (1, 3), (1, 4), (3, 5), (5, 7), (4, 6),
                  (6, 8), (0, 9), (0, 10), (9, 11), (11, 13), (10, 12),
                  (12, 14)]


def plot_skeleton(rec, frame=0, ax=None, color="#2a78d6", axes=(1, 2)):
    """Draw one frame of a canonical pose record; masked joints stay
    absent (never invented)."""
    if ax is None:
        _, ax = _plt().subplots(figsize=(2.6, 3.2))
    pts = rec["coords"][frame][:, list(axes)]
    val = rec["valid_mask"][frame]
    for a, b in SKELETON_EDGES:
        if val[a] and val[b]:
            ax.plot(pts[[a, b], 0], pts[[a, b], 1], "-", lw=2, color=color,
                    solid_capstyle="round")
    ax.scatter(pts[val, 0], pts[val, 1], s=10, color="black", zorder=3)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def plot_trace(rec, n_channels=6, t_start=0.0, t_stop=10.0, ax=None,
               color="#2a78d6"):
    """Stacked-trace view of any signal-bearing record (emg/eeg/imu/
    force), first n channels, mean-centered with per-channel offsets."""
    from moveatlas.frames import to_frame
    df = to_frame(rec)
    df = df.loc[(df.index >= t_start) & (df.index <= t_stop)]
    cols = list(df.columns[:n_channels])
    if ax is None:
        _, ax = _plt().subplots(figsize=(8, 0.65 * len(cols) + 1))
    span = np.nanmax(np.abs(df[cols].to_numpy() -
                            np.nanmean(df[cols].to_numpy(), axis=0)))
    off = 2.2 * (span if np.isfinite(span) and span > 0 else 1.0)
    for k, c in enumerate(cols):
        v = df[c] - np.nanmean(df[c])
        ax.plot(df.index, v + k * off, lw=0.6, color=color)
        name = c if isinstance(c, str) else "/".join(map(str, c))
        ax.text(df.index[0], k * off, name + " ", fontsize=7, ha="right",
                va="center")
    ax.set_yticks([])
    ax.set_xlabel("time (s)")
    return ax
