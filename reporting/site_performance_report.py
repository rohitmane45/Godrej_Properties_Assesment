"""
site_performance_report.py
--------------------------
Generates the Month-End Site Performance Report (CBE-style).
This is the leadership summary that brings everything together.
"""

import pandas as pd
import os
from config import (OUTPUT_DIR, SALES_COLS, COLLECTIONS_COLS,
                    CONSTRUCTION_COLS, INR_TO_CR, PERIOD_LABEL)


def generate_site_performance_report(sales_df, collections_df, construction_df,
                                      aop_targets, cash_flow_summary,
                                      cash_flow_risks, all_flags):
    """Write the Month-End Site Performance Report to Excel."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "07_Month_End_Site_Performance.xlsx")

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        title_fmt = workbook.add_format({
            "bold": True, "font_size": 16, "font_color": "#1F4E79",
        })
        subtitle_fmt = workbook.add_format({
            "bold": True, "font_size": 12, "font_color": "#1F4E79",
        })
        kpi_label_fmt = workbook.add_format({
            "bold": True, "bg_color": "#D6E4F0", "border": 1,
            "font_size": 11,
        })
        kpi_value_fmt = workbook.add_format({
            "bold": True, "border": 1, "font_size": 14,
            "num_format": "#,##0.00", "align": "center",
        })
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})

        # =====================================================================
        # SHEET 1: EXECUTIVE SUMMARY DASHBOARD
        # =====================================================================
        ws = workbook.add_worksheet("Executive Summary")

        ws.write(0, 0, f"Month-End Site Performance Report", title_fmt)
        ws.write(1, 0, f"Period: {PERIOD_LABEL}", subtitle_fmt)
        ws.write(2, 0, f"Project Data Available: Aster Grove Residences",
                 workbook.add_format({"italic": True, "font_color": "#666666"}))

        # ── KPI Section ──────────────────────────────────────────────────
        row = 4
        ws.write(row, 0, "KEY PERFORMANCE INDICATORS", subtitle_fmt)
        row += 1

        active_sales = sales_df[sales_df[SALES_COLS["sales_stage"]] != "Cancelled"]
        total_bookings = len(active_sales)
        total_booking_value = active_sales["Agreement Amount Cr"].sum()
        total_collected = collections_df["Collected Cr"].sum()
        total_outstanding = collections_df["Outstanding Cr"].sum()
        total_demands = collections_df["Demand Amount Cr"].sum()
        collection_rate = (total_collected / total_demands * 100) if total_demands > 0 else 0

        # Construction metrics
        total_activities = len(construction_df)
        completed_activities = len(construction_df[
            construction_df[CONSTRUCTION_COLS["actual_progress"]] >= 100
        ])
        delayed_activities = len(construction_df[
            construction_df[CONSTRUCTION_COLS["delay_days"]] > 15
        ])
        avg_progress = construction_df[CONSTRUCTION_COLS["actual_progress"]].mean()

        total_planned_cost = construction_df[CONSTRUCTION_COLS["planned_cost"]].sum()
        total_actual_cost = (
            construction_df[CONSTRUCTION_COLS["actual_cost"]].fillna(0).sum() +
            construction_df[CONSTRUCTION_COLS["addl_cost"]].fillna(0).sum()
        )
        cost_variance_pct = ((total_actual_cost - total_planned_cost) / total_planned_cost * 100
                             if total_planned_cost > 0 else 0)

        # NCF
        ncf_actual = cash_flow_summary["Net Cash Flow (Cr)"].sum() if "Net Cash Flow (Cr)" in cash_flow_summary.columns else 0

        kpis = [
            ("Total Active Bookings", total_bookings, "units"),
            ("Booking Value (Cr)", round(total_booking_value, 2), "Cr"),
            ("Total Collected (Cr)", round(total_collected, 2), "Cr"),
            ("Total Outstanding (Cr)", round(total_outstanding, 2), "Cr"),
            ("Collection Efficiency", f"{collection_rate:.1f}%", ""),
            ("Construction Activities", total_activities, ""),
            ("Completed Activities", completed_activities, ""),
            ("Delayed Activities (>15d)", delayed_activities, ""),
            ("Avg Construction Progress", f"{avg_progress:.1f}%", ""),
            ("Cost Variance", f"{cost_variance_pct:.1f}%", ""),
            ("Net Cash Flow (Cr)", round(ncf_actual, 2), "Cr"),
        ]

        for i, (label, value, unit) in enumerate(kpis):
            col = (i % 3) * 2
            kpi_row = row + (i // 3) * 2

            ws.write(kpi_row, col, label, kpi_label_fmt)
            ws.write(kpi_row, col + 1, f"{value} {unit}".strip(), kpi_value_fmt)

        ws.set_column(0, 5, 22)

        # ── Risk Summary ─────────────────────────────────────────────────
        risk_row = row + 10
        ws.write(risk_row, 0, "RISK SUMMARY", subtitle_fmt)
        risk_row += 1

        red_flags = [f for f in all_flags if f["severity"] == "Red"]
        amber_flags = [f for f in all_flags if f["severity"] == "Amber"]

        ws.write(risk_row, 0, "Red Items", kpi_label_fmt)
        ws.write(risk_row, 1, len(red_flags), workbook.add_format({
            "bold": True, "font_color": "#C00000", "border": 1, "font_size": 14, "align": "center"}))
        ws.write(risk_row, 2, "Amber Items", kpi_label_fmt)
        ws.write(risk_row, 3, len(amber_flags), workbook.add_format({
            "bold": True, "font_color": "#E36C0A", "border": 1, "font_size": 14, "align": "center"}))

        # ── Top Risks List ───────────────────────────────────────────────
        risk_row += 2
        ws.write(risk_row, 0, "TOP RISKS", subtitle_fmt)
        risk_row += 1

        for i, flag in enumerate(red_flags[:8]):
            ws.write(risk_row + i, 0, flag.get("area", ""), text_fmt)
            ws.write(risk_row + i, 1, flag.get("description", ""), text_fmt)
            ws.write(risk_row + i, 2, flag.get("owner", ""), text_fmt)
            ws.write(risk_row + i, 3, flag.get("suggested_action", ""), text_fmt)

        # =====================================================================
        # SHEET 2: DECISION ITEMS
        # =====================================================================
        decisions = aop_targets.get("decisions")
        if decisions is not None and len(decisions) > 0:
            dec_display = decisions.copy()
            # Handle rupee symbol
            for col in dec_display.columns:
                dec_display[col] = dec_display[col].apply(
                    lambda x: str(x).replace('\u20b9', 'INR ') if isinstance(x, str) else x
                )

            dec_display.to_excel(writer, sheet_name="Decision Items", index=False,
                                 startrow=1)
            ws_dec = writer.sheets["Decision Items"]
            ws_dec.write(0, 0, "Leadership Decision Items",
                         workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
            for col_idx, col_name in enumerate(dec_display.columns):
                ws_dec.write(1, col_idx, col_name, header_fmt)
            ws_dec.set_column(0, 0, 45)
            ws_dec.set_column(1, len(dec_display.columns)-1, 22)

        # =====================================================================
        # SHEET 3: PROJECT-WISE SUMMARY (from AOP perspective)
        # =====================================================================
        aop_sales = aop_targets["sales"].copy()
        project_summary = aop_sales.groupby("Project Name").agg(
            Target_Units=("Total Units Target", "sum"),
            Target_Value=("Booking Value Target", "sum"),
            Sales_Head=("Sales Head", "first"),
        ).reset_index()

        project_summary["Actual Data Available"] = project_summary["Project Name"].apply(
            lambda p: "Yes" if p in sales_df[SALES_COLS["project"]].unique() else "No — Data Missing"
        )

        project_summary.to_excel(writer, sheet_name="Project Summary", index=False,
                                  startrow=1)
        ws_proj = writer.sheets["Project Summary"]
        ws_proj.write(0, 0, "Project-wise AOP Target Summary",
                      workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
        for col_idx, col_name in enumerate(project_summary.columns):
            ws_proj.write(1, col_idx, col_name, header_fmt)
        ws_proj.set_column(0, len(project_summary.columns)-1, 22)

    return filepath
