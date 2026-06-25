-- ============================================================
-- NHS 111 IUC ADC Performance Analysis Queries
-- ============================================================
-- Database: nhs111.db (SQLite)
-- Tables:
--   daily_metrics   - one row per provider per day
--   weekly_metrics  - one row per provider per week
--   national_weekly - England totals per week
--   providers       - provider reference (code, name, region)
--   regions         - region code to name mapping
--
-- All queries work in:
--   SQLite (DB Browser, DBeaver, Python sqlite3)
--   Power BI (via "Get Data > SQLite" or paste into Power Query M)
--   SQL Server with minor syntax adjustments (noted where relevant)
--
-- NHS 111 Targets (for context):
--   95% of calls answered within 60 seconds
--   Abandoned calls < 5% of total demand
-- ============================================================


-- ============================================================
-- SECTION 1: NATIONAL OVERVIEW
-- ============================================================

-- 1.1 Weekly national headline KPIs
-- Use this as the main summary table in Power BI
SELECT
    DATE(week_ending)                                           AS week_ending,
    calls_received,
    calls_answered,
    calls_answered_60s,
    calls_abandoned,
    calls_triaged,
    referred_ambulance,
    recommended_etc,

    -- Answer within 60s rate (NHS target: 95%)
    ROUND(
        CAST(calls_answered_60s AS FLOAT) / NULLIF(calls_answered, 0) * 100, 1
    )                                                           AS pct_answered_60s,

    -- Abandonment rate
    ROUND(
        CAST(calls_abandoned AS FLOAT) / NULLIF(calls_abandoned + calls_answered, 0) * 100, 1
    )                                                           AS pct_abandoned,

    -- Ambulance referral rate (of triaged calls)
    ROUND(
        CAST(referred_ambulance AS FLOAT) / NULLIF(calls_triaged, 0) * 100, 1
    )                                                           AS pct_referred_ambulance,

    -- ETC recommendation rate (of triaged calls)
    ROUND(
        CAST(recommended_etc AS FLOAT) / NULLIF(calls_triaged, 0) * 100, 1
    )                                                           AS pct_recommended_etc,

    -- Week-on-week change in calls received
    calls_received - LAG(calls_received) OVER (ORDER BY week_ending)
                                                                AS wow_calls_change,

    -- Flag weeks that miss the 60s target
    CASE
        WHEN CAST(calls_answered_60s AS FLOAT) / NULLIF(calls_answered, 0) >= 0.95
        THEN 'Meets Target'
        ELSE 'Below Target'
    END                                                         AS target_status

FROM national_weekly
ORDER BY week_ending;


-- 1.2 Period summary - single headline numbers for dashboard cards
SELECT
    MIN(DATE(week_ending))                                      AS period_start,
    MAX(DATE(week_ending))                                      AS period_end,
    COUNT(DISTINCT week_ending)                                 AS weeks_in_period,
    SUM(calls_received)                                         AS total_calls_received,
    SUM(calls_answered)                                         AS total_calls_answered,
    SUM(calls_abandoned)                                        AS total_abandoned,
    ROUND(AVG(pct_answered_60s), 1)                             AS avg_pct_answered_60s,
    ROUND(AVG(pct_abandoned), 1)                                AS avg_pct_abandoned,
    SUM(CASE WHEN meets_60s_target = 1 THEN 1 ELSE 0 END)       AS weeks_meeting_target,
    COUNT(*)                                                    AS total_weeks,
    ROUND(
        100.0 * SUM(CASE WHEN meets_60s_target = 1 THEN 1 ELSE 0 END) / COUNT(*), 0
    )                                                           AS pct_weeks_meeting_target
FROM national_weekly;


-- ============================================================
-- SECTION 2: PROVIDER PERFORMANCE
-- ============================================================

