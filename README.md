# NHS 111 IUC Performance Dashboard

> Operational analytics dashboard for NHS 111 Integrated Urgent Care — built on public NHS England data to surface performance gaps, regional disparities, and demand patterns across England's urgent care network.

---

## Why This Exists

NHS 111 is the front door to urgent care in England. When it underperforms, patients wait longer, ambulances are dispatched unnecessarily, and A&E departments absorb demand that could have been managed upstream.

This dashboard makes the national performance picture visible — week by week, provider by provider, region by region — using only publicly available data.

**Core finding: 78.2% of calls answered within 60 seconds against a 95% NHS target. No week in the 18-week period hit the national target. Not one.**

---

## Dataset

| Dimension | Detail |
|---|---|
| Source | NHS England Weekly IUC ADC (public domain) |
| Period | November 2025 – April 2026 |
| Calls analysed | 7.2 million |
| Weeks covered | 18 |
| Providers | 28 |
| NHS regions | 7 |

Data source: [NHS England UEC SitRep](https://www.england.nhs.uk/statistics/statistical-work-areas/uec-sitrep/)

---

## What's Inside

```
nhs111-dashboard/
│
├── app.py                          ← Streamlit dashboard (run this)
├── process_data.py                 ← Raw Excel → clean CSVs pipeline
├── nhs111_analysis.sql             ← 7-section SQL analysis (fully commented)
├── requirements.txt                ← Python dependencies
│
├── data/
│   ├── nhs111_weekly.csv           ← Weekly data per provider
│   ├── nhs111_national_weekly.csv  ← England-level weekly totals
│   ├── nhs111_daily.csv            ← Daily granularity per provider
│   ├── provider_lookup.csv         ← Provider reference table
│   ├── region_lookup.csv           ← Region reference table
│   └── nhs111.db                   ← SQLite database (all tables)
│
├── powerbi_guide/
│   └── POWERBI_BUILD_GUIDE.md      ← Step-by-step Power BI instructions
│
└── .streamlit/
    └── config.toml                 ← NHS blue colour theme
```

---

## SQL Analysis — 7 Sections

The `nhs111_analysis.sql` file covers the full analytical layer independently of the dashboard:

1. **National KPIs** — headline performance vs 95% target
2. **Provider league table** — ranked performance across all 28 providers
3. **Exception weeks** — identifying weeks with significant target deviation
4. **Regional breakdown** — performance disaggregated across 7 NHS regions
5. **Trend analysis** — week-on-week trajectory
6. **Disposition analysis** — call outcome breakdown (ambulance, A&E, self-care)
7. **Power BI helper views** — pre-aggregated views ready for direct import

---

## Three Ways to Explore This

### Option 1 — Live Dashboard
👉 [https://nhs111-dashboard.streamlit.app](https://nhs111-dashboard.streamlit.app)

### Option 2 — SQL Exploration
Open `data/nhs111.db` in [DB Browser for SQLite](https://sqlitebrowser.org) (free, any OS) and paste queries from `nhs111_analysis.sql`.

### Option 3 — Power BI
Follow `powerbi_guide/POWERBI_BUILD_GUIDE.md` for field-by-field build instructions including DAX measures, conditional formatting rules, and NHS colour codes. Load CSVs from `data/` directly into Power BI Desktop.

---

## How to Run Locally

```bash
git clone https://github.com/freny24/NHS111-dashboard
cd NHS111-dashboard
pip install -r requirements.txt
streamlit run app.py
```

To refresh with new data when NHS England publishes updated figures:
```bash
python process_data.py
```

---

## Clinical Context

This project sits upstream of the hospital admission problem. The SETT Data & AI Research Unit at University Hospital Southampton published work in 2025 predicting discharge delays using ML at the point of admission. This dashboard asks what the signal looks like *before* patients arrive — in the urgent care pathway that precedes that admission decision.

Understanding NHS 111 demand, disposition patterns, and performance gaps is foundational to understanding patient flow across the whole urgent care system.

---

## Author

**Freny Reji**
MS Data Science · Indiana University Bloomington
[LinkedIn](https://www.linkedin.com/in/freny24) · [GitHub](https://github.com/freny24)

*Built with public NHS England data. All analysis reproducible from source.*
