"""
draft_communications.py
-----------------------
Generates draft email / Teams messages for key stakeholders.
These are template-based, populated with actual data from the analysis.
"""

import pandas as pd
import os
from config import OUTPUT_DIR, SALES_COLS, COLLECTIONS_COLS, OVERDUE_DAYS_PRIORITY


def generate_draft_communications(sales_df, collections_df, construction_df,
                                   all_flags, cash_flow_summary, aop_targets):
    """Write draft communications to Excel."""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "05_Draft_Communications.xlsx")

    drafts = []

    # ── 1. Sales Head: Booking Shortfall Alert ───────────────────────────
    sales_flags = [f for f in all_flags if f["area"] == "Sales" and "Booking Value" in f.get("metric", "")]
    if sales_flags:
        flag = sales_flags[0]
        sales_heads = aop_targets["sales"]["Sales Head"].unique().tolist()
        drafts.append({
            "Recipient": f"Sales Heads ({', '.join(sales_heads)})",
            "Subject": f"[Action Required] Booking Value Below Target — {flag['month']}",
            "Channel": "Email",
            "Message": (
                f"Hi Team,\n\n"
                f"This is to flag that the monthly booking value for {flag['month']} "
                f"stands at {flag['actual']:.2f} Cr against the AOP target of {flag['target']:.2f} Cr "
                f"({flag['achievement_pct']:.1f}% achievement).\n\n"
                f"This is below the {flag['threshold']} threshold and needs immediate attention.\n\n"
                f"Suggested Actions:\n"
                f"- Review the current pipeline for near-closure deals\n"
                f"- Activate channel partner network for additional leads\n"
                f"- Evaluate pricing adjustments for slow-moving inventory\n\n"
                f"Please share your recovery plan by EOD tomorrow.\n\n"
                f"Regards,\nSite Performance Team"
            ),
            "Priority": "High",
        })

    # ── 2. Collections Team: Overdue Follow-Up ───────────────────────────
    overdue_flags = [f for f in all_flags
                     if f["area"] == "Collections" and "Overdue" in f.get("metric", "")]
    if overdue_flags:
        overdue_count = len(overdue_flags)
        total_outstanding = collections_df[
            collections_df[COLLECTIONS_COLS["days_overdue"]] > OVERDUE_DAYS_PRIORITY
        ][COLLECTIONS_COLS["outstanding"]].sum()

        coll_owners = collections_df[COLLECTIONS_COLS["coll_owner"]].dropna().unique().tolist()

        drafts.append({
            "Recipient": f"Collections Team ({', '.join(coll_owners[:3])}...)",
            "Subject": f"[Urgent] {overdue_count} Overdue Collections — Follow-Up Required",
            "Channel": "Email",
            "Message": (
                f"Hi Collections Team,\n\n"
                f"We have identified {overdue_count} collection demands that are overdue "
                f"by more than {OVERDUE_DAYS_PRIORITY} days, with a total outstanding of "
                f"INR {total_outstanding:,.0f}.\n\n"
                f"Please prioritise follow-ups with the following approach:\n"
                f"- Customers overdue > 60 days: Personal call + escalation to Sales Owner\n"
                f"- Customers overdue 30-60 days: Reminder email + phone follow-up\n"
                f"- Ensure updated status in the tracker by end of week\n\n"
                f"The detailed overdue list is attached in the Cash Flow Report.\n\n"
                f"Regards,\nSite Performance Team"
            ),
            "Priority": "High",
        })

    # ── 3. Construction Head: Delay Escalation ───────────────────────────
    constr_flags = [f for f in all_flags if f["area"] == "Construction" and "Delay" in f.get("metric", "")]
    if constr_flags:
        severe_delays = [f for f in constr_flags if f["severity"] == "Red"]
        drafts.append({
            "Recipient": "Construction Head / Project Director",
            "Subject": f"[Escalation] {len(constr_flags)} Construction Delays Flagged",
            "Channel": "Email / Teams",
            "Message": (
                f"Hi,\n\n"
                f"The monthly review has flagged {len(constr_flags)} construction activities "
                f"with delays exceeding {15} days. "
                f"{'Of these, ' + str(len(severe_delays)) + ' are critical (>30 days).' if severe_delays else ''}\n\n"
                f"Key issues identified:\n" +
                "\n".join(f"- {f['description']}" for f in constr_flags[:5]) +
                f"\n\nPlease:\n"
                f"1. Provide delay reasons where missing (flagged separately)\n"
                f"2. Submit a recovery plan for activities delayed > 15 days\n"
                f"3. Assess downstream impact on collection milestones\n\n"
                f"Regards,\nSite Performance Team"
            ),
            "Priority": "High" if severe_delays else "Medium",
        })

    # ── 4. Leadership: Month-End Summary ─────────────────────────────────
    red_flags = [f for f in all_flags if f["severity"] == "Red"]
    amber_flags = [f for f in all_flags if f["severity"] == "Amber"]

    drafts.append({
        "Recipient": "Site Head / Project Director",
        "Subject": f"[Monthly Review] Q1 FY27 Site Performance Summary",
        "Channel": "Email",
        "Message": (
            f"Dear Leadership,\n\n"
            f"Please find below the key highlights from the monthly site performance review:\n\n"
            f"ESCALATION SUMMARY:\n"
            f"- Red items: {len(red_flags)}\n"
            f"- Amber items: {len(amber_flags)}\n\n"
            f"KEY AREAS OF CONCERN:\n"
            f"{''.join(chr(10) + '- ' + f['description'] for f in red_flags[:5])}\n\n"
            f"DATA QUALITY NOTE:\n"
            f"- Sales and Collections data is available for Aster Grove Residences only\n"
            f"- AOP targets reference 5 projects — actuals for 4 projects are missing\n"
            f"- Construction file lacks project name, limiting cross-reference capability\n\n"
            f"Detailed reports are attached. Please review and confirm "
            f"action items in the Owner-wise Action Plan.\n\n"
            f"Regards,\nSite Performance Team"
        ),
        "Priority": "High",
    })

    # ── 5. Finance: Cost Overrun Alert ───────────────────────────────────
    cost_flags = [f for f in all_flags if "Cost" in f.get("area", "")]
    if cost_flags:
        drafts.append({
            "Recipient": "Finance Lead",
            "Subject": f"[Review] {len(cost_flags)} Cost Overrun Items Flagged",
            "Channel": "Email",
            "Message": (
                f"Hi Finance Team,\n\n"
                f"{len(cost_flags)} construction activities have been flagged for cost overruns "
                f"exceeding 10% of planned budget.\n\n"
                f"Details:\n" +
                "\n".join(f"- {f['description']}" for f in cost_flags[:5]) +
                f"\n\nPlease review and confirm:\n"
                f"1. Whether provisions have been made in the Q1 forecast\n"
                f"2. Vendor renegotiation opportunities\n"
                f"3. Impact on NCF projections\n\n"
                f"Regards,\nSite Performance Team"
            ),
            "Priority": "Medium",
        })

    # ── Write to Excel ───────────────────────────────────────────────────
    drafts_df = pd.DataFrame(drafts)

    with pd.ExcelWriter(filepath, engine="xlsxwriter",
                         engine_kwargs={"options": {"nan_inf_to_errors": True}}) as writer:
        workbook = writer.book

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E79", "font_color": "white",
            "border": 1, "text_wrap": True, "valign": "vcenter",
        })
        text_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})

        drafts_df.to_excel(writer, sheet_name="Draft Messages", index=False, startrow=2)

        ws = writer.sheets["Draft Messages"]
        ws.write(0, 0, "Draft Communications for Stakeholders",
                 workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E79"}))
        ws.write(1, 0, "These are draft messages — review and customise before sending",
                 workbook.add_format({"italic": True, "font_color": "#666666"}))

        for col_idx, col_name in enumerate(drafts_df.columns):
            ws.write(2, col_idx, col_name, header_fmt)

        ws.set_column(0, 0, 30)   # Recipient
        ws.set_column(1, 1, 45)   # Subject
        ws.set_column(2, 2, 12)   # Channel
        ws.set_column(3, 3, 80)   # Message
        ws.set_column(4, 4, 10)   # Priority

        # Set row heights for messages
        for row_idx in range(len(drafts_df)):
            ws.set_row(row_idx + 3, 150)

    return filepath
