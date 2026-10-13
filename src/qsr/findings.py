"""Turn the computed measures into plain-language findings for the Quality & Safety Committee.

Every number in a finding is computed from the database at build time. Signals are found by scanning the data
(Poisson / chi-square tests against a frozen baseline), not by hard-coding where the planted effects are.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from scipy import stats

from . import measures as M

BASE_START, BASE_END = "2024-11", "2025-10"


def _fmt_q(period: str) -> str:
    return period.replace("Q", " Q")


def scan_event_hotspots(con) -> list[dict]:
    """Unit x event-type 3-month windows with significantly more events than the unit's own baseline."""
    d = pd.read_sql("SELECT unit_id, month, event_type, events, patient_days FROM v_unit_events_monthly", con)
    out = []
    months = sorted(d.month.unique())
    for (unit, et), g in d.groupby(["unit_id", "event_type"]):
        g = g.set_index("month").sort_index()
        base = g.loc[BASE_START:BASE_END]
        if base.events.sum() < 10:
            continue
        rate = base.events.sum() / base.patient_days.sum()
        post = [m for m in months if m > BASE_END]
        for i in range(len(post) - 2):
            w = g.loc[post[i]:post[i + 2]]
            exp = rate * w.patient_days.sum()
            obs = int(w.events.sum())
            if exp > 0 and obs / exp >= 1.8 and obs >= 6:
                p = stats.poisson.sf(obs - 1, exp)
                if p < 0.001:
                    out.append(dict(unit=unit, event_type=et, start=post[i], end=post[i + 2], observed=obs,
                                    expected=round(exp, 1), ratio=obs / exp, p=p,
                                    rate_obs=1000 * obs / w.patient_days.sum(), rate_base=1000 * rate))
    # collapse overlapping windows per unit/type, keep the strongest
    best = {}
    for r in out:
        k = (r["unit"], r["event_type"])
        if k not in best or r["p"] < best[k]["p"]:
            best[k] = r
    return sorted(best.values(), key=lambda r: r["p"])


def infection_clusters(con) -> list[dict]:
    d = pd.read_sql("""SELECT d.unit_id, d.month, d.central_line_days, d.foley_days,
        SUM(i.infection_type='CLABSI') clabsi, SUM(i.infection_type='CAUTI') cauti
        FROM device_days d LEFT JOIN infection i ON i.unit_id=d.unit_id AND i.onset_month=d.month
        GROUP BY d.unit_id, d.month""", con).fillna(0)
    out = []
    for typ, col, days in (("CLABSI", "clabsi", "central_line_days"), ("CAUTI", "cauti", "foley_days")):
        for unit, g in d.groupby("unit_id"):
            g = g.set_index("month").sort_index()
            b = g.loc[BASE_START:BASE_END]
            if b[days].sum() < 500:
                continue
            rate = max(b[col].sum(), 1) / b[days].sum()
            post = [m for m in g.index if m > BASE_END]
            for i in range(len(post) - 1):
                w = g.loc[post[i]:post[i + 1]]
                exp, obs = rate * w[days].sum(), int(w[col].sum())
                if obs >= 3 and stats.poisson.sf(obs - 1, exp) < 0.01:
                    out.append(dict(unit=unit, type=typ, start=post[i], end=post[i + 1], observed=obs, expected=round(exp, 1),
                                    p=stats.poisson.sf(obs - 1, exp), rate_obs=1000 * obs / w[days].sum(), rate_base=1000 * rate))
    return sorted(out, key=lambda r: r["p"])[:3]


