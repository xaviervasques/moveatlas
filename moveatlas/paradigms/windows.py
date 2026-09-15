# -*- coding: utf-8 -*-
"""FixedIntervalWindows: the first concrete paradigm.

A paradigm defines what a valid SAMPLE is, independently of any dataset
(the MOABB transposition). This one cuts continuous canonical records
into fixed-duration windows at each record's NATIVE rate (no resampling,
per the contracts), and returns the (X, y, groups, meta) quadruple that
evaluations consume. Windows inherit their record's subject_ns as group,
so patient-level splits stay leak-free by construction.

Label sources are explicit, never guessed: `label_from="record"` reads
rec["label"] (eval-only labels riding on the record, e.g. stroke vs
able-bodied); `label_from="task_prefix"` derives the class from the task
name stripped of its trial suffix (e.g. gait120's 7 locomotion tasks).
"""
import re

import numpy as np


class FixedIntervalWindows:
    def __init__(self, duration_s=2.0, stride_s=None, label_from="record"):
        self.duration_s = float(duration_s)
        self.stride_s = float(stride_s) if stride_s else self.duration_s
        if label_from not in ("record", "task_prefix"):
            raise ValueError(label_from)
        self.label_from = label_from

    @staticmethod
    def _signal_of(rec):
        if "signal" in rec:                       # emg / imu contracts
            sig = np.asarray(rec["signal"], np.float32)
            return sig.reshape(sig.shape[0], -1)
        if "coords" in rec:                       # pose contract
            sig = np.asarray(rec["coords"], np.float32)
            return sig.reshape(sig.shape[0], -1)
        raise ValueError("record carries neither 'signal' nor 'coords'")

    def _label_of(self, rec):
        if self.label_from == "record":
            if "label" not in rec:
                raise ValueError(f"record {rec.get('subject_ns')} has no "
                                 "eval label; this paradigm needs one")
            return int(rec["label"])
        task = rec["task"] if "task" in rec else rec["take"]
        return re.sub(r"_trial\d+$", "", task)

    def get_data(self, records):
        """records -> (X list of (T_w, C) windows, y, groups). X stays a
        LIST because native rates differ across records; pipelines own
        the featurization."""
        X, y, groups = [], [], []
        for rec in records:
            sig = self._signal_of(rec)
            fps = float(rec["fps"])
            w = int(round(self.duration_s * fps))
            s = int(round(self.stride_s * fps))
            if w < 2 or sig.shape[0] < w:
                continue
            lab = self._label_of(rec)
            for start in range(0, sig.shape[0] - w + 1, s):
                X.append(sig[start:start + w])
                y.append(lab)
                groups.append(rec["subject_ns"])
        return X, np.asarray(y), np.asarray(groups)
