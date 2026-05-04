import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(
    page_title="SAP Archival Intelligence | Capgemini",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Premium CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #F0F4F8; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1628 0%, #1A2B5E 60%, #0F3460 100%) !important;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stTextInput > div > div > input {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: white !important; border-radius: 8px !important;
}
section[data-testid="stSidebar"] label { color: #94B4D4 !important; font-size:0.75rem !important; font-weight:600 !important; letter-spacing:0.05em !important; }
section[data-testid="stSidebar"] p { color: #B8D0E8 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; }
section[data-testid="stSidebar"] h3 { color: white !important; font-size:0.8rem !important; font-weight:700 !important; letter-spacing:0.1em !important; text-transform:uppercase !important; }
section[data-testid="stSidebar"] .stButton>button {
    background: rgba(232,160,32,0.2) !important; border: 1px solid #E8A020 !important;
    color: #E8A020 !important; border-radius: 8px !important; width:100%;
}

/* Hide default streamlit elements */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display:none; }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    background: white; border-radius: 12px; padding: 4px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08); gap: 2px; margin-bottom: 1.2rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important; padding: 0.5rem 1rem !important;
    font-weight: 600 !important; font-size: 0.8rem !important;
    color: #64748B !important; background: transparent !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1A2B5E, #2E86C1) !important;
    color: white !important; box-shadow: 0 2px 8px rgba(26,43,94,0.3) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* KPI Cards */
