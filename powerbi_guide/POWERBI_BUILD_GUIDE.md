# Power BI Dashboard Build Guide
## NHS 111 Integrated Urgent Care — Operational Performance Dashboard

This guide walks you through building the full dashboard step by step.
Every visual is described with exact field placements so you can build it
without guessing. Estimated build time: 90 minutes.

---

## Prerequisites

1. Download **Power BI Desktop** (free): https://powerbi.microsoft.com/desktop
   - Windows only. If you're on Mac, use a Windows VM or Parallels.
2. Run the data pipeline first:
   ```
   pip install pandas openpyxl numpy
   python python/process_data.py
   ```
   This creates the CSV files and SQLite database in `data/`.

---

## PART 1: LOADING THE DATA

### Step 1: Connect to the CSVs

1. Open Power BI Desktop → **Get Data → Text/CSV**
2. Load these four files from the `data/` folder one at a time:
   - `nhs111_weekly.csv` → rename to **WeeklyMetrics**
   - `nhs111_national_weekly.csv` → rename to **NationalWeekly**
   - `provider_lookup.csv` → rename to **Providers**
   - `region_lookup.csv` → rename to **Regions**

### Step 2: Set data types (Transform Data)

Click **Transform Data** to open Power Query. For each table:

**WeeklyMetrics:**
- `week_ending` → Date
- `calls_received`, `calls_answered`, `calls_answered_60s`, `calls_abandoned`, `calls_triaged` → Whole Number
- `pct_answered_60s`, `pct_abandoned` → Decimal Number
- `meets_60s_target` → Whole Number

**NationalWeekly:** same as above

Click **Close & Apply**.

### Step 3: Create the data model (relationships)

Go to **Model view** (left sidebar icon). Create these relationships:

- `WeeklyMetrics[contract_code]` → `Providers[contract_code]` (Many to One)
- `WeeklyMetrics[region_code]` → `Regions[region_code]` (Many to One)

### Step 4: Create key measures (DAX)

Click on the **WeeklyMetrics** table → **New Measure**. Create each of these:

```dax
-- Core performance rate
Pct Answered 60s =
DIVIDE(
    SUM(WeeklyMetrics[calls_answered_60s]),
    SUM(WeeklyMetrics[calls_answered]),
    BLANK()
) * 100

-- Abandonment rate
Pct Abandoned =
DIVIDE(
    SUM(WeeklyMetrics[calls_abandoned]),
    SUM(WeeklyMetrics[calls_abandoned]) + SUM(WeeklyMetrics[calls_answered]),
    BLANK()
) * 100

-- Target status (for conditional formatting)
Meets 60s Target =
IF([Pct Answered 60s] >= 95, "Meets Target", "Below Target")

-- Gap to target (negative = below)
Gap To Target =
[Pct Answered 60s] - 95

-- Week on week demand change
WoW Calls Change =
VAR CurrentWeek = SUM(WeeklyMetrics[calls_received])
VAR PrevWeek =
    CALCULATE(
        SUM(WeeklyMetrics[calls_received]),
        DATEADD(WeeklyMetrics[week_ending], -7, DAY)
    )
RETURN DIVIDE(CurrentWeek - PrevWeek, PrevWeek) * 100

-- RAG status for conditional formatting
RAG Status =
SWITCH(
    TRUE(),
    [Pct Answered 60s] >= 95, "Green",
    [Pct Answered 60s] >= 88, "Amber",
    "Red"
)
```

---

## PART 2: DASHBOARD LAYOUT

Build **4 pages** (tabs at the bottom):

| Page | Purpose |
|------|---------|
| 1. National Overview | Headline KPIs, national trend |
| 2. Provider Performance | League table, regional breakdown |
| 3. Exception Analysis | Who's failing, how often |
| 4. Operational Detail | Dispositions, abandonment deep-dive |

Recommended canvas size: **1280 × 720** (16:9)
Set via: View → Page View → Actual Size, then File → Page Setup

---

## PAGE 1: NATIONAL OVERVIEW

