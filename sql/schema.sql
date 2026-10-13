-- Clean (staging-validated) schema. Raw CSVs are loaded into raw_* tables first,
-- then cleaned in qsr.staging and written into these tables.
DROP TABLE IF EXISTS dq_log;
CREATE TABLE dq_log (
  rule_id TEXT, table_name TEXT, description TEXT, rows_affected INTEGER, action TEXT
);

DROP TABLE IF EXISTS unit;
CREATE TABLE unit (unit_id TEXT PRIMARY KEY, unit_name TEXT, unit_type TEXT, beds INTEGER);

DROP TABLE IF EXISTS patient;
CREATE TABLE patient (patient_id INTEGER PRIMARY KEY, birth_year INTEGER, sex TEXT, payer TEXT);

DROP TABLE IF EXISTS encounter;
CREATE TABLE encounter (
  encounter_id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL, dx_group TEXT NOT NULL, unit_id TEXT NOT NULL,
  age INTEGER, charlson INTEGER, admit_dt TEXT NOT NULL, discharge_dt TEXT NOT NULL,
  from_ed INTEGER, died_flag INTEGER, planned_readmit INTEGER, index_of INTEGER, payer TEXT,
  attending_id INTEGER, disposition TEXT, los_days REAL, discharge_month TEXT,
  FOREIGN KEY (unit_id) REFERENCES unit(unit_id)
);
CREATE INDEX ix_enc_patient ON encounter(patient_id, admit_dt);
CREATE INDEX ix_enc_month ON encounter(discharge_month);

DROP TABLE IF EXISTS ed_visit;
CREATE TABLE ed_visit (
  ed_visit_id INTEGER PRIMARY KEY, encounter_id INTEGER, patient_id INTEGER, arrival_dt TEXT NOT NULL,
  admit_decision_dt TEXT, depart_dt TEXT NOT NULL, ed_disposition TEXT, acuity INTEGER,
  los_min REAL, boarding_min REAL, arrival_month TEXT
);
CREATE INDEX ix_ed_month ON ed_visit(arrival_month);

DROP TABLE IF EXISTS patient_days;
CREATE TABLE patient_days (unit_id TEXT, month TEXT, patient_days INTEGER, PRIMARY KEY (unit_id, month));

DROP TABLE IF EXISTS device_days;
CREATE TABLE device_days (unit_id TEXT, month TEXT, central_line_days INTEGER, foley_days INTEGER, PRIMARY KEY (unit_id, month));

DROP TABLE IF EXISTS infection;
CREATE TABLE infection (infection_id INTEGER PRIMARY KEY, encounter_id INTEGER, unit_id TEXT, infection_type TEXT, onset_dt TEXT, onset_month TEXT);

DROP TABLE IF EXISTS safety_event;
CREATE TABLE safety_event (
  event_id INTEGER PRIMARY KEY, event_dt TEXT NOT NULL, reported_dt TEXT, unit_id TEXT, event_type TEXT,
  harm_level INTEGER, status TEXT, reviewed_dt TEXT, root_cause TEXT, reporter_role TEXT, encounter_id INTEGER,
  event_month TEXT, report_lag_hours REAL, days_to_close REAL
);
CREATE INDEX ix_ev_month ON safety_event(event_month);

DROP TABLE IF EXISTS core_measure_clinical;
CREATE TABLE core_measure_clinical (encounter_id INTEGER, measure_id TEXT, excluded INTEGER, numerator INTEGER, detail TEXT, PRIMARY KEY (encounter_id, measure_id));

DROP TABLE IF EXISTS abstraction_case;
CREATE TABLE abstraction_case (
  case_id INTEGER PRIMARY KEY, measure_id TEXT, encounter_id INTEGER, selected_dt TEXT, due_dt TEXT, abstractor TEXT,
  status TEXT, completed_dt TEXT, abstracted_numerator INTEGER, second_review INTEGER, second_numerator INTEGER
);

DROP TABLE IF EXISTS public_reporting_submission;
CREATE TABLE public_reporting_submission (measure_id TEXT, quarter TEXT, due_dt TEXT, submitted_dt TEXT, records_submitted INTEGER, accepted INTEGER, PRIMARY KEY (measure_id, quarter));

DROP TABLE IF EXISTS meta;
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);

DROP TABLE IF EXISTS mortality_expected;
CREATE TABLE mortality_expected (encounter_id INTEGER PRIMARY KEY, expected_p REAL);
