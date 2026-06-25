# NHS 111 IUC Performance Dashboard

Operational performance dashboard for NHS 111 Integrated Urgent Care, built on
public NHS England Weekly IUC ADC data.

**Data:** 7.2M calls · 18 weeks · 28 providers · 7 NHS regions · Nov 2025–Apr 2026  
**Key finding:** 78.2% avg answered in 60s vs 95% NHS target · 0/18 weeks hit target nationally

---

## What's in this zip

```
nhs111-dashboard/
│
├── app.py                         ← Streamlit dashboard (run this)
├── process_data.py                ← Raw Excel → clean CSVs (re-run if you get new data)
├── nhs111_analysis.sql            ← All SQL queries (7 sections, fully commented)
├── requirements.txt               ← Python packages needed
│
├── data/
│   ├── nhs111_weekly.csv          ← Weekly data per provider (used by dashboard)
│   ├── nhs111_national_weekly.csv ← England totals per week (used by dashboard)
│   ├── nhs111_daily.csv           ← Daily data per provider (for deeper analysis)
│   ├── provider_lookup.csv        ← Provider reference table
│   ├── region_lookup.csv          ← Region reference table
│   └── nhs111.db                  ← SQLite database (all tables, for SQL tools)
│
├── powerbi_guide/
│   └── POWERBI_BUILD_GUIDE.md     ← Step-by-step Power BI build guide (if needed)
│
└── .streamlit/
    └── config.toml                ← NHS blue colour theme
```

---

## Option 1: Run the Streamlit dashboard (recommended)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501. Four pages:
- 🏠 National Overview — headline KPIs, trend charts
- 🏥 Provider Performance — league table with RAG status
- ⚠️ Exception Analysis — who's failing and how often
- 📊 Trend Analysis — rolling averages, provider comparisons

---

## Option 2: Deploy free as a live link (5 minutes)

1. Push this folder to GitHub
2. Go to share.streamlit.io → sign in → New app → select repo → Deploy
3. Get a URL like https://freny24-nhs111-dashboard.streamlit.app
4. Send that link — anyone clicks it, no account needed

---

## Option 3: Explore the SQL

Open `data/nhs111.db` in **DB Browser for SQLite** (free, any OS):
https://sqlitebrowser.org

Then paste queries from `nhs111_analysis.sql`. Seven sections covering:
national KPIs · provider league table · exception weeks · regional breakdown ·
trend analysis · disposition analysis · Power BI helper views

---

## Option 4: Build the Power BI dashboard

Follow `powerbi_guide/POWERBI_BUILD_GUIDE.md` — field-by-field instructions,
DAX measures, conditional formatting rules, NHS colour codes.
Load the CSVs from the `data/` folder directly into Power BI Desktop (free).

---

## Data source

[NHS England Weekly IUC ADC](https://www.england.nhs.uk/statistics/statistical-work-areas/uec-sitrep/)
Public domain. NHS 111 target: 95% of calls answered within 60 seconds.
