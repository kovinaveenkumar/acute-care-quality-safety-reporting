-- Median arrival-to-departure for discharged ED patients (OP-18-style), computed with window functions.
DROP VIEW IF EXISTS v_m_ed;
CREATE VIEW v_m_ed AS
WITH ranked AS (
  SELECT arrival_month AS month, los_min AS v,
         ROW_NUMBER() OVER (PARTITION BY arrival_month ORDER BY los_min) AS rn,
         COUNT(*) OVER (PARTITION BY arrival_month) AS c
  FROM ed_visit WHERE ed_disposition = 'Discharged'
), med_los AS (
  SELECT month, AVG(v) AS value, MAX(c) AS n FROM ranked WHERE rn IN ((c + 1) / 2, (c + 2) / 2) GROUP BY month
), ranked_b AS (
  SELECT arrival_month AS month, boarding_min AS v,
         ROW_NUMBER() OVER (PARTITION BY arrival_month ORDER BY boarding_min) AS rn,
         COUNT(*) OVER (PARTITION BY arrival_month) AS c
  FROM ed_visit WHERE ed_disposition = 'Admitted'
), med_board AS (
  SELECT month, AVG(v) AS value, MAX(c) AS n FROM ranked_b WHERE rn IN ((c + 1) / 2, (c + 2) / 2) GROUP BY month
)
SELECT month, 'ed_los_median' AS measure_key, NULL AS numerator, n AS denominator, value FROM med_los
WHERE month IN (SELECT month FROM v_months)
UNION ALL
SELECT month, 'ed_boarding_median', NULL, n, value FROM med_board WHERE month IN (SELECT month FROM v_months)
UNION ALL
SELECT arrival_month, 'ed_lwbs_rate', SUM(ed_disposition = 'LWBS'), COUNT(*), 100.0 * SUM(ed_disposition = 'LWBS') / COUNT(*)
FROM ed_visit WHERE arrival_month IN (SELECT month FROM v_months) GROUP BY arrival_month;
