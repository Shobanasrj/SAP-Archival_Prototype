"""
SAP Archiving Assistant — Streamlit prototype.

Client-demo app for SAP ECC/S/4 archiving assessment:
- scans synthetic SAP objects for data-quality, workflow, dependency, and residence-time risks
- scores archivability with transparent rules plus optional IsolationForest anomaly detection
- plans cleanup backlog and archive run packages
- supports what-if policy tuning and downloadable client-ready outputs

Run: python -m streamlit run app.py
All data is synthetic. No SAP connection is required.
"""
from __future__ import annotations

import io
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import streamlit as st

from archivability import (
    RULES,
    RULE_WEIGHTS,
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
except Exception:
    PLOTLY_AVAILABLE = False


st.set_page_config(
    page_title="SAP Archiving Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)


PRIMARY = "#0a6e8c"
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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono&display=swap');

  html, body, [class*="css"], [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    color: {INK};
  }}
  [data-testid="stAppViewContainer"] {{ background: {BG}; }}
  [data-testid="stHeader"] {{ background: transparent; }}
  .block-container {{
    padding-top: 1.35rem !important;
    padding-bottom: 1.5rem !important;
    max-width: 1420px;
  }}
  [data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {PRIMARY_DARK} 0%, #04303f 100%);
  }}
  [data-testid="stSidebar"] > div:first-child {{
    padding-top: 1.35rem;
  }}
  [data-testid="stSidebar"] * {{ color: #e8f1f5 !important; }}
  [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {{
    color: {INK} !important;
  }}
  [data-testid="stSidebar"] [role="option"], [data-testid="stSidebar"] [data-baseweb="select"] * {{
    color: {INK} !important;
  }}
  [data-testid="stSidebar"] [data-baseweb="tag"] {{
    background: #12a7c8 !important;
  }}
  [data-testid="stSidebar"] .stButton > button {{
    width: 100%;
    min-height: 46px;
    background: linear-gradient(90deg, #12a7c8, #0a7c97);
    border-radius: 12px;
    color: white;
    box-shadow: 0 10px 24px rgba(0,0,0,0.18);
  }}
  .sidebar-brand {{
    border: 1px solid rgba(255,255,255,.16);
    background: rgba(255,255,255,.08);
    border-radius: 18px;
    padding: 16px 14px;
    margin-bottom: 16px;
  }}
  .cap-logo {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 20px;
    font-weight: 850;
    letter-spacing: -0.03em;
  }}
  .cap-mark {{
    width: 34px;
    height: 34px;
    border-radius: 11px 11px 18px 11px;
    display: inline-grid;
    place-items: center;
    background: linear-gradient(135deg, #12a7c8, #7de3f5);
    color: #04303f;
    font-weight: 900;
    font-size: 18px;
  }}
  .side-caption {{
    margin-top: 8px;
    color: rgba(232,241,245,.76) !important;
    font-size: 12px;
    line-height: 1.4;
  }}
  .side-card {{
    background: rgba(255,255,255,.08);
    border: 1px solid rgba(255,255,255,.14);
    border-radius: 15px;
    padding: 13px 13px 5px;
    margin: 12px 0;
  }}
  .side-card-title {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 850;
    color: rgba(232,241,245,.72) !important;
    margin-bottom: 8px;
  }}
  .brand-bar {{
    background: linear-gradient(90deg, {PRIMARY_DARK} 0%, {PRIMARY} 64%, {ACCENT} 100%);
    color: #fff;
    padding: 18px 24px;
    border-radius: 18px;
    margin-bottom: 14px;
    box-shadow: 0 8px 24px rgba(6,63,81,0.12);
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 18px;
    align-items: center;
  }}
  .brand-bar h1 {{
    margin: 0;
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.02em;
  }}
  .brand-bar p {{
    margin: 6px 0 0 0;
    opacity: 0.94;
    font-size: 14px;
    max-width: 980px;
    line-height: 1.55;
  }}
  .top-logo {{
    text-align: right;
    min-width: 210px;
  }}
  .capgemini-word {{
    font-size: 24px;
    font-weight: 850;
    letter-spacing: -0.04em;
  }}
  .capgemini-note {{
    margin-top: 4px;
    font-size: 11px;
    letter-spacing: .12em;
    text-transform: uppercase;
    opacity: .78;
  }}
  .status-strip {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 0 0 14px 0;
  }}
  .status-tile {{
    background: white;
    border: 1px solid #e1e8ee;
    border-radius: 14px;
    padding: 10px 14px;
    box-shadow: 0 1px 2px rgba(14,28,38,0.035);
  }}
  .status-label {{
    color: {MUTED};
    font-size: 10px;
    letter-spacing: .1em;
    text-transform: uppercase;
    font-weight: 850;
  }}
  .status-value {{
    margin-top: 4px;
    font-size: 15px;
    font-weight: 800;
    color: {INK};
  }}
  .badges {{
    margin-top: 12px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }}
  .pill {{
    display: inline-block;
    background: rgba(255,255,255,0.16);
    border: 1px solid rgba(255,255,255,0.18);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }}
  .section {{
    background: {SURFACE};
    border: 1px solid #e1e8ee;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 2px rgba(14,28,38,0.035);
  }}
  .section h2 {{
    font-size: 17px;
    font-weight: 750;
    margin: 0 0 12px 0;
    letter-spacing: -0.01em;
  }}
  .hint {{
    color: {MUTED};
    font-size: 13px;
    font-weight: 450;
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 12px;
  }}
  @media (max-width: 1280px) {{
    .kpi-grid {{ grid-template-columns: repeat(3, 1fr); }}
  }}
  @media (max-width: 820px) {{
    .kpi-grid {{ grid-template-columns: repeat(1, 1fr); }}
  }}
  .kpi {{
    background: {SURFACE};
    border: 1px solid #e1e8ee;
    border-radius: 14px;
    padding: 15px 16px;
    min-height: 110px;
    box-shadow: 0 1px 2px rgba(14,28,38,0.04);
  }}
  .kpi .label {{
    color: {MUTED};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 800;
  }}
  .kpi .value {{
    color: {INK};
    font-size: 28px;
    font-weight: 800;
    margin-top: 6px;
    font-variant-numeric: tabular-nums;
  }}
  .kpi .delta {{ color: {MUTED}; font-size: 12px; margin-top: 4px; line-height: 1.35; }}
  .accent {{ border-left: 4px solid {PRIMARY}; }}
  .good {{ border-left: 4px solid #2f8a3e; }}
  .warn {{ border-left: 4px solid #c97a17; }}
  .danger {{ border-left: 4px solid #a83232; }}
  .purple {{ border-left: 4px solid #7a3aa8; }}
  .badge {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 0.03em;
  }}
  .playbook {{
    border: 1px solid #e1e8ee;
    border-radius: 12px;
    padding: 12px 14px;
    background: #f8fbfc;
    margin-bottom: 10px;
  }}
  .stButton > button, .stDownloadButton > button {{
    background: {PRIMARY};
    color: #fff;
    border: 0;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 700;
  }}
  .stButton > button:hover, .stDownloadButton > button:hover {{
    background: {PRIMARY_DARK};
  }}
  [data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}
  .footer {{
    color: {MUTED};
    font-size: 12px;
    text-align: center;
    padding: 16px 0 4px;
  }}
  @media (max-width: 900px) {{
    .brand-bar {{ grid-template-columns: 1fr; }}
    .top-logo {{ text-align:left; min-width:0; }}
    .status-strip {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data(seed: int, n_per_object: int) -> pd.DataFrame:
    df = generate_objects(seed=seed, n_per_object=n_per_object)
    return run_full_pipeline(df)


def gb(series: pd.Series) -> float:
    return round(float(series.sum()) / 1024, 2)


def pct(part: int | float, total: int | float) -> float:
    return round(100.0 * float(part) / max(float(total), 1.0), 1)


def fig_layout(fig, height: int = 340):
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=height,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Inter", size=12, color=INK),
        legend_title_text="",
    )
    return fig


def render_kpis(cards: list[dict]):
    """Render KPI cards using Streamlit-native metrics.

    Avoid custom HTML here because Streamlit can occasionally render partial
    HTML as raw text depending on local browser/markdown parsing behavior.
    """
    render_native_metrics(cards)


def render_native_metrics(cards: list[dict]):
    """Render compact KPI cards using Streamlit-native metrics for maximum reliability."""
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        col.metric(card["label"], card["value"], card.get("delta", None))


def recommendation_counts(frame: pd.DataFrame) -> pd.DataFrame:
    order = ["ARCHIVE", "REVIEW", "REMEDIATE", "DEDUPLICATE", "RETAIN"]
    counts = frame["recommendation"].value_counts().reindex(order, fill_value=0)
    return counts.rename_axis("recommendation").reset_index(name="count")


def build_cleanup_backlog(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    backlog = frame[
        (frame["recommendation"].isin(["REMEDIATE", "DEDUPLICATE", "REVIEW"]))
        | frame["duplicate_flag"]
        | frame["inconsistency_flag"]
        | (frame["workflow_completion"] < 0.95)
        | frame["has_open_dependencies"]
        | frame["legal_hold"]
    ].copy()

    conditions = [
        backlog["legal_hold"],
        backlog["duplicate_flag"],
        backlog["inconsistency_flag"] | (backlog["data_quality_score"] < 0.7),
        backlog["has_open_dependencies"],
        backlog["workflow_completion"] < 0.95,
    ]
    backlog["issue_type"] = np.select(
        conditions,
        ["Legal hold", "Duplicate", "Data inconsistency", "Open dependency", "Incomplete workflow"],
        default="Manual review",
    )
    backlog["suggested_action"] = np.select(
        conditions,
        [
            "Confirm retention/legal hold owner before excluding from archive package",
            "Run duplicate-key consolidation and retain golden document",
            "Correct status/reference mismatch, then re-run archivability rules",
            "Resolve downstream document flow or open settlement dependencies",
            "Close or cancel workflow items with business owner approval",
        ],
        default="Route to business owner for disposition decision",
    )
    backlog["owner_group"] = np.select(
        conditions,
        ["Legal/Compliance", "Data Steward", "Data Steward", "Functional Owner", "Workflow Owner"],
        default="Business Owner",
    )
    backlog["effort"] = np.select(
        [
            backlog["issue_type"].isin(["Legal hold", "Open dependency"]),
            backlog["issue_type"].isin(["Data inconsistency", "Duplicate"]),
        ],
        ["High", "Medium"],
        default="Low",
    )
    backlog["target_sla_days"] = np.select(
        [
            backlog["effort"].eq("High"),
            backlog["effort"].eq("Medium"),
        ],
        [20, 10],
        default=5,
    )
    return backlog.sort_values(["priority_score", "size_mb"], ascending=False)


def build_archive_packages(frame: pd.DataFrame, max_package_gb: float, max_records: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = frame[frame["recommendation"] == "ARCHIVE"].copy()
    if candidates.empty:
        return pd.DataFrame(), candidates

    candidates = candidates.sort_values(
        ["archiving_object", "priority_score", "size_mb"],
        ascending=[True, False, False],
    ).copy()
    package_ids = []
    current_object = None
    wave = 1
    package_gb = 0.0
    package_records = 0

    for _, row in candidates.iterrows():
        row_gb = float(row["size_mb"]) / 1024
        if row["archiving_object"] != current_object:
            current_object = row["archiving_object"]
            wave = 1
            package_gb = 0.0
            package_records = 0
        elif package_gb + row_gb > max_package_gb or package_records >= max_records:
            wave += 1
            package_gb = 0.0
            package_records = 0

        package_ids.append(f"{row['archiving_object']}-W{wave:02d}")
        package_gb += row_gb
        package_records += 1

    candidates["archive_package"] = package_ids
    summary = (
        candidates.groupby(["archive_package", "archiving_object", "module"], as_index=False)
        .agg(
            records=("object_id", "count"),
            size_mb=("size_mb", "sum"),
            avg_score=("archivability_score", "mean"),
            max_priority=("priority_score", "max"),
            oldest_days=("age_days", "max"),
        )
        .sort_values(["archiving_object", "archive_package"])
    )
    summary["size_gb"] = (summary["size_mb"] / 1024).round(2)
    summary["avg_score"] = summary["avg_score"].round(1)
    summary["estimated_runtime_min"] = (summary["records"] * 0.018 + summary["size_gb"] * 5).round(0).astype(int).clip(lower=5)
    summary["sequence"] = range(1, len(summary) + 1)
    return summary, candidates


def add_deletion_readiness(frame: pd.DataFrame, retention_buffer_months: int = 12) -> pd.DataFrame:
    """Classify records for deletion/purge after archive validation.

    In SAP archiving, deletion is not the first action. Records should only be
    considered purge-ready after archive write/read validation and after
    retention, legal hold, dependency, and data-quality rules pass.
    """
    if frame.empty:
        return frame.copy()

    out = frame.copy()
    surplus_residence = out["residence_months"] >= (
        out["min_residence_months"] + retention_buffer_months
    )
    clean_gates = (
        out["recommendation"].eq("ARCHIVE")
        & surplus_residence
        & ~out["legal_hold"]
        & ~out["has_open_dependencies"]
        & ~out["duplicate_flag"]
        & ~out["inconsistency_flag"]
        & (out["data_quality_score"] >= 0.85)
        & (out["workflow_completion"] >= 0.98)
        & (out["days_since_activity"] >= 540)
        & (out["anomaly_score"] <= 0.35)
    )
    archive_only = out["recommendation"].eq("ARCHIVE") & ~clean_gates
    blocked = out["recommendation"].isin(["RETAIN", "REMEDIATE", "DEDUPLICATE"])

    out["deletion_readiness"] = np.select(
        [clean_gates, archive_only, blocked],
        [
            "DELETE_AFTER_ARCHIVE_VALIDATION",
            "ARCHIVE_ONLY_RETAIN_COPY",
            "NOT_DELETE_ELIGIBLE",
        ],
        default="REVIEW_BEFORE_DELETE",
    )
    out["deletion_rationale"] = np.select(
        [clean_gates, archive_only, blocked],
        [
            "Passed strict purge gates; delete only after archive write/read validation and approval.",
            "Archive candidate, but not purge-ready under stricter retention/quality gates.",
            "Blocked by retain/remediate/deduplicate recommendation.",
        ],
        default="Needs business/legal review before any deletion decision.",
    )
    out["residence_surplus_months"] = (
        out["residence_months"] - out["min_residence_months"]
    ).round(1)
    return out


def build_scenario(frame: pd.DataFrame, residence_buffer: int, workflow_threshold: float, dq_threshold: float, idle_months: int) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    scenario = frame.copy()
    residence_ok = scenario["residence_months"] >= (scenario["min_residence_months"] + residence_buffer)
    status_ok = scenario["status"].isin(["COMPLETED", "ARCHIVED_CANDIDATE"])
    workflow_ok = scenario["workflow_completion"] >= workflow_threshold
    idle_ok = scenario["days_since_activity"] >= idle_months * 30
    hold_ok = ~scenario["legal_hold"]
    deps_ok = ~scenario["has_open_dependencies"]
    dq_ok = scenario["data_quality_score"] >= dq_threshold

    score = (
        residence_ok.astype(float) * RULE_WEIGHTS["residence_met"]
        + status_ok.astype(float) * RULE_WEIGHTS["status_terminal"]
        + workflow_ok.astype(float) * RULE_WEIGHTS["workflow_complete"]
        + idle_ok.astype(float) * RULE_WEIGHTS["no_recent_activity"]
        + hold_ok.astype(float) * RULE_WEIGHTS["no_legal_hold"]
        + deps_ok.astype(float) * RULE_WEIGHTS["no_open_dependencies"]
        + dq_ok.astype(float) * RULE_WEIGHTS["data_quality_ok"]
    )
    scenario["scenario_score"] = score.round(1)
    scenario["scenario_archive_ready"] = (
        (scenario["scenario_score"] >= 80)
        & residence_ok
        & status_ok
        & workflow_ok
        & idle_ok
        & hold_ok
        & deps_ok
        & dq_ok
        & ~scenario["duplicate_flag"]
        & ~scenario["inconsistency_flag"]
    )
    return scenario


def client_report(frame: pd.DataFrame, packages: pd.DataFrame, backlog: pd.DataFrame, issues: dict, summary: pd.DataFrame) -> str:
    base = build_markdown_report(frame, issues, summary)
    archive_n = int((frame["recommendation"] == "ARCHIVE").sum())
    cleanup_n = len(backlog)
    package_n = len(packages)
    lines = [
        base,
        "",
        "## Client implementation plan",
        "",
        f"- Recommended archive packages: **{package_n:,}**",
        f"- Archive candidates to include in pilot: **{archive_n:,}**",
        f"- Cleanup backlog items before broad archive run: **{cleanup_n:,}**",
        "",
        "### Proposed phases",
        "",
        "1. **Validate rules:** confirm residence/retention policy by object with business, legal, and compliance owners.",
        "2. **Clean blockers:** remediate duplicate, workflow, dependency, legal-hold, and status inconsistency items.",
        "3. **Pilot archive package:** run the highest-score, lowest-risk package first and verify retrieval/read-only access.",
        "4. **Scale waves:** schedule remaining packages by object family, storage impact, and business calendar constraints.",
        "5. **Validate deletion rules:** only mark records for purge after archive write/read validation, retention approval, and legal/compliance review.",
        "6. **Operationalize:** convert prototype rules into SAP ILM/ADK jobs, retention warehouse controls, and monitoring KPIs.",
    ]
    if len(packages):
        lines.extend(["", "### Top archive packages", "", "| Package | Object | Records | Size GB | Avg score | Runtime min |", "| --- | --- | ---: | ---: | ---: | ---: |"])
        for _, r in packages.head(10).iterrows():
            lines.append(
                f"| {r['archive_package']} | {r['archiving_object']} | {int(r['records']):,} | {r['size_gb']} | {r['avg_score']} | {int(r['estimated_runtime_min'])} |"
            )
    return "\n".join(lines)


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
          <div class="cap-logo"><span class="cap-mark">⌁</span><span>Capgemini</span></div>
          <div class="side-caption">SAP Archiving Assistant<br>AI-powered data retirement cockpit</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-card"><div class="side-card-title">Dataset controls</div>', unsafe_allow_html=True)
    seed = st.number_input("Random seed", value=42, step=1, min_value=0, max_value=9999)
    n_per_object = st.slider("Records per object", 100, 800, 350, step=50)
    if st.button("Regenerate dataset", width="stretch"):
        st.cache_data.clear()
    st.markdown("</div>", unsafe_allow_html=True)

df = load_data(int(seed), int(n_per_object))

with st.sidebar:
    st.markdown('<div class="side-card"><div class="side-card-title">Scope filters</div>', unsafe_allow_html=True)
    objects_avail = sorted(df["archiving_object"].unique().tolist())
    modules_avail = sorted(df["module"].unique().tolist())
    company_codes = sorted(df["company_code"].unique().tolist())
    statuses_avail = sorted(df["status"].unique().tolist())

    sel_objects = st.multiselect("Archiving object", objects_avail, default=objects_avail)
    sel_modules = st.multiselect("Module", modules_avail, default=modules_avail)
    sel_company = st.multiselect("Company code", company_codes, default=company_codes)
    sel_status = st.multiselect("Status", statuses_avail, default=statuses_avail)
    min_score = st.slider("Min archivability score", 0, 100, 0, step=5)
    only_archivable = st.checkbox("Only show ARCHIVE candidates", value=False)
    exclude_legal_hold = st.checkbox("Exclude legal-hold records", value=True)
    search_text = st.text_input("Search object ID/table/status", value="")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="side-card"><div class="side-card-title">Client context</div>', unsafe_allow_html=True)
    client_name = st.text_input("Client / program name", value="SAP Data Archiving Assessment")
    ml_label = "scikit-learn IsolationForest" if SKLEARN_AVAILABLE else "Heuristic fallback"
    chart_label = "Plotly" if PLOTLY_AVAILABLE else "Streamlit native"
    st.markdown(
        f"""
        <div class="side-caption">
          Anomaly engine: <b>{ml_label}</b><br>
          Chart engine: <b>{chart_label}</b><br>
          Mode: Client demo / synthetic data
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

mask = (
    df["archiving_object"].isin(sel_objects)
    & df["module"].isin(sel_modules)
    & df["company_code"].isin(sel_company)
    & df["status"].isin(sel_status)
    & (df["archivability_score"] >= min_score)
)
if only_archivable:
    mask &= df["recommendation"].eq("ARCHIVE")
if exclude_legal_hold:
    mask &= ~df["legal_hold"]
if search_text.strip():
    q = search_text.strip().lower()
    mask &= (
        df["object_id"].str.lower().str.contains(q)
        | df["archiving_object"].str.lower().str.contains(q)
        | df["table"].str.lower().str.contains(q)
        | df["status"].str.lower().str.contains(q)
    )

fdf = df[mask].copy()
issues = detect_data_issues(fdf) if len(fdf) else {
    "duplicates": 0,
    "inconsistencies": 0,
    "incomplete_workflows": 0,
    "stale_open": 0,
    "errors": 0,
    "legal_holds": 0,
}
obj_summary = summary_by_object(fdf) if len(fdf) else pd.DataFrame()
cleanup_backlog = build_cleanup_backlog(fdf)
deletion_df = add_deletion_readiness(fdf)

total = len(fdf)
archive_n = int((fdf["recommendation"] == "ARCHIVE").sum()) if total else 0
review_n = int((fdf["recommendation"] == "REVIEW").sum()) if total else 0
remediate_n = int(fdf["recommendation"].isin(["REMEDIATE", "DEDUPLICATE"]).sum()) if total else 0
retain_n = int((fdf["recommendation"] == "RETAIN").sum()) if total else 0
total_size_gb = gb(fdf["size_mb"]) if total else 0.0
archive_size_gb = gb(fdf.loc[fdf["recommendation"] == "ARCHIVE", "size_mb"]) if total else 0.0
pct_archivable = pct(archive_n, total)

st.markdown(
    f"""
    <div class="brand-bar">
      <div>
        <h1>SAP Archiving Assistant</h1>
        <p><b>{client_name}</b> — AI-powered SAP data retirement cockpit for discovery, cleanup planning,
        archive package sequencing, deletion readiness, and policy what-if analysis.</p>
        <div class="badges">
          <span class="pill">Synthetic SAP ECC/S/4 data</span>
          <span class="pill">Anomaly: {ml_label}</span>
          <span class="pill">Charts: {chart_label}</span>
          <span class="pill">{len(df):,} generated records</span>
        </div>
      </div>
      <div class="top-logo">
        <div class="capgemini-word">Capgemini</div>
        <div class="capgemini-note">Insights & Data</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="status-strip">
      <div class="status-tile"><div class="status-label">Program lens</div><div class="status-value">Archive + ILM readiness</div></div>
      <div class="status-tile"><div class="status-label">Filtered records</div><div class="status-value">{total:,}</div></div>
      <div class="status-tile"><div class="status-label">Archive-ready</div><div class="status-value">{archive_n:,} records</div></div>
      <div class="status-tile"><div class="status-label">Recoverable footprint</div><div class="status-value">{archive_size_gb:,} GB</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

tabs = st.tabs(
    [
        "Executive Cockpit",
        "Scan Results",
        "Cleanup Backlog",
        "Archive Planner",
        "Deletion Rules",
        "Object Drilldown",
        "What-if Rules",
        "Exports",
    ]
)

with tabs[0]:
    st.markdown(
        f"""
        <div class="section">
          <h2>Executive summary</h2>
          <p style="margin:0;color:{INK};font-size:14px;line-height:1.58;">
            Across <b>{total:,}</b> filtered records (<b>{total_size_gb:,} GB</b>), the assistant identified
            <b>{archive_n:,}</b> high-confidence archive candidates ({pct_archivable}%) with up to
            <b>{archive_size_gb:,} GB</b> of recoverable online storage. <b>{review_n:,}</b> records need review,
            <b>{remediate_n:,}</b> need remediation/deduplication, and <b>{retain_n:,}</b> should remain online.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_kpis(
        [
            {"label": "Records in scope", "value": f"{total:,}", "delta": f"{total_size_gb:,} GB online footprint", "style": "accent"},
            {"label": "Archive candidates", "value": f"{archive_n:,}", "delta": f"{pct_archivable}% ready • {archive_size_gb:,} GB recoverable", "style": "good"},
            {"label": "Review / remediation", "value": f"{review_n + remediate_n:,}", "delta": f"{review_n:,} review · {remediate_n:,} remediate", "style": "warn"},
            {"label": "Data quality findings", "value": f"{issues['duplicates'] + issues['inconsistencies']:,}", "delta": f"{issues['duplicates']:,} duplicates · {issues['inconsistencies']:,} inconsistencies", "style": "danger"},
            {"label": "Open workflow gaps", "value": f"{issues['incomplete_workflows']:,}", "delta": f"{issues['stale_open']:,} stale OPEN records", "style": "purple"},
        ]
    )

    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.markdown('<div class="section"><h2>Recommendation mix</h2>', unsafe_allow_html=True)
        mix = recommendation_counts(fdf) if total else pd.DataFrame(columns=["recommendation", "count"])
        if PLOTLY_AVAILABLE and len(mix):
            fig = px.bar(
                mix,
                x="recommendation",
                y="count",
                color="recommendation",
                color_discrete_map=STATUS_COLORS,
                text="count",
            )
            fig.update_traces(textposition="outside")
            fig_layout(fig, 330)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Records", gridcolor="#eef2f5")
            st.plotly_chart(fig, width="stretch")
        else:
            st.bar_chart(mix.set_index("recommendation"))
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section"><h2>Storage recoverable by object</h2>', unsafe_allow_html=True)
        storage = (
            fdf[fdf["recommendation"] == "ARCHIVE"]
            .groupby("archiving_object")["size_mb"]
            .sum()
            .div(1024)
            .round(2)
            .reset_index(name="GB recoverable")
            .sort_values("GB recoverable", ascending=True)
        )
        if PLOTLY_AVAILABLE and len(storage):
            fig = px.bar(storage, x="GB recoverable", y="archiving_object", orientation="h", text="GB recoverable", color_discrete_sequence=[PRIMARY])
            fig.update_traces(textposition="outside")
            fig_layout(fig, 330)
            fig.update_xaxes(title="GB", gridcolor="#eef2f5")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, width="stretch")
        elif len(storage):
            st.bar_chart(storage.set_index("archiving_object"))
        else:
            st.info("No archive candidates in the current filter.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section"><h2>Readiness by archiving object</h2>', unsafe_allow_html=True)
    if len(obj_summary):
        readiness = (
            fdf.groupby("archiving_object")
            .agg(
                records=("object_id", "count"),
                archive=("recommendation", lambda s: int((s == "ARCHIVE").sum())),
                avg_score=("archivability_score", "mean"),
                blockers=("blocked", "sum"),
            )
            .reset_index()
        )
        readiness["archive_rate"] = (100 * readiness["archive"] / readiness["records"]).round(1)
        readiness["avg_score"] = readiness["avg_score"].round(1)
        st.dataframe(
            readiness.rename(
                columns={
                    "archiving_object": "Archiving Object",
                    "records": "Records",
                    "archive": "Archive Ready",
                    "avg_score": "Avg Score",
                    "blockers": "Hard Blockers",
                    "archive_rate": "Archive Rate %",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("No records match the current filters.")
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[1]:
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown('<div class="section"><h2>Archivability by object and action</h2>', unsafe_allow_html=True)
        by_obj = fdf.groupby(["archiving_object", "recommendation"]).size().reset_index(name="count") if total else pd.DataFrame()
        if PLOTLY_AVAILABLE and len(by_obj):
            fig = px.bar(
                by_obj,
                x="archiving_object",
                y="count",
                color="recommendation",
                color_discrete_map=STATUS_COLORS,
                barmode="stack",
            )
            fig_layout(fig, 360)
            fig.update_xaxes(title="", showgrid=False)
            fig.update_yaxes(title="Records", gridcolor="#eef2f5")
            st.plotly_chart(fig, width="stretch")
        elif len(by_obj):
            st.bar_chart(by_obj.pivot(index="archiving_object", columns="recommendation", values="count").fillna(0))
        else:
            st.info("No records match the current filters.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section"><h2>Data-quality finding counts</h2>', unsafe_allow_html=True)
        qdata = pd.DataFrame(
            [
                ("Duplicates", issues["duplicates"]),
                ("Inconsistencies", issues["inconsistencies"]),
                ("Incomplete workflows", issues["incomplete_workflows"]),
                ("Stale OPEN >1y", issues["stale_open"]),
                ("ERROR status", issues["errors"]),
                ("Legal holds", issues["legal_holds"]),
            ],
            columns=["Finding", "Count"],
        )
        if PLOTLY_AVAILABLE:
            fig = px.bar(qdata.sort_values("Count"), x="Count", y="Finding", orientation="h", text="Count", color_discrete_sequence=["#c97a17"])
            fig.update_traces(textposition="outside")
            fig_layout(fig, 360)
            fig.update_xaxes(gridcolor="#eef2f5")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, width="stretch")
        else:
            st.bar_chart(qdata.set_index("Finding"))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section"><h2>Inventory by archiving object</h2>', unsafe_allow_html=True)
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

    st.markdown('<div class="section"><h2>Full scan results</h2>', unsafe_allow_html=True)
    scan_cols = [
        "object_id",
        "archiving_object",
        "module",
        "company_code",
        "status",
        "age_days",
        "days_since_activity",
        "workflow_completion",
        "data_quality_score",
        "anomaly_score",
        "archivability_score",
        "priority_score",
        "size_mb",
        "recommendation",
        "rationale",
    ]
    st.dataframe(
        fdf.sort_values("priority_score", ascending=False)[scan_cols].rename(
            columns={
                "object_id": "Object ID",
                "archiving_object": "Archiving Object",
                "module": "Module",
                "company_code": "CoCd",
                "status": "Status",
                "age_days": "Age (days)",
                "days_since_activity": "Idle days",
                "workflow_completion": "Workflow %",
                "data_quality_score": "DQ Score",
                "anomaly_score": "Anomaly",
                "archivability_score": "Archive Score",
                "priority_score": "Priority",
                "size_mb": "Size MB",
                "recommendation": "Action",
                "rationale": "Rationale",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[2]:
    st.markdown('<div class="section"><h2>Cleanup backlog summary</h2>', unsafe_allow_html=True)
    if len(cleanup_backlog):
        backlog_summary = (
            cleanup_backlog.groupby(["issue_type", "owner_group", "effort"], as_index=False)
            .agg(records=("object_id", "count"), size_gb=("size_mb", lambda s: round(s.sum() / 1024, 2)))
            .sort_values("records", ascending=False)
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            st.dataframe(
                backlog_summary.rename(
                    columns={
                        "issue_type": "Issue Type",
                        "owner_group": "Owner Group",
                        "effort": "Effort",
                        "records": "Records",
                        "size_gb": "Size GB",
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        with c2:
            if PLOTLY_AVAILABLE:
                fig = px.bar(backlog_summary, x="records", y="issue_type", color="effort", orientation="h", text="records")
                fig.update_traces(textposition="outside")
                fig_layout(fig, 320)
                fig.update_xaxes(title="Records", gridcolor="#eef2f5")
                fig.update_yaxes(title="")
                st.plotly_chart(fig, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h2>Remediation playbook</h2>', unsafe_allow_html=True)
        playbook = [
            ("Legal hold", "Confirm hold source, retention authority, and exclusion rules before archive package release."),
            ("Duplicate", "Create duplicate cluster report, identify golden document, and de-duplicate or mark survivors."),
            ("Data inconsistency", "Resolve status/reference mismatch, missing dependencies, or failed posting metadata."),
            ("Open dependency", "Clear document flow, settlement, invoice, delivery, or workflow dependencies."),
            ("Incomplete workflow", "Close, cancel, or route workflow item to business owner for disposition."),
        ]
        for title, body in playbook:
            st.markdown(f"<div class='playbook'><b>{title}</b><br><span class='hint'>{body}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h2>Detailed cleanup backlog</h2>', unsafe_allow_html=True)
        backlog_cols = [
            "object_id",
            "archiving_object",
            "company_code",
            "status",
            "issue_type",
            "owner_group",
            "effort",
            "target_sla_days",
            "priority_score",
            "size_mb",
            "suggested_action",
        ]
        st.dataframe(
            cleanup_backlog[backlog_cols].head(300).rename(
                columns={
                    "object_id": "Object ID",
                    "archiving_object": "Archiving Object",
                    "company_code": "CoCd",
                    "status": "Status",
                    "issue_type": "Issue",
                    "owner_group": "Owner",
                    "effort": "Effort",
                    "target_sla_days": "SLA Days",
                    "priority_score": "Priority",
                    "size_mb": "Size MB",
                    "suggested_action": "Suggested Action",
                }
            ),
            width="stretch",
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("No cleanup backlog for the current filters.")
        st.markdown("</div>", unsafe_allow_html=True)

with tabs[3]:
    pcol1, pcol2 = st.columns([0.35, 0.65])
    with pcol1:
        st.markdown('<div class="section"><h2>Package planning controls</h2>', unsafe_allow_html=True)
        max_package_gb = st.slider("Max package size (GB)", 0.25, 10.0, 2.5, step=0.25)
        max_records = st.slider("Max records per package", 50, 1000, 250, step=50)
        st.caption("Packages are sequenced by object, priority, and estimated footprint.")
        st.markdown("</div>", unsafe_allow_html=True)

    package_summary, package_detail = build_archive_packages(fdf, max_package_gb, max_records)
    with pcol2:
        st.markdown('<div class="section"><h2>Archive package KPIs</h2>', unsafe_allow_html=True)
        render_native_metrics(
            [
                {"label": "Archive packages", "value": f"{len(package_summary):,}", "delta": "Generated"},
                {"label": "Packaged records", "value": f"{len(package_detail):,}", "delta": f"{gb(package_detail['size_mb']) if len(package_detail) else 0:,} GB"},
                {"label": "Avg runtime", "value": f"{round(package_summary['estimated_runtime_min'].mean(), 0):.0f} min" if len(package_summary) else "0 min", "delta": "Estimate"},
                {"label": "Largest package", "value": f"{package_summary['size_gb'].max():.2f} GB" if len(package_summary) else "0 GB", "delta": "Max"},
                {"label": "Recoverable", "value": f"{archive_size_gb:,} GB", "delta": "Ready"},
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section"><h2>Archive run packages</h2>', unsafe_allow_html=True)
    if len(package_summary):
        c1, c2 = st.columns([1, 1])
        with c1:
            st.dataframe(
                package_summary[
                    [
                        "sequence",
                        "archive_package",
                        "archiving_object",
                        "module",
                        "records",
                        "size_gb",
                        "avg_score",
                        "estimated_runtime_min",
                        "oldest_days",
                    ]
                ].rename(
                    columns={
                        "sequence": "Seq",
                        "archive_package": "Package",
                        "archiving_object": "Object",
                        "module": "Module",
                        "records": "Records",
                        "size_gb": "Size GB",
                        "avg_score": "Avg Score",
                        "estimated_runtime_min": "Runtime Min",
                        "oldest_days": "Oldest Age Days",
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        with c2:
            if PLOTLY_AVAILABLE:
                fig = px.bar(package_summary, x="archive_package", y="size_gb", color="archiving_object", text="records")
                fig_layout(fig, 390)
                fig.update_xaxes(title="", tickangle=-35)
                fig.update_yaxes(title="Size GB", gridcolor="#eef2f5")
                st.plotly_chart(fig, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section"><h2>Pilot package recommendation</h2>', unsafe_allow_html=True)
        pilot = package_summary.sort_values(["avg_score", "size_gb"], ascending=[False, True]).head(1)
        if len(pilot):
            r = pilot.iloc[0]
            st.success(
                f"Recommended pilot: {r['archive_package']} ({int(r['records']):,} records, {r['size_gb']} GB, average score {r['avg_score']}). "
                "Use this as a low-risk archive write/read validation package before scaling."
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No ARCHIVE candidates available for package planning under the current filters.")
        st.markdown("</div>", unsafe_allow_html=True)

with tabs[4]:
    st.markdown('<div class="section"><h2>Deletion / purge readiness rules</h2>', unsafe_allow_html=True)
    st.warning(
        "Client-safe rule: deletion is only considered after successful archive write/read validation, retention approval, "
        "and legal/compliance confirmation. This prototype labels deletion readiness; it does not delete anything."
    )
    retention_buffer = st.slider(
        "Extra residence buffer before delete/purge eligibility (months)",
        0,
        60,
        12,
        step=6,
    )
    deletion_df = add_deletion_readiness(fdf, retention_buffer)
    delete_ready = deletion_df[
        deletion_df["deletion_readiness"].eq("DELETE_AFTER_ARCHIVE_VALIDATION")
    ]
    archive_only = deletion_df[
        deletion_df["deletion_readiness"].eq("ARCHIVE_ONLY_RETAIN_COPY")
    ]
    not_eligible = deletion_df[
        deletion_df["deletion_readiness"].eq("NOT_DELETE_ELIGIBLE")
    ]
    review_delete = deletion_df[
        deletion_df["deletion_readiness"].eq("REVIEW_BEFORE_DELETE")
    ]
    render_native_metrics(
        [
            {"label": "Delete after validation", "value": f"{len(delete_ready):,}", "delta": f"{gb(delete_ready['size_mb']) if len(delete_ready) else 0:,} GB"},
            {"label": "Archive only", "value": f"{len(archive_only):,}", "delta": "Retain archived copy"},
            {"label": "Review before delete", "value": f"{len(review_delete):,}", "delta": "Business/legal review"},
            {"label": "Not delete eligible", "value": f"{len(not_eligible):,}", "delta": "Blocked or not ready"},
            {"label": "Buffer", "value": f"{retention_buffer} mo", "delta": "Beyond residence"},
        ]
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Deletion-readiness rule gates**")
        gates = pd.DataFrame(
            [
                ("Archive recommendation", "Must already be ARCHIVE-ready"),
                ("Extra residence buffer", f"Residence must exceed object minimum by {retention_buffer} months"),
                ("Legal hold", "Must not be under legal hold"),
                ("Dependencies", "Must have no open downstream dependencies"),
                ("Data quality", "Data quality score must be ≥ 0.85"),
                ("Workflow", "Workflow completion must be ≥ 98%"),
                ("Activity", "No activity for at least 540 days"),
                ("Anomaly risk", "Anomaly score must be ≤ 0.35"),
                ("Validation", "Delete only after archive write/read validation and approval"),
            ],
            columns=["Gate", "Rule"],
        )
        st.dataframe(gates, width="stretch", hide_index=True)
    with c2:
        readiness = (
            deletion_df["deletion_readiness"]
            .value_counts()
            .rename_axis("Readiness")
            .reset_index(name="Records")
        )
        if PLOTLY_AVAILABLE and len(readiness):
            fig = px.bar(
                readiness,
                x="Records",
                y="Readiness",
                orientation="h",
                text="Records",
                color="Readiness",
                color_discrete_map={
                    "DELETE_AFTER_ARCHIVE_VALIDATION": "#2f8a3e",
                    "ARCHIVE_ONLY_RETAIN_COPY": PRIMARY,
                    "REVIEW_BEFORE_DELETE": "#c97a17",
                    "NOT_DELETE_ELIGIBLE": "#4a5c66",
                },
            )
            fig.update_traces(textposition="outside")
            fig_layout(fig, 360)
            fig.update_xaxes(gridcolor="#eef2f5")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, width="stretch")
        else:
            st.bar_chart(readiness.set_index("Readiness"))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section"><h2>Deletion candidate worklist</h2>', unsafe_allow_html=True)
    deletion_cols = [
        "object_id",
        "archiving_object",
        "company_code",
        "status",
        "residence_months",
        "min_residence_months",
        "residence_surplus_months",
        "workflow_completion",
        "data_quality_score",
        "anomaly_score",
        "size_mb",
        "deletion_readiness",
        "deletion_rationale",
    ]
    st.dataframe(
        deletion_df.sort_values(
            ["deletion_readiness", "residence_surplus_months", "size_mb"],
            ascending=[True, False, False],
        )[deletion_cols].rename(
            columns={
                "object_id": "Object ID",
                "archiving_object": "Archiving Object",
                "company_code": "CoCd",
                "status": "Status",
                "residence_months": "Residence Mo",
                "min_residence_months": "Min Residence",
                "residence_surplus_months": "Surplus Mo",
                "workflow_completion": "Workflow %",
                "data_quality_score": "DQ Score",
                "anomaly_score": "Anomaly",
                "size_mb": "Size MB",
                "deletion_readiness": "Deletion Readiness",
                "deletion_rationale": "Rationale",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[5]:
    st.markdown('<div class="section"><h2>Object drilldown</h2>', unsafe_allow_html=True)
    ids_avail = (
        fdf.sort_values("priority_score", ascending=False)["object_id"].drop_duplicates().head(800).tolist()
        if len(fdf)
        else []
    )
    if ids_avail:
        pick = st.selectbox("Select an object to inspect", ids_avail, index=0)
        rec = fdf[fdf["object_id"] == pick].iloc[0]
        badge_color = STATUS_COLORS.get(rec["recommendation"], "#888")
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin: 4px 0 14px 0;">
              <div style="font-family:'JetBrains Mono', monospace; font-size:18px; font-weight:700;">{rec['object_id']}</div>
              <span class="badge" style="background:{badge_color}; color:#fff;">{rec['recommendation']}</span>
              <span class="badge" style="background:#eef3f6; color:{INK};">{rec['archiving_object']}</span>
              <span class="badge" style="background:#eef3f6; color:{INK};">{rec['module']}</span>
              <span class="hint">{rec['rationale']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        dcol1, dcol2, dcol3, dcol4, dcol5 = st.columns(5)
        dcol1.metric("Archivability", f"{rec['archivability_score']:.0f}")
        dcol2.metric("Priority", f"{rec['priority_score']:.0f}")
        dcol3.metric("Anomaly", f"{rec['anomaly_score']:.2f}")
        dcol4.metric("Size", f"{rec['size_mb']:.1f} MB")
        dcol5.metric("Workflow", f"{rec['workflow_completion']*100:.0f}%")

        d1, d2 = st.columns([0.48, 0.52])
        with d1:
            st.markdown("**Record attributes**")
            attrs = pd.DataFrame(
                [
                    ("Object", rec["archiving_object"]),
                    ("Table", rec["table"]),
                    ("Company Code", rec["company_code"]),
                    ("Plant", rec["plant"] or "n/a"),
                    ("Status", rec["status"]),
                    ("Created On", str(rec["created_on"].date())),
                    ("Last Activity", str(rec["last_activity_on"].date())),
                    ("Residence", f"{rec['residence_months']} mo / {rec['min_residence_months']}+ required"),
                    ("Failed Rules", rec["failed_rules"]),
                ],
                columns=["Attribute", "Value"],
            )
            st.dataframe(attrs, width="stretch", hide_index=True)
        with d2:
            st.markdown("**Rule evaluation**")
            rule_rows = []
            for key, _, label in RULES:
                passed = bool(rec[f"rule_{key}"])
                rule_rows.append(
                    {
                        "Rule": label,
                        "Weight": RULE_WEIGHTS[key],
                        "Passed": "PASS" if passed else "FAIL",
                        "Contribution": RULE_WEIGHTS[key] if passed else 0,
                    }
                )
            st.dataframe(pd.DataFrame(rule_rows), width="stretch", hide_index=True)

        flags = []
        if rec["legal_hold"]:
            flags.append("LEGAL HOLD")
        if rec["has_open_dependencies"]:
            flags.append("OPEN DEPENDENCIES")
        if rec["duplicate_flag"]:
            flags.append("DUPLICATE")
        if rec["inconsistency_flag"]:
            flags.append("INCONSISTENT")
        if flags:
            st.warning("Blocking / cleanup flags: " + ", ".join(flags))
        else:
            st.success("No hard blockers detected for this object.")
    else:
        st.info("No records to drill into.")
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[6]:
    st.markdown('<div class="section"><h2>What-if archivability rules</h2>', unsafe_allow_html=True)
    w1, w2, w3, w4 = st.columns(4)
    residence_buffer = w1.slider("Residence buffer months", -12, 24, 0, step=3)
    workflow_threshold = w2.slider("Workflow completion threshold", 0.70, 1.00, 0.95, step=0.01)
    dq_threshold = w3.slider("Data quality threshold", 0.40, 0.95, 0.70, step=0.05)
    idle_months = w4.slider("No-activity threshold months", 3, 36, 12, step=3)
    scenario = build_scenario(fdf, residence_buffer, workflow_threshold, dq_threshold, idle_months)
    scenario_ready = int(scenario["scenario_archive_ready"].sum()) if len(scenario) else 0
    current_ready = archive_n
    delta_ready = scenario_ready - current_ready
    scenario_gb = gb(scenario.loc[scenario["scenario_archive_ready"], "size_mb"]) if len(scenario) else 0

    render_native_metrics(
        [
            {"label": "Current archive-ready", "value": f"{current_ready:,}", "delta": "Baseline"},
            {"label": "Scenario archive-ready", "value": f"{scenario_ready:,}", "delta": f"{scenario_gb:,} GB"},
            {"label": "Ready delta", "value": f"{delta_ready:+,}", "delta": "vs baseline"},
            {"label": "Workflow threshold", "value": f"{workflow_threshold*100:.0f}%", "delta": "Policy"},
            {"label": "Residence buffer", "value": f"{residence_buffer:+} mo", "delta": "Policy"},
        ]
    )

    if len(scenario):
        comparison = (
            scenario.groupby("archiving_object")
            .agg(
                records=("object_id", "count"),
                current_ready=("recommendation", lambda s: int((s == "ARCHIVE").sum())),
                scenario_ready=("scenario_archive_ready", "sum"),
                scenario_gb=("size_mb", lambda s: 0),
            )
            .reset_index()
        )
        scenario_gb_by_obj = (
            scenario[scenario["scenario_archive_ready"]]
            .groupby("archiving_object")["size_mb"]
            .sum()
            .div(1024)
            .round(2)
        )
        comparison["scenario_gb"] = comparison["archiving_object"].map(scenario_gb_by_obj).fillna(0)
        comparison["delta"] = comparison["scenario_ready"] - comparison["current_ready"]

        c1, c2 = st.columns([1, 1])
        with c1:
            st.dataframe(
                comparison.rename(
                    columns={
                        "archiving_object": "Object",
                        "records": "Records",
                        "current_ready": "Current Ready",
                        "scenario_ready": "Scenario Ready",
                        "scenario_gb": "Scenario GB",
                        "delta": "Delta",
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        with c2:
            if PLOTLY_AVAILABLE:
                fig = go.Figure()
                fig.add_bar(name="Current", x=comparison["archiving_object"], y=comparison["current_ready"], marker_color=PRIMARY)
                fig.add_bar(name="Scenario", x=comparison["archiving_object"], y=comparison["scenario_ready"], marker_color="#c97a17")
                fig_layout(fig, 350)
                fig.update_layout(barmode="group")
                fig.update_xaxes(title="", tickangle=-25)
                fig.update_yaxes(title="Records", gridcolor="#eef2f5")
                st.plotly_chart(fig, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

with tabs[7]:
    st.markdown('<div class="section"><h2>Exports and client handoff</h2>', unsafe_allow_html=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    package_summary, package_detail = build_archive_packages(fdf, 2.5, 250)
    deletion_export = add_deletion_readiness(fdf)
    report_text = client_report(fdf, package_summary, cleanup_backlog, issues, obj_summary)

    csv_buf = io.StringIO()
    fdf.to_csv(csv_buf, index=False)
    backlog_buf = io.StringIO()
    cleanup_backlog.to_csv(backlog_buf, index=False)
    package_buf = io.StringIO()
    package_summary.to_csv(package_buf, index=False)
    deletion_buf = io.StringIO()
    deletion_export.to_csv(deletion_buf, index=False)

    e1, e2, e3, e4, e5 = st.columns(5)
    with e1:
        st.download_button(
            "Download scan results CSV",
            data=csv_buf.getvalue(),
            file_name=f"sap_archiving_scan_results_{ts}.csv",
            mime="text/csv",
            width="stretch",
        )
    with e2:
        st.download_button(
            "Download cleanup backlog CSV",
            data=backlog_buf.getvalue(),
            file_name=f"sap_archiving_cleanup_backlog_{ts}.csv",
            mime="text/csv",
            width="stretch",
        )
    with e3:
        st.download_button(
            "Download archive packages CSV",
            data=package_buf.getvalue(),
            file_name=f"sap_archiving_packages_{ts}.csv",
            mime="text/csv",
            width="stretch",
        )
    with e4:
        st.download_button(
            "Download deletion rules CSV",
            data=deletion_buf.getvalue(),
            file_name=f"sap_archiving_deletion_readiness_{ts}.csv",
            mime="text/csv",
            width="stretch",
        )
    with e5:
        st.download_button(
            "Download client report MD",
            data=report_text,
            file_name=f"sap_archiving_client_report_{ts}.md",
            mime="text/markdown",
            width="stretch",
        )

    st.markdown("**Client-demo talking points**")
    st.markdown(
        """
        - Show the Executive Cockpit first to frame value: storage reclaimed, blockers, and archive readiness.
        - Use Scan Results to explain how rules and anomaly scoring identify risk.
        - Use Cleanup Backlog to convert findings into remediation owners and action plans.
        - Use Archive Planner to demonstrate package sequencing for SAP ADK/ILM archive runs.
        - Use What-if Rules to show how policy changes affect archive readiness.
        """
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="footer">
      Prototype • All data synthetic • No SAP connection required •
      Anomaly engine: <b>{ml_label}</b> • Charts: <b>{chart_label}</b>
    </div>
    """,
    unsafe_allow_html=True,
)