### Layout sketch:
```
┌─────────────────────────────────────────────────────────┐
│  [Title]  NHS 111 Integrated Urgent Care Performance     │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  CALLS   │  CALLS   │ % ANS   │ % ABND  │  TARGET     │
│ RECEIVED │ ANSWERED │  IN 60s  │         │  STATUS     │
│ KPI card │ KPI card │ KPI card │ KPI card│  KPI card   │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│                                                         │
│         Line Chart: Weekly % Answered in 60s            │
│         (with 95% target reference line)                │
│                                                         │
├─────────────────────────────┬───────────────────────────┤
│  Bar Chart: Weekly Calls    │  Line Chart: Abandonment  │
│  Received (demand trend)    │  Rate trend               │
└─────────────────────────────┴───────────────────────────┘
```

### Visual 1A–1E: KPI Cards (top row, 5 cards)

Insert → **Card** visual × 5. Configure each:

**Card 1 — Total Calls Received:**
- Field: `SUM(WeeklyMetrics[calls_received])`
- Title: "Total Calls Received"
- Format: Thousands separator on

**Card 2 — Calls Answered:**
- Field: `SUM(WeeklyMetrics[calls_answered])`
- Title: "Calls Answered"

**Card 3 — % Answered in 60s:**
- Field: `[Pct Answered 60s]` (your DAX measure)
- Title: "% Answered in 60s"
- Format: 1 decimal place, add "%" suffix
- Add **Target line**: Format pane → Callout value → Target = 95

**Card 4 — % Abandoned:**
- Field: `[Pct Abandoned]`
- Title: "Abandonment Rate"
- Format: 1 decimal place

**Card 5 — Target Status:**
- Field: `[Meets 60s Target]`
- Title: "60s Target"

### Visual 2: Main trend line — % Answered in 60s over time

Insert → **Line Chart**
- X-axis: `NationalWeekly[week_ending]`
- Y-axis: `NationalWeekly[pct_answered_60s]`
- Format pane → Y-axis → Min: 50, Max: 100
- Add a **constant line** at Y = 95:
  Format pane → Analytics → Constant line → Value: 95, Color: Red, Dash: Dashed
  Label: "95% Target"
