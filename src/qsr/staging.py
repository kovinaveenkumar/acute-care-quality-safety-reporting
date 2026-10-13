"""Load raw CSVs, apply documented cleaning rules, log every fix, write the clean SQLite database.

Every rule writes a row to dq_log so reviewers can see exactly what changed and how many records.
"""
from __future__ import annotations

import sqlite3
import numpy as np
import pandas as pd

from .config import AS_OF, DB_PATH, RAW_DIR, SQL_DIR, START, END
from .mortality import fit_and_score

UNIT_MAP = {"icu": "ICU", "tele": "TELE", "4w": "TELE", "mse": "MSE", "3east": "MSE", "msw": "MSW", "3west": "MSW",
            "surg": "SURG", "ob": "OB"}


def _norm_unit(s: str) -> str:
    k = str(s).strip().lower().replace(" ", "")
    return UNIT_MAP.get(k, str(s).strip().upper())


def _read(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / f"{name}.csv", **kw)


def clean() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    log: list[dict] = []

    def note(rule, table, desc, n, action):
        log.append(dict(rule_id=rule, table_name=table, description=desc, rows_affected=int(n), action=action))

    # ---------------- encounters
    enc = _read("encounters", parse_dates=["admit_dt", "discharge_dt"])
    n0 = len(enc)
    dup = enc.duplicated(keep="first")
    note("ENC-01", "encounter", "Exact duplicate encounter rows", dup.sum(), "dropped")
    enc = enc[~dup].copy()
    sw = enc.discharge_dt < enc.admit_dt
    note("ENC-02", "encounter", "Discharge earlier than admit (dates swapped)", sw.sum(), "swapped back")
    enc.loc[sw, ["admit_dt", "discharge_dt"]] = enc.loc[sw, ["discharge_dt", "admit_dt"]].to_numpy()
    out = (enc.age > 110) | (enc.age < 0)
    note("ENC-03", "encounter", "Age outside 0-110", out.sum(), "age set to null (excluded from age-based stats)")
    enc.loc[out, "age"] = np.nan
    miss = enc.disposition.isna()
    note("ENC-04", "encounter", "Missing discharge disposition", miss.sum(), "set to 'Unknown' (kept in denominators except where disposition exclusion applies)")
    enc.loc[miss, "disposition"] = "Unknown"
    enc["los_days"] = (enc.discharge_dt - enc.admit_dt).dt.total_seconds() / 86400
    enc["discharge_month"] = enc.discharge_dt.dt.to_period("M").astype(str)
    note("ENC-00", "encounter", "Rows loaded after cleaning", len(enc), f"from {n0} raw rows")

    # ---------------- ED visits
    ed = _read("ed_visits", parse_dates=["arrival_dt", "admit_decision_dt", "depart_dt"])
    bad = ed.depart_dt < ed.arrival_dt
    note("ED-01", "ed_visit", "ED departure before arrival", bad.sum(), "dropped")
    ed = ed[~bad].copy()
    ed["los_min"] = (ed.depart_dt - ed.arrival_dt).dt.total_seconds() / 60
    ed["boarding_min"] = (ed.depart_dt - ed.admit_decision_dt).dt.total_seconds() / 60
    ed["arrival_month"] = ed.arrival_dt.dt.to_period("M").astype(str)

    # ---------------- safety events
    ev = _read("safety_events", parse_dates=["event_dt", "reported_dt", "reviewed_dt"])
    dup = ev.duplicated(subset=[c for c in ev.columns], keep="first")
    note("EVT-01", "safety_event", "Exact duplicate event rows", dup.sum(), "dropped")
    ev = ev[~dup].copy()
    raw_codes = ev.unit_code.copy()
    ev["unit_id"] = ev.unit_code.map(_norm_unit)
    typo = raw_codes != ev.unit_id
    note("EVT-02", "safety_event", "Unit code not in standard form (case/spacing/aliases)", typo.sum(), "mapped to standard unit_id")
    nr = ev.reported_dt.isna()
    note("EVT-03", "safety_event", "Missing reported_dt", nr.sum(), "kept; excluded from timeliness measures")
    rb = ev.reported_dt < ev.event_dt
    note("EVT-04", "safety_event", "Reported before event occurred", rb.sum(), "reported_dt set to event_dt")
    ev.loc[rb, "reported_dt"] = ev.loc[rb, "event_dt"]
    ev["event_month"] = ev.event_dt.dt.to_period("M").astype(str)
    ev["report_lag_hours"] = (ev.reported_dt - ev.event_dt).dt.total_seconds() / 3600
    ev["days_to_close"] = (ev.reviewed_dt - ev.reported_dt).dt.total_seconds() / 86400
    ev = ev.drop(columns=["unit_code"])

    # ---------------- passthrough tables
    inf = _read("infections", parse_dates=["onset_dt"])
    inf["onset_month"] = inf.onset_dt.dt.to_period("M").astype(str)
    cl = _read("core_measure_clinical")
    cl["excluded"] = cl.excluded.astype(int)
    cl["numerator"] = cl.numerator.astype(int)
    cases = _read("abstraction_cases", parse_dates=["selected_dt", "due_dt", "completed_dt"])
    for c in ("abstracted_numerator", "second_numerator"):
        cases[c] = cases[c].map({True: 1, False: 0, "True": 1, "False": 0})
    cases["second_review"] = cases.second_review.astype(int)
    subs = _read("public_reporting_submissions", parse_dates=["due_dt", "submitted_dt"])
    subs["accepted"] = subs.accepted.map({True: 1, False: 0, "True": 1, "False": 0})

    # orphan checks (FK-style) logged for transparency
    orphan = ~ev.encounter_id.isna() & ~ev.encounter_id.isin(enc.encounter_id)
    note("EVT-05", "safety_event", "Event linked to an encounter that does not exist", orphan.sum(), "link cleared")
    ev.loc[orphan, "encounter_id"] = np.nan

    tables = dict(
        unit=_read("units"), patient=_read("patients"), encounter=enc, ed_visit=ed,
        patient_days=_read("patient_days"), device_days=_read("device_days"), infection=inf, safety_event=ev,
        core_measure_clinical=cl, abstraction_case=cases, public_reporting_submission=subs)
    return tables, pd.DataFrame(log)


def build_db(db_path=DB_PATH) -> pd.DataFrame:
    tables, log = clean()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript((SQL_DIR / "schema.sql").read_text())
    for name, df in tables.items():
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({name})")]
        d = df[[c for c in cols if c in df.columns]].copy()
        for c in d.columns:
            if pd.api.types.is_datetime64_any_dtype(d[c]):
                d[c] = d[c].dt.strftime("%Y-%m-%d %H:%M:%S")
        d = d.astype(object).where(d.notna(), None)
        d.to_sql(name, con, if_exists="append", index=False)
    log.to_sql("dq_log", con, if_exists="append", index=False)
    con.execute("INSERT INTO meta VALUES ('as_of', ?)", (AS_OF.strftime('%Y-%m-%d 00:00:00'),))
    mort = fit_and_score(tables['encounter'])
    mort.to_sql('mortality_expected', con, if_exists='append', index=False)
    # measure views
    for f in sorted((SQL_DIR / "measures").glob("*.sql")):
        con.executescript(f.read_text())
    con.commit()
    con.close()
    return log


if __name__ == "__main__":
    lg = build_db()
    print(lg.to_string(index=False))
