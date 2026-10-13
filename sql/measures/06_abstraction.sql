-- Abstraction workflow: cases due on or before the extract date; late = not completed, or completed after due date.
DROP VIEW IF EXISTS v_m_abstraction;
CREATE VIEW v_m_abstraction AS
SELECT strftime('%Y-%m', selected_dt) AS month, 'abstraction_on_time' AS measure_key,
       SUM(status = 'Completed' AND completed_dt <= due_dt) AS numerator, COUNT(*) AS denominator,
       100.0 * SUM(status = 'Completed' AND completed_dt <= due_dt) / COUNT(*) AS value
FROM abstraction_case
WHERE due_dt <= (SELECT v FROM meta WHERE k = 'as_of') AND strftime('%Y-%m', selected_dt) IN (SELECT month FROM v_months)
GROUP BY strftime('%Y-%m', selected_dt);

-- Current workload by abstractor.
DROP VIEW IF EXISTS v_abstractor_workload;
CREATE VIEW v_abstractor_workload AS
SELECT abstractor,
       COUNT(*) AS cases_total,
       SUM(status = 'Completed') AS completed,
       SUM(status <> 'Completed') AS open_cases,
       SUM(status <> 'Completed' AND due_dt < (SELECT v FROM meta WHERE k = 'as_of')) AS overdue,
       ROUND(AVG(CASE WHEN status = 'Completed' THEN julianday(completed_dt) - julianday(selected_dt) END), 1) AS avg_days_to_complete
FROM abstraction_case GROUP BY abstractor;

-- Inter-rater agreement on second-reviewed cases (kappa is computed in Python).
DROP VIEW IF EXISTS v_second_review;
CREATE VIEW v_second_review AS
SELECT case_id, measure_id, abstracted_numerator AS rater1, second_numerator AS rater2
FROM abstraction_case WHERE second_review = 1 AND status = 'Completed';

-- Abstracted vs EHR-derived agreement (data validation, similar in spirit to CMS validation).
DROP VIEW IF EXISTS v_data_validation;
CREATE VIEW v_data_validation AS
SELECT a.measure_id, COUNT(*) AS cases, SUM(a.abstracted_numerator = c.numerator) AS agree,
       100.0 * SUM(a.abstracted_numerator = c.numerator) / COUNT(*) AS agreement_pct
FROM abstraction_case a JOIN core_measure_clinical c ON c.encounter_id = a.encounter_id AND c.measure_id = a.measure_id
WHERE a.status = 'Completed' GROUP BY a.measure_id;

-- Public-reporting submission timeliness.
DROP VIEW IF EXISTS v_submission_status;
CREATE VIEW v_submission_status AS
SELECT measure_id, quarter, due_dt, submitted_dt, records_submitted, accepted,
       CASE WHEN submitted_dt IS NULL AND due_dt > (SELECT v FROM meta WHERE k = 'as_of') THEN 'Not yet due'
            WHEN submitted_dt IS NULL THEN 'OVERDUE'
            WHEN submitted_dt > due_dt THEN 'Submitted late'
            ELSE 'Submitted on time' END AS status,
       CASE WHEN submitted_dt IS NOT NULL THEN CAST(julianday(due_dt) - julianday(submitted_dt) AS INTEGER) END AS days_before_due
FROM public_reporting_submission;
