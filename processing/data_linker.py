"""
data_linker.py
--------------
Links data across the four input files using common fields like
project name, unit number, customer code, and milestone.
Flags records that cannot be linked.
"""

import pandas as pd
from config import SALES_COLS, COLLECTIONS_COLS, CONSTRUCTION_COLS


def link_sales_to_collections(sales_df, collections_df):
    """
    Link Sales and Collections data using Unit Number and SAP Customer Code.

    Returns
    -------
    linked : pd.DataFrame – merged data where matches were found
    unlinked_sales : pd.DataFrame – sales records with no matching collection
    unlinked_collections : pd.DataFrame – collection records with no matching sale
    issues : list[dict]
    """
    issues = []

    # Standardise the join keys
    sales_key = sales_df[[SALES_COLS["unit"], SALES_COLS["customer_code"]]].copy()
    sales_key.columns = ["Unit Number", "SAP Customer Code"]

    coll_key = collections_df[[COLLECTIONS_COLS["unit"],
                                COLLECTIONS_COLS["customer_code"]]].copy()
    coll_key.columns = ["Unit Number", "SAP Customer Code"]

    # Find units present in collections but not in sales
    coll_units = set(collections_df[COLLECTIONS_COLS["unit"]].dropna().unique())
    sales_units = set(sales_df[SALES_COLS["unit"]].dropna().unique())

    only_in_collections = coll_units - sales_units
    only_in_sales = sales_units - coll_units

    if only_in_collections:
        issues.append({
            "file": "Cross-File (Sales ↔ Collections)",
            "issue_type": "Data Mismatch",
            "field": "Unit Number",
            "count": len(only_in_collections),
            "details": f"Units in Collections but not in Sales: {', '.join(sorted(only_in_collections)[:5])}",
            "action_needed": "Verify if these are valid bookings missing from the Sales file",
        })

    if only_in_sales:
        issues.append({
            "file": "Cross-File (Sales ↔ Collections)",
            "issue_type": "Data Note",
            "field": "Unit Number",
            "count": len(only_in_sales),
            "details": f"Units in Sales but not in Collections: {', '.join(sorted(only_in_sales)[:5])}",
            "action_needed": "May be new bookings with no demand raised yet — verify",
        })

    # Merge on Unit Number (primary key for linking)
    linked = pd.merge(
        sales_df,
        collections_df,
        left_on=SALES_COLS["unit"],
        right_on=COLLECTIONS_COLS["unit"],
        how="inner",
        suffixes=("_sales", "_coll"),
    )

    unlinked_sales = sales_df[
        ~sales_df[SALES_COLS["unit"]].isin(
            collections_df[COLLECTIONS_COLS["unit"]]
        )
    ]

    unlinked_collections = collections_df[
        ~collections_df[COLLECTIONS_COLS["unit"]].isin(
            sales_df[SALES_COLS["unit"]]
        )
    ]

    return linked, unlinked_sales, unlinked_collections, issues


def check_project_name_alignment(sales_df, collections_df, aop_targets):
    """
    Check if project names across files match the AOP target projects.
    This is the major mismatch test in the assignment.

    Returns
    -------
    issues : list[dict]
    """
    issues = []

    sales_projects = set(sales_df[SALES_COLS["project"]].dropna().unique())
    coll_projects = set(collections_df[COLLECTIONS_COLS["project"]].dropna().unique())
    aop_projects = set(aop_targets["sales"]["Project Name"].dropna().unique())

    # Compare
    actual_projects = sales_projects | coll_projects
    in_actual_not_aop = actual_projects - aop_projects
    in_aop_not_actual = aop_projects - actual_projects

    if in_actual_not_aop:
        issues.append({
            "file": "Cross-File (Sales/Collections ↔ AOP)",
            "issue_type": "Critical Mismatch",
            "field": "Project Name",
            "count": len(in_actual_not_aop),
            "details": (f"Projects in actuals but NOT in AOP targets: "
                        f"{', '.join(sorted(in_actual_not_aop))}. "
                        f"Cannot compare performance vs target for these projects."),
            "action_needed": ("Verify project name mapping. These projects have sales/collections "
                              "data but no AOP baseline to compare against."),
        })

    if in_aop_not_actual:
        issues.append({
            "file": "Cross-File (Sales/Collections ↔ AOP)",
            "issue_type": "Missing Actuals",
            "field": "Project Name",
            "count": len(in_aop_not_actual),
            "details": (f"AOP targets exist but no actual data found for: "
                        f"{', '.join(sorted(in_aop_not_actual))}"),
            "action_needed": "Provide Sales and Collections data for these projects",
        })

    return issues


def link_construction_to_aop(construction_df, aop_targets):
    """
    Attempt to link construction data to AOP CoC targets.
    Since construction file has no project name, this is limited.

    Returns
    -------
    issues : list[dict]
    """
    issues = []

    constr_towers = set(construction_df[CONSTRUCTION_COLS["tower"]].dropna().unique())
    aop_towers = set(aop_targets["construction"]["Tower"].dropna().unique())

    overlap = constr_towers & aop_towers
    only_actual = constr_towers - aop_towers
    only_target = aop_towers - constr_towers

    if not overlap:
        issues.append({
            "file": "Cross-File (Construction ↔ AOP)",
            "issue_type": "Critical Mismatch",
            "field": "Tower",
            "count": len(constr_towers),
            "details": (f"No tower overlap found. Actual towers: {sorted(constr_towers)}, "
                        f"AOP towers: {sorted(aop_towers)}. "
                        f"Construction data cannot be compared to AOP targets."),
            "action_needed": "Construction file is missing project name. Confirm tower-to-project mapping.",
        })
    else:
        if only_actual:
            issues.append({
                "file": "Cross-File (Construction ↔ AOP)",
                "issue_type": "Data Mismatch",
                "field": "Tower",
                "count": len(only_actual),
                "details": f"Towers in actuals but not in AOP: {sorted(only_actual)}",
                "action_needed": "Add AOP targets for these towers",
            })

    return issues
