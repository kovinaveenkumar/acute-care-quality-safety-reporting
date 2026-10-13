"""Export everything the QualityLens web app needs into app/data.js (works from file://, no server)."""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from . import measures as M
from .config import AS_OF, HOSPITAL, ROOT, TARGETS
from .report_data import collect

DEFS = {
    "readmit_30d_rate": ("Unplanned return to the hospital within 30 days of discharge.", "Index stays with an unplanned readmission", "Eligible index stays (adult, alive, not OB/behavioral, not AMA/transfer/hospice)"),
    "readmit_30d_hf": ("30-day unplanned readmission for heart-failure index stays.", "HF index stays readmitted", "Eligible HF index stays"),
    "fall_rate": ("Reported patient falls per 1,000 midnight-census patient days.", "Fall events", "Patient days"),
    "fall_injury_rate": ("Falls with any documented harm per 1,000 patient days.", "Fall events with harm level 1+", "Patient days"),
    "med_event_rate": ("Reported medication events per 1,000 patient days.", "Medication events", "Patient days"),
    "clabsi_rate": ("Central-line associated bloodstream infections per 1,000 central-line days.", "CLABSI events", "Central-line days"),
    "cauti_rate": ("Catheter-associated urinary tract infections per 1,000 catheter days.", "CAUTI events", "Urinary catheter days"),
    "ed_los_median": ("Median minutes from ED arrival to departure for patients discharged from the ED.", "n/a (median)", "Discharged ED patients"),
    "ed_boarding_median": ("Median minutes from admit decision to ED departure for admitted patients.", "n/a (median)", "Admitted ED patients"),
    "ed_lwbs_rate": ("Share of ED visits where the patient left before being seen.", "LWBS visits", "All ED visits"),
    "sep1_rate": ("Sepsis bundle: lactate, culture before antibiotics, antibiotics, fluids if hypotensive, repeat lactate if initial > 2. All applicable elements must be met.", "Cases meeting every element", "Non-excluded sepsis cases"),
    "ami_asa_rate": ("Aspirin given within 24h of arrival for AMI.", "Aspirin given", "Non-excluded AMI cases"),
    "hf_acei_rate": ("ACEI/ARB/ARNI prescribed at discharge for HF with reduced ejection fraction.", "Prescribed", "Non-excluded HF-LVSD discharges"),
    "vte_ppx_rate": ("VTE prophylaxis received by end of admission day 1, adult med/surg stays of 2+ days.", "Prophylaxis received", "Non-excluded eligible stays"),
    "mortality_oe": ("Observed inpatient deaths divided by deaths expected from a simple logistic case-mix model.", "Observed deaths", "Expected deaths (sum of model probabilities)"),
    "event_report_24h": ("Safety events reported within 24 hours of occurrence.", "Reported within 24h", "Events with a reported time"),
    "event_closed_30d": ("Safety events closed within 30 days of report (only events old enough to qualify).", "Closed within 30 days", "Events reported 30+ days before extract"),
    "abstraction_on_time": ("Abstraction cases completed by their due date.", "Completed on or before due date", "Cases due on or before extract date"),
}
UNIT_NAMES = {"ICU": "ICU", "TELE": "4 West Tele", "MSE": "3 East Med-Surg", "MSW": "3 West Med-Surg", "SURG": "5 North Surgical", "OB": "2 East OB"}


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating, float)): return None if np.isnan(o) else round(float(o), 4)
    if isinstance(o, (np.bool_, bool)): return bool(o)
    if isinstance(o, pd.Timestamp): return o.strftime("%Y-%m-%d")
    return o


