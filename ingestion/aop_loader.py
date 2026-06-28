"""
aop_loader.py
-------------
Reads all sheets from the AOP Targets workbook and returns them
as a dictionary of cleaned DataFrames.
"""

import pandas as pd
from config import INPUT_FILES


def load_aop_targets():
    """
    Load all AOP target sheets and return a structured dictionary.

    Returns
    -------
    targets : dict with keys:
        "summary"      – monthly summary targets (Booking, Collections, CoC, NCF, etc.)
        "sales"        – project-wise monthly sales targets with product mix
        "collections"  – milestone-linked collection targets per project/tower
        "construction" – construction CoC targets per project/tower/milestone
        "ncf"          – monthly NCF breakdown per project
        "decisions"    – pre-defined leadership decision items
    quality_issues : list[dict]
    """
    filepath = INPUT_FILES["aop"]
    xls = pd.ExcelFile(filepath)

    quality_issues = []
    targets = {}

    # ── Summary Targets ──────────────────────────────────────────────────
    df = pd.read_excel(xls, sheet_name="Summary Targets", header=1)
    df.columns = df.columns.str.strip()
    targets["summary"] = df

    # ── Sales Targets ────────────────────────────────────────────────────
    df = pd.read_excel(xls, sheet_name="Sales Targets", header=1)
    df.columns = df.columns.str.strip()
    # Ensure Month is datetime
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    targets["sales"] = df

    # ── Collections Targets ──────────────────────────────────────────────
    df = pd.read_excel(xls, sheet_name="Collections Targets", header=1)
    df.columns = df.columns.str.strip()
    date_cols = ["Milestone Target Date", "Expected Collection Deadline", "Month"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    # Ensure numeric fields
    for col in ["Demand Trigger %", "Expected Demand Value"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    targets["collections"] = df

    # ── Construction / CoC Targets ───────────────────────────────────────
    df = pd.read_excel(xls, sheet_name="Construction CoC Targets", header=1)
    df.columns = df.columns.str.strip()
    date_cols = ["Month", "Planned Start Date", "Planned Finish Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["Planned Progress %", "Planned CoC"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    targets["construction"] = df

    # ── NCF Details Target ───────────────────────────────────────────────
    df = pd.read_excel(xls, sheet_name="NCF Details Target", header=1)
    df.columns = df.columns.str.strip()
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    # All financial columns should be numeric
    fin_cols = [c for c in df.columns if c not in ["Project Name", "Month"]]
    for col in fin_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    targets["ncf"] = df

    # ── Decision Items ───────────────────────────────────────────────────
    df = pd.read_excel(xls, sheet_name="Decision Items", header=1)
    df.columns = df.columns.str.strip()
    targets["decisions"] = df

    # ── Cross-check: which projects have targets? ────────────────────────
    aop_projects = set(targets["sales"]["Project Name"].unique())
    quality_issues.append({
        "file": "AOP Targets",
        "issue_type": "Reference Info",
        "field": "Project Names",
        "count": len(aop_projects),
        "details": f"AOP targets defined for: {', '.join(sorted(aop_projects))}",
        "action_needed": "Verify these match the actual project names in Sales/Collections data",
    })

    return targets, quality_issues
