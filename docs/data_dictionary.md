# Data dictionary

Generated from the live schema by `python -m qsr.make_docs`. All data is synthetic.

## `abstraction_case` (2,009 rows)

Sampled case sent to a quality abstractor: due date, status, abstracted result, optional second review.

| column | type | key |
|---|---|---|
| case_id | INTEGER | PK |
| measure_id | TEXT |  |
| encounter_id | INTEGER |  |
| selected_dt | TEXT |  |
| due_dt | TEXT |  |
| abstractor | TEXT |  |
| status | TEXT |  |
| completed_dt | TEXT |  |
| abstracted_numerator | INTEGER |  |
| second_review | INTEGER |  |
| second_numerator | INTEGER |  |

## `core_measure_clinical` (14,604 rows)

EHR-derived measure population: exclusion flag and numerator flag per encounter and measure.

| column | type | key |
|---|---|---|
| encounter_id | INTEGER | PK |
| measure_id | TEXT | PK |
| excluded | INTEGER |  |
| numerator | INTEGER |  |
| detail | TEXT |  |

## `device_days` (150 rows)

Central-line and urinary-catheter days per unit and month (denominator for infection rates).

| column | type | key |
|---|---|---|
| unit_id | TEXT | PK |
| month | TEXT | PK |
| central_line_days | INTEGER |  |
| foley_days | INTEGER |  |

## `dq_log` (11 rows)

Every cleaning rule applied, with the number of rows affected.

| column | type | key |
|---|---|---|
| rule_id | TEXT |  |
| table_name | TEXT |  |
| description | TEXT |  |
| rows_affected | INTEGER |  |
| action | TEXT |  |

## `ed_visit` (82,455 rows)

One ED visit. Admitted visits link to an encounter; treat-and-release visits do not.

| column | type | key |
|---|---|---|
| ed_visit_id | INTEGER | PK |
| encounter_id | INTEGER |  |
| patient_id | INTEGER |  |
| arrival_dt | TEXT |  |
| admit_decision_dt | TEXT |  |
| depart_dt | TEXT |  |
| ed_disposition | TEXT |  |
| acuity | INTEGER |  |
| los_min | REAL |  |
| boarding_min | REAL |  |
| arrival_month | TEXT |  |

## `encounter` (17,809 rows)

One inpatient stay (index and readmission stays). Cleaned: duplicates dropped, swapped dates fixed.

| column | type | key |
|---|---|---|
| encounter_id | INTEGER | PK |
| patient_id | INTEGER |  |
| dx_group | TEXT |  |
| unit_id | TEXT |  |
| age | INTEGER |  |
| charlson | INTEGER |  |
| admit_dt | TEXT |  |
| discharge_dt | TEXT |  |
| from_ed | INTEGER |  |
| died_flag | INTEGER |  |
| planned_readmit | INTEGER |  |
| index_of | INTEGER |  |
| payer | TEXT |  |
| attending_id | INTEGER |  |
| disposition | TEXT |  |
| los_days | REAL |  |
| discharge_month | TEXT |  |

## `infection` (34 rows)

Device-associated infection (CLABSI / CAUTI) linked to an encounter and unit.

| column | type | key |
|---|---|---|
| infection_id | INTEGER | PK |
| encounter_id | INTEGER |  |
| unit_id | TEXT |  |
| infection_type | TEXT |  |
| onset_dt | TEXT |  |
| onset_month | TEXT |  |

## `meta` (1 rows)

Extract date and other run metadata.

| column | type | key |
|---|---|---|
| k | TEXT | PK |
| v | TEXT |  |

## `mortality_expected` (15,851 rows)

Expected probability of death per encounter from the logistic baseline model.

| column | type | key |
|---|---|---|
| encounter_id | INTEGER | PK |
| expected_p | REAL |  |

## `patient` (14,953 rows)

Synthetic patient demographics.

| column | type | key |
|---|---|---|
| patient_id | INTEGER | PK |
| birth_year | INTEGER |  |
| sex | TEXT |  |
| payer | TEXT |  |

## `patient_days` (150 rows)

Midnight-census patient days per unit and month (denominator for event rates).

| column | type | key |
|---|---|---|
| unit_id | TEXT | PK |
| month | TEXT | PK |
| patient_days | INTEGER |  |

## `public_reporting_submission` (32 rows)

Quarterly submission log per measure with due and submitted dates.

| column | type | key |
|---|---|---|
| measure_id | TEXT | PK |
| quarter | TEXT | PK |
| due_dt | TEXT |  |
| submitted_dt | TEXT |  |
| records_submitted | INTEGER |  |
| accepted | INTEGER |  |

## `safety_event` (1,428 rows)

Voluntarily reported patient-safety event (fall, medication, etc.) with harm level 0-5 and review status.

| column | type | key |
|---|---|---|
| event_id | INTEGER | PK |
| event_dt | TEXT |  |
| reported_dt | TEXT |  |
| unit_id | TEXT |  |
| event_type | TEXT |  |
| harm_level | INTEGER |  |
| status | TEXT |  |
| reviewed_dt | TEXT |  |
| root_cause | TEXT |  |
| reporter_role | TEXT |  |
| encounter_id | INTEGER |  |
| event_month | TEXT |  |
| report_lag_hours | REAL |  |
| days_to_close | REAL |  |

## `unit` (6 rows)

Nursing units and bed counts.

| column | type | key |
|---|---|---|
| unit_id | TEXT | PK |
| unit_name | TEXT |  |
| unit_type | TEXT |  |
| beds | INTEGER |  |

## Measure views

- `v_abstractor_workload`
- `v_data_validation`
- `v_event_aging`
- `v_house_patient_days`
- `v_index_admission`
- `v_m_abstraction`
- `v_m_core`
- `v_m_ed`
- `v_m_event_mgmt`
- `v_m_events`
- `v_m_infection`
- `v_m_mortality`
- `v_m_readmit`
- `v_monthly_measures`
- `v_months`
- `v_second_review`
- `v_submission_status`
- `v_unit_events_monthly`
- `v_vte_drilldown`
