"""Pull measures from the SQL views, run SPC, build the quarterly scorecard and drill-downs."""
from __future__ import annotations

import sqlite3
import numpy as np
import pandas as pd

from .config import DB_PATH, TARGETS
from .spc import control_chart

# measure_key -> (chart kind, scale factor to the displayed value)
MEASURE_KIND = {
    "readmit_30d_rate": ("p", 100), "readmit_30d_hf": ("p", 100), "readmit_30d_ami": ("p", 100), "readmit_30d_pn": ("p", 100),
    "fall_rate": ("u", 1000), "fall_injury_rate": ("u", 1000), "med_event_rate": ("u", 1000),
    "clabsi_rate": ("u", 1000), "cauti_rate": ("u", 1000),
    "ed_los_median": ("i", 1), "ed_boarding_median": ("i", 1), "ed_lwbs_rate": ("p", 100),
    "sep1_rate": ("p", 100), "ami_asa_rate": ("p", 100), "hf_acei_rate": ("p", 100), "vte_ppx_rate": ("p", 100),
    "mortality_oe": ("i", 1), "event_report_24h": ("p", 100), "event_closed_30d": ("p", 100), "abstraction_on_time": ("p", 100),
}
SCORECARD_ORDER = [
    ("Patient Safety", ["fall_rate", "fall_injury_rate", "med_event_rate", "clabsi_rate", "cauti_rate"]),
    ("Outcomes", ["readmit_30d_rate", "readmit_30d_hf", "mortality_oe"]),
    ("Core Measures", ["sep1_rate", "ami_asa_rate", "hf_acei_rate", "vte_ppx_rate"]),
    ("Emergency Department", ["ed_los_median", "ed_boarding_median", "ed_lwbs_rate"]),
    ("Quality Operations", ["event_report_24h", "event_closed_30d", "abstraction_on_time"]),
]


