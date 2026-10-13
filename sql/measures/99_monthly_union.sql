DROP VIEW IF EXISTS v_monthly_measures;
CREATE VIEW v_monthly_measures AS
SELECT month, measure_key, numerator, denominator, value FROM v_m_readmit
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_events
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_infection
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_ed
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_core
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_event_mgmt
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_abstraction
UNION ALL SELECT month, measure_key, numerator, denominator, value FROM v_m_mortality;
