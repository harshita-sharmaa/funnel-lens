-- Retention by signup month: % of each cohort active in week 1, 4 and 8 after signup.
-- Week N covers days 7N to 7N+6 after signup. A user only counts toward week N
-- if that whole week falls inside the data, so recent cohorts show NULL
-- instead of a retention number that looks low because the data stops.
WITH data_end AS (
    SELECT MAX(event_date) AS last_day FROM events
),
activity AS (
    SELECT
        u.user_id,
        u.signup_date,
        MAX(CAST((julianday(e.event_date) - julianday(u.signup_date)) / 7 AS INTEGER) = 1) AS active_wk1,
        MAX(CAST((julianday(e.event_date) - julianday(u.signup_date)) / 7 AS INTEGER) = 4) AS active_wk4,
        MAX(CAST((julianday(e.event_date) - julianday(u.signup_date)) / 7 AS INTEGER) = 8) AS active_wk8
    FROM users u
    JOIN events e ON e.user_id = u.user_id
    GROUP BY u.user_id, u.signup_date
)
SELECT
    strftime('%Y-%m', a.signup_date) AS signup_month,
    COUNT(*)                          AS users,
    ROUND(100.0 * AVG(CASE WHEN julianday(d.last_day) - julianday(a.signup_date) >= 13 THEN a.active_wk1 END), 1) AS week1_retention_pct,
    ROUND(100.0 * AVG(CASE WHEN julianday(d.last_day) - julianday(a.signup_date) >= 34 THEN a.active_wk4 END), 1) AS week4_retention_pct,
    ROUND(100.0 * AVG(CASE WHEN julianday(d.last_day) - julianday(a.signup_date) >= 62 THEN a.active_wk8 END), 1) AS week8_retention_pct
FROM activity a
CROSS JOIN data_end d
GROUP BY signup_month
ORDER BY signup_month;
