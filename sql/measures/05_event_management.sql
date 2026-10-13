DROP VIEW IF EXISTS v_m_event_mgmt;
CREATE VIEW v_m_event_mgmt AS
SELECT event_month AS month, 'event_report_24h' AS measure_key,
       SUM(report_lag_hours <= 24) AS numerator, COUNT(*) AS denominator, 100.0 * SUM(report_lag_hours <= 24) / COUNT(*) AS value
FROM safety_event WHERE reported_dt IS NOT NULL AND event_month IN (SELECT month FROM v_months) GROUP BY event_month
UNION ALL
-- Closure within 30 days, only for events old enough (reported >= 30 days before the extract date) to have had the chance.
SELECT event_month, 'event_closed_30d',
       SUM(status = 'Closed' AND days_to_close <= 30), COUNT(*),
       100.0 * SUM(status = 'Closed' AND days_to_close <= 30) / COUNT(*)
FROM safety_event
WHERE reported_dt IS NOT NULL AND reported_dt <= datetime((SELECT v FROM meta WHERE k = 'as_of'), '-30 days')
  AND event_month IN (SELECT month FROM v_months)
GROUP BY event_month;

-- Open-event aging snapshot as of the extract date.
DROP VIEW IF EXISTS v_event_aging;
CREATE VIEW v_event_aging AS
SELECT status,
       CASE WHEN julianday((SELECT v FROM meta WHERE k = 'as_of')) - julianday(reported_dt) <= 7 THEN '0-7 days'
            WHEN julianday((SELECT v FROM meta WHERE k = 'as_of')) - julianday(reported_dt) <= 30 THEN '8-30 days'
            ELSE '>30 days' END AS age_bucket,
       COUNT(*) AS events, SUM(harm_level >= 3) AS high_harm_events
FROM safety_event WHERE status <> 'Closed' AND reported_dt IS NOT NULL GROUP BY status, age_bucket;
