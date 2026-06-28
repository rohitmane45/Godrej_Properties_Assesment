"""
main.py
-------
Entry point for the AI Site Performance & Cash Flow Agent.
Orchestrates the full workflow:
  1. Load all 4 input files
  2. Link data across files
  3. Apply business rules
  4. Compute cash flow
  5. Generate all 7 output reports
  6. Print summary

Usage:
    python main.py
"""

import sys
import os

# Make sure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import OUTPUT_DIR, PERIOD_LABEL

# ── Ingestion ────────────────────────────────────────────────────────────────
from ingestion.sales_loader import load_sales
from ingestion.construction_loader import load_construction
from ingestion.collections_loader import load_collections
from ingestion.aop_loader import load_aop_targets

# ── Processing ───────────────────────────────────────────────────────────────
from processing.data_linker import (
    link_sales_to_collections,
    check_project_name_alignment,
    link_construction_to_aop,
)
from processing.business_rules import run_all_rules
from processing.cash_flow_engine import compute_cash_flow

# ── Reporting ────────────────────────────────────────────────────────────────
from reporting.cash_flow_report import generate_cash_flow_report
from reporting.progress_update import generate_progress_update
from reporting.escalation_summary import generate_escalation_summary
from reporting.action_plan import generate_action_plan
from reporting.draft_communications import generate_draft_communications
from reporting.data_quality_report import generate_data_quality_report
from reporting.site_performance_report import generate_site_performance_report


def main():
    print("=" * 70)
    print("  AI SITE PERFORMANCE & CASH FLOW AGENT")
    print(f"  Period: {PERIOD_LABEL}")
    print("=" * 70)

    all_quality_issues = []

    # ─────────────────────────────────────────────────────────────────────
    # STEP 1: LOAD ALL INPUT FILES
    # ─────────────────────────────────────────────────────────────────────
    print("\n[1/5] Loading input files...")

    print("  → Sales data...", end=" ")
    sales_df, sales_issues = load_sales()
    all_quality_issues.extend(sales_issues)
    print(f"OK ({len(sales_df)} rows, {len(sales_issues)} issues)")

    print("  → Construction tracking...", end=" ")
    construction_df, constr_issues = load_construction()
    all_quality_issues.extend(constr_issues)
    print(f"OK ({len(construction_df)} rows, {len(constr_issues)} issues)")

    print("  → Collections tracker...", end=" ")
    collections_df, as_of_date, coll_issues = load_collections()
    all_quality_issues.extend(coll_issues)
    print(f"OK ({len(collections_df)} rows, as of {as_of_date}, {len(coll_issues)} issues)")

    print("  → AOP targets...", end=" ")
    aop_targets, aop_issues = load_aop_targets()
    all_quality_issues.extend(aop_issues)
    print(f"OK ({len(aop_targets)} sheets, {len(aop_issues)} issues)")

    # ─────────────────────────────────────────────────────────────────────
    # STEP 2: LINK DATA ACROSS FILES
    # ─────────────────────────────────────────────────────────────────────
    print("\n[2/5] Linking data across files...")

    linked, unlinked_sales, unlinked_coll, link_issues = \
        link_sales_to_collections(sales_df, collections_df)
    all_quality_issues.extend(link_issues)
    print(f"  → Sales ↔ Collections: {len(linked)} linked rows, "
          f"{len(unlinked_sales)} unlinked sales, {len(unlinked_coll)} unlinked collections")

    project_issues = check_project_name_alignment(sales_df, collections_df, aop_targets)
    all_quality_issues.extend(project_issues)
    if project_issues:
        print(f"  → Project name alignment: {len(project_issues)} mismatches found")

    constr_link_issues = link_construction_to_aop(construction_df, aop_targets)
    all_quality_issues.extend(constr_link_issues)

    linkage_issues = link_issues + project_issues + constr_link_issues

    # ─────────────────────────────────────────────────────────────────────
    # STEP 3: APPLY BUSINESS RULES
    # ─────────────────────────────────────────────────────────────────────
    print("\n[3/5] Applying business rules...")

    all_flags = run_all_rules(sales_df, collections_df, construction_df, aop_targets)

    red_count = sum(1 for f in all_flags if f["severity"] == "Red")
    amber_count = sum(1 for f in all_flags if f["severity"] == "Amber")
    print(f"  → {len(all_flags)} items flagged ({red_count} Red, {amber_count} Amber)")

    # ─────────────────────────────────────────────────────────────────────
    # STEP 4: COMPUTE CASH FLOW
    # ─────────────────────────────────────────────────────────────────────
    print("\n[4/5] Computing cash flow...")

    cash_flow_summary, cash_flow_risks = compute_cash_flow(
        collections_df, construction_df, aop_targets
    )
    print(f"  → {len(cash_flow_summary)} monthly periods analysed")
    print(f"  → {len(cash_flow_risks)} cash flow risks identified")

    # ─────────────────────────────────────────────────────────────────────
    # STEP 5: GENERATE ALL OUTPUT REPORTS
    # ─────────────────────────────────────────────────────────────────────
    print("\n[5/5] Generating output reports...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    reports = []

    print("  → 01 Cash Flow Report...", end=" ")
    path = generate_cash_flow_report(cash_flow_summary, cash_flow_risks,
                                      collections_df, all_flags)
    reports.append(path)
    print("Done")

    print("  → 02 Progress Update...", end=" ")
    path = generate_progress_update(sales_df, collections_df, construction_df,
                                     aop_targets, cash_flow_summary)
    reports.append(path)
    print("Done")

    print("  → 03 Escalation Summary...", end=" ")
    path = generate_escalation_summary(all_flags)
    reports.append(path)
    print("Done")

    print("  → 04 Owner Action Plan...", end=" ")
    path = generate_action_plan(all_flags, aop_targets)
    reports.append(path)
    print("Done")

    print("  → 05 Draft Communications...", end=" ")
    path = generate_draft_communications(sales_df, collections_df, construction_df,
                                          all_flags, cash_flow_summary, aop_targets)
    reports.append(path)
    print("Done")

    print("  → 06 Data Quality Report...", end=" ")
    path = generate_data_quality_report(all_quality_issues, linkage_issues)
    reports.append(path)
    print("Done")

    print("  → 07 Site Performance Report...", end=" ")
    path = generate_site_performance_report(sales_df, collections_df, construction_df,
                                             aop_targets, cash_flow_summary,
                                             cash_flow_risks, all_flags)
    reports.append(path)
    print("Done")

    # ─────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  EXECUTION COMPLETE")
    print("=" * 70)
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print(f"  Reports generated: {len(reports)}")
    for r in reports:
        print(f"    ✓ {os.path.basename(r)}")

    print(f"\n  Data Quality Issues Found: {len(all_quality_issues)}")
    print(f"  Business Rule Flags: {len(all_flags)} ({red_count} Red, {amber_count} Amber)")
    print(f"  Cash Flow Risks: {len(cash_flow_risks)}")

    # Highlight critical findings
    critical = [i for i in all_quality_issues if "Critical" in i.get("issue_type", "")]
    if critical:
        print(f"\n  ⚠ CRITICAL DATA ISSUES:")
        for c in critical:
            print(f"    • {c['details'][:100]}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
