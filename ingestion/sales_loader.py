"""
sales_loader.py
---------------
Reads and cleans the Sales input file.
Handles Excel serial date conversion, month extraction, and null flagging.
"""

import pandas as pd
from config import INPUT_FILES, SALES_COLS, excel_serial_to_date, INR_TO_CR


def load_sales():
    """
    Load the sales Excel file and return a cleaned DataFrame.

    Returns
    -------
    df : pd.DataFrame   – cleaned sales data with proper dates and derived columns
    quality_issues : list[dict] – data quality problems found during loading
    """
    filepath = INPUT_FILES["sales"]
    df = pd.read_excel(filepath)

    quality_issues = []

    # ── Convert Excel serial dates to proper datetime ────────────────────
    date_cols = ["Booking Date", "SAP Customer Created Date",
                 "Expected Agreement Date", "Expected Closure Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(excel_serial_to_date)

    # ── Derive booking month (first day of month) for aggregation ────────
    df["Booking Month"] = df[SALES_COLS["booking_date"]].apply(
        lambda d: d.replace(day=1) if d is not None else None
    )

    # ── Convert agreement amount to Cr for comparison with AOP ───────────
    df["Agreement Amount Cr"] = df[SALES_COLS["agreement_amount"]] / INR_TO_CR

    # ── Flag missing Sales Owner ─────────────────────────────────────────
    missing_owner = df[SALES_COLS["sales_owner"]].isna()
    if missing_owner.any():
        affected_units = df.loc[missing_owner, SALES_COLS["unit"]].tolist()
        quality_issues.append({
            "file": "Sales",
            "issue_type": "Missing Data",
            "field": "Sales Owner",
            "count": int(missing_owner.sum()),
            "details": f"Units with no Sales Owner: {', '.join(str(u) for u in affected_units[:5])}{'...' if len(affected_units) > 5 else ''}",
            "action_needed": "Assign Sales Owner for these bookings",
        })

    # ── Flag missing SAP Customer Code ───────────────────────────────────
    missing_code = df[SALES_COLS["customer_code"]].isna()
    if missing_code.any():
        quality_issues.append({
            "file": "Sales",
            "issue_type": "Missing Data",
            "field": "SAP Customer Code",
            "count": int(missing_code.sum()),
            "details": "Customer records without SAP code cannot be linked to Collections",
            "action_needed": "Update SAP Customer Code in CRM",
        })

    # ── Flag Carpet Area entirely missing ────────────────────────────────
    if "Carpet Area" in df.columns and df["Carpet Area"].isna().all():
        quality_issues.append({
            "file": "Sales",
            "issue_type": "Missing Data",
            "field": "Carpet Area",
            "count": len(df),
            "details": "Carpet Area is blank for all 80 records",
            "action_needed": "Populate Carpet Area from project master data",
        })

    # ── Flag cancelled bookings ──────────────────────────────────────────
    cancelled = df[df[SALES_COLS["sales_stage"]] == "Cancelled"]
    if len(cancelled) > 0:
        quality_issues.append({
            "file": "Sales",
            "issue_type": "Data Note",
            "field": "Sales Stage",
            "count": len(cancelled),
            "details": f"{len(cancelled)} bookings are in 'Cancelled' stage",
            "action_needed": "Verify if cancelled bookings should be excluded from targets",
        })

    # ── Flag 2.5 BHK units (not in AOP targets) ─────────────────────────
    bhk25 = df[df[SALES_COLS["unit_type"]] == "2.5 BHK"]
    if len(bhk25) > 0:
        quality_issues.append({
            "file": "Sales",
            "issue_type": "Data Mismatch",
            "field": "Type",
            "count": len(bhk25),
            "details": "2.5 BHK units found in sales but AOP targets only have 1BHK/2BHK/3BHK",
            "action_needed": "Clarify how 2.5 BHK should be mapped for product mix comparison",
        })

    return df, quality_issues