-- 2.1 Provider league table (full period average performance)
-- Sort by pct_answered_60s to show best vs worst performers
SELECT
    p.region_name,
    w.contract_code,
    w.contract_name,
    SUM(w.calls_received)                                       AS total_calls_received,
    SUM(w.calls_answered)                                       AS total_calls_answered,
    SUM(w.calls_answered_60s)                                   AS total_answered_60s,
    ROUND(
        CAST(SUM(w.calls_answered_60s) AS FLOAT)
        / NULLIF(SUM(w.calls_answered), 0) * 100, 1
    )                                                           AS pct_answered_60s,
    ROUND(
        CAST(SUM(w.calls_abandoned) AS FLOAT)
        / NULLIF(SUM(w.calls_abandoned) + SUM(w.calls_answered), 0) * 100, 1
    )                                                           AS pct_abandoned,
    COUNT(DISTINCT w.week_ending)                               AS weeks_reported,
    SUM(CASE WHEN w.meets_60s_target = 1 THEN 1 ELSE 0 END)    AS weeks_meeting_target,

    -- RAG rating for dashboard colour coding
    CASE
        WHEN CAST(SUM(w.calls_answered_60s) AS FLOAT)
             / NULLIF(SUM(w.calls_answered), 0) >= 0.95 THEN 'Green'
        WHEN CAST(SUM(w.calls_answered_60s) AS FLOAT)
             / NULLIF(SUM(w.calls_answered), 0) >= 0.90 THEN 'Amber'
        ELSE 'Red'
    END                                                         AS rag_status

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
GROUP BY w.contract_code, w.contract_name, p.region_name
ORDER BY pct_answered_60s DESC;


-- 2.2 Provider weekly trend (for sparklines / line charts in Power BI)
SELECT
    DATE(w.week_ending)                                         AS week_ending,
    w.contract_code,
    w.contract_name,
    p.region_name,
    w.calls_received,
    w.calls_answered,
    w.calls_answered_60s,
    w.calls_abandoned,
    ROUND(w.pct_answered_60s, 1)                                AS pct_answered_60s,
    ROUND(w.pct_abandoned, 1)                                   AS pct_abandoned,
    w.meets_60s_target,

    -- Rolling 4-week average of 60s rate per provider
    ROUND(
        AVG(
            CAST(w.calls_answered_60s AS FLOAT) / NULLIF(w.calls_answered, 0) * 100
        ) OVER (
            PARTITION BY w.contract_code
            ORDER BY w.week_ending
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ), 1
    )                                                           AS rolling_4wk_pct_60s

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
ORDER BY w.contract_code, w.week_ending;


-- ============================================================
-- SECTION 3: REGIONAL PERFORMANCE
-- ============================================================

-- 3.1 Regional weekly aggregation
SELECT
    DATE(w.week_ending)                                         AS week_ending,
    p.region_name,
    w.region_code,
    SUM(w.calls_received)                                       AS calls_received,
    SUM(w.calls_answered)                                       AS calls_answered,
    SUM(w.calls_answered_60s)                                   AS calls_answered_60s,
    SUM(w.calls_abandoned)                                      AS calls_abandoned,
    ROUND(
        CAST(SUM(w.calls_answered_60s) AS FLOAT)
        / NULLIF(SUM(w.calls_answered), 0) * 100, 1
    )                                                           AS pct_answered_60s,
    ROUND(
        CAST(SUM(w.calls_abandoned) AS FLOAT)
        / NULLIF(SUM(w.calls_abandoned) + SUM(w.calls_answered), 0) * 100, 1
    )                                                           AS pct_abandoned

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
GROUP BY w.week_ending, p.region_name, w.region_code
ORDER BY w.week_ending, p.region_name;


-- 3.2 Region comparison - full period
SELECT
    p.region_name,
    COUNT(DISTINCT w.contract_code)                             AS n_providers,
    SUM(w.calls_received)                                       AS total_calls,
    ROUND(
        CAST(SUM(w.calls_answered_60s) AS FLOAT)
        / NULLIF(SUM(w.calls_answered), 0) * 100, 1
    )                                                           AS pct_answered_60s,
    ROUND(
        CAST(SUM(w.calls_abandoned) AS FLOAT)
        / NULLIF(SUM(w.calls_abandoned) + SUM(w.calls_answered), 0) * 100, 1
    )                                                           AS pct_abandoned

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
GROUP BY p.region_name
ORDER BY pct_answered_60s DESC;


