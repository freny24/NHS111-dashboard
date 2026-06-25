"""
NHS 111 IUC Performance Dashboard
===================================
Streamlit web app for operational monitoring of NHS 111 call-handling
performance. Based on public NHS England Weekly IUC ADC data.

Run locally:  streamlit run app.py
Deploy:       streamlit.io/cloud (free, connects to GitHub)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NHS 111 IUC Performance Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── NHS colour palette ──────────────────────────────────────────────────────
NHS_BLUE       = "#003087"
NHS_BRIGHT     = "#0072CE"
NHS_GREEN      = "#00A651"
NHS_AMBER      = "#FFA500"
NHS_RED        = "#DA291C"
NHS_LIGHT_GREY = "#F0F4F5"
NHS_DARK_GREY  = "#425563"

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Main background */
.main { background-color: #F0F4F5; }
[data-testid="stSidebar"] { background-color: #003087; }
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stSelectbox label { color: white !important; }
[data-testid="stSidebar"] .stMultiSelect label { color: white !important; }

/* KPI metric cards */
[data-testid="metric-container"] {
    background-color: white;
    border: 1px solid #d8dde0;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

/* Section headings */
h1 { color: #003087 !important; font-size: 1.8rem !important; }
h2 { color: #003087 !important; border-bottom: 3px solid #003087;
     padding-bottom: 6px; }
h3 { color: #003087 !important; }

/* RAG badges */
.rag-green  { background:#00A651; color:white; padding:3px 10px;
               border-radius:12px; font-weight:600; font-size:0.82rem; }
.rag-amber  { background:#FFA500; color:white; padding:3px 10px;
               border-radius:12px; font-weight:600; font-size:0.82rem; }
.rag-red    { background:#DA291C; color:white; padding:3px 10px;
               border-radius:12px; font-weight:600; font-size:0.82rem; }

/* Info box */
.info-box { background:white; border-left:4px solid #003087;
             padding:12px 16px; border-radius:0 8px 8px 0;
             margin:8px 0; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    base = Path(__file__).parent / "data"

    weekly   = pd.read_csv(base / "nhs111_weekly.csv",
                           parse_dates=["week_ending"])
    national = pd.read_csv(base / "nhs111_national_weekly.csv",
                           parse_dates=["week_ending"])
    providers = pd.read_csv(base / "provider_lookup.csv")

    # Clean up region names (join from providers)
    region_map = providers.set_index("contract_code")["region_name"].to_dict()
    weekly["region_name"] = weekly["contract_code"].map(region_map)

    # Remove incomplete last week
    weekly   = weekly[weekly["calls_received"] > 0].copy()
    national = national[national["calls_received"] > 0].copy()

    # Recalculate KPIs cleanly
    for df in [weekly, national]:
        df["pct_60s"] = (
            df["calls_answered_60s"] / df["calls_answered"].replace(0, np.nan) * 100
        ).round(1)
        df["pct_abandoned"] = (
            df["calls_abandoned"]
            / (df["calls_abandoned"] + df["calls_answered"]).replace(0, np.nan)
            * 100
        ).round(1)
        df["meets_target"] = df["pct_60s"] >= 95

    return weekly, national, providers


weekly, national, providers = load_data()

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3"
        "/NHS-Logo.svg/1200px-NHS-Logo.svg.png",
        width=80,
    )
    st.markdown("## NHS 111 IUC Dashboard")
    st.markdown("**Period:** Nov 2025 – Apr 2026")
    st.markdown("**Source:** NHS England Weekly IUC ADC")
    st.markdown("---")

    page = st.radio(
        "Navigate to",
        ["🏠 National Overview",
         "🏥 Provider Performance",
         "⚠️ Exception Analysis",
         "📊 Trend Analysis"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Date range filter
    min_date = national["week_ending"].min().date()
    max_date = national["week_ending"].max().date()
    date_range = st.date_input(
        "Week ending range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if len(date_range) == 2:
        d_start, d_end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    else:
        d_start, d_end = pd.Timestamp(min_date), pd.Timestamp(max_date)

    # Region filter
    all_regions = sorted(providers["region_name"].dropna().unique().tolist())
    selected_regions = st.multiselect(
        "Filter by region",
        options=all_regions,
        default=all_regions,
        help="Select one or more NHS regions",
    )

# Apply filters
nat_f = national[
    (national["week_ending"] >= d_start) & (national["week_ending"] <= d_end)
]
wkly_f = weekly[
    (weekly["week_ending"] >= d_start)
    & (weekly["week_ending"] <= d_end)
    & (weekly["region_name"].isin(selected_regions))
]


# ── Helpers ─────────────────────────────────────────────────────────────────
def rag_color(val, green=95, amber=88):
    if pd.isna(val):
        return NHS_DARK_GREY
    if val >= green:
        return NHS_GREEN
    if val >= amber:
        return NHS_AMBER
    return NHS_RED


def rag_badge(val, green=95, amber=88):
    if pd.isna(val):
        return '<span class="rag-amber">N/A</span>'
    if val >= green:
        return '<span class="rag-green">● Green</span>'
    if val >= amber:
        return '<span class="rag-amber">● Amber</span>'
    return '<span class="rag-red">● Red</span>'


def fmt_pct(v):
    return f"{v:.1f}%" if pd.notna(v) else "—"


def plotly_theme(fig, height=400):
    fig.update_layout(
        height=height,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Helvetica, Arial, sans-serif", color=NHS_DARK_GREY),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, linecolor="#d8dde0"),
        yaxis=dict(gridcolor="#e8ecef", linecolor="#d8dde0"),
    )
    return fig


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — NATIONAL OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
if page == "🏠 National Overview":

    st.title("🏠 NHS 111 National Overview")
    st.markdown(
        '<div class="info-box">Performance data covers <b>28 NHS 111 providers</b> '
        'across <b>7 regions</b>. '
        'The NHS 111 target is <b>95% of calls answered within 60 seconds</b>.</div>',
        unsafe_allow_html=True,
    )

    # ── KPI Row ──────────────────────────────────────────────────────────
    total_calls  = nat_f["calls_received"].sum()
    total_ans    = nat_f["calls_answered"].sum()
    total_60s    = nat_f["calls_answered_60s"].sum()
    total_aband  = nat_f["calls_abandoned"].sum()
    avg_60s      = (total_60s / total_ans * 100) if total_ans else 0
    avg_aband    = (total_aband / (total_aband + total_ans) * 100) if (total_aband + total_ans) else 0
    weeks_target = nat_f["meets_target"].sum()
    n_weeks      = len(nat_f)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📞 Total Calls", f"{total_calls:,.0f}")
    c2.metric("✅ Calls Answered", f"{total_ans:,.0f}")
    c3.metric(
        "⏱️ % Answered in 60s",
        fmt_pct(avg_60s),
        delta=f"{avg_60s - 95:.1f}pp vs target",
        delta_color="inverse",
    )
    c4.metric("📵 Abandonment Rate", fmt_pct(avg_aband))
    c5.metric(
        "🎯 Weeks Meeting Target",
        f"{int(weeks_target)}/{n_weeks}",
        delta="95% threshold",
        delta_color="off",
    )

    st.markdown("---")

    # ── Main trend chart ─────────────────────────────────────────────────
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("% Calls Answered in 60 Seconds — Weekly Trend")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=nat_f["week_ending"], y=nat_f["pct_60s"],
            mode="lines+markers",
            name="% Answered in 60s",
            line=dict(color=NHS_BRIGHT, width=2.5),
            marker=dict(size=7,
                        color=[rag_color(v) for v in nat_f["pct_60s"]],
                        line=dict(width=1.5, color="white")),
            hovertemplate="Week: %{x|%d %b %Y}<br>% in 60s: %{y:.1f}%<extra></extra>",
        ))
        # 95% target line
        fig.add_hline(y=95, line_dash="dash", line_color=NHS_RED,
                      annotation_text="95% Target",
                      annotation_position="right",
                      annotation_font=dict(color=NHS_RED, size=11))
        # Shade below target
        fig.add_hrect(y0=0, y1=95, fillcolor=NHS_RED,
                      opacity=0.04, line_width=0)
        fig.update_layout(yaxis=dict(range=[50, 100], title="% Answered in 60s"),
                          xaxis=dict(title="Week ending"))
        plotly_theme(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Weekly Call Volume")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=nat_f["week_ending"],
            y=nat_f["calls_received"],
            name="Calls Received",
            marker_color=NHS_BLUE,
            hovertemplate="Week: %{x|%d %b %Y}<br>Calls: %{y:,.0f}<extra></extra>",
        ))
        fig2.update_layout(
            yaxis=dict(title="Calls Received"),
            xaxis=dict(title="Week ending"),
            showlegend=False,
        )
        plotly_theme(fig2, height=380)
        st.plotly_chart(fig2, use_container_width=True)

    # ── Abandonment trend ─────────────────────────────────────────────────
    st.subheader("Abandonment Rate Trend")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=nat_f["week_ending"], y=nat_f["pct_abandoned"],
        mode="lines+markers",
        name="Abandonment Rate",
        line=dict(color=NHS_AMBER, width=2.5),
        fill="tozeroy", fillcolor="rgba(255,165,0,0.08)",
        hovertemplate="Week: %{x|%d %b %Y}<br>Abandonment: %{y:.1f}%<extra></extra>",
    ))
    fig3.add_hline(y=5, line_dash="dash", line_color=NHS_RED,
                   annotation_text="5% Threshold",
                   annotation_position="right",
                   annotation_font=dict(color=NHS_RED, size=11))
    fig3.update_layout(
        yaxis=dict(title="Abandonment Rate (%)"),
        xaxis=dict(title="Week ending"),
        showlegend=False,
    )
    plotly_theme(fig3, height=280)
    st.plotly_chart(fig3, use_container_width=True)

    st.caption(
        "Source: NHS England Weekly Integrated Urgent Care ADC · "
        "Not for clinical use · Data is aggregated and anonymised at provider level"
    )


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — PROVIDER PERFORMANCE
# ════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Provider Performance":

    st.title("🏥 Provider Performance")
    st.markdown(
        '<div class="info-box">'
        '<b>RAG Status:</b> '
        '<span class="rag-green">Green</span> ≥ 95% &nbsp;│&nbsp; '
        '<span class="rag-amber">Amber</span> ≥ 88% &nbsp;│&nbsp; '
        '<span class="rag-red">Red</span> &lt; 88%'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Provider summary table ────────────────────────────────────────────
    prov_summary = (
        wkly_f.groupby(["contract_code", "contract_name", "region_name"])
        .agg(
            total_calls=("calls_received", "sum"),
            calls_answered=("calls_answered", "sum"),
            calls_answered_60s=("calls_answered_60s", "sum"),
            calls_abandoned=("calls_abandoned", "sum"),
            weeks=("week_ending", "nunique"),
        )
        .reset_index()
    )
    prov_summary["pct_60s"] = (
        prov_summary["calls_answered_60s"]
        / prov_summary["calls_answered"].replace(0, np.nan)
        * 100
    ).round(1)
    prov_summary["pct_abandoned"] = (
        prov_summary["calls_abandoned"]
        / (prov_summary["calls_abandoned"] + prov_summary["calls_answered"]).replace(0, np.nan)
        * 100
    ).round(1)
    prov_summary["RAG"] = prov_summary["pct_60s"].apply(
        lambda v: "🟢 Green" if v >= 95 else ("🟡 Amber" if v >= 88 else "🔴 Red")
    )
    prov_summary = prov_summary.sort_values("pct_60s", ascending=False)

    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Provider League Table")
        display = prov_summary[[
            "contract_name", "region_name", "total_calls",
            "pct_60s", "pct_abandoned", "weeks", "RAG"
        ]].rename(columns={
            "contract_name": "Provider",
            "region_name": "Region",
            "total_calls": "Total Calls",
            "pct_60s": "% in 60s",
            "pct_abandoned": "Abnd. %",
            "weeks": "Wks",
            "RAG": "Status",
        })

        # Colour the % in 60s column
        def colour_pct(val):
            if pd.isna(val):
                return ""
            if val >= 95:
                return f"color: {NHS_GREEN}; font-weight:bold"
            if val >= 88:
                return f"color: {NHS_AMBER}; font-weight:bold"
            return f"color: {NHS_RED}; font-weight:bold"

        styled = display.style.applymap(
            colour_pct, subset=["% in 60s"]
        ).format({"Total Calls": "{:,.0f}", "% in 60s": "{:.1f}", "Abnd. %": "{:.1f}"})
        st.dataframe(styled, use_container_width=True, height=500)

    with col_b:
        st.subheader("% Answered in 60s by Provider")
        fig = go.Figure()
        sorted_df = prov_summary.sort_values("pct_60s")
        fig.add_trace(go.Bar(
            y=sorted_df["contract_name"],
            x=sorted_df["pct_60s"],
            orientation="h",
            marker_color=[rag_color(v) for v in sorted_df["pct_60s"]],
            hovertemplate="%{y}<br>% in 60s: %{x:.1f}%<extra></extra>",
        ))
        fig.add_vline(x=95, line_dash="dash", line_color=NHS_RED,
                      annotation_text="95% Target",
                      annotation_position="top",
                      annotation_font=dict(color=NHS_RED, size=10))
        fig.update_layout(
            xaxis=dict(range=[0, 105], title="% Answered in 60s"),
            yaxis=dict(title=""),
            showlegend=False,
        )
        plotly_theme(fig, height=620)
        st.plotly_chart(fig, use_container_width=True)

    # ── Regional comparison ───────────────────────────────────────────────
    st.subheader("Performance by Region")
    region_agg = (
        wkly_f.groupby("region_name")
        .agg(
            calls_answered=("calls_answered", "sum"),
            calls_answered_60s=("calls_answered_60s", "sum"),
            calls_received=("calls_received", "sum"),
            calls_abandoned=("calls_abandoned", "sum"),
            providers=("contract_code", "nunique"),
        )
        .reset_index()
    )
    region_agg["pct_60s"] = (
        region_agg["calls_answered_60s"]
        / region_agg["calls_answered"].replace(0, np.nan)
        * 100
    ).round(1)
    region_agg = region_agg.sort_values("pct_60s", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            region_agg,
            x="region_name", y="pct_60s",
            color="pct_60s",
            color_continuous_scale=[[0, NHS_RED], [0.4, NHS_AMBER], [0.6, NHS_GREEN], [1, NHS_GREEN]],
            range_color=[50, 100],
            labels={"region_name": "Region", "pct_60s": "% Answered in 60s"},
            title="% Answered in 60s by NHS Region",
        )
        fig.add_hline(y=95, line_dash="dash", line_color="black",
                      annotation_text="95% Target")
        fig.update_coloraxes(showscale=False)
        plotly_theme(fig, height=340)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(
            region_agg,
            x="region_name", y="calls_received",
            color_discrete_sequence=[NHS_BLUE],
            labels={"region_name": "Region", "calls_received": "Total Calls"},
            title="Total Calls Received by NHS Region",
        )
        plotly_theme(fig2, height=340)
        st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — EXCEPTION ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
elif page == "⚠️ Exception Analysis":

    st.title("⚠️ Exception Analysis")
    st.markdown(
        '<div class="info-box">Exception weeks are any provider-week where '
        '% answered in 60s fell <b>below the 95% NHS target</b>. '
        'Providers with persistent exceptions may require targeted support.</div>',
        unsafe_allow_html=True,
    )

    # ── Exception counts ──────────────────────────────────────────────────
    exception_df = wkly_f[wkly_f["calls_answered"] > 0].copy()
    exception_df["is_exception"] = exception_df["pct_60s"] < 95

    exc_by_provider = (
        exception_df.groupby(["contract_code", "contract_name", "region_name"])
        .agg(
            total_weeks=("week_ending", "nunique"),
            exception_weeks=("is_exception", "sum"),
            worst_pct=("pct_60s", "min"),
            avg_pct=("pct_60s", "mean"),
        )
        .reset_index()
    )
    exc_by_provider["pct_exception"] = (
        exc_by_provider["exception_weeks"] / exc_by_provider["total_weeks"] * 100
    ).round(0)
    exc_by_provider = exc_by_provider.sort_values("exception_weeks", ascending=False)

    # ── Top KPI cards ─────────────────────────────────────────────────────
    total_exc_weeks = exception_df["is_exception"].sum()
    total_pw = len(exception_df)
    always_below = (exc_by_provider["pct_exception"] == 100).sum()
    worst_prov = exc_by_provider.iloc[0]["contract_name"] if not exc_by_provider.empty else "—"
    worst_pct  = exc_by_provider.iloc[-1]["worst_pct"] if not exc_by_provider.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚨 Total Exception Provider-Weeks", f"{int(total_exc_weeks)}")
    c2.metric("📉 % of Reporting Weeks Below Target",
              f"{100*total_exc_weeks/total_pw:.0f}%" if total_pw else "—")
    c3.metric("🔴 Providers NEVER Meeting Target", f"{int(always_below)}")
    c4.metric("⬇️ Lowest Single-Week Performance",
              fmt_pct(exc_by_provider["worst_pct"].min()))

    st.markdown("---")

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Exception Weeks per Provider")
        fig = go.Figure()
        df_plot = exc_by_provider.sort_values("exception_weeks")
        fig.add_trace(go.Bar(
            y=df_plot["contract_name"],
            x=df_plot["exception_weeks"],
            orientation="h",
            marker_color=[NHS_RED if v == v_max else NHS_AMBER
                          for v, v_max in zip(
                              df_plot["exception_weeks"],
                              [df_plot["exception_weeks"].max()] * len(df_plot)
                          )],
            hovertemplate="%{y}<br>Exception weeks: %{x}<extra></extra>",
        ))
        fig.update_layout(
            xaxis=dict(title="Number of Weeks Below 95% Target"),
            yaxis=dict(title=""),
            showlegend=False,
        )
        plotly_theme(fig, height=600)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Exception Weeks Detail")
        exc_detail = exception_df[exception_df["is_exception"]].copy()
        exc_detail["week_ending_str"] = exc_detail["week_ending"].dt.strftime("%d %b %Y")
        exc_display = exc_detail[[
            "week_ending_str", "contract_name", "region_name",
            "calls_received", "pct_60s", "pct_abandoned"
        ]].rename(columns={
            "week_ending_str": "Week Ending",
            "contract_name": "Provider",
            "region_name": "Region",
            "calls_received": "Calls",
            "pct_60s": "% in 60s",
            "pct_abandoned": "Abnd. %",
        }).sort_values("% in 60s")

        def colour_exc(val):
            if pd.isna(val): return ""
            if val >= 88: return f"color:{NHS_AMBER};font-weight:bold"
            return f"color:{NHS_RED};font-weight:bold"

        styled_exc = exc_display.style.applymap(
            colour_exc, subset=["% in 60s"]
        ).format({"Calls": "{:,.0f}", "% in 60s": "{:.1f}", "Abnd. %": "{:.1f}"})
        st.dataframe(styled_exc, use_container_width=True, height=600)

    # ── High abandonment detail ───────────────────────────────────────────
    st.subheader("High Abandonment Rate Events (>5% threshold)")
    high_aband = wkly_f[
        (wkly_f["pct_abandoned"] > 5) & (wkly_f["calls_answered"] > 0)
    ].copy().sort_values("pct_abandoned", ascending=False)

    if not high_aband.empty:
        ha_display = high_aband[[
            "week_ending", "contract_name", "region_name",
            "calls_received", "calls_abandoned", "pct_abandoned"
        ]].copy()
        ha_display["week_ending"] = ha_display["week_ending"].dt.strftime("%d %b %Y")
        ha_display = ha_display.rename(columns={
            "week_ending": "Week", "contract_name": "Provider",
            "region_name": "Region", "calls_received": "Total Calls",
            "calls_abandoned": "Abandoned", "pct_abandoned": "Abnd. %"
        })
        st.dataframe(
            ha_display.style.format({"Total Calls": "{:,.0f}", "Abandoned": "{:,.0f}",
                                     "Abnd. %": "{:.1f}"}),
            use_container_width=True, height=300,
        )
    else:
        st.success("No provider-weeks exceeded the 5% abandonment threshold in the selected period.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 — TREND ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
elif page == "📊 Trend Analysis":

    st.title("📊 Trend Analysis")
    st.markdown(
        '<div class="info-box">Rolling averages and week-on-week comparisons '
        'to identify sustained improvement or deterioration trends.</div>',
        unsafe_allow_html=True,
    )

    # ── Rolling average chart ─────────────────────────────────────────────
    nat_trend = nat_f.copy().sort_values("week_ending")
    nat_trend["roll_4wk_60s"]   = nat_trend["pct_60s"].rolling(4, min_periods=1).mean()
    nat_trend["roll_4wk_calls"] = nat_trend["calls_received"].rolling(4, min_periods=1).mean()
    nat_trend["wow_calls"] = nat_trend["calls_received"].pct_change() * 100

    st.subheader("60s Answer Rate: Actual vs 4-Week Rolling Average")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=nat_trend["week_ending"], y=nat_trend["pct_60s"],
        mode="lines+markers", name="Weekly actual",
        line=dict(color=NHS_BRIGHT, width=1.5, dash="dot"),
        marker=dict(size=6, color=NHS_BRIGHT),
        hovertemplate="Week: %{x|%d %b %Y}<br>Actual: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=nat_trend["week_ending"], y=nat_trend["roll_4wk_60s"].round(1),
        mode="lines", name="4-week rolling avg",
        line=dict(color=NHS_BLUE, width=3),
        hovertemplate="Week: %{x|%d %b %Y}<br>4-wk avg: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=95, line_dash="dash", line_color=NHS_RED,
                  annotation_text="95% Target", annotation_position="right",
                  annotation_font=dict(color=NHS_RED))
    fig.update_layout(yaxis=dict(range=[50, 100], title="% Answered in 60s"),
                      xaxis=dict(title="Week ending"))
    plotly_theme(fig, height=380)
    st.plotly_chart(fig, use_container_width=True)

    # ── Provider trend selector ───────────────────────────────────────────
    st.subheader("Provider Trend Comparison")
    all_provs = sorted(wkly_f["contract_name"].unique().tolist())
    sel_provs = st.multiselect(
        "Select providers to compare",
        options=all_provs,
        default=all_provs[:4] if len(all_provs) >= 4 else all_provs,
    )

    if sel_provs:
        prov_trend = wkly_f[wkly_f["contract_name"].isin(sel_provs)].copy()
        fig2 = px.line(
            prov_trend,
            x="week_ending", y="pct_60s",
            color="contract_name",
            markers=True,
            labels={"week_ending": "Week Ending", "pct_60s": "% Answered in 60s",
                    "contract_name": "Provider"},
        )
        fig2.add_hline(y=95, line_dash="dash", line_color=NHS_RED,
                       annotation_text="95% Target",
                       annotation_position="top right",
                       annotation_font=dict(color=NHS_RED))
        fig2.update_layout(yaxis=dict(range=[0, 105]))
        plotly_theme(fig2, height=420)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select at least one provider above to view their trend.")

    # ── Demand trend ──────────────────────────────────────────────────────
    st.subheader("Demand Trend: Actual vs Rolling Average")
    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Bar(
        x=nat_trend["week_ending"], y=nat_trend["calls_received"],
        name="Weekly calls", marker_color=NHS_LIGHT_GREY,
        hovertemplate="Week: %{x|%d %b %Y}<br>Calls: %{y:,.0f}<extra></extra>",
    ), secondary_y=False)
    fig3.add_trace(go.Scatter(
        x=nat_trend["week_ending"], y=nat_trend["roll_4wk_calls"].round(0),
        name="4-week rolling avg", line=dict(color=NHS_BLUE, width=2.5),
        hovertemplate="4-wk avg: %{y:,.0f}<extra></extra>",
    ), secondary_y=False)
    fig3.update_layout(
        height=340, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Helvetica, Arial, sans-serif"),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(title="Week ending", showgrid=False),
        yaxis=dict(title="Calls Received", gridcolor="#e8ecef"),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Peak demand table ─────────────────────────────────────────────────
    st.subheader("Top 5 Highest Demand Weeks")
    peak_df = (
        nat_f.sort_values("calls_received", ascending=False)
        .head(5)[["week_ending", "calls_received", "pct_60s", "pct_abandoned"]]
        .copy()
    )
    peak_df["week_ending"] = peak_df["week_ending"].dt.strftime("%d %b %Y")
    peak_df = peak_df.rename(columns={
        "week_ending": "Week Ending",
        "calls_received": "Calls Received",
        "pct_60s": "% in 60s",
        "pct_abandoned": "Abnd. %",
    })
    st.dataframe(
        peak_df.style.format({
            "Calls Received": "{:,.0f}", "% in 60s": "{:.1f}", "Abnd. %": "{:.1f}"
        }),
        use_container_width=True, hide_index=True,
    )

    st.caption(
        "Source: NHS England Weekly IUC ADC · "
        "Period: Nov 2025 – Apr 2026 · 28 providers · 7 NHS regions"
    )
