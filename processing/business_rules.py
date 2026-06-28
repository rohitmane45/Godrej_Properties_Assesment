"""
business_rules.py
-----------------
Implements all the business rules defined in the assignment brief.
Each rule function returns a list of flagged items (dicts) that feed
into escalation, action plans, and reports.
"""

import pandas as pd
from config import (
    SALES_COLS, COLLECTIONS_COLS, CONSTRUCTION_COLS,
    SALES_RISK_THRESHOLD, COLLECTIONS_RISK_THRESHOLD,
    CONSTRUCTION_DELAY_DAYS, COST_OVERRUN_THRESHOLD,
    OVERDUE_DAYS_PRIORITY, PERIOD_MONTHS, INR_TO_CR,
)


def check_sales_vs_target(sales_df, aop_sales_targets):
    """
    Rule 1: If monthly booking value is below 80% of AOP target,
    flag Sales risk and generate Sales Head action.

    We compare the actual project's booking value against the total
    monthly AOP target since project names don't match.
    """
    flags = []

    # Aggregate actual bookings by month (exclude Cancelled)
    active_sales = sales_df[sales_df[SALES_COLS["sales_stage"]] != "Cancelled"].copy()
    monthly_actual = (
        active_sales
        .groupby("Booking Month")["Agreement Amount Cr"]
        .sum()
        .reset_index()
    )
    monthly_actual.columns = ["Month", "Actual Booking Cr"]

    # Monthly AOP target totals
    monthly_target = (
        aop_sales_targets
        .groupby("Month")["Booking Value Target"]
        .sum()
        .reset_index()
    )
    monthly_target.columns = ["Month", "Target Booking Cr"]

    # Compare for each AOP month
    for _, row in monthly_target.iterrows():
        month = row["Month"]
        target = row["Target Booking Cr"]

        actual_row = monthly_actual[monthly_actual["Month"] == month]
        actual = actual_row["Actual Booking Cr"].values[0] if len(actual_row) > 0 else 0

        achievement = actual / target if target > 0 else 0

        if achievement < SALES_RISK_THRESHOLD:
            flags.append({
                "area": "Sales",
                "severity": "Red" if achievement < 0.60 else "Amber",
                "project": "All Projects (AOP)",
                "month": month.strftime("%b-%Y") if hasattr(month, "strftime") else str(month),
                "metric": "Booking Value",
                "target": round(target, 2),
                "actual": round(actual, 2),
                "achievement_pct": round(achievement * 100, 1),
                "threshold": f"{SALES_RISK_THRESHOLD*100:.0f}%",
                "description": (f"Monthly booking value {actual:.2f} Cr is "
                                f"{achievement*100:.1f}% of target {target:.2f} Cr "
                                f"(below {SALES_RISK_THRESHOLD*100:.0f}% threshold)"),
                "owner": "Sales Head",
                "suggested_action": "Review pipeline, accelerate closures, activate channel partners",
            })

    return flags


def check_product_mix(sales_df, aop_sales_targets):
    """
    Rule 2: Compare actual product mix sold against 1BHK/2BHK/3BHK
    unit targets. Flag material shortfall by product type.
    """
    flags = []

    active_sales = sales_df[sales_df[SALES_COLS["sales_stage"]] != "Cancelled"].copy()

    # Count units by type and month
    type_mapping = {"1 BHK": "1BHK", "2 BHK": "2BHK", "3 BHK": "3BHK", "2.5 BHK": "2.5BHK"}
    active_sales["BHK Type"] = active_sales[SALES_COLS["unit_type"]].map(type_mapping)

    monthly_mix = (
        active_sales
        .groupby(["Booking Month", "BHK Type"])
        .size()
        .reset_index(name="Actual Units")
    )

    # For each target month and type, compare
    for _, target_row in aop_sales_targets.iterrows():
        month = target_row["Month"]
        project = target_row["Project Name"]

        for bhk, target_col in [("1BHK", "1BHK Units Target"),
                                 ("2BHK", "2BHK Units Target"),
                                 ("3BHK", "3BHK Units Target")]:
            target_units = target_row[target_col]

            actual_row = monthly_mix[
                (monthly_mix["Booking Month"] == month) &
                (monthly_mix["BHK Type"] == bhk)
            ]
            actual_units = actual_row["Actual Units"].values[0] if len(actual_row) > 0 else 0

            shortfall = target_units - actual_units
            if shortfall > 0 and target_units > 0:
                pct = actual_units / target_units * 100
                flags.append({
                    "area": "Sales",
                    "severity": "Amber",
                    "project": project,
                    "month": month.strftime("%b-%Y") if hasattr(month, "strftime") else str(month),
                    "metric": f"Product Mix – {bhk}",
                    "target": target_units,
                    "actual": actual_units,
                    "achievement_pct": round(pct, 1),
                    "threshold": "Target units",
                    "description": f"{bhk} shortfall of {shortfall} units for {project} in {month.strftime('%b-%Y') if hasattr(month, 'strftime') else month}",
                    "owner": "Sales Head",
                    "suggested_action": f"Push {bhk} inventory, review pricing and availability",
                })

    return flags


