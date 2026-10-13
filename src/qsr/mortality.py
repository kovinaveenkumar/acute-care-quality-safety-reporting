"""Risk-adjusted inpatient mortality: logistic regression fit on a baseline window, scored on all discharges.

Observed/Expected (O/E) below 1 means fewer deaths than the baseline case-mix predicts. The model is deliberately
simple (age, comorbidity, diagnosis group, ICU, ED admit) and is NOT a validated CMS/Vizient model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

BASELINE = ("2024-11", "2025-10")


def _features(df: pd.DataFrame) -> pd.DataFrame:
    x = pd.DataFrame(index=df.index)
    x["const"] = 1.0
    age = df.age.fillna(df.age.median())
    x["age_c"] = (age - 65) / 15
    x["charlson"] = df.charlson / 3
    x["icu"] = (df.unit_id == "ICU").astype(float)
    x["from_ed"] = df.from_ed.astype(float)
    for d in sorted(df.dx_group.unique()):
        if d != "OTHER_MED":
            x[f"dx_{d}"] = (df.dx_group == d).astype(float)
    return x


def fit_and_score(enc: pd.DataFrame) -> pd.DataFrame:
    enc = enc[enc.dx_group != "OB"].copy()
    X = _features(enc)
    y = enc.died_flag.to_numpy(float)
    base = enc.discharge_month.between(*BASELINE).to_numpy()

    def nll(b, Xm, ym, l2=1e-2):
        z = Xm @ b
        return np.sum(np.logaddexp(0, z) - ym * z) + l2 * np.sum(b[1:] ** 2)

    def grad(b, Xm, ym, l2=1e-2):
        p = 1 / (1 + np.exp(-(Xm @ b)))
        g = Xm.T @ (p - ym)
        g[1:] += 2 * l2 * b[1:]
        return g

    res = minimize(nll, np.zeros(X.shape[1]), args=(X.to_numpy()[base], y[base]), jac=grad, method="L-BFGS-B")
    p = 1 / (1 + np.exp(-(X.to_numpy() @ res.x)))
    out = pd.DataFrame({"encounter_id": enc.encounter_id.to_numpy(), "expected_p": p})
    # auditable coefficients
    out.attrs["coef"] = dict(zip(X.columns, np.round(res.x, 4)))
    return out
