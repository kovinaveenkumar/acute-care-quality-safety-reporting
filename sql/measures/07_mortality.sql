-- Expected mortality is produced by a logistic model in qsr.measures (table mortality_expected).
DROP VIEW IF EXISTS v_m_mortality;
CREATE VIEW v_m_mortality AS
SELECT e.discharge_month AS month, 'mortality_oe' AS measure_key,
       SUM(e.died_flag) AS numerator, SUM(x.expected_p) AS denominator, SUM(e.died_flag) / SUM(x.expected_p) AS value
FROM encounter e JOIN mortality_expected x ON x.encounter_id = e.encounter_id
WHERE e.discharge_month IN (SELECT month FROM v_months) AND e.dx_group <> 'OB'
GROUP BY e.discharge_month;