-- ============================================================
-- SECTION 4: EXCEPTION ANALYSIS
-- ============================================================

-- 4.1 Exception weeks - all provider-weeks BELOW the 95% target
-- These are the rows you'd flag red on an operational dashboard
SELECT
    DATE(w.week_ending)                                         AS week_ending,
    p.region_name,
    w.contract_code,
    w.contract_name,
    w.calls_received,
    w.calls_answered,
    w.calls_answered_60s,
    ROUND(
        CAST(w.calls_answered_60s AS FLOAT) / NULLIF(w.calls_answered, 0) * 100, 1
    )                                                           AS pct_answered_60s,
    -- Gap to target (negative = how far below 95%)
    ROUND(
        CAST(w.calls_answered_60s AS FLOAT) / NULLIF(w.calls_answered, 0) * 100 - 95.0, 1
    )                                                           AS gap_to_target

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
WHERE
    w.calls_answered > 0
    AND CAST(w.calls_answered_60s AS FLOAT) / NULLIF(w.calls_answered, 0) < 0.95
ORDER BY gap_to_target ASC; -- worst performers first


-- 4.2 Count of exception weeks per provider (persistent underperformers)
SELECT
    p.region_name,
    w.contract_code,
    w.contract_name,
    COUNT(*)                                                    AS total_weeks,
    SUM(CASE WHEN
        CAST(w.calls_answered_60s AS FLOAT) / NULLIF(w.calls_answered, 0) < 0.95
        THEN 1 ELSE 0 END)                                      AS exception_weeks,
    ROUND(
        100.0 * SUM(CASE WHEN
            CAST(w.calls_answered_60s AS FLOAT) / NULLIF(w.calls_answered, 0) < 0.95
            THEN 1 ELSE 0 END) / COUNT(*), 0
    )                                                           AS pct_weeks_below_target

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
WHERE w.calls_answered > 0
GROUP BY w.contract_code, w.contract_name, p.region_name
ORDER BY pct_weeks_below_target DESC, exception_weeks DESC;


-- 4.3 High abandonment rate exceptions (> 5% threshold)
SELECT
    DATE(w.week_ending)                                         AS week_ending,
    p.region_name,
    w.contract_code,
    w.contract_name,
    w.calls_received,
    w.calls_abandoned,
    ROUND(
        CAST(w.calls_abandoned AS FLOAT)
        / NULLIF(w.calls_abandoned + w.calls_answered, 0) * 100, 1
    )                                                           AS pct_abandoned

FROM weekly_metrics w
LEFT JOIN providers p ON w.contract_code = p.contract_code
WHERE
    w.calls_answered > 0
    AND CAST(w.calls_abandoned AS FLOAT)
        / NULLIF(w.calls_abandoned + w.calls_answered, 0) > 0.05
ORDER BY pct_abandoned DESC;


-- ============================================================
-- SECTION 5: TREND ANALYSIS
-- ============================================================

