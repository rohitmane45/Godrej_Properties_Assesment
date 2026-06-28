"""
progress_update.py
------------------
Generates the Progress Update Excel output.
Sheet 1: Sales vs Target
Sheet 2: Collections vs Target
Sheet 3: Construction Progress
Sheet 4: Cost Variance
"""

import pandas as pd
import os
from config import (OUTPUT_DIR, SALES_COLS, COLLECTIONS_COLS,
                    CONSTRUCTION_COLS, INR_TO_CR)


def generate_progress_update(sales_df, collections_df, construction_df,
                              aop_targets, cash_flow_summary):
    """Write the Progress Update report to Excel."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "02_Progress_Update.xlsx")

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        pct_fmt = workbook.add_format({"num_format": "0.0%", "border": 1})
        number_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})

        # ── Sheet 1: Sales vs Target ─────────────────────────────────────
        active = sales_df[sales_df[SALES_COLS["sales_stage"]] != "Cancelled"].copy()

        # Monthly booking summary
        monthly_sales = (
            active.groupby("Booking Month")
            .agg(
                Total_Bookings=("Agreement Amount Cr", "count"),
                Booking_Value_Cr=("Agreement Amount Cr", "sum"),
            )
            .reset_index()
        )
        monthly_sales.columns = ["Month", "Units Booked", "Booking Value (Cr)"]

        # Product mix
        type_mapping = {"1 BHK": "1BHK", "2 BHK": "2BHK", "3 BHK": "3BHK", "2.5 BHK": "2.5BHK"}
        active["BHK"] = active[SALES_COLS["unit_type"]].map(type_mapping)
        mix_pivot = active.pivot_table(
            index="Booking Month", columns="BHK", values=SALES_COLS["unit"],
            aggfunc="count", fill_value=0
        ).reset_index()
        mix_pivot.columns.name = None

        sales_summary = pd.merge(monthly_sales, mix_pivot, left_on="Month",
                                  right_on="Booking Month", how="left")
        if "Booking Month" in sales_summary.columns:
            sales_summary = sales_summary.drop(columns=["Booking Month"])

        # Add AOP targets for context
        aop_monthly = (
            aop_targets["sales"]
            .groupby("Month")
            .agg(
                Target_Units=("Total Units Target", "sum"),
                Target_Value=("Booking Value Target", "sum"),
                Target_1BHK=("1BHK Units Target", "sum"),
                Target_2BHK=("2BHK Units Target", "sum"),
                Target_3BHK=("3BHK Units Target", "sum"),
            )
            .reset_index()
        )

        sales_combined = pd.merge(
            sales_summary, aop_monthly, on="Month", how="outer"
        ).fillna(0)

        sales_combined["Achievement %"] = (
            sales_combined["Booking Value (Cr)"] /
            sales_combined["Target_Value"].replace(0, float("nan"))
        )

        sales_combined["Month"] = sales_combined["Month"].apply(
            lambda x: x.strftime("%b-%Y") if hasattr(x, "strftime") else str(x)
        )

        sales_combined.to_excel(writer, sheet_name="Sales vs Target", index=False,
                                startrow=2)
        ws = writer.sheets["Sales vs Target"]
        ws.write(0, 0, "Sales Performance vs AOP Target — Q1 FY27",
                 workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
        ws.write(1, 0, "Note: Actuals are for Aster Grove Residences only; AOP targets cover 5 projects",
                 workbook.add_format({"italic": True, "font_color": "#666666"}))
        for col_idx, col_name in enumerate(sales_combined.columns):
            ws.write(2, col_idx, col_name, header_fmt)
        ws.set_column(0, 0, 12)
        ws.set_column(1, len(sales_combined.columns)-1, 16)

        # ── Sheet 2: Collections vs Target ───────────────────────────────
        coll_monthly = (
            collections_df
            .groupby("Collection Month")
            .agg(
                Total_Demands=("Demand Amount Cr", "count"),
                Demand_Value=("Demand Amount Cr", "sum"),
                Collected=("Collected Cr", "sum"),
                Outstanding=("Outstanding Cr", "sum"),
            )
            .reset_index()
        )
        coll_monthly.columns = ["Month", "No. of Demands", "Demand Value (Cr)",
                                "Collected (Cr)", "Outstanding (Cr)"]

        coll_monthly["Collection Rate %"] = (
            coll_monthly["Collected (Cr)"] /
            coll_monthly["Demand Value (Cr)"].replace(0, float("nan"))
        )

        coll_monthly["Month"] = coll_monthly["Month"].apply(
            lambda x: x.strftime("%b-%Y") if hasattr(x, "strftime") else str(x)
        )

        coll_monthly.to_excel(writer, sheet_name="Collections vs Target", index=False,
                              startrow=1)
        ws2 = writer.sheets["Collections vs Target"]
        ws2.write(0, 0, "Collections Performance — Q1 FY27",
                  workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
        for col_idx, col_name in enumerate(coll_monthly.columns):
            ws2.write(1, col_idx, col_name, header_fmt)
        ws2.set_column(0, len(coll_monthly.columns)-1, 18)

        # ── Sheet 3: Construction Progress ───────────────────────────────
        constr_display = construction_df[[
            CONSTRUCTION_COLS["tower"], CONSTRUCTION_COLS["activity"],
            CONSTRUCTION_COLS["planned_start"], CONSTRUCTION_COLS["planned_finish"],
            CONSTRUCTION_COLS["actual_progress"], CONSTRUCTION_COLS["delay_days"],
            CONSTRUCTION_COLS["delay_reason"], CONSTRUCTION_COLS["linked_milestone"],
            CONSTRUCTION_COLS["owner"],
        ]].copy()

        # Format dates
        for col in [CONSTRUCTION_COLS["planned_start"], CONSTRUCTION_COLS["planned_finish"]]:
            constr_display[col] = constr_display[col].apply(
                lambda x: x.strftime("%d-%b-%Y") if hasattr(x, "strftime") else str(x)
            )

        constr_display.to_excel(writer, sheet_name="Construction Progress", index=False,
                                startrow=1)
        ws3 = writer.sheets["Construction Progress"]
        ws3.write(0, 0, "Construction Progress — R5B Site",
                  workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
        for col_idx, col_name in enumerate(constr_display.columns):
            ws3.write(1, col_idx, col_name, header_fmt)
        ws3.set_column(0, len(constr_display.columns)-1, 18)

        # ── Sheet 4: Cost Variance ───────────────────────────────────────
        cost_data = construction_df[[
            CONSTRUCTION_COLS["tower"], CONSTRUCTION_COLS["activity"],
            CONSTRUCTION_COLS["planned_cost"], CONSTRUCTION_COLS["actual_cost"],
            CONSTRUCTION_COLS["addl_cost"],
        ]].copy()

        cost_data["Total Actual"] = (
            cost_data[CONSTRUCTION_COLS["actual_cost"]].fillna(0) +
            cost_data[CONSTRUCTION_COLS["addl_cost"]].fillna(0)
        )
        cost_data["Variance"] = (
            cost_data["Total Actual"] -
            cost_data[CONSTRUCTION_COLS["planned_cost"]].fillna(0)
        )
        cost_data["Variance %"] = (
            cost_data["Variance"] /
            cost_data[CONSTRUCTION_COLS["planned_cost"]].replace(0, float("nan"))
        )

        cost_data = cost_data.sort_values("Variance", ascending=False)

        cost_data.to_excel(writer, sheet_name="Cost Variance", index=False, startrow=1)
        ws4 = writer.sheets["Cost Variance"]
        ws4.write(0, 0, "Construction Cost Variance Analysis",
                  workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
        for col_idx, col_name in enumerate(cost_data.columns):
            ws4.write(1, col_idx, col_name, header_fmt)
        ws4.set_column(0, len(cost_data.columns)-1, 18)

    return filepath
