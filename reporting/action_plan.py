"""
action_plan.py
--------------
Generates the Owner-wise Action Plan Excel output.
Groups action items by functional owner (Sales, Collections, Construction,
Finance, Leadership) with priorities and deadlines.
"""

import pandas as pd
import os
from collections import defaultdict
from config import OUTPUT_DIR


def generate_action_plan(all_flags, aop_targets):
    """Write the Owner-wise Action Plan to Excel."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "04_Owner_Action_Plan.xlsx")

    # ── Group flags by owner / function ──────────────────────────────────
    owner_actions = defaultdict(list)

    for flag in all_flags:
        owner = flag.get("owner", "Unassigned")
        # Normalise owner to function group
        owner_lower = str(owner).lower()

        if any(k in owner_lower for k in ["sales", "rohan", "neha iyer", "arjun", "kavya", "siddharth menon"]):
            group = "Sales"
        elif any(k in owner_lower for k in ["collection", "kunal", "meera", "priya", "ankit", "rohan iyer"]):
            group = "Collections"
        elif any(k in owner_lower for k in ["construction", "prakash", "nilesh", "farhan", "amit", "project director"]):
            group = "Construction"
        elif any(k in owner_lower for k in ["finance"]):
            group = "Finance"
        elif any(k in owner_lower for k in ["site head", "director", "leadership"]):
            group = "Leadership"
        else:
            group = "Other"

        owner_actions[group].append({
            "Owner": owner,
            "Area": flag.get("area", ""),
            "Severity": flag.get("severity", ""),
            "Action Item": flag.get("suggested_action", ""),
            "Context": flag.get("description", ""),
            "Project": flag.get("project", ""),
            "Metric": flag.get("metric", ""),
        })

    # Add decision items from AOP
    decisions = aop_targets.get("decisions")
    if decisions is not None and len(decisions) > 0:
        for _, row in decisions.iterrows():
            owner_actions["Leadership"].append({
                "Owner": row.get("Owner", "Leadership"),
                "Area": row.get("Linked Metric", "Decision Item"),
                "Severity": "Amber" if row.get("Status") == "Open" else "Info",
                "Action Item": str(row.get("Decision Item", "")),
                "Context": f"Timeline: {row.get('Timeline', '')}. Expected impact: {row.get('Expected Impact', '')}",
                "Project": "",
                "Metric": row.get("Linked Metric", ""),
            })

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})

        # Write one sheet per functional group
        for group in ["Sales", "Collections", "Construction", "Finance", "Leadership", "Other"]:
            actions = owner_actions.get(group, [])
            if not actions:
                continue

            df = pd.DataFrame(actions)

            # Sort by severity
            sev_order = {"Red": 0, "Amber": 1, "Info": 2}
            df["_sort"] = df["Severity"].map(sev_order).fillna(3)
            df = df.sort_values("_sort").drop(columns=["_sort"])

            sheet_name = f"{group} Actions"
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:31]

            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)

            ws = writer.sheets[sheet_name]
            ws.write(0, 0, f"Action Plan — {group}",
                     workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
            ws.write(1, 0, f"Total actions: {len(df)}",
                     workbook.add_format({"italic": True, "font_color": "#666666"}))

            for col_idx, col_name in enumerate(df.columns):
                ws.write(2, col_idx, col_name, header_fmt)

            ws.set_column(0, 0, 20)   # Owner
            ws.set_column(1, 1, 20)   # Area
            ws.set_column(2, 2, 10)   # Severity
            ws.set_column(3, 3, 40)   # Action Item
            ws.set_column(4, 4, 50)   # Context
            ws.set_column(5, 5, 20)   # Project
            ws.set_column(6, 6, 22)   # Metric

    return filepath
