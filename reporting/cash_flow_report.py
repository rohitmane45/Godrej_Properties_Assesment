"""
cash_flow_report.py
-------------------
Generates the Cash Flow Report Excel output.
Sheet 1: Monthly cash flow summary with AOP comparison
Sheet 2: Cash flow risks
Sheet 3: Overdue collections detail
"""

import pandas as pd
import os
from config import OUTPUT_DIR, COLLECTIONS_COLS, OVERDUE_DAYS_PRIORITY


def generate_cash_flow_report(cash_flow_summary, cash_flow_risks,
                               collections_df, all_flags):
    """Write the Cash Flow Report to Excel."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "01_Cash_Flow_Report.xlsx")

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        # ── Formats ──────────────────────────────────────────────────────
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        number_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})
        red_fmt = workbook.add_format({
            "num_format": "#,##0.00", "border": 1,
            "bg_color": "#FFC7CE", "font_color": "#9C0006"
        })
        green_fmt = workbook.add_format({
            "num_format": "#,##0.00", "border": 1,
            "bg_color": "#C6EFCE", "font_color": "#006100"
        })

        # ── Sheet 1: Monthly Cash Flow Summary ──────────────────────────
        cf = cash_flow_summary.copy()
        # Format month column
        cf["Month"] = cf["Month"].apply(
            lambda x: x.strftime("%b-%Y") if hasattr(x, "strftime") else str(x)
        )

        display_cols = [
            "Month", "Collections Inflow (Cr)", "Total Outflow – CoC (Cr)",
            "Net Cash Flow (Cr)", "Target_NCF", "NCF Variance (Cr)",
            "Target_Collection", "Collection Variance (Cr)",
            "Outstanding (Cr)",
        ]
        available_cols = [c for c in display_cols if c in cf.columns]
        cf_display = cf[available_cols]

        # Rename for readability
        rename_map = {
            "Target_NCF": "AOP NCF Target (Cr)",
            "Target_Collection": "AOP Collection Target (Cr)",
        }
        cf_display = cf_display.rename(columns=rename_map)

        cf_display.to_excel(writer, sheet_name="Monthly Cash Flow", index=False,
                            startrow=1)

        ws = writer.sheets["Monthly Cash Flow"]
        ws.write(0, 0, "Cash Flow Summary — Q1 FY27", workbook.add_format({
            "bold": True, "font_size": 14, "font_color": "#1F4E79"
        }))

        # Apply header format
        for col_idx, col_name in enumerate(cf_display.columns):
            ws.write(1, col_idx, col_name, header_fmt)
        ws.set_column(0, 0, 12)
        ws.set_column(1, len(cf_display.columns)-1, 18)

        # ── Sheet 2: Cash Flow Risks ────────────────────────────────────
        if cash_flow_risks:
            risks_df = pd.DataFrame(cash_flow_risks)
            risks_df.to_excel(writer, sheet_name="Cash Flow Risks", index=False,
                              startrow=1)
            ws2 = writer.sheets["Cash Flow Risks"]
            ws2.write(0, 0, "Cash Flow Risks Identified", workbook.add_format({
                "bold": True, "font_size": 14, "font_color": "#C00000"
            }))
            for col_idx, col_name in enumerate(risks_df.columns):
                ws2.write(1, col_idx, col_name, header_fmt)
            ws2.set_column(0, 0, 12)
            ws2.set_column(1, len(risks_df.columns)-1, 22)

        # ── Sheet 3: Overdue Collections Detail ─────────────────────────
        overdue = collections_df[
            collections_df[COLLECTIONS_COLS["days_overdue"]] > OVERDUE_DAYS_PRIORITY
        ].copy()

        if len(overdue) > 0:
            display = overdue[[
                COLLECTIONS_COLS["project"], COLLECTIONS_COLS["unit"],
                COLLECTIONS_COLS["customer_name"], COLLECTIONS_COLS["milestone"],
                COLLECTIONS_COLS["demand_amount"], COLLECTIONS_COLS["collected"],
                COLLECTIONS_COLS["outstanding"], COLLECTIONS_COLS["days_overdue"],
                COLLECTIONS_COLS["status"], COLLECTIONS_COLS["coll_owner"],
            ]].copy()

            display = display.sort_values(COLLECTIONS_COLS["days_overdue"], ascending=False)

            display.to_excel(writer, sheet_name="Overdue Details", index=False,
                             startrow=1)
            ws3 = writer.sheets["Overdue Details"]
            ws3.write(0, 0, f"Overdue Collections (>{OVERDUE_DAYS_PRIORITY} days)",
                      workbook.add_format({
                          "bold": True, "font_size": 14, "font_color": "#C00000"
                      }))
            for col_idx, col_name in enumerate(display.columns):
                ws3.write(1, col_idx, col_name, header_fmt)
            ws3.set_column(0, len(display.columns)-1, 18)

    return filepath
