-- Onboarding funnel: how many signups reach each step, overall and by platform.
-- "pct_of_signups" columns show how far users get; "step_conv" columns show
-- the conversion from the step before, which is where a drop-off shows up.
WITH user_steps AS (
    SELECT
        u.user_id,
        u.platform,
        MAX(e.event_name = 'verified_email')   AS verified,
        MAX(e.event_name = 'created_project')  AS created,
        MAX(e.event_name = 'invited_teammate') AS invited
    FROM users u
    JOIN events e ON e.user_id = u.user_id
    GROUP BY u.user_id, u.platform
),
by_platform AS (
    SELECT platform, COUNT(*) AS signed_up, SUM(verified) AS verified,
           SUM(created) AS created_project, SUM(invited) AS invited_teammate
    FROM user_steps
    GROUP BY platform
    UNION ALL
    SELECT 'All', COUNT(*), SUM(verified), SUM(created), SUM(invited)
    FROM user_steps
)
SELECT
    platform,
    signed_up,
    verified,
    created_project,
    invited_teammate,
    ROUND(100.0 * verified / signed_up, 1)                AS verified_pct_of_signups,
    ROUND(100.0 * created_project / signed_up, 1)         AS created_pct_of_signups,
    ROUND(100.0 * invited_teammate / signed_up, 1)        AS invited_pct_of_signups,
    ROUND(100.0 * created_project / verified, 1)          AS verify_to_create_conv,
    ROUND(100.0 * invited_teammate / created_project, 1)  AS create_to_invite_conv
FROM by_platform
ORDER BY platform = 'All' DESC, signed_up DESC;
