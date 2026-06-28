"""
construction_loader.py
----------------------
Reads and cleans the Construction Tracking input file.
Filters out daily-target rows, converts serial dates, flags data issues.
"""

import pandas as pd
from config import INPUT_FILES, CONSTRUCTION_COLS, excel_serial_to_date, INR_TO_CR


def load_construction():
    """
    Load the construction tracking Excel file and return cleaned data.

    The file has:
      - A title row at row 0 ("R5B Construction Tracking - Summary")
      - Real header at row 1
      - Activity rows mixed with daily-target numeric rows
      - Extra unnamed columns (daily progress data) beyond column 16

    Returns
    -------
    df : pd.DataFrame   – cleaned construction milestone data
    quality_issues : list[dict] – data quality problems found
    """
    filepath = INPUT_FILES["construction"]
    df_raw = pd.read_excel(filepath, header=1)

    quality_issues = []

    # ── Keep only the 16 meaningful columns ──────────────────────────────
    keep_cols = list(CONSTRUCTION_COLS.values())
    available = [c for c in keep_cols if c in df_raw.columns]
    df = df_raw[available].copy()

    # ── Drop fully empty rows ────────────────────────────────────────────
    df = df.dropna(how="all")

    # ── Filter out non-activity rows ─────────────────────────────────────
    # Some rows have numeric values in the Activity column (1, 2, 3, ...)
    # which are daily target layout data, not real milestones.
    # Also filter out rows where Tower is a header repeat or a label.
    noise_towers = ["Tower", "Sample-like Daily Target Layout (for parsing challenge)"]
    df = df[~df[CONSTRUCTION_COLS["tower"]].isin(noise_towers)]
    df = df[df[CONSTRUCTION_COLS["tower"]].notna()]

    # Filter rows where Activity is numeric (daily targets, not real activities)
    def is_real_activity(val):
        if pd.isna(val):
            return False
        if isinstance(val, (int, float)):
            return False
        return True

    df = df[df[CONSTRUCTION_COLS["activity"]].apply(is_real_activity)].copy()

    # ── Convert serial dates ─────────────────────────────────────────────
    for col in [CONSTRUCTION_COLS["planned_start"], CONSTRUCTION_COLS["planned_finish"]]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: excel_serial_to_date(v) if isinstance(v, (int, float)) else v
            )

    # ── Convert costs to numeric ─────────────────────────────────────────
    cost_cols = [CONSTRUCTION_COLS["planned_cost"],
                 CONSTRUCTION_COLS["actual_cost"],
                 CONSTRUCTION_COLS["addl_cost"]]
    for col in cost_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Convert delay days and progress to numeric ───────────────────────
    for col in [CONSTRUCTION_COLS["delay_days"], CONSTRUCTION_COLS["actual_progress"]]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Derive cost in Cr for comparison with AOP ────────────────────────
    df["Planned Cost Cr"] = df[CONSTRUCTION_COLS["planned_cost"]] / INR_TO_CR
    df["Actual Cost Cr"] = df[CONSTRUCTION_COLS["actual_cost"]] / INR_TO_CR
    df["Additional Cost Cr"] = df[CONSTRUCTION_COLS["addl_cost"]] / INR_TO_CR

    # ── Flag: no project name in the file ────────────────────────────────
    quality_issues.append({
        "file": "Construction",
        "issue_type": "Missing Data",
        "field": "Project Name",
        "count": len(df),
        "details": ("Construction file titled 'R5B Construction Tracking' has no "
                     "Project Name column. Cannot link to AOP project targets. "
                     "Towers T4-T7 do not match AOP tower references (T1, T2, T3)."),
        "action_needed": "Confirm which AOP project this construction data belongs to",
    })

    # ── Flag: missing delay reason where delay exists ────────────────────
    delayed = df[df[CONSTRUCTION_COLS["delay_days"]] > 0]
    missing_reason = delayed[delayed[CONSTRUCTION_COLS["delay_reason"]].isna()]
    if len(missing_reason) > 0:
        activities = missing_reason[CONSTRUCTION_COLS["activity"]].tolist()
        quality_issues.append({
            "file": "Construction",
            "issue_type": "Clarification Required",
            "field": "Delay Reason",
            "count": len(missing_reason),
            "details": f"Activities delayed but no reason given: {', '.join(str(a) for a in activities[:5])}",
            "action_needed": "Construction team to provide delay reasons",
        })

    # ── Flag: missing Actual Cost ────────────────────────────────────────
    missing_cost = df[df[CONSTRUCTION_COLS["actual_cost"]].isna()]
    if len(missing_cost) > 0:
        quality_issues.append({
            "file": "Construction",
            "issue_type": "Missing Data",
            "field": "Actual Cost INR",
            "count": len(missing_cost),
            "details": "Actual cost not reported — cannot compute cost variance",
            "action_needed": "Update actual cost for completed/in-progress activities",
        })

    # ── Flag: missing Responsible Owner ──────────────────────────────────
    missing_owner = df[df[CONSTRUCTION_COLS["owner"]].isna()]
    if len(missing_owner) > 0:
        quality_issues.append({
            "file": "Construction",
            "issue_type": "Missing Data",
            "field": "Responsible Owner",
            "count": len(missing_owner),
            "details": "Owner not assigned — escalation routing not possible",
            "action_needed": "Assign responsible owner for all activities",
        })

    df = df.reset_index(drop=True)
    return df, quality_issues
