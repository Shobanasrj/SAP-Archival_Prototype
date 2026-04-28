"""
Synthetic SAP ECC-style dataset generator.

Produces realistic-looking master data and document tables resembling common
SAP archiving objects (FI_DOCUMNT, MM_EKKO, SD_VBAK, MM_MATBEL, BC_SBAL).

All data is fully synthetic. No external connection required.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd

# Canonical SAP archiving objects we simulate
ARCHIVING_OBJECTS = [
    {
        "object": "FI_DOCUMNT",
        "module": "FI",
        "description": "Financial Accounting Documents",
        "table": "BKPF/BSEG",
        "min_residence_months": 24,
    },
    {
        "object": "MM_EKKO",
        "module": "MM",
        "description": "Purchasing Documents",
        "table": "EKKO/EKPO",
        "min_residence_months": 18,
    },
    {
        "object": "SD_VBAK",
        "module": "SD",
        "description": "Sales Documents",
        "table": "VBAK/VBAP",
        "min_residence_months": 18,
    },
    {
        "object": "MM_MATBEL",
        "module": "MM",
        "description": "Material Documents",
        "table": "MKPF/MSEG",
        "min_residence_months": 12,
    },
    {
        "object": "BC_SBAL",
        "module": "BC",
        "description": "Application Log",
        "table": "BALHDR/BALDAT",
        "min_residence_months": 6,
    },
    {
        "object": "CO_ITEM",
        "module": "CO",
        "description": "Controlling Line Items",
        "table": "COEP",
        "min_residence_months": 24,
    },
    {
        "object": "PP_ORDER",
        "module": "PP",
        "description": "Production Orders",
        "table": "AUFK/AFKO",
        "min_residence_months": 18,
    },
]

COMPANY_CODES = ["1000", "2000", "3000", "4500", "5500"]
PLANTS = ["P100", "P200", "P300", "P400"]
USERS = [f"USR{str(i).zfill(3)}" for i in range(1, 21)]
STATUSES = ["COMPLETED", "OPEN", "BLOCKED", "ARCHIVED_CANDIDATE", "ERROR", "IN_PROCESS"]
STATUS_WEIGHTS = [0.55, 0.15, 0.05, 0.10, 0.05, 0.10]


def _seeded_rng(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)


def generate_objects(seed: int = 42, n_per_object: int = 350) -> pd.DataFrame:
    """Generate a unified inventory of SAP business documents/objects."""
    _seeded_rng(seed)
    today = datetime.utcnow().date()
    rows = []
    obj_counter = 0
    for cfg in ARCHIVING_OBJECTS:
        n = n_per_object + random.randint(-50, 100)
        for _ in range(n):
            obj_counter += 1
            # Created between 6 months and 12 years ago, skewed older
            age_days = int(np.random.gamma(shape=2.5, scale=600))
            age_days = max(30, min(age_days, 365 * 12))
            created = today - timedelta(days=age_days)

            # Last activity: usually shortly after creation, sometimes recent
            if random.random() < 0.25:
                last_activity = today - timedelta(days=random.randint(0, 180))
            else:
                last_activity = created + timedelta(
                    days=random.randint(0, max(1, min(age_days, 540)))
                )
            last_activity = min(last_activity, today)

            status = np.random.choice(STATUSES, p=STATUS_WEIGHTS)

            workflow_completion = float(np.clip(np.random.beta(5, 1.5), 0, 1))
            if status in ("OPEN", "IN_PROCESS"):
                workflow_completion = float(np.clip(np.random.beta(2, 3), 0, 1))
            elif status == "ERROR":
                workflow_completion = float(np.clip(np.random.beta(1.5, 4), 0, 1))
            elif status == "COMPLETED":
                workflow_completion = float(np.clip(np.random.beta(20, 1), 0.85, 1))

            legal_hold = random.random() < 0.04
            has_open_dependencies = random.random() < 0.12
            duplicate_flag = random.random() < 0.06
            inconsistency_flag = random.random() < 0.05
            data_quality_score = float(
                np.clip(np.random.normal(0.85, 0.12), 0.1, 1.0)
            )
            if duplicate_flag or inconsistency_flag:
                data_quality_score *= 0.6

            size_mb = float(np.clip(np.random.lognormal(mean=1.0, sigma=0.9), 0.05, 250))
            line_items = int(np.clip(np.random.lognormal(mean=2.5, sigma=1.0), 1, 5000))

            doc_id = f"{cfg['object'][:3]}-{obj_counter:07d}"
            rows.append(
                {
                    "object_id": doc_id,
                    "archiving_object": cfg["object"],
                    "module": cfg["module"],
                    "table": cfg["table"],
                    "company_code": random.choice(COMPANY_CODES),
                    "plant": random.choice(PLANTS) if cfg["module"] in ("MM", "PP") else "",
                    "created_by": random.choice(USERS),
                    "created_on": pd.Timestamp(created),
                    "last_activity_on": pd.Timestamp(last_activity),
                    "age_days": (today - created).days,
                    "days_since_activity": (today - last_activity).days,
                    "status": status,
                    "workflow_completion": round(workflow_completion, 3),
                    "legal_hold": legal_hold,
                    "has_open_dependencies": has_open_dependencies,
                    "duplicate_flag": duplicate_flag,
                    "inconsistency_flag": inconsistency_flag,
                    "data_quality_score": round(data_quality_score, 3),
                    "size_mb": round(size_mb, 3),
                    "line_items": line_items,
                    "min_residence_months": cfg["min_residence_months"],
                    "description": cfg["description"],
                }
            )
    df = pd.DataFrame(rows)
    df["residence_months"] = (df["age_days"] / 30.4375).round(1)
    df["meets_residence"] = df["residence_months"] >= df["min_residence_months"]
    return df


def summary_by_object(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["archiving_object", "module", "description"], as_index=False).agg(
        records=("object_id", "count"),
        total_size_mb=("size_mb", "sum"),
        avg_age_days=("age_days", "mean"),
        legal_holds=("legal_hold", "sum"),
        duplicates=("duplicate_flag", "sum"),
        inconsistencies=("inconsistency_flag", "sum"),
    )
    g["total_size_gb"] = (g["total_size_mb"] / 1024).round(2)
    g["avg_age_years"] = (g["avg_age_days"] / 365).round(1)
    return g.sort_values("records", ascending=False)
