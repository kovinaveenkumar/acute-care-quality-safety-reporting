"""Collect every table the report formats need, once."""
from __future__ import annotations

import pandas as pd

from . import findings as FD
from . import measures as M
from .config import AS_OF, HOSPITAL, TARGETS


def collect(con) -> dict:
    m = M.monthly(con)
    s = M.spc_all(m)
    q = M.quarterly(con, m)
    sc = M.scorecard(q)
    subs = pd.read_sql("SELECT * FROM v_submission_status", con)
    aging = pd.read_sql("SELECT * FROM v_event_aging", con)
    d = dict(
        hospital=HOSPITAL, as_of=AS_OF, monthly=m, spc=s, quarterly=q, scorecard=sc, submissions=subs, aging=aging,
        signals=M.signals_summary(s), irr=M.irr(con),
        workload=pd.read_sql("SELECT * FROM v_abstractor_workload ORDER BY abstractor", con),
        validation=pd.read_sql("SELECT * FROM v_data_validation", con),
        vte=pd.read_sql("SELECT * FROM v_vte_drilldown", con),
        fall_units=M.unit_drilldown(con, "fall_rate"), med_units=M.unit_drilldown(con, "med_event_rate"),
        dq=pd.read_sql("SELECT * FROM dq_log", con),
        events_by_type=pd.read_sql("""SELECT event_type, COUNT(*) AS events, SUM(harm_level>=3) AS serious,
            ROUND(100.0*SUM(report_lag_hours<=24)/COUNT(report_lag_hours),1) AS pct_reported_24h
            FROM safety_event WHERE event_month IN (SELECT month FROM v_months) GROUP BY event_type ORDER BY events DESC""", con),
        harm=pd.read_sql("""SELECT harm_level, COUNT(*) AS events FROM safety_event
            WHERE event_month IN (SELECT month FROM v_months) GROUP BY harm_level ORDER BY harm_level""", con),
        open_cases=pd.read_sql("""SELECT case_id, measure_id, encounter_id, abstractor, status, selected_dt, due_dt,
            CAST(julianday((SELECT v FROM meta WHERE k='as_of')) - julianday(due_dt) AS INTEGER) AS days_overdue
            FROM abstraction_case WHERE status <> 'Completed' ORDER BY due_dt""", con),
        open_events=pd.read_sql("""SELECT event_id, event_type, unit_id, harm_level, status, reported_dt,
            CAST(julianday((SELECT v FROM meta WHERE k='as_of')) - julianday(reported_dt) AS INTEGER) AS days_open
            FROM safety_event WHERE status <> 'Closed' ORDER BY harm_level DESC, reported_dt""", con),
        volumes=pd.read_sql("""SELECT (SELECT COUNT(*) FROM encounter) AS encounters, (SELECT COUNT(*) FROM ed_visit) AS ed_visits,
            (SELECT COUNT(*) FROM safety_event) AS events, (SELECT COUNT(*) FROM abstraction_case) AS cases""", con).iloc[0].to_dict(),
    )
    d["current_quarter"] = sorted(q.quarter.unique())[-1]
    d["findings"] = FD.build(con, m, s, q, sc, subs, aging)
    return d