def main():
    con = M.connect()
    d = collect(con)
    s, q, m = d["spc"], d["quarterly"], d["monthly"]
    measures = {}
    for key, t in TARGETS.items():
        sd = s[s.measure_key == key].sort_values("month")
        qd = q[q.measure_key == key].sort_values("quarter")
        measures[key] = dict(
            key=key, label=t["label"], target=t["target"], direction=t["direction"], kind=M.MEASURE_KIND[key][0],
            domain=next(dom for dom, ks in M.SCORECARD_ORDER if key in ks),
            definition=DEFS[key][0], numerator=DEFS[key][1], denominator=DEFS[key][2],
            monthly=[dict(m=r.month, v=r.value, c=r.center, u=r.ucl, l=r.lcl, n=r.numerator, d=r.denominator,
                          s=int(r.sig_limit) + 2 * int(r.sig_shift) + 4 * int(r.sig_trend)) for r in sd.itertuples()],
            quarterly=[dict(q=r.quarter, v=r.value) for r in qd.itertuples()])
    for key in ("readmit_30d_ami", "readmit_30d_pn"):
        pass
    ev = pd.read_sql("""SELECT event_id id, event_type type, unit_id unit, harm_level harm, status, substr(event_dt,1,16) occurred,
        substr(reported_dt,1,16) reported, substr(reviewed_dt,1,16) reviewed, root_cause cause, reporter_role role,
        ROUND(report_lag_hours,1) lag, encounter_id enc FROM safety_event WHERE event_month IN (SELECT month FROM v_months)
        ORDER BY event_dt""", con)
    cases = pd.read_sql("""SELECT case_id id, measure_id measure, encounter_id enc, abstractor, status, substr(selected_dt,1,10) selected,
        substr(due_dt,1,10) due, substr(completed_dt,1,10) completed, second_review second FROM abstraction_case ORDER BY selected_dt, case_id""", con)
    ed = pd.read_sql("SELECT arrival_dt, los_min FROM ed_visit WHERE ed_disposition='Discharged' AND arrival_month IN (SELECT month FROM v_months)", con, parse_dates=["arrival_dt"])
    ed["dow"], ed["hr"] = ed.arrival_dt.dt.weekday, ed.arrival_dt.dt.hour
    heat = ed.groupby(["dow", "hr"]).los_min.agg(["median", "size"]).reset_index()
    um = pd.read_sql("""SELECT unit_id unit, month, SUM(events) events, MAX(patient_days) pd FROM v_unit_events_monthly GROUP BY unit_id, month""", con)
    tm = pd.read_sql("""SELECT event_month month, event_type type, COUNT(*) n FROM safety_event WHERE event_month IN (SELECT month FROM v_months) GROUP BY 1,2""", con)
    harm_type = pd.read_sql("""SELECT event_type type, harm_level harm, COUNT(*) n FROM safety_event WHERE event_month IN (SELECT month FROM v_months) GROUP BY 1,2""", con)
    fu = d["fall_units"]; mu = d["med_units"]
    vte = d["vte"]
    payload = dict(
        meta=dict(hospital=HOSPITAL, as_of=AS_OF.strftime("%Y-%m-%d"), current_quarter=d["current_quarter"],
                  months=sorted(m.month.unique().tolist()), units=UNIT_NAMES, volumes=d["volumes"]),
        scorecard_order=[dict(domain=dom, keys=ks) for dom, ks in M.SCORECARD_ORDER],
        measures=measures,
        readmit_by_dx={k: [dict(m=r.month, v=r.value, n=r.numerator, d=r.denominator) for r in m[m.measure_key == k].sort_values("month").itertuples()] for k in ("readmit_30d_hf", "readmit_30d_ami", "readmit_30d_pn")},
        findings=d["findings"],
        signals=d["signals"].to_dict("records"),
        events=ev.to_dict("records"), cases=cases.to_dict("records"),
        workload=d["workload"].to_dict("records"), irr=d["irr"].to_dict("records"), validation=d["validation"].to_dict("records"),
        submissions=d["submissions"].assign(due=lambda x: x.due_dt.str[:10], sub=lambda x: x.submitted_dt.str[:10])[["measure_id", "quarter", "due", "sub", "records_submitted", "accepted", "status"]].to_dict("records"),
        ed_heat=[dict(dow=int(r.dow), hr=int(r.hr), med=float(r.median), n=int(r.size)) for r in heat.itertuples()],
        unit_month=um.to_dict("records"), type_month=tm.to_dict("records"), harm_type=harm_type.to_dict("records"),
        falls_unit=fu.to_dict("records"), meds_unit=mu.to_dict("records"), vte=vte.to_dict("records"),
        aging=d["aging"].to_dict("records"), dq=d["dq"].to_dict("records"),
        tests=dict(count=30, note="pytest suite in tests/ (independent SQL-vs-pandas recomputation, cleaning vs injected defects, SPC, detection)"),
    )
    out = ROOT / "app" / "data.js"
    out.write_text("window.QL_DATA = " + json.dumps(_clean(payload), separators=(",", ":")) + ";\n")
    print("wrote", out, f"{out.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
