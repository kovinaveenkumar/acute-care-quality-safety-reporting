"""The cleaning step must find exactly the defects the generator injected."""
import json

from qsr.config import RAW_DIR


def _rows(log, rule):
    return int(log.loc[log.rule_id == rule, "rows_affected"].iloc[0])


def test_cleaning_matches_injected_defects(pipeline):
    m = json.loads((RAW_DIR / "_defect_manifest.json").read_text())
    assert _rows(pipeline, "ENC-01") == m["encounter_duplicate_rows"]
    assert _rows(pipeline, "ENC-02") == m["encounter_dates_swapped"]
    assert _rows(pipeline, "ENC-03") == m["encounter_age_outlier"]
    assert _rows(pipeline, "ENC-04") == m["encounter_missing_disposition"]
    assert _rows(pipeline, "EVT-01") == m["event_duplicate_rows"]
    assert _rows(pipeline, "EVT-02") == m["event_unit_code_typo"]
    assert _rows(pipeline, "EVT-03") == m["event_missing_reported_dt"]
    assert _rows(pipeline, "EVT-04") == m["event_reported_before_event"]


def test_clean_tables_have_no_remaining_defects(tables):
    e, ev = tables["encounter"], tables["safety_event"]
    assert e.encounter_id.is_unique and ev.event_id.is_unique
    assert (e.discharge_dt >= e.admit_dt).all()
    assert (e.los_days >= 0).all()
    assert e.age.dropna().between(0, 110).all()
    assert e.disposition.notna().all()
    assert set(ev.unit_id) <= {"ICU", "TELE", "MSE", "MSW", "SURG", "OB"}
    assert (ev.report_lag_hours.dropna() >= 0).all()


def test_referential_integrity(con):
    q = lambda sql: con.execute(sql).fetchone()[0]
    assert q("SELECT COUNT(*) FROM encounter e LEFT JOIN unit u ON u.unit_id=e.unit_id WHERE u.unit_id IS NULL") == 0
    assert q("SELECT COUNT(*) FROM safety_event s LEFT JOIN encounter e ON e.encounter_id=s.encounter_id "
             "WHERE s.encounter_id IS NOT NULL AND e.encounter_id IS NULL") == 0
    assert q("SELECT COUNT(*) FROM abstraction_case a LEFT JOIN encounter e ON e.encounter_id=a.encounter_id WHERE e.encounter_id IS NULL") == 0
    assert q("SELECT COUNT(*) FROM core_measure_clinical c LEFT JOIN encounter e ON e.encounter_id=c.encounter_id WHERE e.encounter_id IS NULL") == 0
    assert q("SELECT COUNT(*) FROM abstraction_case WHERE due_dt <= selected_dt") == 0
