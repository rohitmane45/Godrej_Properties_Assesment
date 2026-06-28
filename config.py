"""
config.py
---------
Central configuration for the Site Performance & Cash Flow Agent.
All thresholds, file paths, and column mappings live here so nothing
is hard-coded inside the business logic.
"""

import os
from datetime import datetime, timedelta

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILES = {
    "sales":        os.path.join(BASE_DIR, "AI_Assignment_Input_1_Sales_SANITIZED.xlsx"),
    "construction": os.path.join(BASE_DIR, "AI_Assignment_Input_2_Construction_Tracking.xlsx"),
    "collections":  os.path.join(BASE_DIR, "AI_Assignment_Input_3_Collections_Tracker.xlsx"),
    "aop":          os.path.join(BASE_DIR, "AI_Assignment_Input_4_AOP_Targets.xlsx"),
}

OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# ── Assignment Period ────────────────────────────────────────────────────────
# Q1 FY27: April 2026 – June 2026
PERIOD_START = datetime(2026, 4, 1)
PERIOD_END   = datetime(2026, 6, 30)
PERIOD_MONTHS = [
    datetime(2026, 4, 1),
    datetime(2026, 5, 1),
    datetime(2026, 6, 1),
]
PERIOD_LABEL = "Q1 FY27 (Apr-Jun 2026)"

# ── Business Rule Thresholds ─────────────────────────────────────────────────
SALES_RISK_THRESHOLD        = 0.80   # booking value < 80% of AOP target
COLLECTIONS_RISK_THRESHOLD  = 0.85   # monthly collections < 85% of target
CONSTRUCTION_DELAY_DAYS     = 15     # milestone delayed by more than 15 days
COST_OVERRUN_THRESHOLD      = 0.10   # actual cost exceeds target by > 10%
OVERDUE_DAYS_PRIORITY       = 30     # overdue > 30 days → collection priority

# ── Financial Unit ───────────────────────────────────────────────────────────
# AOP targets are in INR Cr; Sales/Collections data is in raw INR.
# We convert raw INR → Cr by dividing by 1,00,00,000 (1e7).
INR_TO_CR = 1e7

# ── Excel Serial Date Epoch ──────────────────────────────────────────────────
# Excel uses 1900-01-01 as day 1 (with the famous Lotus 1-2-3 leap-year bug).
EXCEL_EPOCH = datetime(1899, 12, 30)

def excel_serial_to_date(serial):
    """Convert an Excel serial date number to a Python datetime."""
    if serial is None or (isinstance(serial, float) and str(serial) == 'nan'):
        return None
    try:
        return EXCEL_EPOCH + timedelta(days=int(serial))
    except (ValueError, TypeError):
        return None

# ── Column Name Mappings ─────────────────────────────────────────────────────
# These help us reference columns consistently even if the Excel headers
# change slightly between months.

SALES_COLS = {
    "project":          "Project: Project Name",
    "unit":             "Unit Number",
    "customer_code":    "SAP Customer Code",
    "customer_name":    "Primary Customer: Full Name",
    "booking_date":     "Booking Date",
    "record_type":      "Record Type",
    "unit_type":        "Type",
    "agreement_amount": "Total Agreement Amount",
    "payment_received": "Total Payment Received",
    "paid_pct":         "Total Paid Percent",
    "super_area":       "Super Area",
    "sales_owner":      "Sales Owner",
    "sales_stage":      "Sales Stage",
    "site_head":        "Site Head: Name",
    "fy":               "FY",
    "remarks":          "Remarks",
}

CONSTRUCTION_COLS = {
    "tower":            "Tower",
    "activity":         "Activity",
    "balance_qty":      "Balance Qty",
    "uom":              "UOM",
    "duration_days":    "Duration Days",
    "planned_start":    "Planned Start",
    "planned_finish":   "Planned Finish",
    "actual_progress":  "Actual Progress %",
    "delay_days":       "Delay Days",
    "delay_reason":     "Delay Reason",
    "planned_cost":     "Planned Cost INR",
    "actual_cost":      "Actual Cost INR",
    "addl_cost":        "Additional Cost Expected INR",
    "owner":            "Responsible Owner",
    "dependency":       "Dependency Function",
    "linked_milestone": "Linked Collection Milestone",
}

COLLECTIONS_COLS = {
    "project":          "Project Name",
    "unit":             "Unit Number",
    "customer_code":    "SAP Customer Code",
    "customer_name":    "Customer Name",
    "agreement_value":  "Agreement Value",
    "milestone":        "Milestone Linked",
    "demand_date":      "Demand Raised Date",
    "demand_amount":    "Demand Amount",
    "due_date":         "Due Date",
    "collected":        "Amount Collected",
    "outstanding":      "Outstanding Amount",
    "days_overdue":     "Days Overdue",
    "status":           "Collection Status",
    "coll_owner":       "Collections Owner",
    "risk_flag":        "Customer Risk Flag",
    "remarks":          "Remarks",
    "sales_owner":      "Sales Owner",
}
