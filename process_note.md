# Process Note — AI Site Performance & Cash Flow Agent

## 1. Setup Instructions

### Prerequisites
- Python 3.10 or higher (tested on Python 3.13.5)
- pip (Python package manager)

### Installation
```bash
# Navigate to the project directory
cd "D:\Projects\Godrej Properties"

# Install dependencies
pip install -r requirements.txt
```

The only libraries needed are:
- **pandas** (>=2.0) – data manipulation and analysis
- **openpyxl** (>=3.1) – reading .xlsx input files
- **xlsxwriter** (>=3.2) – writing formatted Excel output files

### Running the Solution
```bash
python main.py
```

On some Windows systems, you may need to set UTF-8 encoding:
```powershell
$env:PYTHONIOENCODING='utf-8'; python main.py
```

The script reads all 4 input files from the project directory and generates 7 output Excel files in the `output/` folder.

---

## 2. How It Works

The solution follows a three-stage pipeline:

### Stage 1: Ingestion
Each of the 4 input files has its own loader module that:
- Reads the Excel file with the correct header row offset
- Converts Excel serial dates to proper datetime objects
- Converts financial amounts from raw INR to INR Crores (for AOP comparison)
- Cleans messy data (filters out daily-target noise rows in Construction file)
- Flags data quality issues found during loading

### Stage 2: Processing
Three engines process the cleaned data:
1. **Data Linker** – joins Sales and Collections by Unit Number, checks project name alignment across all files, identifies mismatches
2. **Business Rules Engine** – applies 10+ rules (sales risk, product mix, collections risk, overdue, cash-flow leakage, construction delays, missing reasons, cost overruns, cross-functional escalation)
3. **Cash Flow Engine** – computes monthly inflows (collections), outflows (construction cost), net cash flow, and compares against AOP NCF targets

### Stage 3: Reporting
Seven report generators produce formatted Excel files, each with multiple sheets, headers, colour-coding, and column widths set for readability.

---

## 3. Tools Used

| Tool | Purpose |
|------|---------|
| Python 3.13 | Core programming language |
| pandas | Data loading, cleaning, aggregation, merging |
| openpyxl | Reading .xlsx input files |
| xlsxwriter | Writing formatted Excel output with colours, headers |

**No external AI APIs or LLMs are used for calculations.** All business rules, thresholds, and comparisons are implemented deterministically through code. The solution is fully offline and reproducible.

---

## 4. Assumptions Made

1. **Financial Units**: AOP targets are in INR Crores. Sales/Collections raw data is in INR. We convert raw INR to Cr by dividing by 1,00,00,000 (1e7) for comparison.

2. **Date Handling**: The Sales file stores dates as Excel serial numbers (e.g., 46080 = a date in 2026). We convert these using the standard Excel epoch (1899-12-30).

3. **Cancelled Bookings**: Bookings with Sales Stage = "Cancelled" are excluded from sales achievement calculations but kept in the data for audit purposes.

4. **2.5 BHK Units**: The Sales data has "2.5 BHK" units which do not exist in AOP targets (only 1BHK/2BHK/3BHK). These are flagged as a data quality issue rather than force-mapped to another type.

5. **Construction Project Mapping**: The Construction file title says "R5B Construction Tracking" but has no Project Name column. Towers T4–T7 do not match any AOP project towers. We treat this as standalone data and flag the gap.

6. **Monthly Aggregation**: For Sales, we use Booking Date to determine the month. For Collections, we use Demand Raised Date. For Construction, we use Planned Start date as a proxy.

7. **Cost Overrun Calculation**: Total actual cost = Actual Cost + Additional Cost Expected. Overrun % = (Total Actual − Planned) / Planned.

8. **Collection Efficiency**: Calculated as Amount Collected / Demand Amount, not against Agreement Value.

---

## 5. Limitations

1. **Project Name Mismatch**: The actual Sales and Collections data is for "Aster Grove Residences", but AOP targets reference 5 different projects (Eden Square, Aurora Heights, Vista Grove, Palm Vista, Riverstone Park). This means we cannot do a direct project-level actual-vs-target comparison. This is flagged prominently in the Data Quality Report.

2. **Construction-AOP Linkage**: Without a project name in the Construction file and with non-overlapping tower identifiers, construction data cannot be compared against AOP CoC targets at the tower level.

3. **No Time-Series Forecasting**: The solution calculates actuals vs targets but does not project future performance. A forecasting model could be added as an enhancement.

4. **Single-Period Data**: The input data appears to cover partial Q1 FY27. A full quarter of data would give more meaningful trend analysis.

5. **No Automated Data Refresh**: The solution reads static Excel files. Integration with live data sources (SAP, CRM) would require API connectors.

---

## 6. Key Data Quality Observations

| # | Finding | Severity |
|---|---------|----------|
| 1 | "Aster Grove Residences" not in AOP targets; 5 AOP projects have no actuals | Critical |
| 2 | Construction file has no project name column | Critical |
| 3 | Tower identifiers don't match (T4-T7 vs T1-T3, A, B, P1, P2) | Critical |
| 4 | 13 sales records missing Sales Owner | Medium |
| 5 | All 80 sales records missing Carpet Area | Medium |
| 6 | 19 collection records missing Sales Owner | Medium |
| 7 | Construction activities with delay but no reason provided | Medium |
| 8 | "2.5 BHK" unit type not in AOP product mix targets | Low |
| 9 | 48 sales records missing Broker Account Name | Low |

---

## 7. Dependencies

```
pandas>=2.0
openpyxl>=3.1
xlsxwriter>=3.2
```

No other system dependencies. No database required. No internet connection needed.

---

## 8. Output Files Generated

| # | File | Description |
|---|------|-------------|
| 1 | `01_Cash_Flow_Report.xlsx` | Monthly cash flow, AOP variance, overdue details |
| 2 | `02_Progress_Update.xlsx` | Sales, collections, construction, cost variance |
| 3 | `03_Escalation_Summary.xlsx` | Red/Amber items with owners and actions |
| 4 | `04_Owner_Action_Plan.xlsx` | Actions grouped by function (Sales, Collections, etc.) |
| 5 | `05_Draft_Communications.xlsx` | Ready-to-send email drafts for stakeholders |
| 6 | `06_Data_Quality_Report.xlsx` | Missing data, mismatches, clarification needed |
| 7 | `07_Month_End_Site_Performance.xlsx` | CBE-style leadership summary with KPIs |
