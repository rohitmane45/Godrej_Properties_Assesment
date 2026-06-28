"""
collections_loader.py
---------------------
Reads and cleans the Collections Tracker input file.
Handles the multi-row header, date parsing, and data quality checks.
"""

import pandas as pd
from datetime import datetime
from config import INPUT_FILES, COLLECTIONS_COLS, INR_TO_CR


def load_collections():
    """
    Load the collections tracker Excel file and return cleaned data.

    The file layout:
      - Row 0: title "AI Assignment Input 3 - Collections Tracker"
      - Row 1: "As of Date"  |  2026-07-31  |  "Currency"  |  "INR"
      - Row 2: blank
      - Row 3: actual column headers
      - Row 4+: data

    Returns
    -------
    df : pd.DataFrame   – cleaned collections data
    as_of_date : datetime – the reporting date from the header
    quality_issues : list[dict] – data quality problems found
    """
    filepath = INPUT_FILES["collections"]

    quality_issues = []

    # ── Extract "As of Date" from the metadata row ───────────────────────
    df_meta = pd.read_excel(filepath, header=None, nrows=3)
    as_of_date = None
    try:
        raw_date = df_meta.iloc[1, 1]  # row 1, col 1 should be the date
        if isinstance(raw_date, str):
            as_of_date = datetime.strptime(raw_date, "%Y-%m-%d")
        elif isinstance(raw_date, datetime):
            as_of_date = raw_date
        elif hasattr(raw_date, 'to_pydatetime'):
            as_of_date = raw_date.to_pydatetime()
    except Exception:
        as_of_date = datetime(2026, 7, 31)  # fallback from known data

    # ── Read actual data with header at row 3 ────────────────────────────
    df = pd.read_excel(filepath, header=3)

    # ── Drop fully empty rows ────────────────────────────────────────────
    df = df.dropna(how="all")

    # ── Parse date columns ───────────────────────────────────────────────
    for col in [COLLECTIONS_COLS["demand_date"], COLLECTIONS_COLS["due_date"]]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # ── Ensure numeric columns are numeric ───────────────────────────────
    numeric_cols = ["Agreement Value", "Demand Amount", "Amount Collected",
                    "Outstanding Amount", "Days Overdue"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Derive collection month from demand date ─────────────────────────
    df["Collection Month"] = df[COLLECTIONS_COLS["demand_date"]].apply(
        lambda d: d.replace(day=1) if pd.notna(d) else None
    )

    # ── Convert amounts to Cr ────────────────────────────────────────────
    df["Agreement Value Cr"] = df[COLLECTIONS_COLS["agreement_value"]] / INR_TO_CR
    df["Demand Amount Cr"] = df[COLLECTIONS_COLS["demand_amount"]] / INR_TO_CR
    df["Collected Cr"] = df[COLLECTIONS_COLS["collected"]] / INR_TO_CR
    df["Outstanding Cr"] = df[COLLECTIONS_COLS["outstanding"]] / INR_TO_CR

    # ── Flag missing Sales Owner ─────────────────────────────────────────
    missing_owner = df[COLLECTIONS_COLS["sales_owner"]].isna()
    if missing_owner.any():
        quality_issues.append({
            "file": "Collections",
            "issue_type": "Missing Data",
            "field": "Sales Owner",
            "count": int(missing_owner.sum()),
            "details": "Sales Owner missing — cannot route action items",
            "action_needed": "Map Sales Owner from Sales CRM data",
        })

    # ── Flag missing milestone linkage ───────────────────────────────────
    missing_milestone = df[COLLECTIONS_COLS["milestone"]].isna()
    if missing_milestone.any():
        quality_issues.append({
            "file": "Collections",
            "issue_type": "Missing Data",
            "field": "Milestone Linked",
            "count": int(missing_milestone.sum()),
            "details": "Collection records without milestone linkage cannot be tied to construction progress",
            "action_needed": "Link collection demands to construction milestones",
        })

    # ── Flag missing Due Date ────────────────────────────────────────────
    missing_due = df[COLLECTIONS_COLS["due_date"]].isna()
    if missing_due.any():
        quality_issues.append({
            "file": "Collections",
            "issue_type": "Missing Data",
            "field": "Due Date",
            "count": int(missing_due.sum()),
            "details": "Due Date missing — cannot calculate overdue status",
            "action_needed": "Populate due dates for all demands",
        })

    df = df.reset_index(drop=True)
    return df, as_of_date, quality_issues
