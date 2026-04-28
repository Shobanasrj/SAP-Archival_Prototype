"""Markdown report generation for the archiving assistant."""
from __future__ import annotations

from datetime import datetime
from typing import Dict

import pandas as pd


def build_markdown_report(
    df: pd.DataFrame,
    issues: Dict[str, int],
    summary_df: pd.DataFrame,
) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    total = len(df)
    archive = int((df["recommendation"] == "ARCHIVE").sum())
    review = int((df["recommendation"] == "REVIEW").sum())
    retain = int((df["recommendation"] == "RETAIN").sum())
    remediate = int((df["recommendation"] == "REMEDIATE").sum())
    dedupe = int((df["recommendation"] == "DEDUPLICATE").sum())

    archive_size_gb = round(
        df.loc[df["recommendation"] == "ARCHIVE", "size_mb"].sum() / 1024, 2
    )
    total_size_gb = round(df["size_mb"].sum() / 1024, 2)
    pct_archivable = round(100.0 * archive / max(total, 1), 1)

    method = df["anomaly_method"].iloc[0] if len(df) else "n/a"

    top10 = (
        df.sort_values("priority_score", ascending=False)
        .head(10)[
            [
                "object_id",
                "archiving_object",
                "module",
                "status",
                "archivability_score",
                "priority_score",
                "size_mb",
                "recommendation",
                "rationale",
            ]
        ]
        .to_dict(orient="records")
    )

    lines = []
    lines.append("# SAP Archiving Assistant — Executive Report")
    lines.append("")
    lines.append(f"_Generated {now}_")
    lines.append("")
    lines.append("## Executive summary")
    lines.append("")
    lines.append(
        f"Across **{total:,} business records** spanning **{total_size_gb:,} GB**, the assistant "
        f"identified **{archive:,} ({pct_archivable}%)** as high-confidence archive candidates, "
        f"reclaiming up to **{archive_size_gb:,} GB** of online storage. "
        f"A further {review:,} records require review and {remediate + dedupe:,} require data "
        "remediation before archiving."
    )
    lines.append("")
    lines.append(f"Anomaly scoring method: **{method}**.")
    lines.append("")

    lines.append("## Recommendation breakdown")
    lines.append("")
    lines.append("| Action | Records | % of total |")
    lines.append("| --- | ---: | ---: |")
    for label, count in [
        ("ARCHIVE", archive),
        ("REVIEW", review),
        ("REMEDIATE", remediate),
        ("DEDUPLICATE", dedupe),
        ("RETAIN", retain),
    ]:
        pct = round(100.0 * count / max(total, 1), 1)
        lines.append(f"| {label} | {count:,} | {pct}% |")
    lines.append("")

    lines.append("## Data quality findings")
    lines.append("")
    lines.append("| Finding | Count |")
    lines.append("| --- | ---: |")
    for k, v in issues.items():
        lines.append(f"| {k.replace('_', ' ').title()} | {v:,} |")
    lines.append("")

    lines.append("## Per-object inventory")
    lines.append("")
    lines.append("| Object | Module | Records | Size (GB) | Avg age (yrs) |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for _, r in summary_df.iterrows():
        lines.append(
            f"| {r['archiving_object']} | {r['module']} | {int(r['records']):,} | "
            f"{r['total_size_gb']:,} | {r['avg_age_years']} |"
        )
    lines.append("")

    lines.append("## Top 10 priority candidates")
    lines.append("")
    lines.append("| Object ID | Archiving Object | Status | Score | Priority | Size (MB) | Action | Rationale |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | --- | --- |")
    for r in top10:
        lines.append(
            f"| {r['object_id']} | {r['archiving_object']} | {r['status']} | "
            f"{r['archivability_score']} | {r['priority_score']} | {round(r['size_mb'], 1)} | "
            f"{r['recommendation']} | {r['rationale']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_This is a prototype. All data is synthetic. No connection to a live SAP "
        "system is required or established._"
    )
    return "\n".join(lines)