def sep1_driver(con) -> dict | None:
    d = pd.read_sql("""SELECT e.discharge_month month, c.detail FROM core_measure_clinical c
        JOIN encounter e ON e.encounter_id=c.encounter_id WHERE c.measure_id='SEP1' AND c.excluded=0""", con)
    det = pd.json_normalize(d.detail.map(json.loads))
    d = pd.concat([d[["month"]], det], axis=1)
    d = d[(d.month >= BASE_START) & (d.month <= "2026-09")]
    d["bundle"] = d[["lactate", "cx", "abx", "fluids", "repeat_lac"]].all(axis=1)
    monthly = d.groupby("month").bundle.mean() * 100
    base = d[d.month.between(BASE_START, BASE_END)]
    worst = monthly.loc["2025-11":].idxmin()
    # window = 3 months ending at worst-month+1
    win_months = [m for m in monthly.index if abs((pd.Period(m) - pd.Period(worst)).n) <= 1]
    win = d[d.month.isin(win_months)]
    elems = {"lactate": "initial lactate", "cx": "blood culture before antibiotics", "abx": "antibiotics within 3h",
             "fluids": "fluid resuscitation (hypotension)", "repeat_lac": "repeat lactate within 6h"}
    rows = []
    for k, label in elems.items():
        if k == "fluids":
            b, w = base[base.hypotension][k].mean(), win[win.hypotension][k].mean()
        elif k == "repeat_lac":
            b, w = base[base.initial_lactate_gt2][k].mean(), win[win.initial_lactate_gt2][k].mean()
        else:
            b, w = base[k].mean(), win[k].mean()
        rows.append((label, 100 * b, 100 * w))
    rows.sort(key=lambda r: r[2] - r[1])
    return dict(worst_month=worst, worst_value=float(monthly[worst]), base=float(100 * base.bundle.mean()),
                window=f"{min(win_months)} to {max(win_months)}", elements=rows)


def vte_gap(con) -> dict | None:
    d = pd.read_sql("SELECT * FROM v_vte_drilldown", con)
    d["fail"] = d.denominator - d.numerator
    d["key"] = d.unit_id + " " + d.admit_day_type
    worst = d.sort_values("value").iloc[0]
    rest_n = d.denominator.sum() - worst.denominator
    rest_f = d.fail.sum() - worst.fail
    table = [[worst.fail, worst.denominator - worst.fail], [rest_f, rest_n - rest_f]]
    chi2, p, *_ = stats.chi2_contingency(table)
    return dict(cell=worst.key, value=float(worst.value), n=int(worst.denominator), rest=float(100 * (1 - rest_f / rest_n)), p=float(p))