def check_collections_vs_target(collections_df, aop_summary):
    """
    Rule 3: If monthly collections are below 85% of target, flag Collections risk.
    """
    flags = []

    # Total collected per month (from demand date)
    monthly_collected = (
        collections_df
        .groupby("Collection Month")["Collected Cr"]
        .sum()
        .reset_index()
    )
    monthly_collected.columns = ["Month", "Actual Collections Cr"]

    # AOP summary has Collections Target per month
    for _, row in aop_summary.iterrows():
        month = row.get("Month")
        if not isinstance(month, pd.Timestamp):
            continue  # skip "Q1 Total" row

        target = row.get("Collections Target", 0)
        actual_row = monthly_collected[monthly_collected["Month"] == month]
        actual = actual_row["Actual Collections Cr"].values[0] if len(actual_row) > 0 else 0

        achievement = actual / target if target > 0 else 0

        if achievement < COLLECTIONS_RISK_THRESHOLD:
            flags.append({
                "area": "Collections",
                "severity": "Red" if achievement < 0.70 else "Amber",
                "project": "All Projects",
                "month": month.strftime("%b-%Y"),
                "metric": "Monthly Collections",
                "target": round(target, 2),
                "actual": round(actual, 2),
                "achievement_pct": round(achievement * 100, 1),
                "threshold": f"{COLLECTIONS_RISK_THRESHOLD*100:.0f}%",
                "description": (f"Collections {actual:.2f} Cr at {achievement*100:.1f}% of "
                                f"target {target:.2f} Cr"),
                "owner": "Collections Lead",
                "suggested_action": "Prioritise overdue follow-ups, escalate high-value defaults",
            })

    return flags


def check_overdue_collections(collections_df):
    """
    Rule 4: If any customer is overdue by more than 30 days,
    mark as collection priority.
    """
    flags = []

    overdue = collections_df[
        collections_df[COLLECTIONS_COLS["days_overdue"]] > OVERDUE_DAYS_PRIORITY
    ].copy()

    for _, row in overdue.iterrows():
        flags.append({
            "area": "Collections",
            "severity": "Red" if row[COLLECTIONS_COLS["days_overdue"]] > 60 else "Amber",
            "project": row[COLLECTIONS_COLS["project"]],
            "month": "",
            "metric": "Overdue Collection",
            "target": 0,
            "actual": row[COLLECTIONS_COLS["days_overdue"]],
            "achievement_pct": 0,
            "threshold": f">{OVERDUE_DAYS_PRIORITY} days",
            "description": (f"Customer {row[COLLECTIONS_COLS['customer_name']]} "
                            f"({row[COLLECTIONS_COLS['unit']]}) overdue by "
                            f"{int(row[COLLECTIONS_COLS['days_overdue']])} days, "
                            f"outstanding: {row[COLLECTIONS_COLS['outstanding']]:,.0f} INR"),
            "owner": row.get(COLLECTIONS_COLS["coll_owner"], "Collections Team"),
            "suggested_action": f"Follow up with customer, escalate if > 60 days",
        })

    return flags


