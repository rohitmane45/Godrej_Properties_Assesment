"""
escalation_summary.py
---------------------
Generates the Escalation Summary Excel output.
Red / Amber items with project, reason, metric, owner, action, due date.
"""

import pandas as pd
import os
from config import OUTPUT_DIR


def generate_escalation_summary(all_flags):
    """Write the Escalation Summary to Excel."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "03_Escalation_Summary.xlsx")

    if not all_flags:
        # Write an empty report if no flags
        pd.DataFrame({"Status": ["No escalation items identified"]}).to_excel(
            filepath, index=False)
        return filepath

    flags_df = pd.DataFrame(all_flags)

    # Sort: Red first, then Amber
    severity_order = {"Red": 0, "Amber": 1}
    flags_df["_sort"] = flags_df["severity"].map(severity_order).fillna(2)
    flags_df = flags_df.sort_values(["_sort", "area", "project"]).drop(columns=["_sort"])

    # Select display columns
    display_cols = ["severity", "area", "project", "month", "metric",
                    "description", "owner", "suggested_action"]
    available = [c for c in display_cols if c in flags_df.columns]
    display = flags_df[available].copy()

    # Rename for business-friendly headers
    display.columns = ["Severity", "Area", "Project", "Month", "Metric",
                        "Issue Description", "Owner", "Suggested Action"][:len(available)]

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        red_fmt = workbook.add_format({
            "bg_color": "#FFC7CE", "font_color": "#9C0006",
            "border": 1, "text_wrap": True,
        })
        amber_fmt = workbook.add_format({
            "bg_color": "#FFEB9C", "font_color": "#9C6500",
            "border": 1, "text_wrap": True,
        })
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})

        display.to_excel(writer, sheet_name="Escalation Items", index=False,
                         startrow=2)

        ws = writer.sheets["Escalation Items"]
        ws.write(0, 0, "Escalation Summary — Q1 FY27",
                 workbook.add_format({"bold": True, "font_size": 14, "font_color": "#C00000"}))

        # Count summary
        red_count = len(flags_df[flags_df["severity"] == "Red"])
        amber_count = len(flags_df[flags_df["severity"] == "Amber"])
        ws.write(1, 0, f"Total: {len(flags_df)} items ({red_count} Red, {amber_count} Amber)",
                 workbook.add_format({"italic": True, "font_color": "#666666"}))

        for col_idx, col_name in enumerate(display.columns):
            ws.write(2, col_idx, col_name, header_fmt)

        # Apply conditional formatting for severity column
        for row_idx in range(len(display)):
            severity = display.iloc[row_idx]["Severity"] if "Severity" in display.columns else ""
            fmt = red_fmt if severity == "Red" else amber_fmt if severity == "Amber" else text_fmt
            for col_idx in range(len(display.columns)):
                val = display.iloc[row_idx, col_idx]
                if col_idx == 0:  # Severity column
                    ws.write(row_idx + 3, col_idx, val, fmt)
                else:
                    ws.write(row_idx + 3, col_idx, val, text_fmt)

        # Column widths
        ws.set_column(0, 0, 10)   # Severity
        ws.set_column(1, 1, 22)   # Area
        ws.set_column(2, 2, 20)   # Project
        ws.set_column(3, 3, 10)   # Month
        ws.set_column(4, 4, 22)   # Metric
        ws.set_column(5, 5, 50)   # Description
        ws.set_column(6, 6, 22)   # Owner
        ws.set_column(7, 7, 40)   # Action

        ws.set_row(0, 25)

    return filepath
