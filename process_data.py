"""
NHS 111 IUC ADC Data Processor
================================
Reads the raw NHS 111 weekly situation report Excel file and produces
clean, analysis-ready CSV files and a SQLite database.

Source: NHS Weekly Integrated Urgent Care Aggregate Data Collection
Period: November 2025 - March 2026

Run:
    python python/process_data.py

Outputs (in data/):
    nhs111_daily.csv           -- one row per provider per day
    nhs111_weekly.csv          -- weekly aggregations per provider
    nhs111_national_weekly.csv -- England-level weekly totals
    provider_lookup.csv        -- provider reference table
    region_lookup.csv          -- region reference table
    nhs111.db                  -- SQLite database (all tables)
"""

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
EXCEL_FILE = DATA_DIR / "Web-File-Timeseries-NHS111-xk360n.xlsx"

REGION_NAMES = {
    "Y56": "London", "Y58": "South West", "Y59": "South East",
    "Y60": "Midlands", "Y61": "East of England",
    "Y62": "North West", "Y63": "North East and Yorkshire",
}

ITEM_LABELS = {
    "A01": "calls_received", "A03": "calls_answered",
    "B01": "calls_answered_60s", "B02": "calls_abandoned",
    "C01": "calls_triaged",
}


def parse_single_metric_sheet(excel_file, sheet_name, metric_code):
    """Parse sheets with one metric per date block."""
    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
    date_row = df.iloc[13]
    records = []
    for col_idx in range(5, len(df.columns)):
        val = date_row.iloc[col_idx]
        if not isinstance(val, pd.Timestamp) and not hasattr(val, "date"):
            continue
        date = pd.Timestamp(val)
        for row_idx in range(16, 44):
            row = df.iloc[row_idx]
            code = row.iloc[2]
            if pd.isna(code) or str(code).strip() == "":
                continue
            v = row.iloc[col_idx]
            if pd.notna(v) and isinstance(v, (int, float)) and float(v) >= 0:
                records.append({
                    "date": date,
                    "region_code": str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "",
                    "contract_code": str(code).strip(),
                    "contract_name": str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else "",
                    "metric_code": metric_code,
                    "value": int(v),
                })
    return pd.DataFrame(records)


def parse_answered_60s_sheet(excel_file):
    """Parse the Calls Answered in 60s sheet (alternating A03/B01 blocks)."""
    df = pd.read_excel(excel_file, sheet_name="Calls Answered in 60s", header=None)
    metric_row = df.iloc[12]
    date_row = df.iloc[13]
    col_map = {}
    current_metric = None
    for col_idx in range(5, len(df.columns)):
        m = metric_row.iloc[col_idx]
        if pd.notna(m) and "A03" in str(m):
            current_metric = "A03"
        elif pd.notna(m) and "B01" in str(m):
            current_metric = "B01"
        d = date_row.iloc[col_idx]
        if (isinstance(d, pd.Timestamp) or hasattr(d, "date")) and current_metric:
            col_map[col_idx] = (pd.Timestamp(d), current_metric)
    records = []
    for col_idx, (date, metric) in col_map.items():
        for row_idx in range(16, 44):
            row = df.iloc[row_idx]
            code = row.iloc[2]
            if pd.isna(code) or str(code).strip() == "":
                continue
            v = row.iloc[col_idx]
            if pd.notna(v) and isinstance(v, (int, float)) and float(v) >= 0:
                records.append({
                    "date": date,
                    "region_code": str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else "",
                    "contract_code": str(code).strip(),
                    "contract_name": str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else "",
                    "metric_code": metric,
                    "value": int(v),
                })
    return pd.DataFrame(records)


if __name__ == "__main__":
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Place the NHS 111 Excel file at:\n  {EXCEL_FILE}"
        )

    print(f"Reading: {EXCEL_FILE}")

    frames = []
    for sheet, metric in [
        ("Calls Received", "A01"),
        ("Calls Abandoned", "B02"),
        ("Triaged Calls", "C01"),
    ]:
        df = parse_single_metric_sheet(str(EXCEL_FILE), sheet, metric)
        frames.append(df)
        print(f"  {sheet}: {len(df):,} rows")

    df_60s = parse_answered_60s_sheet(str(EXCEL_FILE))
    frames.append(df_60s)
    print(f"  Calls Answered in 60s: {len(df_60s):,} rows")

    all_data = pd.concat(frames, ignore_index=True)

    pivot = all_data.pivot_table(
        index=["date", "region_code", "contract_code", "contract_name"],
        columns="metric_code", values="value", aggfunc="sum",
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns=ITEM_LABELS)
    pivot["date"] = pd.to_datetime(pivot["date"])
    pivot["week_ending"] = pivot["date"] + pd.to_timedelta(
        (6 - pivot["date"].dt.dayofweek) % 7, unit="D"
    )

    def add_kpis(df):
        df = df.copy()
        df["pct_answered_60s"] = (
            df["calls_answered_60s"] / df["calls_answered"].replace(0, np.nan) * 100
        ).round(1)
        df["pct_abandoned"] = (
            df["calls_abandoned"]
            / (df["calls_abandoned"] + df["calls_answered"]).replace(0, np.nan)
            * 100
        ).round(1)
        df["meets_60s_target"] = (df["pct_answered_60s"] >= 95).astype(int)
        return df

    pivot = add_kpis(pivot)

    wcols = ["calls_received", "calls_answered", "calls_answered_60s",
             "calls_abandoned", "calls_triaged"]
    weekly = (
        pivot.groupby(["week_ending", "region_code", "contract_code", "contract_name"])[wcols]
        .sum().reset_index()
    )
    weekly = add_kpis(weekly)

    national = pivot.groupby("week_ending")[wcols].sum().reset_index()
    national = add_kpis(national)

    pivot.to_csv(DATA_DIR / "nhs111_daily.csv", index=False)
    weekly.to_csv(DATA_DIR / "nhs111_weekly.csv", index=False)
    national.to_csv(DATA_DIR / "nhs111_national_weekly.csv", index=False)

    provider_lookup = (
        weekly[["contract_code", "contract_name", "region_code"]]
        .drop_duplicates()
        .assign(region_name=lambda x: x["region_code"].map(REGION_NAMES))
    )
    provider_lookup.to_csv(DATA_DIR / "provider_lookup.csv", index=False)

    pd.DataFrame(list(REGION_NAMES.items()), columns=["region_code", "region_name"]).to_csv(
        DATA_DIR / "region_lookup.csv", index=False
    )

    conn = sqlite3.connect(DATA_DIR / "nhs111.db")
    for name, df in [
        ("daily_metrics", pivot), ("weekly_metrics", weekly),
        ("national_weekly", national), ("providers", provider_lookup),
        ("regions", pd.DataFrame(list(REGION_NAMES.items()), columns=["region_code","region_name"])),
    ]:
        df.to_sql(name, conn, if_exists="replace", index=False)
    conn.close()

    print(f"\n✓ Daily: {len(pivot):,} rows | Weekly: {len(weekly):,} rows")
    print(f"✓ Date range: {pivot['date'].min().date()} to {pivot['date'].max().date()}")
    print(f"✓ Providers: {pivot['contract_code'].nunique()} | Regions: 7")
    print(f"✓ Saved to: {DATA_DIR}")
