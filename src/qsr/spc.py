"""Statistical process control: p-, u- and individuals (XmR) charts with Nelson-style signal rules.

Centre line and limits are frozen on a baseline window so that later deterioration shows up as a signal
instead of being absorbed into the limits.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SHIFT_RUN = 8   # consecutive points on one side of the centre line
TREND_RUN = 6   # consecutive points steadily rising or falling


def _runs_same_side(side: np.ndarray, k: int) -> np.ndarray:
    flag = np.zeros(len(side), bool)
    run = 0
    for i, s in enumerate(side):
        run = run + 1 if (i > 0 and s != 0 and s == side[i - 1]) else (1 if s != 0 else 0)
        if run >= k:
            flag[i - k + 1: i + 1] = True
    return flag


def _trend(values: np.ndarray, k: int) -> np.ndarray:
    flag = np.zeros(len(values), bool)
    for i in range(k - 1, len(values)):
        w = values[i - k + 1: i + 1]
        d = np.diff(w)
        if np.all(d > 0) or np.all(d < 0):
            flag[i - k + 1: i + 1] = True
    return flag


def control_chart(df: pd.DataFrame, kind: str, scale: float, baseline_n: int = 12) -> pd.DataFrame:
    """df columns: month, numerator, denominator, value (already scaled).  kind in {'p','u','i'}."""
    d = df.sort_values("month").reset_index(drop=True).copy()
    base = d.iloc[:baseline_n]
    if kind in ("p", "u"):
        cl = base.numerator.sum() / base.denominator.sum()          # unscaled proportion / rate
        n = d.denominator.to_numpy(float)
        if kind == "p":
            sd = np.sqrt(cl * (1 - cl) / n)
            ucl = np.minimum(cl + 3 * sd, 1.0)
            lcl = np.maximum(cl - 3 * sd, 0.0)
        else:
            sd = np.sqrt(cl / n)
            ucl, lcl = cl + 3 * sd, np.maximum(cl - 3 * sd, 0.0)
        d["center"], d["ucl"], d["lcl"] = cl * scale, ucl * scale, lcl * scale
    else:  # individuals chart on the value itself
        v = base.value.to_numpy(float)
        mr = np.abs(np.diff(v)).mean()
        cl = v.mean()
        d["center"], d["ucl"], d["lcl"] = cl, cl + 2.66 * mr, max(cl - 2.66 * mr, 0.0)
    side = np.sign(d.value - d.center).to_numpy()
    d["sig_limit"] = (d.value > d.ucl) | (d.value < d.lcl)
    d["sig_shift"] = _runs_same_side(side, SHIFT_RUN)
    d["sig_trend"] = _trend(d.value.to_numpy(float), TREND_RUN)
    d["any_signal"] = d.sig_limit | d.sig_shift | d.sig_trend
    return d