def check_cashflow_leakage(collections_df, construction_df):
    """
    Rule 5: If construction milestone is achieved but linked collection
    is not received by expected deadline, flag cash-flow leakage.
    """
    flags = []

    # Find construction activities at 100% progress
    completed = construction_df[
        construction_df[CONSTRUCTION_COLS["actual_progress"]] >= 100
    ]

    for _, c_row in completed.iterrows():
        milestone = c_row.get(CONSTRUCTION_COLS["linked_milestone"])
        if pd.isna(milestone) or not isinstance(milestone, str):
            continue

        # Find collection records linked to this milestone
        linked_coll = collections_df[
            collections_df[COLLECTIONS_COLS["milestone"]].str.strip() == milestone.strip()
        ]

        # Check if any are unpaid
        unpaid = linked_coll[
            linked_coll[COLLECTIONS_COLS["status"]].isin(["Part Paid", "Overdue", "Not Due"])
        ]

        for _, u_row in unpaid.iterrows():
            outstanding = u_row[COLLECTIONS_COLS["outstanding"]]
            if outstanding > 0:
                flags.append({
                    "area": "Cash Flow Leakage",
                    "severity": "Red",
                    "project": u_row.get(COLLECTIONS_COLS["project"], "Unknown"),
                    "month": "",
                    "metric": "Milestone-Collection Gap",
                    "target": 0,
                    "actual": outstanding,
                    "achievement_pct": 0,
                    "threshold": "Collection due on milestone completion",
                    "description": (f"Milestone '{milestone}' completed but collection not received "
                                    f"for {u_row[COLLECTIONS_COLS['customer_name']]} "
                                    f"({u_row[COLLECTIONS_COLS['unit']]}). "
                                    f"Outstanding: {outstanding:,.0f} INR"),
                    "owner": u_row.get(COLLECTIONS_COLS["coll_owner"], "Collections Team"),
                    "suggested_action": "Immediately follow up — milestone trigger met",
                })

    return flags


def check_construction_delays(construction_df):
    """
    Rule 6: If a milestone is delayed by more than 15 days, flag Construction risk.
    Rule 7: If delay reason is missing for a delayed milestone, flag Clarification Required.
    """
    flags = []

    delayed = construction_df[
        construction_df[CONSTRUCTION_COLS["delay_days"]] > CONSTRUCTION_DELAY_DAYS
    ].copy()

    for _, row in delayed.iterrows():
        delay = int(row[CONSTRUCTION_COLS["delay_days"]])
        reason = row.get(CONSTRUCTION_COLS["delay_reason"])
        has_reason = pd.notna(reason) and isinstance(reason, str) and reason.strip() != ""

        flags.append({
            "area": "Construction",
            "severity": "Red" if delay > 30 else "Amber",
            "project": "R5B (Project TBD)",
            "month": "",
            "metric": "Construction Delay",
            "target": 0,
            "actual": delay,
            "achievement_pct": 0,
            "threshold": f">{CONSTRUCTION_DELAY_DAYS} days",
            "description": (f"Tower {row[CONSTRUCTION_COLS['tower']]} – "
                            f"'{row[CONSTRUCTION_COLS['activity']]}' delayed by {delay} days"
                            f"{'. Reason: ' + reason if has_reason else ' — NO REASON PROVIDED'}"),
            "owner": row.get(CONSTRUCTION_COLS["owner"], "Construction Head"),
            "suggested_action": ("Provide delay reason" if not has_reason
                                 else "Develop recovery plan, assess downstream impact"),
        })

    # Separately flag all missing delay reasons (including < 15 day delays)
    all_delayed = construction_df[construction_df[CONSTRUCTION_COLS["delay_days"]] > 0]
    no_reason = all_delayed[all_delayed[CONSTRUCTION_COLS["delay_reason"]].isna()]
    if len(no_reason) > 0:
        for _, row in no_reason.iterrows():
            flags.append({
                "area": "Construction – Clarification",
                "severity": "Amber",
                "project": "R5B (Project TBD)",
                "month": "",
                "metric": "Missing Delay Reason",
                "target": 0,
                "actual": int(row[CONSTRUCTION_COLS["delay_days"]]),
                "achievement_pct": 0,
                "threshold": "Reason required for all delays",
                "description": (f"Tower {row[CONSTRUCTION_COLS['tower']]} – "
                                f"'{row[CONSTRUCTION_COLS['activity']]}' delayed {int(row[CONSTRUCTION_COLS['delay_days']])} days, "
                                f"no reason provided"),
                "owner": row.get(CONSTRUCTION_COLS["owner"], "Construction Head"),
                "suggested_action": "Submit delay reason to project controls",
            })

    return flags


