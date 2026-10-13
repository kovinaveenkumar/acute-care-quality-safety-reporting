"""Independent recomputation: every SQL measure is recalculated in pandas from the clean tables and compared."""
import numpy as np
import pandas as pd
import pytest

from qsr import measures as M
from qsr.config import AS_OF

MONTHS = [str(p) for p in pd.period_range("2024-11", "2026-09", freq="M")]


def _sql(con, key):
    return M.monthly(con).query("measure_key == @key").set_index("month").sort_index()


def _cmp(a: pd.Series, b: pd.Series, tol=1e-9):
    a, b = a.reindex(MONTHS), b.reindex(MONTHS)
    assert a.notna().all() and b.notna().all()
    np.testing.assert_allclose(a.to_numpy(float), b.to_numpy(float), rtol=0, atol=tol)


def test_readmission_rate(con, tables):
    e = tables["encounter"].copy()
    for c in ("admit_dt", "discharge_dt"):
        e[c] = pd.to_datetime(e[c])
    idx = e[(e.died_flag == 0) & (e.age.isna() | (e.age >= 18)) & ~e.dx_group.isin(["OB", "BEH"])
            & ~e.disposition.isin(["Left AMA", "Transferred", "Hospice"])
            & (e.discharge_dt <= AS_OF - pd.Timedelta(days=30))].copy()
    unplanned = e[e.planned_readmit == 0][["patient_id", "encounter_id", "admit_dt"]]
    m = idx[["encounter_id", "patient_id", "discharge_dt", "discharge_month"]].merge(unplanned, on="patient_id", suffixes=("", "_r"))
    hit = m[(m.encounter_id != m.encounter_id_r) & (m.admit_dt > m.discharge_dt) & (m.admit_dt <= m.discharge_dt + pd.Timedelta(days=30))]
    idx["readmitted"] = idx.encounter_id.isin(hit.encounter_id).astype(int)
    py = idx.groupby("discharge_month").readmitted.mean() * 100
    _cmp(_sql(con, "readmit_30d_rate").value, py)


def test_fall_and_medication_rates(con, tables):
    ev, pdays = tables["safety_event"], tables["patient_days"].groupby("month").patient_days.sum()
    for key, typ, extra in (("fall_rate", "Fall", None), ("fall_injury_rate", "Fall", 1), ("med_event_rate", "Medication", None)):
        d = ev[ev.event_type == typ]
        if extra:
            d = d[d.harm_level >= extra]
        py = d.groupby("event_month").size().reindex(MONTHS, fill_value=0) / pdays.reindex(MONTHS) * 1000
        _cmp(_sql(con, key).value, py)


def test_ed_measures(con, tables):
    ed = tables["ed_visit"]
    med = ed[ed.ed_disposition == "Discharged"].groupby("arrival_month").los_min.median()
    _cmp(_sql(con, "ed_los_median").value, med)
    board = ed[ed.ed_disposition == "Admitted"].groupby("arrival_month").boarding_min.median()
    _cmp(_sql(con, "ed_boarding_median").value, board)
    lw = ed.assign(l=(ed.ed_disposition == "LWBS")).groupby("arrival_month").l.mean() * 100
    _cmp(_sql(con, "ed_lwbs_rate").value, lw)


def test_core_measures(con, tables):
    c = tables["core_measure_clinical"].merge(tables["encounter"][["encounter_id", "discharge_month"]], on="encounter_id")
    c = c[c.excluded == 0]
    for meas, key in (("SEP1", "sep1_rate"), ("AMI_ASA", "ami_asa_rate"), ("HF_ACEI", "hf_acei_rate"), ("VTE_PPX", "vte_ppx_rate")):
        py = c[c.measure_id == meas].groupby("discharge_month").numerator.mean() * 100
        got = _sql(con, key).value
        np.testing.assert_allclose(got.reindex(MONTHS).to_numpy(float), py.reindex(MONTHS).to_numpy(float), atol=1e-9)


def test_event_management(con, tables):
    ev = tables["safety_event"]
    r = ev[ev.reported_dt.notna()]
    py = r.assign(ok=r.report_lag_hours <= 24).groupby("event_month").ok.mean() * 100
    _cmp(_sql(con, "event_report_24h").value, py)
    old = r[pd.to_datetime(r.reported_dt) <= AS_OF - pd.Timedelta(days=30)]
    py2 = old.assign(ok=(old.status == "Closed") & (old.days_to_close <= 30)).groupby("event_month").ok.mean() * 100
    got = _sql(con, "event_closed_30d").value
    common = [m for m in MONTHS if m in py2.index]
    np.testing.assert_allclose(got.reindex(common).to_numpy(float), py2.reindex(common).to_numpy(float), atol=1e-9)


def test_abstraction_on_time(con, tables):
    a = tables["abstraction_case"].copy()
    a["due_dt"] = pd.to_datetime(a.due_dt); a["completed_dt"] = pd.to_datetime(a.completed_dt)
    a["month"] = pd.to_datetime(a.selected_dt).dt.strftime("%Y-%m")
    a = a[a.due_dt <= AS_OF]
    py = a.assign(ok=(a.status == "Completed") & (a.completed_dt <= a.due_dt)).groupby("month").ok.mean() * 100
    got = _sql(con, "abstraction_on_time").value
    common = [m for m in MONTHS if m in py.index]
    np.testing.assert_allclose(got.reindex(common).to_numpy(float), py.reindex(common).to_numpy(float), atol=1e-9)


def test_infection_rates(con, tables):
    inf, dev = tables["infection"], tables["device_days"].groupby("month")[["central_line_days", "foley_days"]].sum()
    for key, typ, col in (("clabsi_rate", "CLABSI", "central_line_days"), ("cauti_rate", "CAUTI", "foley_days")):
        n = inf[inf.infection_type == typ].groupby("onset_month").size().reindex(MONTHS, fill_value=0)
        _cmp(_sql(con, key).value, n / dev[col].reindex(MONTHS) * 1000)


def test_patient_days_match_encounters(tables):
    """Midnight census recomputed from encounter admit/discharge; first/last partial months excluded."""
    e = tables["encounter"].copy()
    e["a"], e["d"] = pd.to_datetime(e.admit_dt), pd.to_datetime(e.discharge_dt)
    nights = (e.d.dt.normalize() - e.a.dt.normalize()).dt.days.clip(lower=0)
    # generated before duplicates/swaps were injected, so allow tiny drift from the 8 swapped rows being restored
    assert abs(int(nights.sum()) - int(tables["patient_days"].patient_days.sum())) / nights.sum() < 0.002
