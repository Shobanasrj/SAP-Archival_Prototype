import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json, io, requests
from datetime import datetime

st.set_page_config(
    page_title="SAP Archival AI Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1A2B5E 0%, #2E86C1 100%);
        padding: 1.2rem 1.5rem; border-radius: 10px; margin-bottom: 1.2rem; color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.5rem; }
    .main-header p  { color: #D8E6F3; margin: 0.3rem 0 0; font-size: 0.85rem; }
    .metric-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 8px;
        padding: 1rem; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .metric-card .val { font-size: 1.8rem; font-weight: 700; color: #1A2B5E; }
    .metric-card .lbl { font-size: 0.75rem; color: #64748B; margin-top: 0.2rem; }
    .risk-HIGH   { background:#FEF2F2; border-left:4px solid #EF4444; padding:0.5rem 0.8rem; border-radius:4px; margin:0.5rem 0; }
    .risk-MEDIUM { background:#FFFBEB; border-left:4px solid #F59E0B; padding:0.5rem 0.8rem; border-radius:4px; margin:0.5rem 0; }
    .risk-LOW    { background:#F0FDF4; border-left:4px solid #22C55E; padding:0.5rem 0.8rem; border-radius:4px; margin:0.5rem 0; }
    .chat-user { background:#EBF5FF; border-radius:8px; padding:0.75rem 1rem; margin:0.4rem 0; }
    .chat-ai   { background:#F0F5FB; border-radius:8px; padding:0.75rem 1rem; margin:0.4rem 0; border-left:3px solid #1A2B5E; }
    .badge { background:#1A2B5E; color:white; padding:0.2rem 0.7rem; border-radius:20px; font-size:0.75rem; font-weight:600; }
    .ot-box { background:linear-gradient(135deg,#1A2B5E,#2E4070); border:1px solid #E8A020; border-radius:8px; padding:1rem; color:white; margin:0.8rem 0; }
    .ot-box h4 { color:#E8A020; margin:0 0 0.4rem; }
</style>
""", unsafe_allow_html=True)

# ── SAP Archive Objects ─────────────────────────────────────────────
SAP_OBJECTS = {
    "FI_DOCUMNT": {
        "module":"FI", "desc":"FI Financial Documents",
        "tables":["BKPF","BSEG","BSAS","BSAK","BSIK","BSAD"],
        "retention":10, "ilm":True, "ot":True, "complexity":"Medium", "impact":"High",
        "notes":"Largest FI object. Includes G/L, AP, AR. Requires fiscal year-end close.",
        "tcode":"FB03", "prereq":"Cleared items only"
    },
    "MM_MATBEL": {
        "module":"MM", "desc":"Material Documents",
        "tables":["MKPF","MSEG"],
        "retention":7, "ilm":True, "ot":True, "complexity":"Low", "impact":"Medium",
        "notes":"Goods movements. High volume, good quick win.",
        "tcode":"MB03", "prereq":"No open purchase orders"
    },
    "MM_EKKO": {
        "module":"MM", "desc":"Purchasing Documents",
        "tables":["EKKO","EKPO","EKBE","EKET"],
        "retention":7, "ilm":True, "ot":True, "complexity":"Medium", "impact":"Medium",
        "notes":"Purchase orders and contracts. Must be fully delivered and invoiced.",
        "tcode":"ME23N", "prereq":"Delivery complete, invoice verified"
    },
    "SD_VBAK": {
        "module":"SD", "desc":"Sales Documents",
        "tables":["VBAK","VBAP","VBFA","VBUK"],
        "retention":7, "ilm":True, "ot":True, "complexity":"High", "impact":"High",
        "notes":"Sales orders and deliveries. Complex inter-document dependencies.",
        "tcode":"VA03", "prereq":"Fully delivered, billed, and closed"
    },
    "PP_ORDER": {
        "module":"PP", "desc":"Production Orders",
        "tables":["AUFK","AUFM","AFKO","AFPO"],
        "retention":5, "ilm":True, "ot":True, "complexity":"High", "impact":"Medium",
        "notes":"Production orders with settlements. Costing run must be complete.",
        "tcode":"CO03", "prereq":"TECO status, settlement complete"
    },
    "CO_CCTR_EP": {
        "module":"CO", "desc":"CO Cost Centre Postings",
        "tables":["COEP","COEPL","COSP","COSR"],
        "retention":10, "ilm":False, "ot":True, "complexity":"Medium", "impact":"High",
        "notes":"Controlling line items. Period-end and year-end close required.",
        "tcode":"KSB1", "prereq":"Period-end close complete"
    },
    "QM_QMEL": {
        "module":"QM", "desc":"Quality Notifications",
        "tables":["QMEL","QMFE","QMMA"],
        "retention":5, "ilm":True, "ot":True, "complexity":"Low", "impact":"Low",
        "notes":"Good quick win. Must be in completed status (NOCO).",
        "tcode":"QM03", "prereq":"NOCO status"
    },
    "PM_ORDER": {
        "module":"PM", "desc":"PM Maintenance Orders",
        "tables":["AUFK","AFIH","QMEL"],
        "retention":5, "ilm":True, "ot":True, "complexity":"Medium", "impact":"Low",
        "notes":"Plant maintenance orders. TECO status and settlement required.",
        "tcode":"IW33", "prereq":"TECO + settlement"
    },
    "MM_INVBEL": {
        "module":"MM", "desc":"Physical Inventory Documents",
        "tables":["IKPF","ISEG"],
        "retention":5, "ilm":False, "ot":True, "complexity":"Low", "impact":"Low",
        "notes":"Easy quick win with minimal dependencies.",
        "tcode":"MI03", "prereq":"Count completed and posted"
    },
    "CHANGEDOCU": {
        "module":"Basis", "desc":"Change Documents",
        "tables":["CDHDR","CDPOS"],
        "retention":7, "ilm":False, "ot":True, "complexity":"Low", "impact":"Low",
        "notes":"Very large tables. Excellent first run for DB reduction.",
        "tcode":"SCDO", "prereq":"None — run first for quick wins"
    },
    "IDOCREL": {
        "module":"Basis", "desc":"IDoc Records",
        "tables":["EDIDC","EDID4","EDIDS"],
        "retention":3, "ilm":False, "ot":True, "complexity":"Low", "impact":"Low",
        "notes":"Very high volume. Archive aggressively after processing.",
        "tcode":"WE02", "prereq":"Status 53 (successfully posted)"
    },
    "SPOOL": {
        "module":"Basis", "desc":"Spool Requests",
        "tables":["TSP01","TSP02"],
        "retention":1, "ilm":False, "ot":False, "complexity":"Low", "impact":"Low",
        "notes":"Print spool. Automatic deletion preferred.",
        "tcode":"SP01", "prereq":"Completed spool requests"
    },
}

# ── Data generators ─────────────────────────────────────────────────
def make_db02():
    rows = [
        ("BSEG",45200,185.0),("MSEG",38400,92.0),("EDID4",31200,74.0),
        ("CDPOS",28800,68.0),("VBFA",22100,43.0),("BKPF",18600,38.0),
        ("COEPL",16800,31.0),("KONV",14500,29.0),("EDIDC",13200,18.0),
        ("MKPF",11400,22.0),("EKBE",9800,16.0),("EKKO",8700,14.0),
        ("AUFM",7600,13.0),("COEP",7200,12.5),("VBAK",6800,11.8),
        ("BSAD",6200,11.0),("TSP01",5900,8.5),("IKPF",5100,7.5),
        ("AFIH",4800,7.0),("QMEL",4200,6.2),
    ]
    df = pd.DataFrame(rows, columns=["TABLE_NAME","ROWS_K","SIZE_GB"])
    df["ROWS"] = df["ROWS_K"] * 1000
    return df[["TABLE_NAME","SIZE_GB","ROWS"]]

def make_growth():
    months = list(pd.date_range(end=datetime.now(), periods=12, freq="MS"))
    n = len(months)
    sizes = [3800 + i*45 + int(np.random.randint(-10,25)) for i in range(n)]
    return pd.DataFrame({"Month": months, "DB_Size_GB": sizes})

def score_object(key, size_gb):
    obj = SAP_OBJECTS[key]
    s = 50
    if size_gb > 50:   s += 20
    elif size_gb > 10: s += 10
    else:              s -= 5
    if obj["complexity"] == "Low":  s += 15
    elif obj["complexity"] == "High": s -= 15
    if obj["ilm"]: s += 10
    s = max(0, min(100, s))
    p = "HIGH" if s >= 70 else "MEDIUM" if s >= 45 else "LOW"
    return s, p

# ── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1A2B5E,#2E86C1);padding:1rem;border-radius:8px;margin-bottom:1rem">
    <h3 style="color:white;margin:0;font-size:1rem">🗄️ SAP Archival AI Assistant</h3>
    <p style="color:#D8E6F3;margin:0.3rem 0 0;font-size:0.75rem">Capgemini | SAP Data Volume Management</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Configuration")
    client   = st.text_input("Client Name", "Client (Confidential)")
    system   = st.selectbox("SAP System", ["ECC 6.0 EhP8","ECC 6.0 EhP7","S/4HANA 2021","S/4HANA 2023"])
    has_ot   = st.toggle("Has OpenText Archive Center", value=True)
    has_ilm  = st.toggle("SAP ILM Licensed / RISE",    value=False)

    st.markdown("---")
    st.markdown("### 📁 Import SAP Data")
    src = st.selectbox("Source", [
        "Demo Mode",
        "DB02 / DBACOCKPIT Export (CSV)",
        "TAANA Table Analysis (CSV)",
        "SE16 Table Export (CSV)",
        "Excel Workbook (XLSX)",
    ])
    uploaded = st.file_uploader("Upload File", type=["csv","txt","xlsx"])

    st.markdown("---")
    st.markdown("### 🔑 AI Assistant")
    st.caption("Powered by Claude · Confidential")

    if has_ot:
        st.markdown("""<div style="background:#1A2B5E;border:1px solid #E8A020;border-radius:6px;padding:0.6rem;margin-top:0.5rem">
        <p style="color:#E8A020;font-size:0.75rem;font-weight:700;margin:0">✅ OpenText Connected</p>
        <p style="color:#D8E6F3;font-size:0.7rem;margin:0.2rem 0 0">Archives → OpenText via SAP ArchiveLink</p>
        </div>""", unsafe_allow_html=True)
    if has_ilm:
        st.markdown("""<div style="background:#1A6B2E;border-radius:6px;padding:0.6rem;margin-top:0.5rem">
        <p style="color:white;font-size:0.75rem;font-weight:700;margin:0">✅ ILM Enabled</p>
        <p style="color:#D8E6F3;font-size:0.7rem;margin:0.2rem 0 0">ILM-ADK + WebDAV/ILM 3.1 → OpenText</p>
        </div>""", unsafe_allow_html=True)

# ── Load data ────────────────────────────────────────────────────────
data_label = "🔄 Demo Mode"
if uploaded is not None:
    try:
        if uploaded.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded)
        else:
            df = pd.read_csv(uploaded)
        df.columns = [c.upper().strip() for c in df.columns]
        # Normalise columns
        if "TABLE_NAME" not in df.columns:
            df = df.rename(columns={df.columns[0]: "TABLE_NAME"})
        for col_in, col_out in [("SIZE","SIZE_GB"),("SIZE_MB","SIZE_GB")]:
            if col_in in df.columns and "SIZE_GB" not in df.columns:
                df["SIZE_GB"] = pd.to_numeric(df[col_in], errors="coerce") / (1 if col_in=="SIZE" else 1024)
        if "ROWS" not in df.columns and "ROWS_K" in df.columns:
            df["ROWS"] = pd.to_numeric(df["ROWS_K"], errors="coerce") * 1000
        df["SIZE_GB"] = pd.to_numeric(df.get("SIZE_GB", 0), errors="coerce").fillna(0)
        df["ROWS"]    = pd.to_numeric(df.get("ROWS", 0),    errors="coerce").fillna(0)
        df_db = df[["TABLE_NAME","SIZE_GB","ROWS"]].copy()
        data_label = f"📤 {uploaded.name}"
    except Exception as e:
        st.sidebar.error(f"Could not parse file: {e}")
        df_db = make_db02()
else:
    df_db = make_db02()

df_growth = make_growth()

# ── Header ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="main-header">
<h1>🗄️ SAP Data Volume Management — Archival AI Assistant</h1>
<p>{client} &nbsp;|&nbsp; {system} &nbsp;|&nbsp; {data_label} &nbsp;|&nbsp;
{'✅ OpenText' if has_ot else '⬜ No OpenText'} &nbsp;|&nbsp;
{'✅ ILM Active' if has_ilm else '⬜ ILM Not Active'}</p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
t1,t2,t3,t4,t5,t6 = st.tabs([
    "📊 DB Dashboard",
    "🎯 Archivability",
    "🏗️ Object Catalogue",
    "🤖 AI Assistant",
    "📋 Playbook",
    "ℹ️ Methodology",
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — DB Dashboard
# ════════════════════════════════════════════════════════════════════
with t1:
    st.markdown('<span class="badge">📊 Database Sizing & Growth</span>', unsafe_allow_html=True)
    st.caption("Import your DB02 / DBACOCKPIT export or use demo data")
    st.markdown("")

    all_arch_tables = [t for o in SAP_OBJECTS.values() for t in o["tables"]]
    total  = df_db["SIZE_GB"].sum()
    archiv = df_db[df_db["TABLE_NAME"].isin(all_arch_tables)]["SIZE_GB"].sum()
    pct    = (archiv/total*100) if total else 0
    growth = df_growth["DB_Size_GB"].diff().mean() if len(df_growth) > 1 else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, v, l in [
        (c1, f"{total:.0f} GB",   "Total DB Size"),
        (c2, f"{archiv:.0f} GB",  "Archivable Data"),
        (c3, f"{pct:.0f}%",       "Est. Reduction"),
        (c4, f"{growth:.0f} GB",  "Avg Monthly Growth"),
        (c5, f"{len(df_db)}",     "Tables Analysed"),
    ]:
        col.markdown(f'<div class="metric-card"><div class="val">{v}</div><div class="lbl">{l}</div></div>',
                     unsafe_allow_html=True)
    st.markdown("")

    cl, cr = st.columns([3,2])
    with cl:
        st.markdown("##### Top 15 Tables by Size")
        top = df_db.nlargest(15,"SIZE_GB")
        fig = px.bar(top, x="SIZE_GB", y="TABLE_NAME", orientation="h",
                     color="SIZE_GB", color_continuous_scale=[[0,"#BDD7EE"],[1,"#1A2B5E"]],
                     labels={"SIZE_GB":"Size (GB)","TABLE_NAME":""})
        fig.update_layout(height=370, showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0,r=0,t=10,b=0), plot_bgcolor="white")
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_xaxes(gridcolor="#F0F0F0")
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("##### DB Growth Trend")
        fig2 = px.area(df_growth, x="Month", y="DB_Size_GB",
                       color_discrete_sequence=["#2E86C1"])
        fig2.update_layout(height=175, margin=dict(l=0,r=0,t=5,b=0),
                           plot_bgcolor="white", showlegend=False)
        fig2.update_xaxes(gridcolor="#F0F0F0"); fig2.update_yaxes(gridcolor="#F0F0F0")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### By Module")
        mods = {}
        for obj in SAP_OBJECTS.values():
            gb = df_db[df_db["TABLE_NAME"].isin(obj["tables"])]["SIZE_GB"].sum()
            if gb > 0:
                mods[obj["module"]] = mods.get(obj["module"],0) + gb
        if mods:
            fig3 = px.pie(values=list(mods.values()), names=list(mods.keys()),
                          hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
            fig3.update_layout(height=175, margin=dict(l=0,r=0,t=0,b=0),
                               legend=dict(font=dict(size=9)))
            st.plotly_chart(fig3, use_container_width=True)

    st.markdown("##### Full Table Detail")
    display_df = df_db.copy()
    display_df.columns = ["Table","Size (GB)","Row Count"]
    st.dataframe(display_df, use_container_width=True, height=220, hide_index=True)

# ════════════════════════════════════════════════════════════════════
# TAB 2 — Archivability
# ════════════════════════════════════════════════════════════════════
with t2:
    st.markdown('<span class="badge">🎯 Archivability Scoring</span>', unsafe_allow_html=True)
    st.caption("AI-driven prioritisation of SAP archive objects against your system data")
    st.markdown("")

    results = []
    for key, obj in SAP_OBJECTS.items():
        gb   = df_db[df_db["TABLE_NAME"].isin(obj["tables"])]["SIZE_GB"].sum()
        rows = df_db[df_db["TABLE_NAME"].isin(obj["tables"])]["ROWS"].sum()
        sc, pr = score_object(key, gb)
        results.append({
            "Object": key, "Module": obj["module"], "Description": obj["desc"],
            "Size (GB)": round(gb,1), "Complexity": obj["complexity"],
            "ILM": "✅" if obj["ilm"] else "—",
            "OpenText": "✅" if obj["ot"] else "—",
            "Score": sc, "Priority": pr,
            "Retention (yrs)": obj["retention"],
        })
    df_r = pd.DataFrame(results).sort_values("Score", ascending=False).reset_index(drop=True)

    hi = (df_r["Priority"]=="HIGH").sum()
    me = (df_r["Priority"]=="MEDIUM").sum()
    lo = (df_r["Priority"]=="LOW").sum()
    ilm_n = (df_r["ILM"]=="✅").sum()

    c1,c2,c3,c4 = st.columns(4)
    for col,v,l,clr in [
        (c1,hi,"High Priority","#EF4444"),
        (c2,me,"Medium Priority","#F59E0B"),
        (c3,lo,"Lower Priority","#22C55E"),
        (c4,ilm_n,"ILM-Capable","#1A2B5E"),
    ]:
        col.markdown(f'<div class="metric-card"><div class="val" style="color:{clr}">{v}</div><div class="lbl">{l}</div></div>',
                     unsafe_allow_html=True)
    st.markdown("")

    cl,cr = st.columns([2,3])
    with cl:
        st.markdown("##### Priority Matrix")
        color_map = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"}
        fig = px.scatter(df_r, x="Size (GB)", y="Score", color="Priority",
                         hover_data=["Object","Description"],
                         color_discrete_map=color_map,
                         size_max=20)
        fig.add_hline(y=70, line_dash="dash", line_color="#EF4444", opacity=0.4)
        fig.add_hline(y=45, line_dash="dash", line_color="#F59E0B", opacity=0.4)
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("##### Scored Archive Objects")
        # Simple colour coding via st.dataframe without applymap/background_gradient
        def priority_icon(p):
            return "🔴" if p=="HIGH" else "🟡" if p=="MEDIUM" else "🟢"
        df_display = df_r.copy()
        df_display["Pri"] = df_display["Priority"].apply(priority_icon)
        cols_show = ["Pri","Object","Module","Description","Size (GB)","Score","ILM","OpenText"]
        st.dataframe(df_display[cols_show], use_container_width=True,
                     height=290, hide_index=True)

    st.markdown("##### 📅 Wave Plan")
    w1 = df_r[df_r["Priority"]=="HIGH"][["Object","Description","Size (GB)","Retention (yrs)"]]
    w2 = df_r[df_r["Priority"]=="MEDIUM"][["Object","Description","Size (GB)","Retention (yrs)"]]
    col1,col2 = st.columns(2)
    with col1:
        st.markdown("**Wave 1 — High Priority (Quick Wins)**")
        st.dataframe(w1, use_container_width=True, height=160, hide_index=True)
    with col2:
        st.markdown("**Wave 2 — Medium Priority**")
        st.dataframe(w2, use_container_width=True, height=160, hide_index=True)

# ════════════════════════════════════════════════════════════════════
# TAB 3 — Object Catalogue
# ════════════════════════════════════════════════════════════════════
with t3:
    st.markdown('<span class="badge">🏗️ SAP Archive Object Catalogue</span>', unsafe_allow_html=True)
    st.caption("Full technical reference — equivalent to blueprint workshop output")
    st.markdown("")

    mod_opts  = sorted(set(o["module"] for o in SAP_OBJECTS.values()))
    comp_opts = ["Low","Medium","High"]
    c1,c2 = st.columns(2)
    mod_sel  = c1.multiselect("Module", mod_opts, default=mod_opts)
    comp_sel = c2.multiselect("Complexity", comp_opts, default=comp_opts)

    for key, obj in SAP_OBJECTS.items():
        if obj["module"] not in mod_sel: continue
        if obj["complexity"] not in comp_sel: continue
        gb = df_db[df_db["TABLE_NAME"].isin(obj["tables"])]["SIZE_GB"].sum()
        sc, pr = score_object(key, gb)
        icon = "🔴" if pr=="HIGH" else "🟡" if pr=="MEDIUM" else "🟢"
        with st.expander(f"{icon} **{key}** — {obj['desc']} | {obj['module']} | {obj['complexity']} complexity"):
            c1,c2,c3 = st.columns(3)
            c1.markdown(f"**Retention:** {obj['retention']} years")
            c1.markdown(f"**Prerequisite:** {obj['prereq']}")
            c1.markdown(f"**Verify in:** `{obj['tcode']}`")
            c2.markdown(f"**ILM Capable:** {'✅' if obj['ilm'] else '❌'}")
            c2.markdown(f"**OpenText:** {'✅' if obj['ot'] else '❌'}")
            c2.markdown(f"**Tables:** `{'`, `'.join(obj['tables'])}`")
            c3.markdown(f"**Score:** {sc}/100 ({pr})")
            c3.markdown(f"**Est. Size:** {gb:.1f} GB")
            c3.markdown(f"**Notes:** {obj['notes']}")

            if has_ot:
                if obj["ilm"] and has_ilm:
                    st.markdown("""<div class="ot-box">
                    <h4>🔗 ILM + OpenText Path</h4>
                    <p style="color:#D8E6F3;font-size:0.85rem;margin:0">
                    ILM-ADK files with embedded retention metadata → OpenText via WebDAV/ILM 3.1.
                    Retention enforced by OpenText. Legal hold and defensible deletion supported.</p>
                    </div>""", unsafe_allow_html=True)
                elif obj["ot"]:
                    st.markdown("""<div class="ot-box">
                    <h4>🔗 OpenText via ArchiveLink</h4>
                    <p style="color:#D8E6F3;font-size:0.85rem;margin:0">
                    ADK files → OpenText via SAP ArchiveLink. No infrastructure change needed.
                    Activate ILM later — existing ADK files convertible with SAP ILM File Converter, no data loss.</p>
                    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 4 — AI Assistant
# ════════════════════════════════════════════════════════════════════
with t4:
    st.markdown('<span class="badge">🤖 AI Archiving Assistant — Claude</span>', unsafe_allow_html=True)
    st.caption("Ask any SAP archiving question — ILM, SARA, OpenText, objects, retention, S/4HANA")
    st.markdown("")

    SYS = f"""You are a senior SAP Data Volume Management and ILM consultant at Capgemini with 15+ years experience.

CLIENT SETUP:
- SAP System: {system}
- Client: {client}
- OpenText Archive Center: {'Yes — integrated via SAP ArchiveLink' if has_ot else 'Not configured'}
- SAP ILM: {'Licensed and active' if has_ilm else 'Not licensed — using standard ADK archiving'}

EXPERTISE: SAP data archiving (SARA, AS, TAANA, DB02), SAP ILM retention policies and legal hold,
OpenText ArchiveLink and WebDAV/ILM 3.1 integration, archive objects (FI_DOCUMNT, MM_MATBEL, SD_VBAK etc.),
ADK/ILM-ADK file formats, S/4HANA migration readiness, GDPR compliance for data retention.

STYLE: Be specific and technical. Reference exact SAP transaction codes (SARA, TAANA, OAC0, IRMPOL etc.),
table names, and configuration steps. Think like a senior consultant in a blueprint workshop.
Format with clear sections. No generic advice — be precise and actionable."""

    if "history" not in st.session_state:
        st.session_state.history = []

    suggestions = [
        "What are the prerequisites for archiving FI_DOCUMNT and what residence time should I set?",
        "How does OpenText integrate with SAP ILM via WebDAV/ILM 3.1?",
        "Which archive objects give the biggest DB reduction with lowest risk?",
        "What is the difference between ADK and ILM-ADK files?",
        "How do I configure a legal hold in SAP ILM and which transactions are involved?",
        "How should I prepare our ECC archiving for S/4HANA migration?",
        "Walk me through running MM_MATBEL archiving in SARA step by step",
        "What does TAANA show and how do I use it for archiving decisions?",
    ]
    st.markdown("**💡 Suggested questions — click to ask:**")
    cols = st.columns(2)
    for i,q in enumerate(suggestions):
        if cols[i%2].button(q, key=f"q{i}", use_container_width=True):
            st.session_state.pending = q

    st.markdown("---")
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">👤 <b>You:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai">🤖 <b>SAP AI Assistant:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)

    user_q = st.chat_input("Ask your SAP archiving question...")
    if "pending" in st.session_state:
        user_q = st.session_state.pending
        del st.session_state.pending

    if user_q:
        st.session_state.history.append({"role":"user","content":user_q})
        messages = [{"role":m["role"],"content":m["content"]} for m in st.session_state.history]
        with st.spinner("Consulting SAP knowledge base..."):
            try:
                api_key = st.secrets.get("ANTHROPIC_API_KEY","")
                if not api_key:
                    answer = "⚠️ No API key found. Add ANTHROPIC_API_KEY to Streamlit secrets to enable the AI assistant."
                else:
                    r = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                        json={"model":"claude-sonnet-4-20250514","max_tokens":1000,"system":SYS,"messages":messages},
                        timeout=30
                    )
                    if r.status_code == 200:
                        answer = r.json()["content"][0]["text"]
                    else:
                        answer = f"⚠️ API error {r.status_code}: {r.text[:200]}"
            except Exception as e:
                answer = f"⚠️ Error: {e}"
        st.session_state.history.append({"role":"assistant","content":answer})
        st.rerun()

    if st.button("🗑️ Clear chat", type="secondary"):
        st.session_state.history = []
        st.rerun()

# ════════════════════════════════════════════════════════════════════
# TAB 5 — Playbook
# ════════════════════════════════════════════════════════════════════
with t5:
    st.markdown('<span class="badge">📋 Remediation Playbook</span>', unsafe_allow_html=True)
    st.caption("Step-by-step archiving guide per object")
    st.markdown("")

    sel = st.selectbox("Select Archive Object",
        list(SAP_OBJECTS.keys()),
        format_func=lambda k: f"{k} — {SAP_OBJECTS[k]['desc']}")
    obj = SAP_OBJECTS[sel]
    gb  = df_db[df_db["TABLE_NAME"].isin(obj["tables"])]["SIZE_GB"].sum()
    sc, pr = score_object(sel, gb)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Object",     sel)
    c2.metric("Module",     obj["module"])
    c3.metric("Est. Size",  f"{gb:.1f} GB")
    c4.metric("Score",      f"{sc}/100")

    icon_cls = "risk-HIGH" if pr=="HIGH" else "risk-MEDIUM" if pr=="MEDIUM" else "risk-LOW"
    st.markdown(f'<div class="{icon_cls}"><b>Priority: {pr}</b> &nbsp;|&nbsp; Retention: {obj["retention"]} years &nbsp;|&nbsp; Complexity: {obj["complexity"]}</div>',
                unsafe_allow_html=True)
    st.markdown("")

    steps = [
        ("1️⃣ Verify Prerequisites", f"""
- Check status in `{obj['tcode']}`
- Confirm: **{obj['prereq']}**
- Run residence time check in `SARA` → Archive Object: `{sel}`
- Ensure all dependent processes are closed
        """),
        ("2️⃣ Configure in SARA", f"""
- Transaction `SARA` → enter object `{sel}`
- Set residence time: **{obj['retention']} years**
- Configure variant for Write program
- Check logical file path (`FILE` transaction)
- {'Configure ILM retention category (`IRMPSCAT`)' if obj['ilm'] and has_ilm else 'Configure ArchiveLink content repository (`OAC0`, `OAC3`)' if has_ot else 'Configure archive file path'}
        """),
        ("3️⃣ Run Preprocessing / Check", f"""
- SARA → **Preprocessing** or **Check** button
- Review log — resolve all errors before Write
- Tables in scope: `{'`, `'.join(obj['tables'])}`
- Record baseline row counts per table
        """),
        ("4️⃣ Execute Write Program (DEV first)", f"""
- SARA → **Write** → run in **test mode first**
- Review test log for object counts
- Execute production Write run in DEV
- Archive files → {'OpenText via ' + ('ILM 3.1 WebDAV (ILM-ADK)' if has_ilm else 'SAP ArchiveLink (ADK)') if has_ot else 'local file path'}
        """),
        ("5️⃣ Run Delete Program", f"""
- SARA → **Delete** → only after Write completes successfully
- Verify records removed from primary tables
- Spot-check: confirm archived docs visible via `{obj['tcode']}`
- **Do NOT run Delete if Write log has errors**
        """),
        ("6️⃣ Verify Retrieval (UAT)", f"""
- Test retrieval in `{obj['tcode']}`
- Confirm archived documents display via ArchiveLink viewer
- {'Test ILM Workbench (`IRMPOL`) for retention policy check' if has_ilm else 'Verify ArchiveLink connection (`OACT`)'}
- Document retrieval times
        """),
        ("7️⃣ Transport to QA → Production", f"""
- Transport SARA config via `SE01` / `STMS`
- Re-run full cycle in QA
- Get business sign-off before production
- Schedule regular jobs via `SM36` / `SM37`
        """),
    ]
    for title, body in steps:
        with st.expander(title):
            st.markdown(body)

    if has_ot:
        st.markdown("---")
        st.markdown("#### 🔗 OpenText Checklist")
        items = [
            "Content repository configured (`OAC0`)",
            "ArchiveLink connection tested (`OACT`)",
            "Archive object linked to repository (`OAC3`)",
            "ILM storage category configured (`IRMPSCAT`)" if has_ilm else "Logical file path configured (`FILE`)",
            "Retrieval tested from SAP GUI",
            "Legal hold tested in ILM Workbench (`IRMPOL`)" if has_ilm else "ADK→ILM conversion planned for future activation",
        ]
        for item in items:
            st.checkbox(item, value=False)

# ════════════════════════════════════════════════════════════════════
# TAB 6 — Methodology
# ════════════════════════════════════════════════════════════════════
with t6:
    st.markdown('<span class="badge">ℹ️ Methodology & Integration Architecture</span>', unsafe_allow_html=True)
    st.markdown("")

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("#### 📐 Engagement Methodology")
        st.markdown("""
**Phase 1 — Analysis & Strategy (8 weeks)**
1. **DB Sizing** — import DB02 export to baseline the opportunity
2. **Object Scoring** — AI-driven prioritisation against your landscape
3. **Prerequisite Mapping** — per-object readiness assessment
4. **Wave Planning** — risk-sequenced archiving roadmap

**Phase 2 — Execution (26 weeks)**
- ILM configuration (if licensed)
- Archive object configuration DEV → QA → PRD
- Testing, UAT, cutover and hypercare
        """)
        st.markdown("#### 📥 How to Export Data from SAP")
        with st.expander("DB02 / DBACOCKPIT"):
            st.code("""Transaction: DB02 or DBACOCKPIT
→ Space → Tables / Indexes
→ Sort by Size descending
→ Export to CSV
Columns needed: TABLE_NAME, SIZE_GB, ROWS""")
        with st.expander("TAANA — Table Analysis"):
            st.code("""Transaction: TAANA
→ Run table analysis
→ Export results
Columns: TABLE_NAME, ROWS, SIZE_MB""")
        with st.expander("SE16 / SE16N"):
            st.code("""Table: DBSTATC (Oracle)
      or M_TABLE_USED_MEMORY_VIEW (HANA)
→ Export to local file""")

    with c2:
        st.markdown("#### 🏗️ Storage Architecture")
        arch = f"""
**Current Setup:**
- SAP System: {system}
- Content Repository: {'OpenText Archive Center ✅' if has_ot else 'Not configured'}
- ILM: {'Active ✅' if has_ilm else 'Not licensed'}

**Archive Flow:**
```
SAP ECC (SARA)
  ↓ ADK file generation
  {'↓ ILM-ADK (retention metadata)' if has_ilm else '↓ Standard ADK format'}
  ↓ {'WebDAV / ILM 3.1' if has_ilm else 'SAP ArchiveLink'}
  ↓ OpenText Archive Center
  ↓ Archive Storage → NAS
```
**Future ILM Upgrade Path:**
```
Existing ADK files
  ↓ SAP ILM File Converter
  ↓ ILM-ADK (no data loss)
  ↓ ILM Retention Warehouse
  ↓ GDPR + legal hold enabled
```"""
        st.markdown(arch)

        st.markdown("#### 🔑 Key Transactions")
        for tc, desc in [
            ("SARA","Archive Administration — main entry point"),
            ("AS","Archive Information System — retrieve archived data"),
            ("TAANA","Table Analysis — size and age distribution"),
            ("DB02","Database monitor — table sizes"),
            ("OAC0","Content Repositories — ArchiveLink config"),
            ("OACT","Test ArchiveLink connection"),
            ("OAC3","Link objects to content repositories"),
            ("FILE","Logical file paths"),
            ("SM36/37","Job scheduling and monitoring"),
            ("IRMPOL","ILM Policy Management"),
            ("SFW5","Switch Framework — activate ILM"),
        ]:
            st.markdown(f"- `{tc}` — {desc}")

    st.markdown("---")
    st.markdown("""<div style="background:#1A2B5E;border-radius:8px;padding:0.8rem;color:white;text-align:center">
    <p style="margin:0;font-size:0.8rem">
    🔒 <b>Confidential — Capgemini Internal Use Only</b> &nbsp;|&nbsp;
    SAP Data Volume Management Engagement &nbsp;|&nbsp;
    AI powered by Claude (Anthropic)
    </p></div>""", unsafe_allow_html=True)