def build(con, m, s, q, sc, subs: pd.DataFrame, aging: pd.DataFrame) -> list[dict]:
    F = []

    def add(domain, severity, title, evidence, action):
        F.append(dict(domain=domain, severity=severity, title=title, evidence=evidence, action=action))

    # --- event hotspots
    for h in scan_event_hotspots(con)[:3]:
        add("Patient Safety", "High" if h["ratio"] > 2.2 else "Medium",
            f"{h['event_type']} events on {h['unit']} well above that unit's own baseline",
            f"{h['start']} to {h['end']}: {h['observed']} events vs {h['expected']} expected "
            f"({h['rate_obs']:.1f} vs {h['rate_base']:.1f} per 1,000 patient days; {h['ratio']:.1f}x; Poisson p={h['p']:.1g}).",
            "Review the event narratives for the window, check for a process or equipment change at that time, and report back to the committee with an action plan.")
    for c in infection_clusters(con)[:2]:
        add("Patient Safety", "High",
            f"{c['type']} cluster on {c['unit']}",
            f"{c['start']} to {c['end']}: {c['observed']} infections vs {c['expected']} expected "
            f"({c['rate_obs']:.1f} vs {c['rate_base']:.1f} per 1,000 device days; Poisson p={c['p']:.1g}).",
            "Infection Prevention to review maintenance-bundle audits and line insertion/removal practice for those months.")
    # med-event house-level spike
    med = s[(s.measure_key == "med_event_rate") & s.sig_limit]
    if not med.empty:
        r = med.iloc[0]
        add("Patient Safety", "Medium", "Medication event rate above the upper control limit",
            f"{r.month}: {r.value:.1f} per 1,000 patient days vs centre line {r.center:.1f} (UCL {r.ucl:.1f}).",
            "Compare with the timing of system changes (e.g., EHR updates) and sample events for ordering/administration steps.")
    # --- core measures
    d = sep1_driver(con)
    if d and d["worst_value"] < d["base"] - 8:
        w = d["elements"][0]
        add("Core Measures", "High", "Sepsis bundle compliance dipped well below baseline",
            f"Lowest month {d['worst_month']}: {d['worst_value']:.0f}% vs a {d['base']:.0f}% baseline. In {d['window']} the weakest element was "
            f"{w[0]} ({w[2]:.0f}% vs {w[1]:.0f}% at baseline).",
            "Check whether order sets or documentation changed in that window; re-educate on the failing element.")
    v = vte_gap(con)
    if v and v["p"] < 0.01:
        add("Core Measures", "Medium", f"VTE prophylaxis gap: {v['cell']}",
            f"{v['cell']}: {v['value']:.1f}% (n={v['n']}) vs {v['rest']:.1f}% for all other unit/day combinations (chi-square p={v['p']:.1g}).",
            "Review weekend admission order-set use and pharmacy verification on that unit.")
    reds = sc[sc.status == "Red"]
    if not reds.empty:
        items = "; ".join(f"{r.measure} {r.current:.1f} (target {r.target:g})" for r in reds.itertuples())
        add("Scorecard", "Medium", f"{len(reds)} measure(s) are Red in the latest quarter",
            items + ". Small denominators make single-quarter infection rates volatile; interpret with the control charts.",
            "Review the red measures with the owning department and confirm whether each is a real change or normal variation.")
    # --- outcomes
    hf = q[q.measure_key == "readmit_30d_hf"].sort_values("quarter")
    if not hf.empty:
        top = hf.loc[hf.value.idxmax()]
        if top.value > 22:
            add("Outcomes", "Medium", "Heart-failure 30-day readmissions peaked",
                f"{_fmt_q(top.quarter)}: {top.value:.1f}% (target 20%). Latest quarter {hf.iloc[-1].value:.1f}%.",
                "Review post-discharge follow-up scheduling and discharge education for HF patients discharged in the peak quarter.")
    # --- ED
    ed = s[s.measure_key.isin(["ed_los_median", "ed_boarding_median", "ed_lwbs_rate"]) & s.sig_limit]
    if not ed.empty:
        months = sorted(ed.month.unique())
        parts = []
        for k, g in ed.groupby("measure_key"):
            parts.append(f"{M.TARGETS[k]['label'].split(' (')[0]} peaked at {g.value.max():.1f}" if hasattr(M, 'TARGETS') else "")
        from .config import TARGETS
        parts = [f"{TARGETS[k]['label']}: peak {g.value.max():.1f}" for k, g in ed.groupby("measure_key")]
        add("Emergency Department", "Medium", "ED throughput signals during the winter surge",
            f"Out-of-control points in {months[0]} to {months[-1]}. " + "; ".join(parts) + ".",
            "Review surge staffing and inpatient bed-flow plans before next winter.")
    # --- quality operations
    ab = s[(s.measure_key == "abstraction_on_time") & s.sig_limit]
    if not ab.empty:
        add("Quality Operations", "Medium", "Abstraction backlog",
            f"On-time completion fell to {ab.value.min():.0f}% (centre line {ab.center.iloc[0]:.0f}%) for cases selected "
            f"{ab.month.min()} to {ab.month.max()}.",
            "Rebalance case assignment across abstractors; protect time before quarterly submission deadlines.")
    late = subs[subs.status.isin(["Submitted late", "OVERDUE"])]
    for r in late.itertuples():
        add("Quality Operations", "High" if r.status == "OVERDUE" else "Medium",
            f"Public-reporting submission {r.status.lower()}: {r.measure_id} {r.quarter}",
            f"Due {str(r.due_dt)[:10]}; submitted {str(r.submitted_dt)[:10] if r.submitted_dt else 'not submitted'}.",
            "Add a 30-day reminder to the abstraction calendar and name a backup submitter.")
    old = aging[aging.age_bucket == ">30 days"].events.sum() if not aging.empty else 0
    if old:
        hh = int(aging[aging.age_bucket == ">30 days"].high_harm_events.sum())
        add("Quality Operations", "Medium", "Safety events open longer than 30 days",
            f"{int(old)} events are still not closed more than 30 days after reporting ({hh} with harm level 3 or higher).",
            "Escalate the high-harm items to the Director of Quality, Risk and Patient Safety.")
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(F, key=lambda f: order[f["severity"]])
