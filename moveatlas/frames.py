# -*- coding: utf-8 -*-
"""Records as pandas DataFrames.

`to_frame(record)` turns any canonical record into a tidy, time-indexed
DataFrame with NAMED columns, so a researcher can `.head()`, `.describe()`,
resample, merge and plot with the pandas they already know. The masks are
honored the honest way: whatever a mask marks invalid becomes NaN in the
frame, never a silent zero.

Column layout per family::

  pose        MultiIndex (joint, axis['x','y','z'])
  emg / eeg   channel names (muscle_side for EMG, site for EEG)
  imu         MultiIndex (location, channel) for instrumented slots only
  force       MultiIndex (foot['left','right'], sensor['s1'..'s8','total'])
  silhouette  the 8 per-frame scalar descriptors (undetected frames NaN)

The index is time in seconds at the record's native rate.
"""
import numpy as np
import pandas as pd

POSE_JOINTS = ["pelvis", "neck", "head", "l_shoulder", "r_shoulder",
               "l_elbow", "r_elbow", "l_wrist", "r_wrist", "l_hip",
               "r_hip", "l_knee", "r_knee", "l_ankle", "r_ankle"]
IMU_LOCATIONS = ["head", "trunk", "lower_back", "wrist_L", "wrist_R",
                 "thigh_L", "thigh_R", "shank_L", "shank_R", "ankle_L",
                 "ankle_R", "foot_L", "foot_R", "pocket"]
IMU_CHANNELS = ["acc_x", "acc_y", "acc_z", "gyr_x", "gyr_y", "gyr_z",
                "mag_x", "mag_y", "mag_z"]
SIL_SCALARS = ["area", "height", "width", "cx", "cy", "aspect",
               "solidity", "orientation"]


def _time_index(n, fps):
    return pd.Index(np.arange(n) / float(fps), name="time_s")


def to_frame(rec):
    """Canonical record -> tidy time-indexed DataFrame (see module doc)."""
    if "coords" in rec:                                     # pose
        T = rec["coords"].shape[0]
        vals = rec["coords"].astype(float).copy()
        vals[~rec["valid_mask"]] = np.nan                  # masked -> NaN
        n_ax = int(np.sum(rec.get("coord_mask", [True] * 3)))
        axes = ["x", "y", "z"][:vals.shape[2]]
        cols = pd.MultiIndex.from_product([POSE_JOINTS, axes],
                                          names=["joint", "axis"])
        df = pd.DataFrame(vals.reshape(T, -1), columns=cols,
                          index=_time_index(T, rec["fps"]))
        if n_ax == 2 and "z" in axes:                      # padded 2D
            df = df.drop(columns="z", level="axis")
        return df
    if "channels" in rec and "signal" in rec:              # emg / eeg
        ch = rec["channels"]
        if ch and isinstance(ch[0], dict):
            names = []
            for c in ch:
                if c.get("site"):                          # eeg channel table
                    names.append(str(c["site"]))
                else:                                      # emg channel table
                    nm = f"{c.get('muscle') or c.get('kind', 'ch')}_" \
                         f"{c.get('side', '')}".rstrip("_")
                    if c.get("electrode"):
                        nm += f"_{c['electrode']}"
                    names.append(nm)
        else:                                              # plain site list
            names = [str(c) for c in ch]
        return pd.DataFrame(np.asarray(rec["signal"], float),
                            columns=pd.Index(names, name="channel"),
                            index=_time_index(rec["signal"].shape[0],
                                              rec["fps"]))
    if "location_ids" in rec:                              # imu
        sig = np.asarray(rec["signal"], float)
        T = sig.shape[0]
        frames = {}
        for li, loc_id in enumerate(rec["location_ids"]):
            loc = IMU_LOCATIONS[int(loc_id)]
            for ci in np.where(rec["channel_mask"][li])[0]:
                col = sig[:, li, ci].copy()
                sv = rec.get("sample_valid")
                if sv is not None:
                    col[~sv[:, li]] = np.nan               # dropouts -> NaN
                frames[(loc, IMU_CHANNELS[ci])] = col
        cols = pd.MultiIndex.from_tuples(frames, names=["location",
                                                        "channel"])
        return pd.DataFrame(np.column_stack(list(frames.values())),
                            columns=cols, index=_time_index(T, rec["fps"]))
    if "force" in rec:                                     # force
        f = np.asarray(rec["force"], float).copy()
        T = f.shape[0]
        f[:, ~rec["sensor_mask"]] = np.nan
        sensors = [f"s{i}" for i in range(1, f.shape[2])] + ["total"]
        cols = pd.MultiIndex.from_product([["left", "right"], sensors],
                                          names=["foot", "sensor"])
        return pd.DataFrame(f.reshape(T, -1), columns=cols,
                            index=_time_index(T, rec["fps"]))
    if "contour" in rec:                                   # silhouette
        sc = np.asarray(rec["scalars"], float).copy()
        sc[~rec["detect_mask"]] = np.nan
        names = SIL_SCALARS[:sc.shape[1]]
        return pd.DataFrame(sc, columns=pd.Index(names, name="scalar"),
                            index=_time_index(sc.shape[0], rec["fps"]))
    raise ValueError("unrecognized canonical record layout")
