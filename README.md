# SAP Archiving Assistant — Prototype

An AI-powered Streamlit prototype that scans simulated SAP ECC tables for
archiving candidates, surfaces data-quality risks, and produces actionable
cleanup recommendations.

> **Prototype only.** All data is synthetic. The app does not connect to a real
> SAP system and requires no credentials.

## Features

- **Synthetic SAP ECC-style datasets** for canonical archiving objects:
  `FI_DOCUMNT`, `MM_EKKO`, `SD_VBAK`, `MM_MATBEL`, `BC_SBAL`, `CO_ITEM`, `PP_ORDER`.
- **Archivability rules engine** covering residence time, object status,
  workflow completion, recent activity, legal hold, dependencies, and data
  quality. Each rule contributes a transparent weight to a 0-100 score.
- **ML-style anomaly detection** via `sklearn.IsolationForest` when available,
  with a graceful heuristic fallback (z-score blend) when scikit-learn is not
  installed.
- **Recommendation engine** assigning each record to one of:
  `ARCHIVE`, `REVIEW`, `REMEDIATE`, `DEDUPLICATE`, or `RETAIN`, with a priority
  score that blends archivability, footprint, and anomaly signal.
- **Enterprise dashboard UI** with KPI cards, executive summary, multi-facet
  filters, charts (Plotly preferred, Streamlit-native fallback), per-object
  inventory, priority worklist, and object drilldown with rule-by-rule breakdown.
- **Exports**: filtered records CSV, archive worklist CSV, executive report
  Markdown.

## Project layout

```
sap-archiving-assistant/
├── app.py                # Streamlit entry point
├── archivability.py      # Rules engine + IsolationForest scoring
├── data_generator.py     # Synthetic SAP ECC-style data
├── reporting.py          # Markdown executive report builder
├── requirements.txt
├── README.md
└── site/
    └── index.html        # Static launcher page
```

## Run locally (port 8501)

```bash
cd sap-archiving-assistant
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Then open <http://localhost:8501>.

## Notes on resilience

- If `scikit-learn` is unavailable, anomaly scoring falls back to a deterministic
  z-score heuristic — the rest of the app continues to function unchanged.
- If `plotly` is unavailable, charts fall back to Streamlit's built-in
  `bar_chart` / `scatter_chart` primitives.
- All filters, KPIs, and exports respect the active sidebar filter set so
  reports always match what the user sees.

## Disclaimer

This is a demonstration prototype. Archiving decisions in a production SAP
landscape must follow your organisation's retention, legal, and audit policies
and be validated against `SARA`/`DB02`/relevant ILM tooling before execution.
