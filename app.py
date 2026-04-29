"""
SAP Archiving Assistant — Streamlit prototype.

An AI-powered, enterprise-styled dashboard that scans simulated SAP ECC tables
for archiving candidates, applies a transparent rules engine plus optional
ML-based anomaly detection, and produces actionable cleanup recommendations.

Run: `streamlit run app.py --server.port 8501`
All data is synthetic. No SAP connection is required.
"""
from __future__ import annotations

import io
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import streamlit as st

from archivability import (
    SKLEARN_AVAILABLE,
    detect_data_issues,
    run_full_pipeline,
)
from data_generator import generate_objects, summary_by_object
from reporting import build_markdown_report

try:
    import plotly.express as px
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except Exception:  # pragma: no cover
    PLOTLY_AVAILABLE = False


# ---------- Page config ----------
st.set_page_config(
    page_title="SAP Archiving Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Theme / CSS ----------
PRIMARY = "#0a6e8c"      # SAP-adjacent teal
PRIMARY_DARK = "#063f51"
ACCENT = "#1ba0bf"
SURFACE = "#ffffff"
BG = "#f4f7fa"
INK = "#0e1c26"
MUTED = "#5c6f7a"

STATUS_COLORS = {
    "ARCHIVE": "#0a6e8c",
    "REVIEW": "#c97a17",
    "REMEDIATE": "#a83232",
    "DEDUPLICATE": "#7a3aa8",
    "RETAIN": "#4a5c66",
}

CUSTOM_CSS = f"""
<style>
  /* Fonts */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');

  html, body, [class*="css"], [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    color: {INK};
  }}
  [data-testid="stAppViewContainer"] {{
    background: {BG};
  }}
  [data-testid="stHeader"] {{ background: transparent; }}
  [data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {PRIMARY_DARK} 0%, #04303f 100%);
  }}
  [data-testid="stSidebar"] * {{ color: #e8f1f5 !important; }}
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {{ color: #ffffff !important; letter-spacing: 0.02em; }}

  /* App brand bar */
  .brand-bar {{
    background: linear-gradient(90deg, {PRIMARY_DARK} 0%, {PRIMARY} 65%, {ACCENT} 100%);
    color: #fff;
    padding: 22px 28px;
    border-radius: 12px;
    margin-bottom: 22px;
    box-shadow: 0 4px 14px rgba(6,63,81,0.10);
  }}
  .brand-bar h1 {{ margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.01em; }}
  .brand-bar p {{ margin: 4px 0 0 0; opacity: 0.92; font-size: 14px; }}
  .brand-bar .badges {{ margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }}
  .brand-bar .pill {{
    background: rgba(255,255,255,0.16);
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
  }}

  /* KPI cards */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
  @media (max-width: 1100px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  .kpi {{
    background: {SURFACE};
    border: 1px solid #e1e8ee;
    border-radius: 12px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(14,28,38,0.04);
  }}
  .kpi .label {{
    color: {MUTED}; font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.08em; font-weight: 600;
  }}
  .kpi .value {{
    color: {INK}; font-size: 28px; font-weight: 700; margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }}
  .kpi .delta {{ color: {MUTED}; font-size: 12px; margin-top: 4px; }}
  .kpi.accent {{ border-left: 4px solid {PRIMARY}; }}
  .kpi.warn {{ border-left: 4px solid #c97a17; }}
  .kpi.danger {{ border-left: 4px solid #a83232; }}
  .kpi.good {{ border-left: 4px solid #2f8a3e; }}

  /* Section card */
  .section {{
    background: {SURFACE};
    border: 1px solid #e1e8ee;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 18px;
  }}
  .section h2 {{
    font-size: 16px; font-weight: 600; margin: 0 0 14px 0;
    color: {INK}; letter-spacing: -0.005em;
  }}
  .section h2 .hint {{
    font-weight: 400; color: {MUTED}; font-size: 13px; margin-left: 8px;
  }}

  /* Status badges */
  .badge {{
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.03em;
  }}

  /* Buttons */
  .stButton > button, .stDownloadButton > button {{
    background: {PRIMARY}; color: #fff; border: 0; border-radius: 8px;
    padding: 8px 16px; font-weight: 600;
  }}
  .stButton > button:hover, .stDownloadButton > button:hover {{
    background: {PRIMARY_DARK};
  }}

  /* Tables */
  [data-testid="stDataFrame"] {{ border-radius: 8px; overflow: hidden; }}

  /* Footer */
  .footer {{
    color: {MUTED}; font-size: 12px; text-align: center; padding: 14px 0 4px;
  }}
  .footer a {{ color: {PRIMARY}; }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------- Data load (cached) ----------
@st.cache_data(show_spinner=False)
def load_data(seed: int, n_per_object: int) -> pd.DataFrame:
    df = generate_objects(seed=seed, n_per_object=n_per_object)
    return run_full_pipeline(df)


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### SAP Archiving Assistant")
    st.caption("Prototype • Synthetic data only")

    st.markdown("#### Dataset")
    seed = st.number_input("Random seed", value=42, step=1, min_value=0, max_value=9999)
    n_per_object = st.slider("Records per object", 100, 800, 350, step=50)

    if st.button("🔄 Regenerate dataset", width="stretch"):
        st.cache_data.clear()

    st.markdown("---")
    st.markdown("#### Filters")

df = load_data(int(seed), int(n_per_object))

with st.sidebar:
    objects_avail = sorted(df["archiving_object"].unique().tolist())
    sel_objects = st.multiselect("Archiving object", objects_avail, default=objects_avail)

    modules_avail = sorted(df["module"].unique().tolist())
    sel_modules = st.multiselect("Module", modules_avail, default=modules_avail)

    company_codes = sorted(df["company_code"].unique().tolist())
    sel_company = st.multiselect("Company code", company_codes, default=company_codes)

    statuses_avail = sorted(df["status"].unique().tolist())
    sel_status = st.multiselect("Status", statuses_avail, default=statuses_avail)

    min_score = st.slider("Min archivability score", 0, 100, 0, step=5)
    only_archivable = st.checkbox("Only show ARCHIVE candidates", value=False)
    exclude_legal_hold = st.checkbox("Exclude legal-hold records", value=True)

    st.markdown("---")
    ml_label = "scikit-learn IsolationForest" if SKLEARN_AVAILABLE else "Heuristic fallback"
    chart_label = "Plotly" if PLOTLY_AVAILABLE else "Streamlit native"
    st.caption(f"**Anomaly engine:** {ml_label}")
    st.caption(f"**Chart engine:** {chart_label}")


# Apply filters
mask = (
    df["archiving_object"].isin(sel_objects)
    & df["module"].isin(sel_modules)
    & df["company_code"].isin(sel_company)
    & df["status"].isin(sel_status)
    & (df["archivability_score"] >= min_score)
)
if only_archivable:
    mask &= df["recommendation"] == "ARCHIVE"
if exclude_legal_hold:
    mask &= ~df["legal_hold"]

fdf = df[mask].copy()


# ---------- Header ----------
st.markdown(
    f"""
    <div class="brand-bar">
      <h1>SAP Archiving Assistant</h1>
      <p>AI-assisted archivability analysis across simulated SAP ECC business objects.
      Identify cleanup candidates, surface data-quality risks, and prioritize archive runs.</p>
      <div class="badges">
        <span class="pill">Synthetic data</span>
        <span class="pill">Anomaly: {ml_label}</span>
        <span class="pill">Charts: {chart_label}</span>
        <span class="pill">{len(df):,} total records</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Executive summary ----------
total = len(fdf)
archive_n = int((fdf["recommendation"] == "ARCHIVE").sum())
review_n = int((fdf["recommendation"] == "REVIEW").sum())
remediate_n = int(fdf["recommendation"].isin(["REMEDIATE", "DEDUPLICATE"]).sum())
retain_n = int((fdf["recommendation"] == "RETAIN").sum())
total_size_gb = round(fdf["size_mb"].sum() / 1024, 2)
archive_size_gb = round(
    fdf.loc[fdf["recommendation"] == "ARCHIVE", "size_mb"].sum() / 1024, 2
)
pct_archivable = round(100.0 * archive_n / max(total, 1), 1)
issues = detect_data_issues(fdf)

st.markdown(
    f"""
    <div class="section">
      <h2>Executive summary <span class="hint">snapshot of current filter</span></h2>
      <p style="margin:0;color:{INK};font-size:14px;line-height:1.55;">
        Across <b>{total:,}</b> filtered records (<b>{total_size_gb:,} GB</b>),
        <b>{archive_n:,}</b> ({pct_archivable}%) are high-confidence archive candidates,
        reclaiming up to <b>{archive_size_gb:,} GB</b> of online storage.
        <b>{review_n:,}</b> need manual review, <b>{remediate_n:,}</b> require data remediation,
        and <b>{retain_n:,}</b> should remain online.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- KPI cards ----------
st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi accent">
        <div class="label">Records in scope</div>
        <div class="value">{total:,}</div>
        <div class="delta">{total_size_gb:,} GB online</div>
      </div>
      <div class="kpi good">
        <div class="label">Archive candidates</div>
        <div class="value">{archive_n:,}</div>
        <div class="delta">{pct_archivable}% • {archive_size_gb:,} GB recoverable</div>
      </div>
      <div class="kpi warn">
        <div class="label">Needs review / remediation</div>
        <div class="value">{review_n + remediate_n:,}</div>
        <div class="delta">{review_n:,} review · {remediate_n:,} remediate</div>
      </div>
      <div class="kpi danger">
        <div class="label">Data quality findings</div>
        <div class="value">{issues['duplicates'] + issues['inconsistencies']:,}</div>
        <div class="delta">{issues['duplicates']:,} duplicates · {issues['inconsistencies']:,} inconsistencies</div>
      </div>
    </div>
    <div style="height:18px"></div>
    """,
    unsafe_allow_html=True,
)


# ---------- Charts ----------
def _color_for(recs: pd.Series) -> list:
    return [STATUS_COLORS.get(r, "#888") for r in recs]


col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown('<div class="section"><h2>Archivability by object <span class="hint">stacked recommendation breakdown</span></h2>', unsafe_allow_html=True)
    by_obj = (
        fdf.groupby(["archiving_object", "recommendation"]).size().reset_index(name="count")
    )
    if PLOTLY_AVAILABLE and len(by_obj):
        fig = px.bar(
            by_obj,
            x="archiving_object",
            y="count",
            color="recommendation",
            color_discrete_map=STATUS_COLORS,
            barmode="stack",
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend_title_text="",
            xaxis_title="",
            yaxis_title="Records",
            font=dict(family="Inter", size=12, color=INK),
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#eef2f5")
        st.plotly_chart(fig, width="stretch")
    else:
        pivot = by_obj.pivot(index="archiving_object", columns="recommendation", values="count").fillna(0)
        st.bar_chart(pivot)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section"><h2>Recommendation mix</h2>', unsafe_allow_html=True)
    mix = fdf["recommendation"].value_counts().reset_index()
    mix.columns = ["recommendation", "count"]
    if PLOTLY_AVAILABLE and len(mix):
        fig = px.pie(
            mix,
            values="count",
            names="recommendation",
            color="recommendation",
            color_discrete_map=STATUS_COLORS,
            hole=0.55,
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            font=dict(family="Inter", size=12, color=INK),
            showlegend=True,
        )
        fig.update_traces(textposition="outside", textinfo="label+percent")
        st.plotly_chart(fig, width="stretch")
    else:
        st.bar_chart(mix.set_index("recommendation"))
    st.markdown("</div>", unsafe_allow_html=True)


col3, col4 = st.columns([1, 1])

with col3:
    st.markdown('<div class="section"><h2>Age vs archivability <span class="hint">size = record footprint, color = action</span></h2>', unsafe_allow_html=True)
    sample = fdf.sample(min(len(fdf), 1500), random_state=1) if len(fdf) else fdf
    if PLOTLY_AVAILABLE and len(sample):
        fig = px.scatter(
            sample,
            x="age_days",
            y="archivability_score",
            color="recommendation",
            size="size_mb",
            size_max=22,
            opacity=0.75,
            hover_data=["object_id", "archiving_object", "status", "priority_score"],
            color_discrete_map=STATUS_COLORS,
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend_title_text="",
            xaxis_title="Age (days)",
            yaxis_title="Archivability score",
            font=dict(family="Inter", size=12, color=INK),
        )
        fig.update_xaxes(gridcolor="#eef2f5")
        fig.update_yaxes(gridcolor="#eef2f5", range=[0, 105])
        st.plotly_chart(fig, width="stretch")
    else:
        if len(sample):
            st.scatter_chart(sample, x="age_days", y="archivability_score", size="size_mb")
        else:
            st.info("No records match the current filters.")
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown('<div class="section"><h2>Storage recoverable by object <span class="hint">GB if archived now</span></h2>', unsafe_allow_html=True)
    arch_only = fdf[fdf["recommendation"] == "ARCHIVE"]
    storage = (
        arch_only.groupby("archiving_object")["size_mb"].sum().div(1024).round(2).reset_index()
    )
    storage.columns = ["archiving_object", "GB recoverable"]
    storage = storage.sort_values("GB recoverable", ascending=True)
    if PLOTLY_AVAILABLE and len(storage):
        fig = px.bar(
            storage,
            x="GB recoverable",
            y="archiving_object",
            orientation="h",
            color_discrete_sequence=[PRIMARY],
            text="GB recoverable",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="GB",
            yaxis_title="",
            font=dict(family="Inter", size=12, color=INK),
        )
        fig.update_xaxes(gridcolor="#eef2f5")
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(fig, width="stretch")
    elif len(storage):
        st.bar_chart(storage.set_index("archiving_object"))
    else:
        st.info("No archive candidates in current filter.")
    st.markdown("</div>", unsafe_allow_html=True)


# ---------- Data quality findings ----------
st.markdown('<div class="section"><h2>Data-quality findings <span class="hint">cross-table scan</span></h2>', unsafe_allow_html=True)
qcols = st.columns(6)
labels = [
    ("Duplicates", issues["duplicates"]),
    ("Inconsistencies", issues["inconsistencies"]),
    ("Incomplete workflows", issues["incomplete_workflows"]),
    ("Stale OPEN >1y", issues["stale_open"]),
    ("ERROR status", issues["errors"]),
    ("Legal holds", issues["legal_holds"]),
]
for c, (lab, val) in zip(qcols, labels):
    c.metric(lab, f"{val:,}")
st.markdown("</div>", unsafe_allow_html=True)


# ---------- Per-object summary table ----------
st.markdown('<div class="section"><h2>Inventory by archiving object</h2>', unsafe_allow_html=True)
obj_summary = summary_by_object(fdf) if len(fdf) else pd.DataFrame()
if len(obj_summary):
    st.dataframe(
        obj_summary[
            [
                "archiving_object",
                "module",
                "description",
                "records",
                "total_size_gb",
                "avg_age_years",
                "legal_holds",
                "duplicates",
                "inconsistencies",
            ]
        ].rename(
            columns={
                "archiving_object": "Object",
                "module": "Module",
                "description": "Description",
                "records": "Records",
                "total_size_gb": "Size (GB)",
                "avg_age_years": "Avg age (yrs)",
                "legal_holds": "Legal holds",
                "duplicates": "Dupes",
                "inconsistencies": "Inconsist.",
            }
        ),
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No records match the current filters.")
st.markdown("</div>", unsafe_allow_html=True)


# ---------- Priority table ----------
st.markdown('<div class="section"><h2>Priority candidates <span class="hint">sorted by priority score</span></h2>', unsafe_allow_html=True)

priority_cols = [
    "object_id",
    "archiving_object",
    "module",
    "company_code",
    "status",
    "age_days",
    "residence_months",
    "workflow_completion",
    "data_quality_score",
    "anomaly_score",
    "archivability_score",
    "priority_score",
    "size_mb",
    "recommendation",
    "rationale",
]
top = fdf.sort_values("priority_score", ascending=False)[priority_cols].head(50)
st.dataframe(
    top.rename(
        columns={
            "object_id": "Object ID",
            "archiving_object": "Archiving Object",
            "module": "Mod.",
            "company_code": "CoCd",
            "status": "Status",
            "age_days": "Age (d)",
            "residence_months": "Residence (mo)",
            "workflow_completion": "Workflow %",
            "data_quality_score": "DQ score",
            "anomaly_score": "Anomaly",
            "archivability_score": "Score",
            "priority_score": "Priority",
            "size_mb": "Size (MB)",
            "recommendation": "Action",
            "rationale": "Rationale",
        }
    ),
    width="stretch",
    hide_index=True,
    column_config={
        "Workflow %": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
        "DQ score": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
        "Anomaly": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
        "Score": st.column_config.NumberColumn(format="%d"),
        "Priority": st.column_config.NumberColumn(format="%d"),
    },
)
st.markdown("</div>", unsafe_allow_html=True)


# ---------- Drilldown ----------
st.markdown('<div class="section"><h2>Object drilldown</h2>', unsafe_allow_html=True)
ids_avail = top["object_id"].tolist() + fdf["object_id"].tolist()
ids_avail = list(dict.fromkeys(ids_avail))[:500]
if ids_avail:
    pick = st.selectbox("Select an object to inspect", ids_avail, index=0)
    rec = fdf[fdf["object_id"] == pick].iloc[0]

    badge_color = STATUS_COLORS.get(rec["recommendation"], "#888")
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; margin: 4px 0 12px 0;">
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600;">
            {rec['object_id']}
          </div>
          <span class="badge" style="background:{badge_color}; color:#fff;">{rec['recommendation']}</span>
          <span class="badge" style="background:#eef3f6; color:{INK};">{rec['archiving_object']}</span>
          <span class="badge" style="background:#eef3f6; color:{INK};">{rec['module']}</span>
          <span style="color:{MUTED}; font-size:13px;">{rec['rationale']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dcol1, dcol2, dcol3, dcol4 = st.columns(4)
    dcol1.metric("Archivability", f"{rec['archivability_score']:.0f}", help="0-100 weighted rule score")
    dcol2.metric("Priority", f"{rec['priority_score']:.0f}")
    dcol3.metric("Anomaly", f"{rec['anomaly_score']:.2f}")
    dcol4.metric("Size", f"{rec['size_mb']:.1f} MB")

    dcol5, dcol6, dcol7, dcol8 = st.columns(4)
    dcol5.metric("Status", rec["status"])
    dcol6.metric("Age", f"{int(rec['age_days'])} d")
    dcol7.metric("Residence", f"{rec['residence_months']} mo / {rec['min_residence_months']}+")
    dcol8.metric("Workflow", f"{rec['workflow_completion']*100:.0f}%")

    # Rule pass/fail breakdown
    st.markdown("**Rule evaluation**")
    rule_rows = []
    from archivability import RULES, RULE_WEIGHTS  # late import to avoid cycles
    for key, _, label in RULES:
        passed = bool(rec[f"rule_{key}"])
        rule_rows.append(
            {
                "Rule": label,
                "Weight": RULE_WEIGHTS[key],
                "Passed": "✅" if passed else "❌",
                "Contribution": RULE_WEIGHTS[key] if passed else 0,
            }
        )
    st.dataframe(pd.DataFrame(rule_rows), width="stretch", hide_index=True)

    flag_bits = []
    if rec["legal_hold"]:
        flag_bits.append('<span class="badge" style="background:#a83232;color:#fff;">LEGAL HOLD</span>')
    if rec["has_open_dependencies"]:
        flag_bits.append('<span class="badge" style="background:#c97a17;color:#fff;">OPEN DEPENDENCIES</span>')
    if rec["duplicate_flag"]:
        flag_bits.append('<span class="badge" style="background:#7a3aa8;color:#fff;">DUPLICATE</span>')
    if rec["inconsistency_flag"]:
        flag_bits.append('<span class="badge" style="background:#c97a17;color:#fff;">INCONSISTENT</span>')
    if flag_bits:
        st.markdown(" ".join(flag_bits), unsafe_allow_html=True)
else:
    st.info("No records to drill into.")
st.markdown("</div>", unsafe_allow_html=True)


# ---------- Export ----------
st.markdown('<div class="section"><h2>Export</h2>', unsafe_allow_html=True)

ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
csv_buf = io.StringIO()
fdf.to_csv(csv_buf, index=False)

md_report = build_markdown_report(
    fdf, issues, summary_by_object(fdf) if len(fdf) else pd.DataFrame(
        columns=["archiving_object", "module", "records", "total_size_gb", "avg_age_years"]
    )
)

ec1, ec2, ec3 = st.columns(3)
with ec1:
    st.download_button(
        "⬇️ Download filtered records (CSV)",
        data=csv_buf.getvalue(),
        file_name=f"sap_archiving_records_{ts}.csv",
        mime="text/csv",
        width="stretch",
    )
with ec2:
    st.download_button(
        "⬇️ Download executive report (Markdown)",
        data=md_report,
        file_name=f"sap_archiving_report_{ts}.md",
        mime="text/markdown",
        width="stretch",
    )
with ec3:
    archive_only = fdf[fdf["recommendation"] == "ARCHIVE"]
    arch_csv = io.StringIO()
    archive_only.to_csv(arch_csv, index=False)
    st.download_button(
        "⬇️ Download ARCHIVE worklist (CSV)",
        data=arch_csv.getvalue(),
        file_name=f"sap_archive_worklist_{ts}.csv",
        mime="text/csv",
        width="stretch",
    )
st.markdown("</div>", unsafe_allow_html=True)


# ---------- Footer ----------
st.markdown(
    f"""
    <div class="footer">
      Prototype • All data synthetic • No SAP connection required •
      Anomaly engine: <b>{ml_label}</b> • Charts: <b>{chart_label}</b>
    </div>
    """,
    unsafe_allow_html=True,
)