def check_cost_overrun(construction_df):
    """
    Rule 8: If expected or actual construction cost exceeds target by > 10%,
    flag cost overrun.
    """
    flags = []

    df = construction_df.copy()
    df["Total Actual Cost"] = (
        df[CONSTRUCTION_COLS["actual_cost"]].fillna(0) +
        df[CONSTRUCTION_COLS["addl_cost"]].fillna(0)
    )

    planned = df[CONSTRUCTION_COLS["planned_cost"]]

    for idx, row in df.iterrows():
        p_cost = row[CONSTRUCTION_COLS["planned_cost"]]
        t_cost = row["Total Actual Cost"]

        if pd.isna(p_cost) or p_cost == 0:
            continue

        overrun_pct = (t_cost - p_cost) / p_cost

        if overrun_pct > COST_OVERRUN_THRESHOLD:
            flags.append({
                "area": "Cost of Construction",
                "severity": "Red" if overrun_pct > 0.20 else "Amber",
                "project": "R5B (Project TBD)",
                "month": "",
                "metric": "Cost Overrun",
                "target": round(p_cost, 0),
                "actual": round(t_cost, 0),
                "achievement_pct": round(overrun_pct * 100, 1),
                "threshold": f">{COST_OVERRUN_THRESHOLD*100:.0f}%",
                "description": (f"Tower {row[CONSTRUCTION_COLS['tower']]} – "
                                f"'{row[CONSTRUCTION_COLS['activity']]}' cost overrun "
                                f"{overrun_pct*100:.1f}% "
                                f"(Planned: {p_cost:,.0f}, Actual+Addl: {t_cost:,.0f})"),
                "owner": row.get(CONSTRUCTION_COLS["owner"], "Construction Head"),
                "suggested_action": "Review cost variance, negotiate with vendors",
            })

    return flags


def check_cross_functional_escalation(all_flags):
    """
    Rule 10: If the same project has Sales risk plus Collections or
    Construction risk, mark as cross-functional escalation.
    """
    escalations = []

    # Group flags by project
    from collections import defaultdict
    project_areas = defaultdict(set)

    for flag in all_flags:
        project = flag.get("project", "")
        area = flag.get("area", "")
        if "Sales" in area:
            project_areas[project].add("Sales")
        if "Collections" in area:
            project_areas[project].add("Collections")
        if "Construction" in area:
            project_areas[project].add("Construction")
        if "Cost" in area:
            project_areas[project].add("Construction")

    for project, areas in project_areas.items():
        if "Sales" in areas and ("Collections" in areas or "Construction" in areas):
            other_areas = areas - {"Sales"}
            escalations.append({
                "area": "Cross-Functional Escalation",
                "severity": "Red",
                "project": project,
                "month": "",
                "metric": "Multi-Area Risk",
                "target": 0,
                "actual": 0,
                "achievement_pct": 0,
                "threshold": "Sales + other area risk",
                "description": (f"Project '{project}' has risks in Sales AND "
                                f"{', '.join(sorted(other_areas))}. "
                                f"Cross-functional leadership attention required."),
                "owner": "Project Director / Site Head",
                "suggested_action": "Convene cross-functional review meeting",
            })

    return escalations


def run_all_rules(sales_df, collections_df, construction_df, aop_targets):
    """
    Execute all business rules and return consolidated flags.

    Returns
    -------
    all_flags : list[dict] – every flagged item from all rules
    """
    all_flags = []

    # Rule 1: Sales vs target
    all_flags.extend(check_sales_vs_target(sales_df, aop_targets["sales"]))

    # Rule 2: Product mix
    all_flags.extend(check_product_mix(sales_df, aop_targets["sales"]))

    # Rule 3: Collections vs target
    all_flags.extend(check_collections_vs_target(collections_df, aop_targets["summary"]))

    # Rule 4: Overdue collections
    all_flags.extend(check_overdue_collections(collections_df))

    # Rule 5: Cash-flow leakage
    all_flags.extend(check_cashflow_leakage(collections_df, construction_df))

    # Rules 6 & 7: Construction delays
    all_flags.extend(check_construction_delays(construction_df))

    # Rule 8: Cost overrun
    all_flags.extend(check_cost_overrun(construction_df))

    # Rule 10: Cross-functional escalation
    all_flags.extend(check_cross_functional_escalation(all_flags))

    return all_flags