.kpi-card {
    background: white; border-radius: 16px; padding: 1.2rem 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #E8EDF5;
    text-align: center; position: relative; overflow: hidden;
    transition: transform 0.2s; height: 100%;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: var(--accent, linear-gradient(90deg,#1A2B5E,#2E86C1));
}
.kpi-value { font-size: 2rem; font-weight: 800; color: #1A2B5E; line-height:1.1; }
.kpi-label { font-size: 0.7rem; color: #94A3B8; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 0.3rem; }
.kpi-delta { font-size: 0.75rem; font-weight: 600; margin-top: 0.2rem; }
.kpi-delta.up { color: #22C55E; }
.kpi-delta.down { color: #EF4444; }

/* Section headers */
.section-hdr {
    display: flex; align-items: center; gap: 0.6rem;
    margin-bottom: 1rem; padding-bottom: 0.6rem;
    border-bottom: 2px solid #E8EDF5;
}
.section-hdr h3 { margin:0; font-size:1rem; font-weight:700; color:#1A2B5E; }
.section-icon {
    width:32px; height:32px; border-radius:8px;
    background: linear-gradient(135deg,#1A2B5E,#2E86C1);
    display:flex; align-items:center; justify-content:center;
    font-size:16px; flex-shrink:0;
}

/* Content cards */
.content-card {
    background: white; border-radius: 12px; padding: 1.2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05); border: 1px solid #E8EDF5;
    margin-bottom: 1rem;
}

/* Priority badges */
.badge-high   { background:#FEF2F2; color:#991B1B; padding:0.2rem 0.6rem; border-radius:20px; font-size:0.7rem; font-weight:700; }
.badge-medium { background:#FFFBEB; color:#92400E; padding:0.2rem 0.6rem; border-radius:20px; font-size:0.7rem; font-weight:700; }
.badge-low    { background:#F0FDF4; color:#166534; padding:0.2rem 0.6rem; border-radius:20px; font-size:0.7rem; font-weight:700; }

/* Object cards */
.obj-card {
    background: white; border-radius: 12px; border: 1px solid #E8EDF5;
    overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    margin-bottom: 0.6rem;
}
.obj-card-header {
    padding: 0.7rem 1rem; display:flex; justify-content:space-between; align-items:center;
    cursor: pointer;
}
.obj-card-header.HIGH   { border-left: 4px solid #EF4444; }
.obj-card-header.MEDIUM { border-left: 4px solid #F59E0B; }
.obj-card-header.LOW    { border-left: 4px solid #22C55E; }

/* Chat */
.chat-wrap { max-height: 420px; overflow-y: auto; padding: 0.5rem; border-radius: 12px; background: #F8FAFC; border: 1px solid #E8EDF5; }
.chat-user { background: linear-gradient(135deg,#1A2B5E,#2E86C1); color:white; border-radius:12px 12px 4px 12px; padding:0.8rem 1rem; margin:0.4rem 0; }
.chat-ai   { background: white; border: 1px solid #E8EDF5; border-radius:12px 12px 12px 4px; padding:0.8rem 1rem; margin:0.4rem 0; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
.chat-user p, .chat-ai p { margin:0; font-size:0.88rem; line-height:1.5; }
.chat-user .role { font-size:0.7rem; font-weight:700; opacity:0.8; margin-bottom:0.3rem; letter-spacing:0.05em; }
.chat-ai .role   { font-size:0.7rem; font-weight:700; color:#1A2B5E; margin-bottom:0.3rem; letter-spacing:0.05em; }

/* OpenText integration box */
.ot-box {
    background: linear-gradient(135deg, #0A1628 0%, #1A2B5E 100%);
    border: 1px solid #E8A020; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
}
.ot-box h4 { color: #E8A020; margin: 0 0 0.4rem; font-size:0.85rem; font-weight:700; }
.ot-box p  { color: #B8D0E8; font-size: 0.8rem; margin:0; line-height:1.4; }

/* Step cards in playbook */
.step-card {
    background: white; border-radius: 10px; border: 1px solid #E8EDF5;
    padding: 1rem; margin-bottom: 0.6rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
}
.step-num {
    width:28px; height:28px; border-radius:50%;
    background: linear-gradient(135deg,#1A2B5E,#2E86C1);
    color:white; font-weight:700; font-size:0.8rem;
    display:inline-flex; align-items:center; justify-content:center;
    margin-right:0.6rem;
}

/* Suggest buttons */
.stButton>button {
    border-radius: 8px !important; border: 1px solid #E2E8F0 !important;
    background: white !important; color: #1A2B5E !important;
    font-size: 0.78rem !important; font-weight: 500 !important;
    text-align: left !important; padding: 0.5rem 0.8rem !important;
    transition: all 0.15s !important; width: 100% !important;
}
.stButton>button:hover {
    border-color: #1A2B5E !important; background: #F0F5FB !important;
    box-shadow: 0 2px 8px rgba(26,43,94,0.1) !important;
}

/* Streamlit dataframe */
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #E8EDF5 !important; }

/* Progress bar */
.prog-bar-wrap { background:#EEF2FF; border-radius:20px; height:8px; overflow:hidden; margin:0.3rem 0; }
.prog-bar      { height:100%; border-radius:20px; background:linear-gradient(90deg,#1A2B5E,#2E86C1); }
</style>
""", unsafe_allow_html=True)

# ── Data ────────────────────────────────────────────────────────────
SAP_OBJECTS = {
    "FI_DOCUMNT": {"module":"FI","desc":"FI Financial Documents","tables":["BKPF","BSEG","BSAS","BSAK","BSIK","BSAD"],"retention":10,"ilm":True,"ot":True,"complexity":"Medium","impact":"High","notes":"Largest FI object. G/L, AP, AR. Requires fiscal year-end close.","tcode":"FB03","prereq":"Cleared items only"},
    "MM_MATBEL":  {"module":"MM","desc":"Material Documents","tables":["MKPF","MSEG"],"retention":7,"ilm":True,"ot":True,"complexity":"Low","impact":"Medium","notes":"Goods movements. High volume, excellent quick win.","tcode":"MB03","prereq":"No open purchase orders"},
    "MM_EKKO":    {"module":"MM","desc":"Purchasing Documents","tables":["EKKO","EKPO","EKBE","EKET"],"retention":7,"ilm":True,"ot":True,"complexity":"Medium","impact":"Medium","notes":"POs and contracts. Must be delivered and invoiced.","tcode":"ME23N","prereq":"Delivery complete, invoice verified"},
    "SD_VBAK":    {"module":"SD","desc":"Sales Documents","tables":["VBAK","VBAP","VBFA","VBUK"],"retention":7,"ilm":True,"ot":True,"complexity":"High","impact":"High","notes":"Sales orders. Complex VBFA dependencies.","tcode":"VA03","prereq":"Fully delivered, billed, closed"},
    "PP_ORDER":   {"module":"PP","desc":"Production Orders","tables":["AUFK","AUFM","AFKO","AFPO"],"retention":5,"ilm":True,"ot":True,"complexity":"High","impact":"Medium","notes":"Costing run must be complete before archiving.","tcode":"CO03","prereq":"TECO status, settlement complete"},
    "CO_CCTR_EP": {"module":"CO","desc":"CO Cost Centre Postings","tables":["COEP","COEPL","COSP","COSR"],"retention":10,"ilm":False,"ot":True,"complexity":"Medium","impact":"High","notes":"Controlling line items. Year-end close required.","tcode":"KSB1","prereq":"Period-end close complete"},
    "QM_QMEL":    {"module":"QM","desc":"Quality Notifications","tables":["QMEL","QMFE","QMMA"],"retention":5,"ilm":True,"ot":True,"complexity":"Low","impact":"Low","notes":"Good quick win. NOCO status required.","tcode":"QM03","prereq":"NOCO status"},
    "PM_ORDER":   {"module":"PM","desc":"PM Maintenance Orders","tables":["AUFK","AFIH","QMEL"],"retention":5,"ilm":True,"ot":True,"complexity":"Medium","impact":"Low","notes":"TECO and settlement required.","tcode":"IW33","prereq":"TECO + settlement"},
    "CHANGEDOCU": {"module":"Basis","desc":"Change Documents","tables":["CDHDR","CDPOS"],"retention":7,"ilm":False,"ot":True,"complexity":"Low","impact":"Low","notes":"Very large tables. Excellent first run for DB reduction.","tcode":"SCDO","prereq":"None — run first for quick wins"},
    "IDOCREL":    {"module":"Basis","desc":"IDoc Records","tables":["EDIDC","EDID4","EDIDS"],"retention":3,"ilm":False,"ot":True,"complexity":"Low","impact":"Low","notes":"Very high volume. Archive after status 53.","tcode":"WE02","prereq":"Status 53 (successfully posted)"},
    "MM_INVBEL":  {"module":"MM","desc":"Physical Inventory Docs","tables":["IKPF","ISEG"],"retention":5,"ilm":False,"ot":True,"complexity":"Low","impact":"Low","notes":"Easy quick win.","tcode":"MI03","prereq":"Count completed and posted"},
    "SPOOL":      {"module":"Basis","desc":"Spool Requests","tables":["TSP01","TSP02"],"retention":1,"ilm":False,"ot":False,"complexity":"Low","impact":"Low","notes":"Deletion usually preferred.","tcode":"SP01","prereq":"Completed spool requests"},
}

def make_db():
    data = [("BSEG",45200,185.0),("MSEG",38400,92.0),("EDID4",31200,74.0),
            ("CDPOS",28800,68.0),("VBFA",22100,43.0),("BKPF",18600,38.0),
            ("COEPL",16800,31.0),("KONV",14500,29.0),("EDIDC",13200,18.0),
            ("MKPF",11400,22.0),("EKBE",9800,16.0),("EKKO",8700,14.0),
            ("AUFM",7600,13.0),("COEP",7200,12.5),("VBAK",6800,11.8),
            ("BSAD",6200,11.0),("TSP01",5900,8.5),("IKPF",5100,7.5),
            ("AFIH",4800,7.0),("QMEL",4200,6.2)]
    df = pd.DataFrame(data, columns=["TABLE","SIZE_GB","ROWS_K"])
    df["ROWS"] = df["ROWS_K"] * 1000
    return df[["TABLE","SIZE_GB","ROWS"]]

def make_growth():
    months = list(pd.date_range(end=datetime.now(), periods=12, freq="MS"))
    n = len(months)
    np.random.seed(42)
    sizes = [3800 + i*45 + int(np.random.randint(-10,25)) for i in range(n)]
    return pd.DataFrame({"Month": months, "GB": sizes})

def score(key, gb):
    obj = SAP_OBJECTS[key]; s = 50
    s += 20 if gb>50 else 10 if gb>10 else -5
    s += 15 if obj["complexity"]=="Low" else -15 if obj["complexity"]=="High" else 0
    if obj["ilm"]: s += 10
    s = max(0,min(100,s))
    return s, ("HIGH" if s>=70 else "MEDIUM" if s>=45 else "LOW")

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    # Logo area
    st.markdown("""
    <div style="padding:1.2rem 0.5rem 1rem">
      <div style="font-size:1.4rem;font-weight:800;letter-spacing:-0.02em">
        <span style="color:#E8A020">●</span> SAP Archival
      </div>
      <div style="font-size:0.75rem;color:#94B4D4;font-weight:500;margin-top:0.1rem">Intelligence Platform</div>
      <div style="font-size:0.65rem;color:#5A7A9A;margin-top:0.3rem;letter-spacing:0.05em">CAPGEMINI CONFIDENTIAL</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<hr style="border:1px solid rgba(255,255,255,0.1);margin:0 0 1rem">', unsafe_allow_html=True)

    st.markdown("### CLIENT SETUP")
    client  = st.text_input("", "Client (Confidential)", placeholder="Client name")
    system  = st.selectbox("", ["ECC 6.0 EhP8","ECC 6.0 EhP7","S/4HANA 2021","S/4HANA 2023"])
    has_ot  = st.toggle("OpenText Archive Center", value=True)
    has_ilm = st.toggle("SAP ILM / RISE Licensed",  value=False)

    st.markdown('<hr style="border:1px solid rgba(255,255,255,0.1);margin:1rem 0">', unsafe_allow_html=True)
    st.markdown("### IMPORT DATA")
    uploaded = st.file_uploader("Upload DB02 / TAANA / SE16 export", type=["csv","xlsx","txt"])

    st.markdown('<hr style="border:1px solid rgba(255,255,255,0.1);margin:1rem 0">', unsafe_allow_html=True)

    if has_ot:
        st.markdown("""<div style="background:rgba(232,160,32,0.15);border:1px solid rgba(232,160,32,0.4);border-radius:8px;padding:0.7rem">
        <div style="color:#E8A020;font-size:0.7rem;font-weight:700;letter-spacing:0.05em">✅ OPENTEXT CONNECTED</div>
        <div style="color:#94B4D4;font-size:0.7rem;margin-top:0.2rem">ArchiveLink · {'ILM 3.1' if has_ilm else 'ADK'} protocol</div>
        </div>""", unsafe_allow_html=True)
    if has_ilm:
        st.markdown("""<div style="background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.3);border-radius:8px;padding:0.7rem;margin-top:0.5rem">
        <div style="color:#4ADE80;font-size:0.7rem;font-weight:700;letter-spacing:0.05em">✅ ILM ACTIVE</div>
        <div style="color:#94B4D4;font-size:0.7rem;margin-top:0.2rem">Retention · Legal Hold · WebDAV</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr style="border:1px solid rgba(255,255,255,0.1);margin:1rem 0">', unsafe_allow_html=True)
    st.markdown("""<div style="color:#5A7A9A;font-size:0.65rem;line-height:1.6">
    🤖 AI powered by Claude<br>🔒 Confidential — internal use only<br>
    📊 Data Volume Management v2.0</div>""", unsafe_allow_html=True)

# ── Load data ────────────────────────────────────────────────────────
label = "Demo Mode"
if uploaded:
    try:
        df_db = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
        df_db.columns = [c.upper().strip() for c in df_db.columns]
        for alias in ["TABLE_NAME","TABLE","TABNAME"]:
            if alias in df_db.columns: df_db = df_db.rename(columns={alias:"TABLE"}); break
        if "TABLE" not in df_db.columns: df_db.rename(columns={df_db.columns[0]:"TABLE"}, inplace=True)
        if "SIZE_GB" not in df_db.columns:
            for c in ["SIZE","SIZE_MB"]:
                if c in df_db.columns:
                    df_db["SIZE_GB"] = pd.to_numeric(df_db[c],errors="coerce") / (1 if c=="SIZE" else 1024); break
        df_db["SIZE_GB"] = pd.to_numeric(df_db.get("SIZE_GB",0), errors="coerce").fillna(0)
        df_db["ROWS"]    = pd.to_numeric(df_db.get("ROWS",0),    errors="coerce").fillna(0)
        df_db = df_db[["TABLE","SIZE_GB","ROWS"]]
        label = f"📤 {uploaded.name}"
    except Exception as e:
        st.sidebar.error(f"Parse error: {e}"); df_db = make_db()
else:
    df_db = make_db()
df_growth = make_growth()

# ── Hero header ──────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0A1628 0%,#1A2B5E 50%,#1A4480 100%);
     border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;
     box-shadow:0 8px 32px rgba(26,43,94,0.3);position:relative;overflow:hidden">
  <div style="position:absolute;top:-20px;right:-20px;width:200px;height:200px;
       background:rgba(232,160,32,0.08);border-radius:50%"></div>
  <div style="position:absolute;bottom:-40px;right:80px;width:120px;height:120px;
       background:rgba(46,134,193,0.1);border-radius:50%"></div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;position:relative">
    <div>
      <div style="font-size:0.7rem;color:#E8A020;font-weight:700;letter-spacing:0.15em;margin-bottom:0.4rem">
        CAPGEMINI · SAP DATA VOLUME MANAGEMENT</div>
      <h1 style="color:white;margin:0;font-size:1.7rem;font-weight:800;line-height:1.1">
        SAP Archival Intelligence</h1>
      <p style="color:#7BA7CC;margin:0.4rem 0 0;font-size:0.9rem">{client} &nbsp;·&nbsp; {system}</p>
    </div>
    <div style="text-align:right">
      <div style="color:#E8A020;font-size:0.65rem;font-weight:700;letter-spacing:0.1em">DATA SOURCE</div>
      <div style="color:white;font-size:0.8rem;font-weight:600">{label}</div>
      <div style="margin-top:0.5rem">
        {"<span style='background:rgba(34,197,94,0.2);color:#4ADE80;padding:0.15rem 0.5rem;border-radius:20px;font-size:0.65rem;font-weight:700;border:1px solid rgba(34,197,94,0.3)'>✅ OpenText</span> " if has_ot else ""}
        {"<span style='background:rgba(232,160,32,0.2);color:#E8A020;padding:0.15rem 0.5rem;border-radius:20px;font-size:0.65rem;font-weight:700;border:1px solid rgba(232,160,32,0.3)'>✅ ILM Active</span>" if has_ilm else ""}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ─────────────────────────────────────────────────────────────
t1,t2,t3,t4,t5,t6 = st.tabs([
    "📊  Executive Dashboard",
    "🎯  Archivability",
    "🏗️  Object Catalogue",
    "🤖  AI Assistant",
    "📋  Playbook",
    "ℹ️  Methodology",
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — Executive Dashboard
# ════════════════════════════════════════════════════════════════════
with t1:
    all_arch = [t for o in SAP_OBJECTS.values() for t in o["tables"]]
    total    = df_db["SIZE_GB"].sum()
    archivable = df_db[df_db["TABLE"].isin(all_arch)]["SIZE_GB"].sum()
    pct      = (archivable/total*100) if total else 0
    n        = len(df_growth)
    growth   = (df_growth["GB"].iloc[-1] - df_growth["GB"].iloc[0])/n if n>1 else 0
    savings  = archivable * 0.85  # estimated after archiving

    # KPI row
    kpis = [
        ("🗄️", f"{total:.0f} GB",    "Total DB Size",       "linear-gradient(135deg,#1A2B5E,#2E86C1)", None),
        ("📦", f"{archivable:.0f} GB","Archivable Data",     "linear-gradient(135deg,#E8A020,#F59E0B)", f"↓ {pct:.0f}% reduction potential"),
        ("📉", f"{savings:.0f} GB",  "Est. Size After",      "linear-gradient(135deg,#1A6B2E,#22C55E)", "Post archiving target"),
        ("📈", f"{growth:.0f} GB/mo","Monthly Growth",       "linear-gradient(135deg,#7C3AED,#A78BFA)", "Running 12-month avg"),
        ("🏆", f"{len(df_db)}",      "Tables Analysed",      "linear-gradient(135deg,#0369A1,#38BDF8)", "From DB02 export"),
    ]
    cols = st.columns(5)
    for col,(icon,val,lbl,grad,sub) in zip(cols,kpis):
        col.markdown(f"""
        <div class="kpi-card" style="--accent:{grad}">
          <div style="font-size:1.4rem;margin-bottom:0.3rem">{icon}</div>
          <div class="kpi-value">{val}</div>
          <div class="kpi-label">{lbl}</div>
          {f'<div class="kpi-delta up">{sub}</div>' if sub else ''}
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    cl,cr = st.columns([3,2])
    with cl:
        st.markdown("""<div class="section-hdr">
        <div class="section-icon">📊</div><h3>Top Tables by Size</h3></div>""", unsafe_allow_html=True)
        top15 = df_db.nlargest(15,"SIZE_GB")
        fig = go.Figure(go.Bar(
            x=top15["SIZE_GB"], y=top15["TABLE"], orientation="h",
            marker=dict(
                color=top15["SIZE_GB"],
                colorscale=[[0,"#BDD7EE"],[0.5,"#2E86C1"],[1,"#1A2B5E"]],
                showscale=False,
                line=dict(width=0),
            ),
            text=[f"{v:.1f}GB" for v in top15["SIZE_GB"]],
            textposition="outside", textfont=dict(size=10,color="#64748B"),
        ))
        fig.update_layout(
            height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=60,t=5,b=0), showlegend=False,
            xaxis=dict(showgrid=True,gridcolor="#F1F5F9",showline=False,zeroline=False),
            yaxis=dict(categoryorder="total ascending",showgrid=False,tickfont=dict(size=11)),
        )
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("""<div class="section-hdr">
        <div class="section-icon">📈</div><h3>DB Growth Trend</h3></div>""", unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_growth["Month"], y=df_growth["GB"], fill="tozeroy",
            line=dict(color="#2E86C1",width=2.5),
            fillcolor="rgba(46,134,193,0.12)",
            mode="lines+markers", marker=dict(size=5,color="#1A2B5E"),
        ))
        fig2.update_layout(
            height=175, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=0,t=0,b=0), showlegend=False,
            xaxis=dict(showgrid=False,tickfont=dict(size=9)),
            yaxis=dict(showgrid=True,gridcolor="#F1F5F9",tickfont=dict(size=9)),
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("""<div class="section-hdr" style="margin-top:0.8rem">
        <div class="section-icon">🍕</div><h3>By Module</h3></div>""", unsafe_allow_html=True)
        mods = {}
        for obj in SAP_OBJECTS.values():
            gb = df_db[df_db["TABLE"].isin(obj["tables"])]["SIZE_GB"].sum()
            if gb>0: mods[obj["module"]] = mods.get(obj["module"],0)+gb
        if mods:
            fig3 = go.Figure(go.Pie(
                values=list(mods.values()), labels=list(mods.keys()),
                hole=0.55, textinfo="label+percent",
                marker=dict(colors=px.colors.sequential.Blues_r[:len(mods)]),
                textfont=dict(size=10),
            ))
            fig3.update_layout(
                height=170, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0,r=0,t=0,b=0), showlegend=False,
            )
            st.plotly_chart(fig3, use_container_width=True)

    # Archivable opportunity table
    st.markdown("""<div class="section-hdr">
    <div class="section-icon">🎯</div><h3>Archiving Opportunity by Object</h3></div>""", unsafe_allow_html=True)
    opp = []
    for k,obj in SAP_OBJECTS.items():
        gb = df_db[df_db["TABLE"].isin(obj["tables"])]["SIZE_GB"].sum()
        sc,pr = score(k,gb)
        opp.append({"Archive Object":k,"Module":obj["module"],"Size (GB)":round(gb,1),
                    "Score":sc,"Priority":pr,"ILM":"✅" if obj["ilm"] else "—"})
    df_opp = pd.DataFrame(opp).sort_values("Score",ascending=False).reset_index(drop=True)
    df_opp["Priority"] = df_opp["Priority"].map({"HIGH":"🔴 HIGH","MEDIUM":"🟡 MEDIUM","LOW":"🟢 LOW"})
    st.dataframe(df_opp, use_container_width=True, height=250, hide_index=True)

# ════════════════════════════════════════════════════════════════════
# TAB 2 — Archivability
# ════════════════════════════════════════════════════════════════════
with t2:
    results = []
    for k,obj in SAP_OBJECTS.items():
        gb = df_db[df_db["TABLE"].isin(obj["tables"])]["SIZE_GB"].sum()
        sc,pr = score(k,gb)
        results.append({"key":k,"module":obj["module"],"desc":obj["desc"],"gb":gb,"sc":sc,"pr":pr,
                        "ilm":obj["ilm"],"ot":obj["ot"],"complexity":obj["complexity"]})
    df_r = pd.DataFrame(results).sort_values("sc",ascending=False)

    hi=(df_r["pr"]=="HIGH").sum(); me=(df_r["pr"]=="MEDIUM").sum(); lo=(df_r["pr"]=="LOW").sum()

    st.markdown("""<div class="section-hdr">
    <div class="section-icon">🎯</div><h3>Archivability Scoring & Priority Matrix</h3></div>""", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col,v,l,c in [(c1,hi,"HIGH Priority","#EF4444"),(c2,me,"MEDIUM Priority","#F59E0B"),
                       (c3,lo,"LOWER Priority","#22C55E"),(c4,(df_r["ilm"]==True).sum(),"ILM-Capable","#1A2B5E")]:
        col.markdown(f"""<div class="kpi-card"><div class="kpi-value" style="color:{c}">{v}</div>
        <div class="kpi-label">{l}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    cl,cr = st.columns([5,5])
    with cl:
        st.markdown("##### Score Distribution")
        fig = go.Figure()
        colors = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"}
        for pr in ["HIGH","MEDIUM","LOW"]:
            sub = df_r[df_r["pr"]==pr]
            fig.add_trace(go.Scatter(
                x=sub["gb"], y=sub["sc"], mode="markers+text",
                text=sub["key"], textposition="top center",
                textfont=dict(size=8), name=pr,
                marker=dict(size=sub["gb"].apply(lambda x: max(8,min(30,x/3))),
                            color=colors[pr], opacity=0.8,
                            line=dict(width=1,color="white")),
            ))
        fig.add_hline(y=70,line_dash="dot",line_color="#EF4444",opacity=0.5,annotation_text="HIGH threshold")
        fig.add_hline(y=45,line_dash="dot",line_color="#F59E0B",opacity=0.5,annotation_text="MEDIUM threshold")
        fig.update_layout(height=320,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=0,r=0,t=10,b=0),
                          xaxis=dict(title="Table Size (GB)",gridcolor="#F1F5F9"),
                          yaxis=dict(title="Archivability Score",gridcolor="#F1F5F9"),
                          legend=dict(orientation="h",yanchor="bottom",y=1.02))
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        st.markdown("##### Score Leaderboard")
        for _,row in df_r.iterrows():
            pr = row["pr"]; clr = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"}[pr]
            pct_w = row["sc"]
            st.markdown(f"""
            <div style="background:white;border-radius:8px;padding:0.6rem 0.8rem;margin-bottom:0.4rem;
                 border:1px solid #E8EDF5;border-left:4px solid {clr}">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem">
                <span style="font-weight:700;font-size:0.8rem;color:#1A2B5E">{row['key']}</span>
                <span style="font-size:0.7rem;font-weight:700;color:{clr}">{row['sc']}/100</span>
              </div>
              <div style="font-size:0.7rem;color:#94A3B8;margin-bottom:0.3rem">{row['desc']}</div>
              <div class="prog-bar-wrap"><div class="prog-bar" style="width:{pct_w}%;background:linear-gradient(90deg,{clr},{clr}88)"></div></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 📅 Recommended Wave Plan")
    cw1,cw2 = st.columns(2)
    with cw1:
        st.markdown("""<div style="background:linear-gradient(135deg,#FEF2F2,#FFF5F5);border:1px solid #FECACA;
        border-radius:10px;padding:0.8rem;margin-bottom:0.5rem">
        <div style="color:#991B1B;font-size:0.75rem;font-weight:700;letter-spacing:0.05em">🔴 WAVE 1 — HIGH PRIORITY</div>
        <div style="color:#6B7280;font-size:0.7rem;margin-top:0.2rem">Execute first — maximum DB impact</div></div>""",
        unsafe_allow_html=True)
        for _,row in df_r[df_r["pr"]=="HIGH"].iterrows():
            st.markdown(f"""<div style="background:white;border-radius:8px;padding:0.5rem 0.7rem;
            margin-bottom:0.3rem;border:1px solid #FEE2E2;display:flex;justify-content:space-between">
            <div><b style="font-size:0.8rem">{row['key']}</b><br>
            <span style="font-size:0.7rem;color:#94A3B8">{row['desc']}</span></div>
            <span style="font-weight:700;color:#EF4444;font-size:0.85rem">{row['gb']:.0f}GB</span>
            </div>""", unsafe_allow_html=True)
    with cw2:
        st.markdown("""<div style="background:linear-gradient(135deg,#FFFBEB,#FFFDF0);border:1px solid #FDE68A;
        border-radius:10px;padding:0.8rem;margin-bottom:0.5rem">
        <div style="color:#92400E;font-size:0.75rem;font-weight:700;letter-spacing:0.05em">🟡 WAVE 2 — MEDIUM PRIORITY</div>
        <div style="color:#6B7280;font-size:0.7rem;margin-top:0.2rem">Execute after Wave 1 stabilises</div></div>""",
        unsafe_allow_html=True)
        for _,row in df_r[df_r["pr"]=="MEDIUM"].iterrows():
            st.markdown(f"""<div style="background:white;border-radius:8px;padding:0.5rem 0.7rem;
            margin-bottom:0.3rem;border:1px solid #FDE68A;display:flex;justify-content:space-between">
            <div><b style="font-size:0.8rem">{row['key']}</b><br>
            <span style="font-size:0.7rem;color:#94A3B8">{row['desc']}</span></div>
            <span style="font-weight:700;color:#F59E0B;font-size:0.85rem">{row['gb']:.0f}GB</span>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 3 — Object Catalogue
# ════════════════════════════════════════════════════════════════════
with t3:
    st.markdown("""<div class="section-hdr">
    <div class="section-icon">🏗️</div><h3>SAP Archive Object Reference Catalogue</h3></div>""", unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    mod_f  = c1.multiselect("Module", sorted(set(o["module"] for o in SAP_OBJECTS.values())),
                             default=list(set(o["module"] for o in SAP_OBJECTS.values())))
    comp_f = c2.multiselect("Complexity", ["Low","Medium","High"], default=["Low","Medium","High"])

    for k,obj in SAP_OBJECTS.items():
        if obj["module"] not in mod_f or obj["complexity"] not in comp_f: continue
        gb = df_db[df_db["TABLE"].isin(obj["tables"])]["SIZE_GB"].sum()
        sc,pr = score(k,gb)
        clr = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"}[pr]
        icon = {"HIGH":"🔴","MEDIUM":"🟡","LOW":"🟢"}[pr]
        with st.expander(f"{icon} **{k}** — {obj['desc']}"):
            col1,col2,col3 = st.columns(3)
            with col1:
                st.markdown(f"""<div class="content-card">
                <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.5rem">CONFIGURATION</div>
                <div style="margin-bottom:0.3rem"><b>Retention:</b> {obj['retention']} years</div>
                <div style="margin-bottom:0.3rem"><b>Prereq:</b> {obj['prereq']}</div>
                <div><b>Verify:</b> <code>{obj['tcode']}</code></div>
                </div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class="content-card">
                <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.5rem">TECHNICAL</div>
                <div style="margin-bottom:0.3rem"><b>ILM:</b> {'✅ Capable' if obj['ilm'] else '❌ Not supported'}</div>
                <div style="margin-bottom:0.3rem"><b>OpenText:</b> {'✅ Compatible' if obj['ot'] else '❌ N/A'}</div>
                <div><b>Tables:</b> <code>{'` `'.join(obj['tables'][:3])}</code></div>
                </div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class="content-card">
                <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.5rem">SCORING</div>
                <div style="font-size:1.5rem;font-weight:800;color:{clr}">{sc}<span style="font-size:0.8rem;color:#94A3B8">/100</span></div>
                <div class="prog-bar-wrap"><div class="prog-bar" style="width:{sc}%;background:linear-gradient(90deg,{clr},{clr}88)"></div></div>
                <div style="margin-top:0.4rem;font-size:0.75rem;color:#64748B">{obj['complexity']} complexity · {obj['impact']} impact</div>
                </div>""", unsafe_allow_html=True)
            st.markdown(f"**Notes:** {obj['notes']}")
            if has_ot and obj["ot"]:
                if obj["ilm"] and has_ilm:
                    st.markdown("""<div class="ot-box"><h4>🔗 ILM + OpenText Path</h4>
                    <p>ILM-ADK files with retention metadata → OpenText via WebDAV/ILM 3.1. Retention enforced by OpenText. Legal hold supported.</p></div>""", unsafe_allow_html=True)
                else:
                    st.markdown("""<div class="ot-box"><h4>🔗 OpenText via ArchiveLink</h4>
                    <p>ADK files → OpenText via SAP ArchiveLink. No infrastructure change. Enable ILM later — files convertible with SAP ILM File Converter, no data loss.</p></div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 4 — AI Assistant
# ════════════════════════════════════════════════════════════════════
with t4:
    st.markdown("""<div class="section-hdr">
    <div class="section-icon">🤖</div><h3>SAP Archiving AI Assistant — Powered by Claude</h3></div>""", unsafe_allow_html=True)

    SYS = f"""You are a senior SAP Data Volume Management and ILM consultant at Capgemini with 15+ years experience.
CLIENT: {client} | SYSTEM: {system} | OpenText: {'Yes' if has_ot else 'No'} | ILM: {'Licensed' if has_ilm else 'Not licensed'}
Be specific, technical and actionable. Reference exact SAP tcodes, table names, config steps.
Think like a senior consultant in a blueprint workshop. Format clearly with sections."""

    if "history" not in st.session_state:
        st.session_state.history = []

    # Suggestion chips
    suggestions = [
        "What are the prerequisites for FI_DOCUMNT and residence time to set?",
        "How does OpenText integrate with SAP ILM via WebDAV/ILM 3.1?",
        "Which objects give biggest DB reduction with lowest risk?",
        "Difference between ADK and ILM-ADK files — can I convert?",
        "How do I configure legal hold in SAP ILM?",
        "How to prepare ECC archiving for S/4HANA migration?",
        "Walk me through MM_MATBEL archiving in SARA step by step",
        "What does TAANA show and how do I use it?",
    ]
    cols = st.columns(4)
    for i,q in enumerate(suggestions):
        if cols[i%4].button(q, key=f"s{i}"):
            st.session_state.pending = q

    st.markdown("<br>", unsafe_allow_html=True)

    # Chat window
    chat_html = '<div class="chat-wrap">'
    if not st.session_state.history:
        chat_html += """<div style="text-align:center;padding:2rem;color:#94A3B8">
        <div style="font-size:2rem;margin-bottom:0.5rem">🤖</div>
        <div style="font-weight:600;color:#64748B">SAP Archiving AI Assistant</div>
        <div style="font-size:0.8rem;margin-top:0.3rem">Ask any question about SAP data archiving, ILM, OpenText integration, or S/4HANA readiness</div>
        </div>"""
    for msg in st.session_state.history:
        if msg["role"]=="user":
            chat_html += f'<div class="chat-user"><div class="role">YOU</div><p>{msg["content"]}</p></div>'
        else:
            txt = msg["content"].replace("\n","<br>")
            chat_html += f'<div class="chat-ai"><div class="role">🤖 SAP AI ASSISTANT</div><p>{txt}</p></div>'
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    c1,c2 = st.columns([5,1])
    user_q = c1.chat_input("Ask your SAP archiving question...")
    if "pending" in st.session_state:
        user_q = st.session_state.pending
        del st.session_state.pending

    if user_q:
        st.session_state.history.append({"role":"user","content":user_q})
        msgs = [{"role":m["role"],"content":m["content"]} for m in st.session_state.history]
        with st.spinner("Consulting SAP knowledge base..."):
            try:
                key = st.secrets.get("ANTHROPIC_API_KEY","")
                if not key:
                    ans = "⚠️ No API key. Add ANTHROPIC_API_KEY to Streamlit secrets."
                else:
                    r = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},
                        json={"model":"claude-sonnet-4-20250514","max_tokens":1000,"system":SYS,"messages":msgs},
                        timeout=30)
                    ans = r.json()["content"][0]["text"] if r.status_code==200 else f"⚠️ API error {r.status_code}"
            except Exception as e:
                ans = f"⚠️ Error: {e}"
        st.session_state.history.append({"role":"assistant","content":ans})
        st.rerun()

    if st.button("🗑️ Clear conversation"):
        st.session_state.history = []; st.rerun()

# ════════════════════════════════════════════════════════════════════
# TAB 5 — Playbook
# ════════════════════════════════════════════════════════════════════
with t5:
    st.markdown("""<div class="section-hdr">
    <div class="section-icon">📋</div><h3>Archiving Remediation Playbook</h3></div>""", unsafe_allow_html=True)

    sel = st.selectbox("Select Archive Object", list(SAP_OBJECTS.keys()),
                        format_func=lambda k: f"{k} — {SAP_OBJECTS[k]['desc']}")
    obj = SAP_OBJECTS[sel]
    gb  = df_db[df_db["TABLE"].isin(obj["tables"])]["SIZE_GB"].sum()
    sc,pr = score(sel,gb)
    clr = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#22C55E"}[pr]

    # Object summary card
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0A1628,#1A2B5E);border-radius:12px;padding:1.2rem 1.5rem;
         border:1px solid rgba(232,160,32,0.3);margin-bottom:1rem">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="color:#E8A020;font-size:0.7rem;font-weight:700;letter-spacing:0.1em">{obj['module']} MODULE</div>
          <div style="color:white;font-size:1.2rem;font-weight:800;margin:0.2rem 0">{sel}</div>
          <div style="color:#7BA7CC;font-size:0.85rem">{obj['desc']}</div>
          <div style="margin-top:0.5rem;font-size:0.75rem;color:#94B4D4">
            📅 Retention: {obj['retention']} yrs &nbsp;·&nbsp; ⚙️ {obj['complexity']} complexity &nbsp;·&nbsp;
            {'✅ ILM capable' if obj['ilm'] else '❌ ILM not supported'} &nbsp;·&nbsp;
            {'✅ OpenText' if obj['ot'] else '❌ No OpenText'}
          </div>
        </div>
        <div style="text-align:center;background:rgba(255,255,255,0.05);border-radius:10px;padding:0.8rem 1.2rem">
          <div style="color:{clr};font-size:2rem;font-weight:800">{sc}</div>
          <div style="color:white;font-size:0.7rem;font-weight:700">/100</div>
          <div style="color:{clr};font-size:0.65rem;font-weight:700;margin-top:0.2rem">{pr}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"⚠️ **Prerequisite:** {obj['prereq']}  |  🔍 **Verify in:** `{obj['tcode']}`")
    st.markdown("---")

    steps = [
        ("Verify Prerequisites", f"Check status in `{obj['tcode']}`. Confirm: **{obj['prereq']}`. Run residence time check in `SARA` → Object: `{sel}`. Ensure all dependent processes are closed."),
        ("Configure in SARA", f"Transaction `SARA` → enter `{sel}`. Set residence time: **{obj['retention']} years**. Configure Write variant. Check file path in `FILE` transaction. {'Configure ILM retention category (`IRMPSCAT`).' if obj['ilm'] and has_ilm else 'Configure content repository (`OAC0`, `OAC3`).' if has_ot else 'Configure archive file path.'}"),
        ("Run Preprocessing / Check", f"SARA → **Preprocessing** or **Check**. Review log — resolve all errors. Tables in scope: `{'`, `'.join(obj['tables'])}`. Document baseline row counts."),
        ("Execute Write Program (DEV first)", f"SARA → **Write** → run **test mode first**. Review test log. Execute production Write in DEV. Files → {'OpenText via ' + ('ILM 3.1 WebDAV (ILM-ADK)' if has_ilm else 'SAP ArchiveLink (ADK)') if has_ot else 'local file path'}."),
        ("Run Delete Program", f"SARA → **Delete** — only after successful Write. Verify records removed from primary tables. Spot-check in `{obj['tcode']}`. **Never run Delete if Write log has errors.**"),
        ("Verify Retrieval — UAT", f"Test retrieval in `{obj['tcode']}`. Confirm archived docs display via ArchiveLink viewer. {'Test ILM Workbench (`IRMPOL`) for retention.' if has_ilm else 'Verify ArchiveLink connection (`OACT`).'} Document retrieval times."),
        ("Transport QA → Production", f"Transport SARA config via `SE01` / `STMS`. Re-run full cycle in QA. Business sign-off required. Schedule regular jobs via `SM36` / `SM37`."),
    ]
    for i,(title,body) in enumerate(steps,1):
        with st.expander(f"Step {i} — {title}"):
            st.markdown(body)

    if has_ot and obj["ot"]:
        if obj["ilm"] and has_ilm:
            st.markdown("""<div class="ot-box"><h4>🔗 ILM + OpenText Integration</h4>
            <p>ILM-ADK files with embedded retention metadata → OpenText via WebDAV/ILM 3.1.
            Retention enforced natively. Legal hold and defensible deletion supported.</p></div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="ot-box"><h4>🔗 OpenText via ArchiveLink</h4>
            <p>ADK files → OpenText via SAP ArchiveLink. No hardware change. Activate ILM later —
            existing files convertible with SAP ILM File Converter, zero data loss.</p></div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 6 — Methodology
# ════════════════════════════════════════════════════════════════════
with t6:
    st.markdown("""<div class="section-hdr">
    <div class="section-icon">ℹ️</div><h3>Methodology & Integration Architecture</h3></div>""", unsafe_allow_html=True)

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("""<div class="content-card">
        <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.8rem">📐 ENGAGEMENT METHODOLOGY</div>
        <b>Phase 1 — Analysis & Strategy (8 weeks)</b><br>
        <ol style="margin:0.5rem 0;padding-left:1.2rem;font-size:0.85rem;color:#374151;line-height:1.8">
        <li>Import DB02 export → baseline the opportunity</li>
        <li>AI-driven archivability scoring against your landscape</li>
        <li>Per-object prerequisite & readiness mapping</li>
        <li>Wave-sequenced archiving roadmap</li>
        </ol>
        <b>Phase 2 — Execution (26 weeks)</b><br>
        <ul style="margin:0.5rem 0;padding-left:1.2rem;font-size:0.85rem;color:#374151;line-height:1.8">
        <li>ILM configuration (if licensed)</li>
        <li>Archive object config DEV → QA → PRD</li>
        <li>Testing, UAT, cutover, hypercare</li>
        </ul>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="content-card" style="margin-top:0.8rem">
        <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.8rem">📥 HOW TO EXPORT FROM SAP</div>
        <b>DB02 / DBACOCKPIT</b><br>
        <code style="font-size:0.75rem">Space → Tables/Indexes → Sort by Size → Export CSV</code><br>
        <code style="font-size:0.75rem">Columns: TABLE_NAME, SIZE_GB, ROWS</code><br><br>
        <b>TAANA — Table Analysis</b><br>
        <code style="font-size:0.75rem">Run analysis → Export → TABLE_NAME, SIZE_MB, ROWS</code><br><br>
        <b>SE16 / SE16N</b><br>
        <code style="font-size:0.75rem">Table: DBSTATC (Oracle) or M_TABLE_USED_MEMORY_VIEW (HANA)</code>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""<div class="content-card">
        <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.8rem">🏗️ STORAGE ARCHITECTURE</div>
        <div style="font-family:monospace;font-size:0.78rem;line-height:2;background:#F8FAFC;padding:0.8rem;border-radius:8px;border:1px solid #E8EDF5">
        SAP ECC (SARA)<br>
        &nbsp;&nbsp;↓ ADK / ILM-ADK generation<br>
        &nbsp;&nbsp;↓ {'WebDAV / ILM 3.1' if has_ilm else 'SAP ArchiveLink'}<br>
        &nbsp;&nbsp;↓ OpenText Archive Center<br>
        &nbsp;&nbsp;↓ Archive Storage → NAS<br>
        {'<br>&nbsp;&nbsp;── Future ILM Path ──<br>&nbsp;&nbsp;↓ SAP ILM File Converter<br>&nbsp;&nbsp;↓ ILM Retention Warehouse<br>&nbsp;&nbsp;↓ GDPR + Legal Hold' if not has_ilm else ''}
        </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="content-card" style="margin-top:0.8rem">
        <div style="font-size:0.65rem;color:#94A3B8;font-weight:700;letter-spacing:0.05em;margin-bottom:0.8rem">🔑 KEY SAP TRANSACTIONS</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;font-size:0.78rem">""" +
        "".join([f'<div><code style="background:#EEF2FF;padding:0.1rem 0.3rem;border-radius:4px;color:#1A2B5E;font-weight:600">{tc}</code> {desc}</div>'
                 for tc,desc in [("SARA","Archive Admin"),("AS","Archive Info"),("TAANA","Table Analysis"),
                                  ("DB02","DB Monitor"),("OAC0","Content Repos"),("OACT","Test ArchiveLink"),
                                  ("OAC3","Link Objects"),("FILE","File Paths"),("IRMPOL","ILM Policies"),
                                  ("SFW5","Switch Framework"),("SM36","Job Schedule"),("SE01","Transports")]]) +
        """</div></div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:linear-gradient(135deg,#0A1628,#1A2B5E);border-radius:10px;
    padding:0.8rem 1.2rem;text-align:center;margin-top:1rem;border:1px solid rgba(232,160,32,0.2)">
    <p style="margin:0;font-size:0.75rem;color:#7BA7CC">
    🔒 <b style="color:#E8A020">Confidential</b> — Capgemini Internal Use Only &nbsp;·&nbsp;
    SAP Data Volume Management &nbsp;·&nbsp; AI powered by Claude (Anthropic)
    </p></div>""", unsafe_allow_html=True)
