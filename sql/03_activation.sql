-- Which first-week behaviour goes with users sticking around?
-- Users are grouped by what they did in their first 7 days, then compared on
-- retention in week 4 and week 8 after signup.
WITH data_end AS (
    SELECT MAX(event_date) AS last_day FROM events
),
first_week AS (
    SELECT
        u.user_id,
        u.signup_date,
        MAX(e.event_name = 'created_project'
            AND julianday(e.event_date) - julianday(u.signup_date) < 7)  AS created_in_wk0,
        MAX(e.event_name = 'invited_teammate'
            AND julianday(e.event_date) - julianday(u.signup_date) < 7)  AS invited_in_wk0,
        MAX(e.event_name = 'session'
            AND CAST((julianday(e.event_date) - julianday(u.signup_date)) / 7 AS INTEGER) = 4) AS active_wk4,
        MAX(e.event_name = 'session'
            AND CAST((julianday(e.event_date) - julianday(u.signup_date)) / 7 AS INTEGER) = 8) AS active_wk8
    FROM users u
    JOIN events e ON e.user_id = u.user_id
    GROUP BY u.user_id, u.signup_date
),
grouped AS (
    SELECT
        *,
        CASE
            WHEN invited_in_wk0 THEN '1. Invited a teammate'
            WHEN created_in_wk0 THEN '2. Created a project only'
            ELSE '3. Did neither'
        END AS first_week_group
    FROM first_week
)
SELECT
    first_week_group,
    COUNT(*)                                             AS users,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS share_of_users_pct,
    ROUND(100.0 * AVG(CASE WHEN julianday(d.last_day) - julianday(g.signup_date) >= 34 THEN g.active_wk4 END), 1) AS week4_retention_pct,
    ROUND(100.0 * AVG(CASE WHEN julianday(d.last_day) - julianday(g.signup_date) >= 62 THEN g.active_wk8 END), 1) AS week8_retention_pct
FROM grouped g
CROSS JOIN data_end d
GROUP BY first_week_group
ORDER BY first_week_group;
