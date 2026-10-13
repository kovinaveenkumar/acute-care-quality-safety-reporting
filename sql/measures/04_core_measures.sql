-- Chart-abstracted core-measure-style rates on the full eligible population (EHR-derived), by discharge month.
-- Specifications are simplified and modelled on Joint Commission / CMS measures; they are not the official specs.
DROP VIEW IF EXISTS v_m_core;
CREATE VIEW v_m_core AS
SELECT e.discharge_month AS month,
       CASE c.measure_id WHEN 'SEP1' THEN 'sep1_rate' WHEN 'AMI_ASA' THEN 'ami_asa_rate'
                         WHEN 'HF_ACEI' THEN 'hf_acei_rate' WHEN 'VTE_PPX' THEN 'vte_ppx_rate' END AS measure_key,
       SUM(c.numerator) AS numerator, COUNT(*) AS denominator, 100.0 * SUM(c.numerator) / COUNT(*) AS value
FROM core_measure_clinical c JOIN encounter e ON e.encounter_id = c.encounter_id
WHERE c.excluded = 0 AND e.discharge_month IN (SELECT month FROM v_months)
GROUP BY e.discharge_month, c.measure_id;

-- VTE prophylaxis by unit and weekday type (drill-down used to localise the weekend gap).
DROP VIEW IF EXISTS v_vte_drilldown;
CREATE VIEW v_vte_drilldown AS
SELECT e.unit_id,
       CASE WHEN CAST(strftime('%w', e.admit_dt) AS INTEGER) IN (0, 6) THEN 'Weekend' ELSE 'Weekday' END AS admit_day_type,
       SUM(c.numerator) AS numerator, COUNT(*) AS denominator, 100.0 * SUM(c.numerator) / COUNT(*) AS value
FROM core_measure_clinical c JOIN encounter e ON e.encounter_id = c.encounter_id
WHERE c.measure_id = 'VTE_PPX' AND c.excluded = 0 AND e.discharge_month IN (SELECT month FROM v_months)
GROUP BY e.unit_id, admit_day_type;
