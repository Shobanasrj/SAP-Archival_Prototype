import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json, io, requests
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="SAP Archival AI Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1A2B5E 0%, #2E86C1 100%);
        padding: 1.2rem 1.5rem; border-radius: 10px; margin-bottom: 1.2rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.6rem; }
    .main-header p  { color: #D8E6F3; margin: 0.3rem 0 0; font-size: 0.9rem; }
    .metric-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 1rem; text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .metric-card .val { font-size: 1.8rem; font-weight: 700; color: #1A2B5E; }
    .metric-card .lbl { font-size: 0.75rem; color: #64748B; margin-top: 0.2rem; }
    .risk-HIGH   { background: #FEF2F2; border-left: 4px solid #EF4444; padding: 0.5rem 0.8rem; border-radius: 4px; }
    .risk-MEDIUM { background: #FFFBEB; border-left: 4px solid #F59E0B; padding: 0.5rem 0.8rem; border-radius: 4px; }
    .risk-LOW    { background: #F0FDF4; border-left: 4px solid #22C55E; padding: 0.5rem 0.8rem; border-radius: 4px; }
    .chat-msg-user { background: #EBF5FF; border-radius: 8px; padding: 0.75rem 1rem; margin: 0.4rem 0; }
    .chat-msg-ai   { background: #F0F5FB; border-radius: 8px; padding: 0.75rem 1rem; margin: 0.4rem 0; border-left: 3px solid #1A2B5E; }
    .section-badge { 
        background: #1A2B5E; color: white; padding: 0.25rem 0.75rem; 
        border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block;
    }
    .opentext-box {
        background: linear-gradient(135deg, #1A2B5E 0%, #2E4070 100%);
        border: 1px solid #E8A020; border-radius: 8px;
        padding: 1rem; color: white; margin: 0.8rem 0;
    }
    .opentext-box h4 { color: #E8A020; margin: 0 0 0.5rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background: #F0F5FB; border-radius: 6px 6px 0 0;
        padding: 0.5rem 1.2rem; font-weight: 600; color: #1A2B5E;
    }
    .stTabs [aria-selected="true"] {
        background: #1A2B5E !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ── SAP Archiving Objects Master Reference ─────────────────────────
SAP_ARCHIVE_OBJECTS = {
    "FI_DOCUMNT": {
        "module": "FI", "description": "FI Financial Documents",
        "tables": ["BKPF","BSEG","BSAS","BSAK","BSIK","BSAD"],
        "typical_retention_yrs": 10,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "Medium", "business_impact": "High",
        "notes": "Largest FI object. Includes G/L, AP, AR. Requires fiscal year-end close before archiving.",
        "tcode_check": "FB03", "prerequisite": "Cleared items only"
    },
    "MM_MATBEL": {
        "module": "MM", "description": "Material Documents",
        "tables": ["MKPF","MSEG"],
        "typical_retention_yrs": 7,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "Low", "business_impact": "Medium",
        "notes": "Goods movements. High volume, good quick win. No open items dependency.",
        "tcode_check": "MB03", "prerequisite": "No open purchase orders"
    },
    "MM_EKKO": {
        "module": "MM", "description": "Purchasing Documents",
        "tables": ["EKKO","EKPO","EKBE","EKET"],
        "typical_retention_yrs": 7,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "Medium", "business_impact": "Medium",
        "notes": "Purchase orders, contracts, RFQs. Must be fully delivered and invoiced.",
        "tcode_check": "ME23N", "prerequisite": "Delivery complete, invoice verified"
    },
    "SD_VBAK": {
        "module": "SD", "description": "Sales Documents",
        "tables": ["VBAK","VBAP","VBFA","VBUK"],
        "typical_retention_yrs": 7,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "High", "business_impact": "High",
        "notes": "Sales orders and deliveries. Complex inter-document dependencies via VBFA.",
        "tcode_check": "VA03", "prerequisite": "Fully delivered, billed, and closed"
    },
    "PP_ORDER": {
        "module": "PP", "description": "Production Orders",
        "tables": ["AUFK","AUFM","AFKO","AFPO"],
        "typical_retention_yrs": 5,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "High", "business_impact": "Medium",
        "notes": "Production orders with settlements. Costing run must be complete.",
        "tcode_check": "CO03", "prerequisite": "TECO status, settlement complete"
    },
    "CO_CCTR_EP": {
        "module": "CO", "description": "CO Cost Centre Actual Postings",
        "tables": ["COEP","COEPL","COSP","COSR"],
        "typical_retention_yrs": 10,
        "ilm_capable": False, "opentext_compatible": True,
        "complexity": "Medium", "business_impact": "High",
        "notes": "Controlling line items. Period-end and year-end close required.",
        "tcode_check": "KSB1", "prerequisite": "Period-end close complete"
    },
    "QM_QMEL": {
        "module": "QM", "description": "Quality Notifications",
        "tables": ["QMEL","QMFE","QMMA"],
        "typical_retention_yrs": 5,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "Low", "business_impact": "Low",
        "notes": "Good quick win. Must be in completed status (NOCO).",
        "tcode_check": "QM03", "prerequisite": "NOCO status"
    },
    "PM_ORDER": {
        "module": "PM", "description": "PM Maintenance Orders",
        "tables": ["AUFK","AFIH","QMEL"],
        "typical_retention_yrs": 5,
        "ilm_capable": True, "opentext_compatible": True,
        "complexity": "Medium", "business_impact": "Low",
        "notes": "Plant maintenance orders. Must have TECO status and settlement complete.",
        "tcode_check": "IW33", "prerequisite": "TECO + settlement"
    },
    "MM_INVBEL": {
        "module": "MM", "description": "Inventory Documents (Physical Inv)",
        "tables": ["IKPF","ISEG"],
        "typical_retention_yrs": 5,
        "ilm_capable": False, "opentext_compatible": True,
        "complexity": "Low", "business_impact": "Low",
        "notes": "Physical inventory documents. Easy quick win with minimal dependencies.",
        "tcode_check": "MI03", "prerequisite": "Count completed and posted"
    },
    "CHANGEDOCU": {
        "module": "Basis", "description": "Change Documents",
        "tables": ["CDHDR","CDPOS"],
        "typical_retention_yrs": 7,
        "ilm_capable": False, "opentext_compatible": True,
        "complexity": "Low", "business_impact": "Low",
        "notes": "Change log for master data. Very large tables. Excellent quick win for DB reduction.",
        "tcode_check": "SCDO", "prerequisite": "None — run first for quick wins"
    },
    "IDOCREL": {
        "module": "Basis", "description": "IDoc Records",
        "tables": ["EDIDC","EDID4","EDIDS"],
        "typical_retention_yrs": 3,
        "ilm_capable": False, "opentext_compatible": True,
        "complexity": "Low", "business_impact": "Low",
        "notes": "EDI/IDoc records. Very high volume. Can be archived aggressively after processing.",
        "tcode_check": "WE02", "prerequisite": "Status 53 (successfully posted)"
    },
    "SPOOL": {
        "module": "Basis", "description": "Spool Requests",
        "tables": ["TSP01","TSP02"],
        "typical_retention_yrs": 1,
        "ilm_capable": False, "opentext_compatible": False,
        "complexity": "Low", "business_impact": "Low",
        "notes": "Print spool. Automatic deletion usually preferred over archiving. Quick DB win.",
        "tcode_check": "SP01", "prerequisite": "Completed spool requests"
    },
}

# ── Helper: generate synthetic table data ──────────────────────────
def generate_db02_data():
    """Simulate what you'd export from SAP DB02 / DBACOCKPIT"""
    tables = [
        ("BSEG",    45200, 1850), ("MSEG",    38400, 920),
        ("EDID4",   31200, 740),  ("CDPOS",   28800, 680),
        ("VBFA",    22100, 430),  ("BKPF",    18600, 380),
        ("COEPL",   16800, 310),  ("KONV",    14500, 290),
        ("EDIDC",   13200, 180),  ("MKPF",    11400, 220),
        ("EKBE",     9800, 160),  ("EKKO",     8700, 140),
        ("AUFM",     7600, 130),  ("COEP",     7200, 125),
        ("VBAK",     6800, 118),  ("BSAD",     6200, 110),
        ("TSP01",    5900, 85),   ("IKPF",     5100, 75),
        ("AFIH",     4800, 70),   ("QMEL",     4200, 62),
    ]
    df = pd.DataFrame(tables, columns=["TABLE_NAME","ROWS_K","SIZE_GB"])
    df["SIZE_GB"] = df["SIZE_GB"] / 10
    df["ROWS"]    = df["ROWS_K"] * 1000
    return df

def generate_growth_data():
    """12-month DB growth simulation"""
    months = list(pd.date_range(end=datetime.now(), periods=12, freq="MS"))
    base = 3800
    sizes = [base + i * 45 + int(np.random.randint(-10, 25)) for i in range(len(months))]
    return pd.DataFrame({"Month": months, "DB_Size_GB": sizes})

def score_archivability(obj_key, size_gb, rows, manual_overrides=None):
    """Score an archive object 0-100 with rationale"""
    obj   = SAP_ARCHIVE_OBJECTS.get(obj_key, {})
    score = 50
    reasons = []
    if size_gb > 50:  score += 20; reasons.append(f"Large table ({size_gb:.0f}GB) — high impact")
    elif size_gb > 10: score += 10; reasons.append(f"Medium table ({size_gb:.0f}GB)")
    else:              score -= 5;  reasons.append(f"Small table ({size_gb:.0f}GB) — lower priority")
    complexity = obj.get("complexity","Medium")
    if   complexity == "Low":    score += 15; reasons.append("Low technical complexity")
    elif complexity == "High":   score -= 15; reasons.append("High complexity — careful planning needed")
    if obj.get("ilm_capable"):   score += 10; reasons.append("ILM-capable — retention policy can be applied")
    if manual_overrides:
        if manual_overrides.get("already_identified"): score += 10
        if manual_overrides.get("business_priority"):  score += 5
    score = max(0, min(100, score))
    if   score >= 70: priority = "HIGH"
    elif score >= 45: priority = "MEDIUM"
    else:             priority = "LOW"
    return score, priority, reasons

# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1A2B5E,#2E86C1);padding:1rem;border-radius:8px;margin-bottom:1rem">
    <h3 style="color:white;margin:0;font-size:1rem">🗄️ SAP Archival AI Assistant</h3>
    <p style="color:#D8E6F3;margin:0.3rem 0 0;font-size:0.75rem">Capgemini</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Configuration")
    client_name  = st.text_input("Client Name", "Client (Confidential)")
    sap_system   = st.selectbox("SAP System", ["ECC 6.0 EhP8","ECC 6.0 EhP7","S/4HANA 2021","S/4HANA 2023"])
    has_opentext = st.toggle("Has OpenText Archive Center", value=True)
    ilm_licensed = st.toggle("SAP ILM Licensed / RISE", value=False)

    st.markdown("---")
    st.markdown("### 📁 Import SAP Data")
    upload_type  = st.selectbox("Source", [
        "DB02 / DBACOCKPIT Export (CSV)",
        "TAANA Table Analysis (CSV)",
        "AL11 File System (TXT)",
        "SE16 Table Export (CSV)",
        "Manual Entry / Demo Mode",
    ])
    uploaded = st.file_uploader("Upload File", type=["csv","txt","xlsx"])

    st.markdown("---")
    st.markdown("### 🔑 AI Assistant")
    st.caption("Powered by Claude · Confidential")

    st.markdown("---")
    if has_opentext:
        st.markdown("""
        <div style="background:#1A2B5E;border:1px solid #E8A020;border-radius:6px;padding:0.6rem">
        <p style="color:#E8A020;font-size:0.75rem;font-weight:700;margin:0">✅ OpenText Detected</p>
        <p style="color:#D8E6F3;font-size:0.7rem;margin:0.2rem 0 0">
        Archives will write to OpenText Archive Center via SAP ArchiveLink</p>
        </div>
        """, unsafe_allow_html=True)
    if ilm_licensed:
        st.markdown("""
        <div style="background:#1A6B2E;border-radius:6px;padding:0.6rem;margin-top:0.5rem">
        <p style="color:white;font-size:0.75rem;font-weight:700;margin:0">✅ ILM Enabled</p>
        <p style="color:#D8E6F3;font-size:0.7rem;margin:0.2rem 0 0">
        ILM-ADK files with retention metadata — WebDAV/ILM 3.1 interface</p>
        </div>
        """, unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────
if uploaded and upload_type != "Manual Entry / Demo Mode":
    try:
        if uploaded.name.endswith(".xlsx"):
            df_db = pd.read_excel(uploaded)
        else:
            df_db = pd.read_csv(uploaded)
        # Try to normalise column names
        df_db.columns = [c.upper().strip() for c in df_db.columns]
        if "SIZE_GB" not in df_db.columns and "SIZE" in df_db.columns:
            df_db["SIZE_GB"] = pd.to_numeric(df_db["SIZE"], errors="coerce") / 1024
        if "ROWS" not in df_db.columns and "ROWS_K" in df_db.columns:
            df_db["ROWS"] = df_db["ROWS_K"].astype(float) * 1000
        data_source = f"📤 Uploaded: {uploaded.name}"
    except Exception as e:
        st.sidebar.error(f"Parse error: {e}")
        df_db = generate_db02_data()
        data_source = "🔄 Demo Mode (upload failed)"
else:
    df_db = generate_db02_data()
    data_source = "🔄 Demo Mode — upload a real SAP DB02 export for live analysis"

df_growth = generate_growth_data()

# ══════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="main-header">
<h1>🗄️ SAP Data Volume Management — AI Archival Assistant</h1>
<p>{client_name} &nbsp;|&nbsp; {sap_system} &nbsp;|&nbsp; {data_source} &nbsp;|&nbsp;
{'✅ OpenText Integrated' if has_opentext else '⬜ No OpenText'} &nbsp;|&nbsp;
{'✅ ILM Enabled' if ilm_licensed else '⬜ ILM Not Active'}</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 DB Sizing Dashboard",
    "🎯 Archivability Analyzer",
    "🏗️ Archive Object Catalogue",
    "🤖 AI Archiving Assistant",
    "📋 Remediation Playbook",
    "ℹ️ Context & Methodology",
])

# ─────────────────────────────────────────────────────────────────────
# TAB 1: DB SIZING DASHBOARD
# ─────────────────────────────────────────────────────────────────────
with tabs[0]:
    st.markdown('<span class="section-badge">📊 Database Sizing & Growth Analysis</span>', unsafe_allow_html=True)
    st.caption("Equivalent to SAP transaction DB02 / DBACOCKPIT — upload your export or use demo data")

    total_gb    = df_db["SIZE_GB"].sum()
    archivable  = df_db[df_db["TABLE_NAME"].isin(
        [t for obj in SAP_ARCHIVE_OBJECTS.values() for t in obj["tables"]]
    )]["SIZE_GB"].sum()
    pct_reduce  = (archivable / total_gb * 100) if total_gb else 0
    growth_rate = (df_growth["DB_Size_GB"].iloc[-1] - df_growth["DB_Size_GB"].iloc[0]) / 12

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, val, lbl in [
        (c1, f"{total_gb:.0f} GB",      "Total DB Size"),
        (c2, f"{archivable:.0f} GB",    "Archivable Data"),
        (c3, f"{pct_reduce:.0f}%",      "Est. Reduction"),
        (c4, f"{growth_rate:.0f} GB/mo","DB Growth Rate"),
        (c5, f"{len(df_db)}",           "Tables Analysed"),
    ]:
        col.markdown(f"""<div class="metric-card">
        <div class="val">{val}</div><div class="lbl">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("")
    col_l, col_r = st.columns([3,2])

    with col_l:
        st.markdown("##### Top 15 Tables by Size")
        top15 = df_db.nlargest(15,"SIZE_GB")
        fig = px.bar(top15, x="SIZE_GB", y="TABLE_NAME", orientation="h",
                     color="SIZE_GB", color_continuous_scale=[[0,"#D8E6F3"],[1,"#1A2B5E"]],
                     labels={"SIZE_GB":"Size (GB)","TABLE_NAME":"Table"})
        fig.update_layout(height=380, showlegend=False, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="white", coloraxis_showscale=False)
        fig.update_xaxes(gridcolor="#F0F0F0")
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("##### DB Growth Trend (12 months)")
        fig2 = px.area(df_growth, x="Month", y="DB_Size_GB",
                       color_discrete_sequence=["#2E86C1"])
        fig2.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=0),
                           plot_bgcolor="white", showlegend=False)
        fig2.update_xaxes(gridcolor="#F0F0F0"); fig2.update_yaxes(gridcolor="#F0F0F0")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### Module Breakdown")
        module_map = {}
        for obj in SAP_ARCHIVE_OBJECTS.values():
            mod = obj["module"]
            for tbl in obj["tables"]:
                row = df_db[df_db["TABLE_NAME"]==tbl]
                if not row.empty:
                    module_map[mod] = module_map.get(mod, 0) + row["SIZE_GB"].iloc[0]
        if module_map:
            fig3 = px.pie(values=list(module_map.values()),
                          names=list(module_map.keys()),
                          color_discrete_sequence=px.colors.sequential.Blues_r,
                          hole=0.4)
            fig3.update_layout(height=165, margin=dict(l=0,r=0,t=0,b=0),
                               legend=dict(font=dict(size=9)))
            st.plotly_chart(fig3, use_container_width=True)

    # Raw table
    st.markdown("##### Full Table Detail")
    st.dataframe(df_db[["TABLE_NAME","SIZE_GB","ROWS"]].rename(columns={
        "TABLE_NAME":"Table","SIZE_GB":"Size (GB)","ROWS":"Row Count"
    }).style.background_gradient(subset=["Size (GB)"],cmap="Blues"),
    use_container_width=True, height=220)

# ─────────────────────────────────────────────────────────────────────
# TAB 2: ARCHIVABILITY ANALYZER
# ─────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown('<span class="section-badge">🎯 Archivability Scoring & Prioritisation</span>', unsafe_allow_html=True)
    st.caption("Score each SAP archiving object against your system data — mirrors the blueprint workshop output")

    results = []
    for obj_key, obj in SAP_ARCHIVE_OBJECTS.items():
        # Find total GB for tables in this object
        obj_tables = obj["tables"]
        size = df_db[df_db["TABLE_NAME"].isin(obj_tables)]["SIZE_GB"].sum()
        rows = df_db[df_db["TABLE_NAME"].isin(obj_tables)]["ROWS"].sum()
        score, priority, reasons = score_archivability(obj_key, size, rows)
        results.append({
            "Archive Object": obj_key,
            "Module": obj["module"],
            "Description": obj["description"],
            "Size (GB)": round(size, 1),
            "Complexity": obj["complexity"],
            "ILM Capable": "✅" if obj["ilm_capable"] else "—",
            "OpenText": "✅" if obj["opentext_compatible"] else "—",
            "Score": score,
            "Priority": priority,
            "Retention (yrs)": obj["typical_retention_yrs"],
            "Prerequisite": obj["prerequisite"],
        })

    df_results = pd.DataFrame(results).sort_values("Score", ascending=False)

    # Summary metrics
    high = len(df_results[df_results["Priority"]=="HIGH"])
    med  = len(df_results[df_results["Priority"]=="MEDIUM"])
    low  = len(df_results[df_results["Priority"]=="LOW"])
    ilm_count = df_results[df_results["ILM Capable"]=="✅"].shape[0]

    c1,c2,c3,c4 = st.columns(4)
    for col, val, lbl, color in [
        (c1, high,      "High Priority Objects", "#EF4444"),
        (c2, med,       "Medium Priority",        "#F59E0B"),
        (c3, low,       "Lower Priority",         "#22C55E"),
        (c4, ilm_count, "ILM-Capable Objects",    "#1A2B5E"),
    ]:
        col.markdown(f"""<div class="metric-card">
        <div class="val" style="color:{color}">{val}</div>
        <div class="lbl">{lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown("")

    col_l, col_r = st.columns([2,3])
    with col_l:
        st.markdown("##### Priority Matrix")
        fig = px.scatter(df_results, x="Size (GB)", y="Score",
                         color="Priority", size="Size (GB)",
                         hover_data=["Archive Object","Description","Complexity"],
                         color_discrete_map={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"},
                         labels={"Score":"Archivability Score","Size (GB)":"Table Size (GB)"})
        fig.add_hline(y=70, line_dash="dash", line_color="#EF4444", opacity=0.4)
        fig.add_hline(y=45, line_dash="dash", line_color="#F59E0B", opacity=0.4)
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown("##### Scored Archive Object List")
        def colour_priority(val):
            colours = {"HIGH":"background-color:#FEF2F2;color:#991B1B",
                       "MEDIUM":"background-color:#FFFBEB;color:#92400E",
                       "LOW":"background-color:#F0FDF4;color:#166534"}
            return colours.get(val,"")
        display_cols = ["Archive Object","Module","Description","Size (GB)","Score","Priority","ILM Capable","OpenText"]
        st.dataframe(
            df_results[display_cols].style
                .applymap(colour_priority, subset=["Priority"])
                .background_gradient(subset=["Score"], cmap="Blues", vmin=0, vmax=100),
            use_container_width=True, height=290, hide_index=True
        )

    # Phase recommendation
    st.markdown("##### 📅 Recommended Phasing (Wave Plan)")
    wave1 = df_results[df_results["Priority"]=="HIGH"][["Archive Object","Description","Size (GB)","Prerequisite"]]
    wave2 = df_results[df_results["Priority"]=="MEDIUM"][["Archive Object","Description","Size (GB)","Prerequisite"]]

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown("**Wave 1 — Quick Wins & High Impact**")
        st.dataframe(wave1, use_container_width=True, height=160, hide_index=True)
    with col_w2:
        st.markdown("**Wave 2 — Medium Complexity**")
        st.dataframe(wave2, use_container_width=True, height=160, hide_index=True)

# ─────────────────────────────────────────────────────────────────────
# TAB 3: ARCHIVE OBJECT CATALOGUE
# ─────────────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown('<span class="section-badge">🏗️ SAP Archive Object Reference Catalogue</span>', unsafe_allow_html=True)
    st.caption("Full technical reference for each archive object — equivalent to what an SAP DVM expert would document in the blueprint")

    col_filter1, col_filter2 = st.columns([2,3])
    with col_filter1:
        module_filter = st.multiselect("Filter by Module",
            sorted(set(o["module"] for o in SAP_ARCHIVE_OBJECTS.values())),
            default=list(set(o["module"] for o in SAP_ARCHIVE_OBJECTS.values())))
    with col_filter2:
        complexity_filter = st.multiselect("Filter by Complexity",
            ["Low","Medium","High"], default=["Low","Medium","High"])

    for obj_key, obj in SAP_ARCHIVE_OBJECTS.items():
        if obj["module"] not in module_filter: continue
        if obj["complexity"] not in complexity_filter: continue

        with st.expander(f"**{obj_key}** — {obj['description']}  |  Module: {obj['module']}  |  Complexity: {obj['complexity']}"):
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Retention:** {obj['typical_retention_yrs']} years")
            col1.markdown(f"**Prerequisite:** {obj['prerequisite']}")
            col1.markdown(f"**Verify in:** `{obj['tcode_check']}`")
            col2.markdown(f"**ILM Capable:** {'✅ Yes' if obj['ilm_capable'] else '❌ No'}")
            col2.markdown(f"**OpenText Compatible:** {'✅ Yes' if obj['opentext_compatible'] else '❌ No'}")
            col2.markdown(f"**Tables:** `{'`, `'.join(obj['tables'])}`")
            col3.markdown(f"**Notes:** {obj['notes']}")

            if has_opentext:
                if obj["ilm_capable"] and ilm_licensed:
                    st.markdown("""<div class="opentext-box">
                    <h4>🔗 ILM + OpenText Integration Path</h4>
                    <p style="color:#D8E6F3;font-size:0.85rem;margin:0">
                    This object supports ILM-ADK file generation. Archives will be written to OpenText Archive Center 
                    via the WebDAV/ILM 3.1 interface with embedded retention metadata. Retention period will be 
                    enforced by OpenText — legal hold and defensible deletion are supported.</p>
                    </div>""", unsafe_allow_html=True)
                elif obj["opentext_compatible"]:
                    st.markdown("""<div class="opentext-box">
                    <h4>🔗 OpenText via ArchiveLink</h4>
                    <p style="color:#D8E6F3;font-size:0.85rem;margin:0">
                    ADK files will be written to OpenText Archive Center via SAP ArchiveLink. 
                    No infrastructure change required. Enable ILM later to upgrade to retention-managed storage 
                    using the SAP ILM File Converter — no data loss.</p>
                    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# TAB 4: AI ARCHIVING ASSISTANT
# ─────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown('<span class="section-badge">🤖 AI Archiving Assistant — Powered by Claude</span>', unsafe_allow_html=True)
    st.caption("Ask any SAP data archiving question — ILM, OpenText, SARA, archive objects, retention, compliance")

    # System prompt with full SAP context
    SYSTEM_PROMPT = f"""You are an expert SAP Data Volume Management and ILM consultant with 15+ years of experience.
You work for Capgemini on an ECC data archival and ILM engagement.

CURRENT CLIENT CONTEXT:
- SAP System: {sap_system}
- Has OpenText Archive Center: {has_opentext}
- SAP ILM Licensed: {ilm_licensed}
- Client: {client_name}

YOUR EXPERTISE INCLUDES:
- SAP Data Archiving (SARA, AS, TAANA, DB02, DBACOCKPIT)
- SAP ILM (Information Lifecycle Management) — retention policies, legal hold, WebDAV ILM 3.1
- OpenText Archive Center integration via SAP ArchiveLink and ILM 3.1 protocol
- All major SAP archiving objects (FI_DOCUMNT, MM_MATBEL, SD_VBAK, CO_CCTR_EP, etc.)
- Archive object prerequisites, residence times, TCODE verification
- ADK file format, ILM-ADK conversion, Retention Warehouse
- S/4HANA migration readiness through data volume management
- GDPR/regulatory compliance for data retention and deletion
- Blueprint methodology, workshop facilitation, sizing and estimation

KNOWN ARCHIVE OBJECTS IN SCOPE: {', '.join(SAP_ARCHIVE_OBJECTS.keys())}

STORAGE ARCHITECTURE:
{f"OpenText is integrated via SAP ArchiveLink. {('ILM-ADK files with retention metadata will be written via WebDAV/ILM 3.1 interface.' if ilm_licensed else 'Currently using standard ADK files. ILM can be activated later with no data loss using the SAP ILM File Converter.')}" if has_opentext else "No content repository configured yet — recommend OpenText or equivalent ILM-certified storage."}

RESPONSE STYLE:
- Be specific, technical, and actionable — like a senior consultant in a blueprint workshop
- Reference exact SAP transaction codes, table names, and configuration steps
- When discussing archive objects, always mention prerequisites and residence time
- Flag regulatory implications for financial archiving (10-year retention for FI documents)
- Keep responses focused and consultant-grade — no generic advice
- Format with clear sections and bullet points where appropriate"""

    # Chat state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Suggested questions
    st.markdown("**💡 Suggested questions:**")
    suggestions = [
        "What are the prerequisites to archive FI_DOCUMNT and how long should I set the residence time?",
        "How does OpenText integrate with SAP ILM using the WebDAV ILM 3.1 interface?",
        "What's the difference between an ADK file and an ILM-ADK file and can I convert existing archives?",
        "Which archive objects should I tackle first for maximum DB reduction with minimum risk?",
        "How do I check the archivability status of MM_MATBEL in SARA before running the write program?",
        "What happens to archived data during an S/4HANA migration and how should I prepare?",
        "How do I configure legal hold in SAP ILM and what transactions are involved?",
    ]
    cols = st.columns(2)
    for i, q in enumerate(suggestions):
        if cols[i%2].button(q, key=f"sugg_{i}", use_container_width=True):
            st.session_state.pending_question = q

    st.markdown("---")

    # Display chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-msg-user">👤 <strong>You:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-msg-ai">🤖 <strong>SAP AI Assistant:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True)

    # Input
    user_input = st.chat_input("Ask your SAP archiving question...")
    if "pending_question" in st.session_state:
        user_input = st.session_state.pending_question
        del st.session_state.pending_question

    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})

        # Build messages for Claude API
        messages = []
        for m in st.session_state.chat_history:
            messages.append({"role": m["role"], "content": m["content"]})

        with st.spinner("Consulting SAP knowledge base..."):
            try:
                resp = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"Content-Type":"application/json"},
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1000,
                        "system": SYSTEM_PROMPT,
                        "messages": messages
                    },
                    timeout=30
                )
                if resp.status_code == 200:
                    answer = resp.json()["content"][0]["text"]
                else:
                    answer = f"⚠️ API error {resp.status_code}. Please check your API key in Streamlit secrets."
            except Exception as e:
                answer = f"⚠️ Connection error: {e}. Ensure the Anthropic API key is set in Streamlit secrets as `ANTHROPIC_API_KEY`."

        st.session_state.chat_history.append({"role":"assistant","content":answer})
        st.rerun()

    if st.button("🗑️ Clear conversation", type="secondary"):
        st.session_state.chat_history = []
        st.rerun()

# ─────────────────────────────────────────────────────────────────────
# TAB 5: REMEDIATION PLAYBOOK
# ─────────────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown('<span class="section-badge">📋 Remediation Playbook</span>', unsafe_allow_html=True)
    st.caption("Step-by-step archiving guide per object — generated from blueprint workshop findings")

    selected_obj = st.selectbox("Select Archive Object",
        list(SAP_ARCHIVE_OBJECTS.keys()),
        format_func=lambda k: f"{k} — {SAP_ARCHIVE_OBJECTS[k]['description']}")

    obj = SAP_ARCHIVE_OBJECTS[selected_obj]
    df_obj = df_db[df_db["TABLE_NAME"].isin(obj["tables"])]
    total_size = df_obj["SIZE_GB"].sum()
    total_rows = df_obj["ROWS"].sum()
    score, priority, reasons = score_archivability(selected_obj, total_size, total_rows)

    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Archive Object",  selected_obj)
    col2.metric("Module",          obj["module"])
    col3.metric("Est. Table Size", f"{total_size:.1f} GB")
    col4.metric("Priority Score",  f"{score}/100")

    st.markdown(f"""
    <div class="{'risk-HIGH' if priority=='HIGH' else 'risk-MEDIUM' if priority=='MEDIUM' else 'risk-LOW'}">
    <strong>Priority: {priority}</strong> &nbsp;|&nbsp; {' · '.join(reasons)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📋 Step-by-Step Archiving Playbook")

    steps = [
        ("1️⃣ Verify Prerequisites", f"""
- Check completion status using `{obj['tcode_check']}`
- Confirm: **{obj['prerequisite']}**
- Run residence time analysis in `SARA` → Archive Object: `{selected_obj}` → Residence time check
- Ensure all dependent business processes are closed
        """),
        ("2️⃣ Configure Archive Object in SARA", f"""
- Transaction: `SARA` → Enter object `{selected_obj}`
- Set residence time: **{obj['typical_retention_yrs']} years** (adjust per retention policy)
- Configure variant for Write program
- Set up logical file path (check `FILE` transaction)
- {'Configure ILM retention category and storage class' if obj['ilm_capable'] and ilm_licensed else 'Configure ArchiveLink content repository (OpenText Archive Center)' if has_opentext else 'Configure archive file path (local or network)'}
        """),
        ("3️⃣ Run Preprocessing / Check Program", f"""
- SARA → `Preprocessing` or `Check` button
- Review log — resolve all errors before Write run
- Expected tables: `{'`, `'.join(obj['tables'])}`
- Note record counts per table — document as baseline
        """),
        ("4️⃣ Execute Write Program (DEV first)", f"""
- SARA → `Write` → Run in **test mode first** (no actual archiving)
- Review test log — check object counts match expectations
- Execute production Write run in DEV environment
- Archive files written to: {'OpenText Archive Center via ' + ('ILM 3.1 WebDAV interface (ILM-ADK format)' if ilm_licensed else 'SAP ArchiveLink (ADK format)') if has_opentext else 'Local archive file path'}
        """),
        ("5️⃣ Run Delete Program", f"""
- SARA → `Delete` → run AFTER Write program completes successfully
- Verify Delete log — check records removed from primary tables
- Spot-check: use `{obj['tcode_check']}` to confirm archived documents are accessible via archive
- **Do NOT run Delete if Write log shows errors**
        """),
        ("6️⃣ Verify Retrieval (UAT)", f"""
- Test retrieval from archive in `{obj['tcode_check']}`
- Confirm archived documents display correctly via ArchiveLink viewer
- Test search via ILM Workbench (`IRMPOL`) if ILM enabled
- Document retrieval times and archive file locations
        """),
        ("7️⃣ Transport to QA & Production", f"""
- Transport SARA configuration via standard SAP transport (`SE01` / `STMS`)
- Re-run check/write/delete cycle in QA environment
- Get business sign-off before production run
- Schedule regular archiving jobs via `SM36` / `SM37`
        """),
    ]

    for title, content in steps:
        with st.expander(title):
            st.markdown(content)

    if has_opentext:
        st.markdown("---")
        st.markdown("#### 🔗 OpenText Integration Checklist")
        checklist_items = [
            ("Content repository configured in SAP (`OAC0`)", True),
            ("ArchiveLink connection tested (`OACT`)", True),
            ("Archive object linked to content repository (`OAC3`)", True),
            ("Retrieval tested from SAP GUI" if not ilm_licensed else "ILM storage category configured (`IRMPSCAT`)", True),
            ("WebDAV/ILM 3.1 interface configured" if ilm_licensed else "ADK file path configured in `FILE` transaction", True),
            ("Legal hold process tested in ILM Workbench" if ilm_licensed else "ADK→ILM conversion planned for future ILM activation", ilm_licensed),
        ]
        for item, done in checklist_items:
            st.checkbox(item, value=done, disabled=True)

# ─────────────────────────────────────────────────────────────────────
# TAB 6: CONTEXT & METHODOLOGY
# ─────────────────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown('<span class="section-badge">ℹ️ Context, Methodology & Integration Architecture</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📐 Methodology: How This Works")
        st.markdown("""
**Phase 1 — Analysis & Strategy (8 weeks)**

This tool supports the blueprint workshop process:
1. **DB Sizing** — import your DB02 export to size the opportunity
2. **Object Scoring** — AI-driven prioritisation against your landscape
3. **Prerequisite Check** — per-object readiness assessment
4. **Wave Planning** — recommended sequencing to minimise risk

**Phase 2 — Execution**

- ILM configuration (if licensed)
- Archive object configuration in DEV → QA → PRD
- Testing with business validation
- Cutover and hypercare
        """)

        st.markdown("#### 📥 How to Export Data from SAP")
        with st.expander("DB02 / DBACOCKPIT Export"):
            st.code("""
-- In SAP:
Transaction: DB02 (for Oracle/HANA) or DBACOCKPIT
→ Space → Tables / Indexes
→ Sort by Size descending
→ Export to local file (CSV)

-- File should have columns:
TABLE_NAME, SIZE_GB (or SIZE in MB), ROWS
            """, language="sql")

        with st.expander("TAANA — Table Analysis Export"):
            st.code("""
-- Transaction: TAANA
-- Run table analysis for all tables or specific selection
-- Export results to spreadsheet
-- Columns: TABLE_NAME, ROWS, SIZE_MB, LAST_CHANGE
            """, language="sql")

        with st.expander("SE16 — Direct Table Query"):
            st.code("""
-- Transaction: SE16 or SE16N
-- Table: DBSTATC or DBSTATTORA (Oracle)
           or M_TABLE_USED_MEMORY_VIEW (HANA)
-- Export to local file
            """, language="sql")

    with col2:
        st.markdown("#### 🏗️ Integration Architecture")
        st.markdown(f"""
**Your Current Setup:**
- SAP System: **{sap_system}**
- Content Repository: **{'OpenText Archive Center ✅' if has_opentext else 'Not configured'}**
- ILM Status: **{'Active ✅' if ilm_licensed else 'Not licensed — using standard ADK'}**

**Integration Flow:**
```
SAP ECC
  ↓ SARA (archive write program)
  ↓ ADK File generation
  {'↓ ILM-ADK (retention metadata embedded)' if ilm_licensed else '↓ Standard ADK format'}
  ↓ {'WebDAV / ILM 3.1 interface' if ilm_licensed else 'SAP ArchiveLink (BC-ArchiveLink)'}
  ↓ OpenText Archive Center
  ↓ Archive Storage Services
  ↓ NAS / Long-term Storage
```

**Future Path (if ILM activated later):**
```
Existing ADK files in OpenText
  ↓ SAP ILM File Converter
  ↓ ILM-ADK format (no data loss)
  ↓ Load to ILM Retention Warehouse
  ↓ Full retention governance + GDPR compliance
```
        """)

        st.markdown("#### 🔑 Key SAP Transactions Reference")
        tcodes = {
            "SARA":    "Archive Administration — main entry point",
            "AS":      "Archive Information System — retrieve archived data",
            "TAANA":   "Table Analysis — size and age distribution",
            "DB02":    "Database Performance Monitor — table sizes",
            "SE16":    "Data Browser — direct table access",
            "OAC0":    "Content Repositories — ArchiveLink config",
            "OACT":    "Test ArchiveLink connection to content server",
            "OAC3":    "Link archive objects to content repositories",
            "FILE":    "Logical File Paths — archive file configuration",
            "SM36/37": "Job scheduling and monitoring",
            "IRMPOL":  "ILM Policy Management (if ILM licensed)",
            "IRMPSCAT":"ILM Storage Categories",
            "SFW5":    "Switch Framework — activate ILM business function",
        }
        for tc, desc in tcodes.items():
            st.markdown(f"- `{tc}` — {desc}")

    st.markdown("---")
    st.markdown("""
    <div style="background:#1A2B5E;border-radius:8px;padding:1rem;color:white;text-align:center">
    <p style="margin:0;font-size:0.8rem">
    🔒 <strong>Confidential — Internal Use</strong> &nbsp;|&nbsp; 
    Capgemini Joint Engagement &nbsp;|&nbsp; 
    Built with Claude AI (Anthropic) &nbsp;|&nbsp;
    Not for distribution outside the engagement team
    </p>
    </div>
    """, unsafe_allow_html=True)