-- 5.1 National week-on-week trend with seasonality note
-- Useful for the main trend line chart
SELECT
    DATE(week_ending)                                           AS week_ending,
    calls_received,
    calls_answered_60s,
    ROUND(pct_answered_60s, 1)                                  AS pct_answered_60s,
    ROUND(pct_abandoned, 1)                                     AS pct_abandoned,

    -- Week-on-week % change in demand
    ROUND(
        100.0 * (calls_received - LAG(calls_received) OVER (ORDER BY week_ending))
        / NULLIF(LAG(calls_received) OVER (ORDER BY week_ending), 0), 1
    )                                                           AS wow_demand_change_pct,

    -- 4-week rolling average for smoothed trend line
    ROUND(
        AVG(CAST(calls_received AS FLOAT))
        OVER (ORDER BY week_ending ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 0
    )                                                           AS rolling_4wk_avg_calls,

    ROUND(
        AVG(pct_answered_60s)
        OVER (ORDER BY week_ending ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 1
    )                                                           AS rolling_4wk_avg_60s,

    meets_60s_target

FROM national_weekly
ORDER BY week_ending;


-- 5.2 Peak demand identification (highest call volume weeks)
SELECT
    DATE(week_ending)                                           AS week_ending,
    calls_received,
    ROUND(pct_answered_60s, 1)                                  AS pct_answered_60s,
    ROUND(pct_abandoned, 1)                                     AS pct_abandoned,
    -- Rank by call volume
    RANK() OVER (ORDER BY calls_received DESC)                  AS demand_rank

FROM national_weekly
ORDER BY calls_received DESC
LIMIT 5;


-- ============================================================
-- SECTION 6: DISPOSITION ANALYSIS
-- ============================================================

-- 6.1 Where are triaged patients sent? (from Raw sheet data)
-- Only available for the most recent week in the Raw sheet
SELECT
    contract_name,
    region_code,
    SUM(calls_triaged)                                          AS total_triaged,
    SUM(referred_ambulance)                                     AS referred_ambulance,
    SUM(recommended_etc)                                        AS recommended_etc,
    ROUND(
        CAST(SUM(referred_ambulance) AS FLOAT) / NULLIF(SUM(calls_triaged), 0) * 100, 1
    )                                                           AS pct_ambulance,
    ROUND(
        CAST(SUM(recommended_etc) AS FLOAT) / NULLIF(SUM(calls_triaged), 0) * 100, 1
    )                                                           AS pct_etc

FROM weekly_metrics
GROUP BY contract_code, contract_name, region_code
HAVING total_triaged > 0
ORDER BY pct_ambulance DESC;


-- ============================================================
-- SECTION 7: POWER BI HELPER VIEWS
-- ============================================================
-- These are the exact views/queries to paste into Power BI's
-- "Transform data" step (Power Query). Each produces a clean
-- table ready to use in visuals.

-- View: KPI Cards (for the top-of-dashboard summary row)
-- Returns single-row summary for the MOST RECENT week
SELECT
    DATE(week_ending)                                           AS latest_week,
    calls_received,
    calls_answered,
    ROUND(pct_answered_60s, 1)                                  AS pct_answered_60s,
    ROUND(pct_abandoned, 1)                                     AS pct_abandoned,
    CASE WHEN meets_60s_target = 1 THEN 'Meets Target' 
         ELSE 'Below Target' END                                AS target_status

FROM national_weekly
ORDER BY week_ending DESC
LIMIT 1;


-- View: RAG Status by Provider (for conditional formatting in Power BI)
SELECT
    contract_code,
    contract_name,
    region_code,
    ROUND(
        CAST(SUM(calls_answered_60s) AS FLOAT) / NULLIF(SUM(calls_answered), 0) * 100, 1
    )                                                           AS overall_pct_60s,
    CASE
        WHEN CAST(SUM(calls_answered_60s) AS FLOAT)
             / NULLIF(SUM(calls_answered), 0) >= 0.95 THEN 'Green'
        WHEN CAST(SUM(calls_answered_60s) AS FLOAT)
             / NULLIF(SUM(calls_answered), 0) >= 0.88 THEN 'Amber'
        ELSE 'Red'
    END                                                         AS rag_60s,

    CASE
        WHEN CAST(SUM(calls_abandoned) AS FLOAT)
             / NULLIF(SUM(calls_abandoned) + SUM(calls_answered), 0) <= 0.05 THEN 'Green'
        WHEN CAST(SUM(calls_abandoned) AS FLOAT)
             / NULLIF(SUM(calls_abandoned) + SUM(calls_answered), 0) <= 0.08 THEN 'Amber'
        ELSE 'Red'
    END                                                         AS rag_abandoned

FROM weekly_metrics
GROUP BY contract_code, contract_name, region_code;
