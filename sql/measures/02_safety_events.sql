DROP VIEW IF EXISTS v_house_patient_days;
CREATE VIEW v_house_patient_days AS SELECT month, SUM(patient_days) AS pd FROM patient_days GROUP BY month;

DROP VIEW IF EXISTS v_m_events;
CREATE VIEW v_m_events AS
SELECT h.month, 'fall_rate' AS measure_key,
       COUNT(e.event_id) AS numerator, h.pd AS denominator, 1000.0 * COUNT(e.event_id) / h.pd AS value
FROM v_house_patient_days h LEFT JOIN safety_event e ON e.event_month = h.month AND e.event_type = 'Fall'
WHERE h.month IN (SELECT month FROM v_months) GROUP BY h.month
UNION ALL
SELECT h.month, 'fall_injury_rate', COUNT(e.event_id), h.pd, 1000.0 * COUNT(e.event_id) / h.pd
FROM v_house_patient_days h LEFT JOIN safety_event e ON e.event_month = h.month AND e.event_type = 'Fall' AND e.harm_level >= 1
WHERE h.month IN (SELECT month FROM v_months) GROUP BY h.month
UNION ALL
SELECT h.month, 'med_event_rate', COUNT(e.event_id), h.pd, 1000.0 * COUNT(e.event_id) / h.pd
FROM v_house_patient_days h LEFT JOIN safety_event e ON e.event_month = h.month AND e.event_type = 'Medication'
WHERE h.month IN (SELECT month FROM v_months) GROUP BY h.month;

-- Unit-level event rates for drill-down.
DROP VIEW IF EXISTS v_unit_events_monthly;
CREATE VIEW v_unit_events_monthly AS
SELECT p.unit_id, p.month, t.event_type AS event_type, COUNT(e.event_id) AS events, p.patient_days,
       1000.0 * COUNT(e.event_id) / p.patient_days AS per_1000_pd
FROM patient_days p
JOIN (SELECT DISTINCT event_type FROM safety_event) t
LEFT JOIN safety_event e ON e.unit_id = p.unit_id AND e.event_month = p.month AND e.event_type = t.event_type
WHERE p.month IN (SELECT month FROM v_months)
GROUP BY p.unit_id, p.month, t.event_type;

-- Device-associated infections.
DROP VIEW IF EXISTS v_m_infection;
CREATE VIEW v_m_infection AS
SELECT d.month, 'clabsi_rate' AS measure_key, COALESCE(i.n, 0) AS numerator, d.days AS denominator,
       1000.0 * COALESCE(i.n, 0) / d.days AS value
FROM (SELECT month, SUM(central_line_days) AS days FROM device_days GROUP BY month) d
LEFT JOIN (SELECT onset_month, COUNT(*) AS n FROM infection WHERE infection_type = 'CLABSI' GROUP BY onset_month) i ON i.onset_month = d.month
WHERE d.month IN (SELECT month FROM v_months)
UNION ALL
SELECT d.month, 'cauti_rate', COALESCE(i.n, 0), d.days, 1000.0 * COALESCE(i.n, 0) / d.days
FROM (SELECT month, SUM(foley_days) AS days FROM device_days GROUP BY month) d
LEFT JOIN (SELECT onset_month, COUNT(*) AS n FROM infection WHERE infection_type = 'CAUTI' GROUP BY onset_month) i ON i.onset_month = d.month
WHERE d.month IN (SELECT month FROM v_months);
