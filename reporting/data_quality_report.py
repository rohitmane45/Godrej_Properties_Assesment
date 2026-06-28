"""
data_quality_report.py
----------------------
Generates the Missing Input / Data Quality Report.
Sheet 1: Summary of all quality issues found across files
Sheet 2: Cross-file mismatches
Sheet 3: Records needing human clarification
"""

import pandas as pd
import os
from config import OUTPUT_DIR


def generate_data_quality_report(all_quality_issues, linkage_issues):
    """
    Write the Data Quality Report to Excel.

    Parameters
    ----------
    all_quality_issues : list[dict] – issues from all loaders
    linkage_issues : list[dict] – issues from data linker
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "06_Data_Quality_Report.xlsx")

    # Combine all issues
    combined = all_quality_issues + linkage_issues

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})
        critical_fmt = workbook.add_format({
            "bg_color": "#FFC7CE", "font_color": "#9C0006",
            "border": 1, "text_wrap": True,
        })
        warning_fmt = workbook.add_format({
            "bg_color": "#FFEB9C", "font_color": "#9C6500",
            "border": 1, "text_wrap": True,
        })

        # ── Sheet 1: All Data Quality Issues ─────────────────────────────
        if combined:
            issues_df = pd.DataFrame(combined)

            # Sort: Critical first
            type_order = {"Critical Mismatch": 0, "Missing Actuals": 1,
                          "Data Mismatch": 2, "Missing Data": 3,
                          "Clarification Required": 4, "Data Note": 5,
                          "Reference Info": 6}
            issues_df["_sort"] = issues_df["issue_type"].map(type_order).fillna(7)
            issues_df = issues_df.sort_values("_sort").drop(columns=["_sort"])

            display_cols = ["file", "issue_type", "field", "count", "details", "action_needed"]
            display = issues_df[display_cols].copy()
            display.columns = ["Source File", "Issue Type", "Field",
                               "Records Affected", "Details", "Action Needed"]

            display.to_excel(writer, sheet_name="All Issues", index=False, startrow=2)

            ws = writer.sheets["All Issues"]
            ws.write(0, 0, "Data Quality Report — All Input Files",
                     workbook.add_format({"bold": True, "font_size": 14, "font_color": "#C00000"}))

            critical_count = len(issues_df[issues_df["issue_type"].str.contains("Critical", na=False)])
            ws.write(1, 0, f"Total issues: {len(display)} ({critical_count} critical)",
                     workbook.add_format({"italic": True, "font_color": "#666666"}))

            for col_idx, col_name in enumerate(display.columns):
                ws.write(2, col_idx, col_name, header_fmt)

            # Color-code rows by severity
            for row_idx in range(len(display)):
                issue_type = display.iloc[row_idx]["Issue Type"]
                if "Critical" in str(issue_type):
                    fmt = critical_fmt
                elif "Missing" in str(issue_type) or "Mismatch" in str(issue_type):
                    fmt = warning_fmt
                else:
                    fmt = text_fmt

                for col_idx in range(len(display.columns)):
                    ws.write(row_idx + 3, col_idx, display.iloc[row_idx, col_idx], fmt)

            ws.set_column(0, 0, 30)
            ws.set_column(1, 1, 22)
            ws.set_column(2, 2, 18)
            ws.set_column(3, 3, 15)
            ws.set_column(4, 4, 60)
            ws.set_column(5, 5, 40)

        # ── Sheet 2: Cross-File Mismatches ───────────────────────────────
        cross_file = [i for i in combined if "Cross-File" in i.get("file", "")]
        if cross_file:
            cf_df = pd.DataFrame(cross_file)
            cf_display = cf_df[["file", "issue_type", "field", "count",
                                "details", "action_needed"]].copy()
            cf_display.columns = ["Source", "Type", "Field",
                                  "Count", "Details", "Action Needed"]

            cf_display.to_excel(writer, sheet_name="Cross-File Mismatches",
                                index=False, startrow=1)
            ws2 = writer.sheets["Cross-File Mismatches"]
            ws2.write(0, 0, "Cross-File Data Mismatches",
                      workbook.add_format({"bold": True, "font_size": 14, "font_color": "#C00000"}))
            for col_idx, col_name in enumerate(cf_display.columns):
                ws2.write(1, col_idx, col_name, header_fmt)
            ws2.set_column(0, len(cf_display.columns)-1, 25)

        # ── Sheet 3: Clarification Needed ────────────────────────────────
        clarification = [i for i in combined
                         if i.get("issue_type") in ["Clarification Required", "Missing Data"]]
        if clarification:
            cl_df = pd.DataFrame(clarification)
            cl_display = cl_df[["file", "field", "count",
                                "details", "action_needed"]].copy()
            cl_display.columns = ["File", "Field", "Count",
                                  "Details", "Action Required"]

            cl_display.to_excel(writer, sheet_name="Human Clarification Needed",
                                index=False, startrow=1)
            ws3 = writer.sheets["Human Clarification Needed"]
            ws3.write(0, 0, "Items Requiring Human Clarification",
                      workbook.add_format({"bold": True, "font_size": 14, "font_color": "#E36C0A"}))
            for col_idx, col_name in enumerate(cl_display.columns):
                ws3.write(1, col_idx, col_name, header_fmt)
            ws3.set_column(0, len(cl_display.columns)-1, 25)

    return filepath