def connect(path=DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(path)


def monthly(con) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM v_monthly_measures ORDER BY measure_key, month", con)


def spc_all(m: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for key, (kind, scale) in MEASURE_KIND.items():
        d = m[m.measure_key == key].copy()
        if d.empty:
            continue
        c = control_chart(d, kind, scale)
        c["measure_key"] = key
        parts.append(c)
    return pd.concat(parts, ignore_index=True)


def quarter_of(month: str) -> str:
    return str(pd.Period(month, freq="M").asfreq("Q"))


def _median_quarterly(con, kind: str) -> pd.DataFrame:
    if kind == "ed_los_median":
        q = "SELECT arrival_dt, los_min v FROM ed_visit WHERE ed_disposition='Discharged'"
    else:
        q = "SELECT arrival_dt, boarding_min v FROM ed_visit WHERE ed_disposition='Admitted'"
    d = pd.read_sql(q, con, parse_dates=["arrival_dt"])
    d["quarter"] = d.arrival_dt.dt.to_period("Q").astype(str)
    out = d.groupby("quarter").v.median().rename("value").reset_index()
    out["measure_key"] = kind
    return out


def quarterly(con, m: pd.DataFrame) -> pd.DataFrame:
    m = m.copy()
    m["quarter"] = m.month.map(quarter_of)
    rows = []
    for key, g in m.groupby("measure_key"):
        kind, scale = MEASURE_KIND[key]
        if key in ("ed_los_median", "ed_boarding_median"):
            continue
        if key == "mortality_oe":
            for q, h in g.groupby("quarter"):
                rows.append((key, q, h.numerator.sum() / h.denominator.sum(), h.denominator.sum()))
        else:
            for q, h in g.groupby("quarter"):
                rows.append((key, q, h.numerator.sum() / h.denominator.sum() * scale, h.denominator.sum()))
    qdf = pd.DataFrame(rows, columns=["measure_key", "quarter", "value", "denominator"])
    for k in ("ed_los_median", "ed_boarding_median"):
        x = _median_quarterly(con, k)
        x["denominator"] = np.nan
        qdf = pd.concat([qdf, x], ignore_index=True)
    # drop partial first quarter (2024Q4 only has Nov-Dec)
    full = m.groupby("quarter").month.nunique()
    keep = full[full == 3].index
    return qdf[qdf.quarter.isin(keep)].reset_index(drop=True)


def rag(value: float, key: str) -> str:
    t = TARGETS[key]
    tgt, direction = t["target"], t["direction"]
    if direction == "lower":
        if value <= tgt: return "Green"
        return "Amber" if value <= tgt * 1.10 else "Red"
    if value >= tgt: return "Green"
    return "Amber" if value >= tgt * 0.93 else "Red"


def scorecard(q: pd.DataFrame, current: str | None = None) -> pd.DataFrame:
    quarters = sorted(q.quarter.unique())
    current = current or quarters[-1]
    cur_p = pd.Period(current)
    prior, yago = str(cur_p - 1), str(cur_p - 4)
    piv = q.pivot(index="measure_key", columns="quarter", values="value")
    rows = []
    for domain, keys in SCORECARD_ORDER:
        for k in keys:
            t = TARGETS[k]
            cur = piv.loc[k, current]
            pr = piv.loc[k, prior] if prior in piv.columns else np.nan
            ya = piv.loc[k, yago] if yago in piv.columns else np.nan
            better_if_lower = t["direction"] == "lower"
            delta = cur - pr
            improving = (delta < 0) == better_if_lower
            rows.append(dict(domain=domain, measure_key=k, measure=t["label"], target=t["target"], direction=t["direction"],
                             current=cur, prior=pr, year_ago=ya, delta_vs_prior=delta,
                             trend=("improving" if improving else "worsening") if abs(delta) > 1e-9 else "flat",
                             status=rag(cur, k)))
    return pd.DataFrame(rows)


def unit_drilldown(con, key: str) -> pd.DataFrame:
    event_type = {"fall_rate": "Fall", "med_event_rate": "Medication"}[key]
    df = pd.read_sql("SELECT unit_id, month, events, patient_days FROM v_unit_events_monthly WHERE event_type = ?", con, params=(event_type,))
    df["quarter"] = df.month.map(quarter_of)
    g = df.groupby(["unit_id", "quarter"]).agg(events=("events", "sum"), patient_days=("patient_days", "sum")).reset_index()
    g["per_1000_pd"] = 1000 * g.events / g.patient_days
    return g


def cohen_kappa(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = np.mean(a == b)
    pe = np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b))
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def irr(con) -> pd.DataFrame:
    d = pd.read_sql("SELECT * FROM v_second_review", con)
    rows = []
    for meas, g in list(d.groupby("measure_id")) + [("ALL", d)]:
        rows.append(dict(measure_id=meas, pairs=len(g), percent_agreement=100 * np.mean(g.rater1 == g.rater2),
                         kappa=cohen_kappa(g.rater1, g.rater2)))
    return pd.DataFrame(rows)


def signals_summary(s: pd.DataFrame) -> pd.DataFrame:
    """Latest signalling run for each measure and whether it is adverse relative to target direction."""
    rows = []
    for key, g in s.groupby("measure_key"):
        g = g.sort_values("month")
        sig = g[g.any_signal]
        if sig.empty:
            continue
        direction = TARGETS[key]["direction"]
        adverse = ((sig.value > sig.center) if direction == "lower" else (sig.value < sig.center))
        rows.append(dict(measure_key=key, label=TARGETS[key]["label"], first_signal=sig.month.min(), last_signal=sig.month.max(),
                         signal_months=len(sig), adverse_months=int(adverse.sum()),
                         peak_month=(sig.loc[sig.value.idxmax(), "month"] if direction == "lower" else sig.loc[sig.value.idxmin(), "month"]),
                         limit_breaches=int(sig.sig_limit.sum()), shifts=int(sig.sig_shift.sum()), trends=int(sig.sig_trend.sum())))
    return pd.DataFrame(rows).sort_values("adverse_months", ascending=False)
