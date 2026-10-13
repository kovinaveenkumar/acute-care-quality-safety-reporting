-- Reporting months: first month is burn-in (patient-day denominators incomplete), so excluded.
DROP VIEW IF EXISTS v_months;
CREATE VIEW v_months AS
WITH RECURSIVE m(month) AS (
  SELECT '2024-11'
  UNION ALL
  SELECT strftime('%Y-%m', date(month || '-01', '+1 month')) FROM m WHERE month < '2026-09'
)
SELECT month FROM m;

-- 30-day all-cause unplanned readmission (simplified hospital-wide logic).
-- Index: adult, alive at discharge, not OB/behavioral, not AMA / transferred / hospice, with a full 30 days of follow-up.
-- Outcome: any later admission of the same patient within 30 days that is not flagged as planned.
DROP VIEW IF EXISTS v_index_admission;
CREATE VIEW v_index_admission AS
SELECT e.encounter_id, e.patient_id, e.dx_group, e.discharge_dt, e.discharge_month,
       CASE WHEN EXISTS (
         SELECT 1 FROM encounter r
         WHERE r.patient_id = e.patient_id AND r.encounter_id <> e.encounter_id
           AND r.admit_dt > e.discharge_dt
           AND r.admit_dt <= datetime(e.discharge_dt, '+30 days')
           AND r.planned_readmit = 0) THEN 1 ELSE 0 END AS readmitted
FROM encounter e
WHERE e.died_flag = 0
  AND (e.age IS NULL OR e.age >= 18)
  AND e.dx_group NOT IN ('OB', 'BEH')
  AND e.disposition NOT IN ('Left AMA', 'Transferred', 'Hospice')
  AND e.discharge_dt <= datetime((SELECT v FROM meta WHERE k = 'as_of'), '-30 days');

DROP VIEW IF EXISTS v_m_readmit;
CREATE VIEW v_m_readmit AS
SELECT discharge_month AS month, 'readmit_30d_rate' AS measure_key,
       SUM(readmitted) AS numerator, COUNT(*) AS denominator, 100.0 * SUM(readmitted) / COUNT(*) AS value
FROM v_index_admission WHERE discharge_month IN (SELECT month FROM v_months) GROUP BY discharge_month
UNION ALL
SELECT discharge_month, 'readmit_30d_' || LOWER(dx_group), SUM(readmitted), COUNT(*), 100.0 * SUM(readmitted) / COUNT(*)
FROM v_index_admission WHERE dx_group IN ('HF', 'AMI', 'PN') AND discharge_month IN (SELECT month FROM v_months)
GROUP BY discharge_month, dx_group;
