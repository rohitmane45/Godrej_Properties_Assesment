"""
cash_flow_engine.py
-------------------
Calculates the cash flow position: inflows (collections), outflows
(construction costs + other costs), net cash flow, and variance vs AOP.
"""

import pandas as pd
from config import COLLECTIONS_COLS, CONSTRUCTION_COLS, INR_TO_CR, PERIOD_MONTHS


def compute_cash_flow(collections_df, construction_df, aop_targets):
    """
    Build a monthly cash flow summary.

    Inflows  = collections received (Amount Collected)
    Outflows = construction actual cost + additional cost
    NCF      = Inflows – Outflows
    Variance = NCF – AOP NCF target

    Returns
    -------
    cash_flow_summary : pd.DataFrame – monthly cash flow with variance
    cash_flow_risks : list[dict] – top risks identified
    """
    # ── INFLOWS: monthly collections ─────────────────────────────────────
    coll_monthly = (
        collections_df
        .groupby("Collection Month")
        .agg(
            Total_Collected=("Collected Cr", "sum"),
            Total_Demand=("Demand Amount Cr", "sum"),
            Total_Outstanding=("Outstanding Cr", "sum"),
            Demand_Count=("Demand Amount Cr", "count"),
        )
        .reset_index()
    )
    coll_monthly.columns = ["Month", "Collections Inflow (Cr)",
                            "Total Demand (Cr)", "Outstanding (Cr)",
                            "No. of Demands"]

    # ── OUTFLOWS: construction costs ─────────────────────────────────────
    # Construction file doesn't have month — we use Planned Start as proxy
    constr = construction_df.copy()
    constr["Construction Month"] = constr[CONSTRUCTION_COLS["planned_start"]].apply(
        lambda d: d.replace(day=1) if pd.notna(d) and hasattr(d, "replace") else None
    )

    constr_monthly = (
        constr
        .groupby("Construction Month")
        .agg(
            Actual_Cost_Cr=("Actual Cost Cr", "sum"),
            Additional_Cost_Cr=("Additional Cost Cr", "sum"),
            Planned_Cost_Cr=("Planned Cost Cr", "sum"),
        )
        .reset_index()
    )
    constr_monthly.columns = ["Month", "Construction Cost (Cr)",
                              "Additional Cost (Cr)", "Planned CoC (Cr)"]

    constr_monthly["Total Outflow – CoC (Cr)"] = (
        constr_monthly["Construction Cost (Cr)"].fillna(0) +
        constr_monthly["Additional Cost (Cr)"].fillna(0)
    )

    # ── MERGE inflows and outflows ───────────────────────────────────────
    cash_flow = pd.merge(
        coll_monthly, constr_monthly, on="Month", how="outer"
    ).fillna(0)

    cash_flow["Net Cash Flow (Cr)"] = (
        cash_flow["Collections Inflow (Cr)"] -
        cash_flow["Total Outflow – CoC (Cr)"]
    )

    # ── COMPARE with AOP NCF targets ─────────────────────────────────────
    ncf_targets = aop_targets["ncf"].copy()
    ncf_monthly = ncf_targets.groupby("Month").agg(
        Target_NCF=("SPV NCF", "sum"),
        Target_Collection=("Collection Target", "sum"),
        Target_CoC=("CoC Target", "sum"),
    ).reset_index()

    cash_flow = pd.merge(
        cash_flow, ncf_monthly,
        on="Month", how="outer"
    ).fillna(0)

    cash_flow["NCF Variance (Cr)"] = (
        cash_flow["Net Cash Flow (Cr)"] - cash_flow["Target_NCF"]
    )

    cash_flow["Collection Variance (Cr)"] = (
        cash_flow["Collections Inflow (Cr)"] - cash_flow["Target_Collection"]
    )

    cash_flow["CoC Variance (Cr)"] = (
        cash_flow["Total Outflow – CoC (Cr)"] - cash_flow["Target_CoC"]
    )

    # Sort by month
    cash_flow = cash_flow.sort_values("Month").reset_index(drop=True)

    # ── Identify cash flow risks ─────────────────────────────────────────
    risks = []

    for _, row in cash_flow.iterrows():
        month = row["Month"]
        if not isinstance(month, pd.Timestamp):
            continue

        # Negative NCF
        if row["Net Cash Flow (Cr)"] < 0:
            risks.append({
                "month": month.strftime("%b-%Y"),
                "risk": "Negative Net Cash Flow",
                "amount_cr": round(row["Net Cash Flow (Cr)"], 2),
                "detail": (f"Outflows ({row['Total Outflow – CoC (Cr)']:.2f} Cr) exceed "
                           f"inflows ({row['Collections Inflow (Cr)']:.2f} Cr)"),
            })

        # NCF below target
        if row["NCF Variance (Cr)"] < -1:  # more than 1 Cr below target
            risks.append({
                "month": month.strftime("%b-%Y"),
                "risk": "NCF Below AOP Target",
                "amount_cr": round(row["NCF Variance (Cr)"], 2),
                "detail": (f"NCF {row['Net Cash Flow (Cr)']:.2f} Cr vs target "
                           f"{row['Target_NCF']:.2f} Cr (variance: {row['NCF Variance (Cr)']:.2f} Cr)"),
            })

        # High outstanding
        if row["Outstanding (Cr)"] > 5:
            risks.append({
                "month": month.strftime("%b-%Y"),
                "risk": "High Outstanding Collections",
                "amount_cr": round(row["Outstanding (Cr)"], 2),
                "detail": f"Outstanding collections of {row['Outstanding (Cr)']:.2f} Cr",
            })

    return cash_flow, risks