- Title: "Weekly % Calls Answered in 60 Seconds — England"
- Line color: Dark blue (#003087 — NHS blue)
- Add **data labels** on

### Visual 3: Weekly demand bar chart

Insert → **Clustered Bar Chart** (or Column Chart)
- X-axis: `NationalWeekly[week_ending]`
- Y-axis: `NationalWeekly[calls_received]`
- Title: "Weekly Call Demand"
- Bar color: NHS blue
- Add a **trend line**: Analytics pane → Trend Line

### Visual 4: Abandonment rate trend

Insert → **Line Chart**
- X-axis: `NationalWeekly[week_ending]`
- Y-axis: `NationalWeekly[pct_abandoned]`
- Add constant line at Y = 5 (5% threshold, red dashed)
- Title: "Weekly Abandonment Rate (%)"
- Line color: Orange

### Slicer: Date range filter

Insert → **Slicer**
- Field: `WeeklyMetrics[week_ending]`
- Format: Between (shows a date range slider)
- Place in top right corner

---

## PAGE 2: PROVIDER PERFORMANCE

### Layout sketch:
```
┌──────────────────────────────┬──────────────────────────┐
│  Slicer: Region              │  Slicer: Week Ending     │
├──────────────────────────────┴──────────────────────────┤
│                                                         │
│    Table: Provider League Table                         │
│    (contract_name | region | % 60s | calls | RAG)       │
│                                                         │
├─────────────────────────────┬───────────────────────────┤
│  Bar Chart: % Answered 60s  │  Map or Bar: Calls        │
│  by Provider (sorted)       │  Received by Region       │
└─────────────────────────────┴───────────────────────────┘
```

### Visual 1: Provider league table

Insert → **Table**
Columns (in order):
1. `Providers[contract_name]` → rename "Provider"
2. `Providers[region_name]` → rename "Region"
3. `SUM(WeeklyMetrics[calls_received])` → rename "Total Calls"
4. `[Pct Answered 60s]` → rename "% Ans. in 60s"
5. `[Pct Abandoned]` → rename "Abnd. Rate %"
6. `[RAG Status]` → rename "RAG"

**Conditional formatting on "% Ans. in 60s":**
- Click the column → Format → Conditional Formatting → Background color
- Rules:
  - Value >= 95 → Green (#00A651)
  - Value >= 88 → Amber (#FFA500)
  - Value < 88 → Red (#DA291C)

**Conditional formatting on "Abnd. Rate %":**
- Value <= 5 → Green
- Value <= 8 → Amber
- Value > 8 → Red

Sort by `% Ans. in 60s` Descending by default.

### Visual 2: Horizontal bar chart — % Answered in 60s by provider

Insert → **Bar Chart** (horizontal)
- Y-axis: `Providers[contract_name]`
- X-axis: `[Pct Answered 60s]`
- Sort: Ascending (worst at top for operational attention)
- X-axis: Min 0, Max 100
- Add constant line at 95 (red)
- Title: "% Calls Answered in 60s by Provider"

**Conditional formatting on bars:**
Format → Data colors → **fx** (conditional) → Based on field: `[RAG Status]`
- "Green" → #00A651
- "Amber" → #FFA500
- "Red" → #DA291C

### Visual 3: Calls by region (bar or filled map)

**Option A — Bar Chart (simpler):**
Insert → **Clustered Column Chart**
- X-axis: `Providers[region_name]`
- Y-axis: `SUM(WeeklyMetrics[calls_received])`
- Title: "Total Calls by Region"

**Option B — Map (more impressive for portfolio):**
Insert → **Filled Map**
- Location: `Providers[region_name]` (Power BI may auto-geocode UK regions)
- Color saturation: `SUM(WeeklyMetrics[calls_received])`
- Note: may need to specify Location type as "State or Province" in field settings

### Slicers

**Region slicer:**
Insert → Slicer → Field: `Providers[region_name]`
Format: List style, multi-select on

**Week ending slicer:**
Insert → Slicer → Field: `WeeklyMetrics[week_ending]`
Format: Between (date range slider)

---

## PAGE 3: EXCEPTION ANALYSIS

This is the most operationally useful page — it shows who is failing,
how often, and how far below target.

### Layout sketch:
```
┌─────────────────────────────────────────────────────────┐
│  [KPI] Weeks Below Target  [KPI] Worst Provider  [KPI]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Table: Exception Weeks                                 │
│  (Week | Provider | Region | % 60s | Gap to Target)     │
│                                                         │
├─────────────────────────────┬───────────────────────────┤
│  Bar: Exception count per   │  Line: Provider trend     │
│  provider (sorted worst→best)│  (selected provider)     │
└─────────────────────────────┴───────────────────────────┘
```

### Visual 1: Exception weeks count KPI card

Insert → **Card**
- New measure:
```dax
Exception Weeks =
CALCULATE(
    COUNTROWS(WeeklyMetrics),
    WeeklyMetrics[pct_answered_60s] < 95
)
```
- Title: "Weeks Below 95% Target"
- Color: Red

### Visual 2: Exception weeks table

Insert → **Table**

First, create a filtered table view or use this approach:
- Include all columns but add **visual-level filter**:
  `WeeklyMetrics[pct_answered_60s]` is less than 95

Columns:
1. `WeeklyMetrics[week_ending]` → "Week Ending"
2. `Providers[contract_name]` → "Provider"
3. `Providers[region_name]` → "Region"
4. `SUM(WeeklyMetrics[calls_received])` → "Calls"
5. `[Pct Answered 60s]` → "% in 60s" (conditional format: all red since all <95)
6. `[Gap To Target]` → "Gap to 95% Target" (all will be negative)

Sort: Gap To Target ascending (most negative = worst performer at top)

### Visual 3: Exception frequency bar chart

Insert → **Clustered Bar Chart**
- Y-axis: `Providers[contract_name]`
- X-axis: Count of exception weeks (use the Exception Weeks measure)
- Sort descending
- Title: "Number of Weeks Below 95% Target by Provider"
- Bar color: Red (#DA291C)

### Visual 4: Provider trend line (drillthrough)

Insert → **Line Chart**
- X-axis: `WeeklyMetrics[week_ending]`
- Y-axis: `[Pct Answered 60s]`
- Legend: `Providers[contract_name]`
- Add constant line at 95
- Title: "Weekly Performance — Selected Providers"

Add a **provider slicer** on this page so viewers can select
which providers to compare.

---

## PAGE 4: OPERATIONAL DETAIL

### Visual 1: Triage disposition breakdown

If your data includes disposition columns (depends on what the raw sheet
provided), create a stacked bar:
Insert → **Stacked Bar Chart**
- Y-axis: `Providers[contract_name]`
- Values: calls_triaged, referred_ambulance, recommended_etc
- Title: "Call Dispositions by Provider"

### Visual 2: Daily demand heatmap (if daily data available)

Use `nhs111_daily.csv` for this:
Insert → **Matrix**
- Rows: `daily_metrics[contract_name]`
- Columns: `daily_metrics[date]` (grouped by week)
- Values: `SUM(daily_metrics[calls_received])`
- Conditional formatting: Color scale (white → dark blue) by value

### Visual 3: Rolling 4-week average vs actuals

Insert → **Line and Clustered Column Chart**
- Column: `NationalWeekly[calls_received]` (actual weekly calls)
- Line: Create a rolling average measure:
```dax
Rolling 4wk Avg Calls =
AVERAGEX(
    DATESINPERIOD(
        NationalWeekly[week_ending],
        LASTDATE(NationalWeekly[week_ending]),
        -28, DAY
    ),
    NationalWeekly[calls_received]
)
```
- Title: "Actual vs Rolling 4-Week Average — Call Demand"

---

## PART 3: FORMATTING AND POLISH

### Colour palette (NHS brand colours)
- NHS Blue: #003087
- NHS Dark Blue: #002060
- NHS Bright Blue: #0072CE
- NHS Green: #00A651
- NHS Amber: #FFA500
- NHS Red: #DA291C
- Background: #F0F4F5 (light grey-blue)
- White: #FFFFFF

### Apply to all pages
1. **Background:** Format pane → Canvas background → #F0F4F5
2. **Visual backgrounds:** White with subtle border
3. **Title font:** Frutiger or Calibri 14pt Bold, NHS Blue
4. **Body font:** Calibri 11pt

### NHS logo / branding
- Download NHS logo from NHS Identity website (free to use in official contexts)
- Insert → Image → place in top left
- Add the title "NHS 111 IUC Performance Dashboard" in NHS Blue

### Page navigation buttons
To link pages together:
Insert → Buttons → Navigator → Page Navigator
This adds automatic page navigation buttons to every page.

### Tooltips
For the league table, add rich tooltips:
- Right-click the % Answered 60s column → Tooltip
- Create a tooltip page (Page → Add Page → mark as Tooltip page in Format)
- Add sparkline showing that provider's trend

---

## PART 4: PUBLISHING

### To share as a static file:
File → Export → Export to PDF
(Anyone can view without Power BI account)

### To publish interactively (free tier):
1. Sign up for **Power BI Service** at app.powerbi.com (free with Microsoft account)
2. In Power BI Desktop: **Publish** → sign in → choose My Workspace
3. Get a shareable link from Power BI Service → Share

### For your portfolio:
- Export as PDF for the GitHub repo (commit to `powerbi_guide/dashboard_screenshots/`)
- Publish to Power BI Service and include the link in your README
- Screenshot each page and include them in your README

---

## COMMON ISSUES

| Problem | Fix |
|---------|-----|
| Dates showing as numbers | Select column → Data type → Date |
| Map not geocoding UK regions | Set Data Category → State or Province |
| Measures returning blank | Check relationship is Many→One direction |
| % showing as decimal (0.87) | Format → Percentage OR multiply measure by 100 |
| Slicer not filtering a visual | Check visual isn't excluded from slicer in Format → Edit Interactions |
