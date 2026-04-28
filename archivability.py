"""
Archivability rules engine + lightweight ML anomaly scoring.

Implements a deterministic, auditable rule set for whether a record is a good
archiving candidate, plus an anomaly score (IsolationForest if scikit-learn is
available, otherwise a heuristic z-score blend).
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

try:  # Optional ML dependency
    from sklearn.ensemble import IsolationForest

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover
    SKLEARN_AVAILABLE = False


# Weighted rule contributions to archivability score (0-100)
RULE_WEIGHTS: Dict[str, float] = {
    "residence_met": 25.0,
    "status_terminal": 20.0,
    "workflow_complete": 15.0,
    "no_recent_activity": 15.0,
    "no_legal_hold": 10.0,  # actually a hard gate, but contributes when passed
    "no_open_dependencies": 8.0,
    "data_quality_ok": 7.0,
}


def _rule_residence(row) -> bool:
    return bool(row["residence_months"] >= row["min_residence_months"])


def _rule_status_terminal(row) -> bool:
    return row["status"] in ("COMPLETED", "ARCHIVED_CANDIDATE")


def _rule_workflow_complete(row) -> bool:
    return float(row["workflow_completion"]) >= 0.95


def _rule_no_recent_activity(row) -> bool:
    return int(row["days_since_activity"]) >= 365


def _rule_no_legal_hold(row) -> bool:
    return not bool(row["legal_hold"])


def _rule_no_open_deps(row) -> bool:
    return not bool(row["has_open_dependencies"])


def _rule_data_quality_ok(row) -> bool:
    return float(row["data_quality_score"]) >= 0.7


RULES = [
    ("residence_met", _rule_residence, "Meets minimum residence time"),
    ("status_terminal", _rule_status_terminal, "Status is terminal (Completed)"),
    ("workflow_complete", _rule_workflow_complete, "Workflow ≥95% complete"),
    ("no_recent_activity", _rule_no_recent_activity, "No activity in last 12 months"),
    ("no_legal_hold", _rule_no_legal_hold, "Not on legal hold"),
    ("no_open_dependencies", _rule_no_open_deps, "No open downstream dependencies"),
    ("data_quality_ok", _rule_data_quality_ok, "Data quality acceptable"),
]


def evaluate_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all archivability rules and compute a 0-100 score."""
    df = df.copy()
    score = np.zeros(len(df), dtype=float)
    failed_lists: List[List[str]] = [[] for _ in range(len(df))]

    for key, fn, label in RULES:
        passes = df.apply(fn, axis=1).to_numpy()
        df[f"rule_{key}"] = passes
        score = score + passes.astype(float) * RULE_WEIGHTS[key]
        for i, ok in enumerate(passes):
            if not ok:
                failed_lists[i].append(label)

    df["archivability_score"] = score.round(1)
    df["failed_rules"] = ["; ".join(x) if x else "—" for x in failed_lists]

    # Hard gates: legal hold or open dependencies => not archivable now
    blocked = df["legal_hold"] | df["has_open_dependencies"]
    df["blocked"] = blocked

    return df


def compute_anomaly_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add anomaly_score (0-1, higher = more anomalous) for QA flagging."""
    df = df.copy()
    feature_cols = [
        "age_days",
        "days_since_activity",
        "workflow_completion",
        "data_quality_score",
        "size_mb",
        "line_items",
    ]
    X = df[feature_cols].to_numpy(dtype=float)

    if SKLEARN_AVAILABLE and len(df) >= 50:
        model = IsolationForest(
            n_estimators=100,
            contamination=0.08,
            random_state=42,
        )
        model.fit(X)
        # decision_function: higher = more normal; invert and scale to 0-1
        raw = -model.decision_function(X)
        anomaly = (raw - raw.min()) / (raw.max() - raw.min() + 1e-9)
        df["anomaly_method"] = "IsolationForest"
    else:
        # Heuristic fallback: blend of z-scores on key risk features
        z_parts = []
        for col, sign in [
            ("workflow_completion", -1),
            ("data_quality_score", -1),
            ("size_mb", +1),
            ("days_since_activity", -1),
        ]:
            x = df[col].to_numpy(dtype=float)
            mu, sd = np.mean(x), np.std(x) + 1e-9
            z_parts.append(sign * (x - mu) / sd)
        z = np.sum(z_parts, axis=0)
        anomaly = (z - z.min()) / (z.max() - z.min() + 1e-9)
        df["anomaly_method"] = "Heuristic (no sklearn)"

    df["anomaly_score"] = np.round(anomaly, 3)
    return df


def assign_recommendation(df: pd.DataFrame) -> pd.DataFrame:
    """Bucket each row into a recommended action."""
    df = df.copy()

    def _rec(row) -> Tuple[str, str]:
        if row["legal_hold"]:
            return "RETAIN", "Subject to legal hold — exclude from archiving."
        if row["has_open_dependencies"]:
            return "REVIEW", "Open downstream dependencies — investigate before archive."
        if row["duplicate_flag"]:
            return "DEDUPLICATE", "Duplicate detected — consolidate before archive."
        if row["inconsistency_flag"] or row["data_quality_score"] < 0.55:
            return "REMEDIATE", "Data quality issue — remediate, then re-evaluate."
        if row["archivability_score"] >= 80 and row["meets_residence"]:
            return "ARCHIVE", "High-confidence archive candidate — schedule archive run."
        if row["archivability_score"] >= 60:
            return "REVIEW", "Borderline candidate — schedule for manual review."
        if not row["meets_residence"]:
            return "RETAIN", "Below minimum residence time — retain online."
        return "RETAIN", "Active or low archivability — retain online."

    recs = df.apply(_rec, axis=1)
    df["recommendation"] = [r[0] for r in recs]
    df["rationale"] = [r[1] for r in recs]

    # Priority: combine archivability, size, anomaly
    norm_size = (df["size_mb"] - df["size_mb"].min()) / (
        df["size_mb"].max() - df["size_mb"].min() + 1e-9
    )
    priority = (
        0.55 * (df["archivability_score"] / 100.0)
        + 0.30 * norm_size
        + 0.15 * df["anomaly_score"]
    )
    # Penalize blocked records
    priority = np.where(df["blocked"], priority * 0.2, priority)
    df["priority_score"] = (priority * 100).round(1)

    return df


def detect_data_issues(df: pd.DataFrame) -> Dict[str, int]:
    """Cross-table style scan for issues."""
    return {
        "duplicates": int(df["duplicate_flag"].sum()),
        "inconsistencies": int(df["inconsistency_flag"].sum()),
        "incomplete_workflows": int((df["workflow_completion"] < 0.95).sum()),
        "stale_open": int(((df["status"] == "OPEN") & (df["days_since_activity"] > 365)).sum()),
        "errors": int((df["status"] == "ERROR").sum()),
        "legal_holds": int(df["legal_hold"].sum()),
    }


def run_full_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    df = evaluate_rules(df)
    df = compute_anomaly_score(df)
    df = assign_recommendation(df)
    return df
