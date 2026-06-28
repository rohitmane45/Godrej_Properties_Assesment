# Godrej Properties Assessment - AI Site Performance & Cash Flow Agent

## Overview
This project is an automated **AI Site Performance & Cash Flow Agent** developed for the Godrej Properties Assessment. It processes various data sources (Sales, Construction Tracking, Collections, and AOP Targets) to generate comprehensive reports on site performance, cash flow, data quality, and escalation summaries. All processing and calculations are strictly deterministic and run offline.

## Features
- **Data Ingestion & Cleaning:** Automated loading and sanitization of raw Excel files (converting dates, normalizing financial amounts to Crores, filtering noise).
- **Business Logic Processing:**
  - **Data Linker:** Joins Sales and Collections data and validates project alignment.
  - **Business Rules Engine:** Applies 10+ rules covering sales risk, product mix deviations, collections risk, cash-flow leakage, construction delays, and cost overruns.
  - **Cash Flow Engine:** Computes monthly inflows, outflows, and net cash flow against AOP targets.
- **Reporting Engine:** Generates 7 formatted Excel reports with clear insights, actionable plans, and draft communications for stakeholders.

## Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/rohitmane45/Godrej_Properties_Assesment.git
   cd Godrej_Properties_Assesment
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Dependencies include `pandas`, `openpyxl`, and `xlsxwriter`.*

### Running the Solution
Execute the main script to process the input files and generate the reports:
```bash
python main.py
```
*Note: On some Windows systems, you may need to set UTF-8 encoding:*
```powershell
$env:PYTHONIOENCODING='utf-8'; python main.py
```

## System Architecture

The solution follows a structured three-stage pipeline:

1. **Stage 1: Ingestion**
   - Dedicated loaders for each input file.
   - Cleans data, normalizes formats, and flags initial data quality issues.
2. **Stage 2: Processing**
   - Applies deterministic calculations to assess project health.
   - Highlights critical issues (e.g., missing reasons for construction delays, product mix discrepancies).
3. **Stage 3: Reporting**
   - Produces formatted `.xlsx` files with multiple sheets, color-coding, and structured layouts in the `output/` directory.

## Input & Output Data

**Input Files (Root Directory):**
- `AI_Assignment_Input_1_Sales_SANITIZED.xlsx`
- `AI_Assignment_Input_2_Construction_Tracking.xlsx`
- `AI_Assignment_Input_3_Collections_Tracker.xlsx`
- `AI_Assignment_Input_4_AOP_Targets.xlsx`

**Output Reports (Generated in `/output`):**
1. `01_Cash_Flow_Report.xlsx` - Monthly cash flow, AOP variance, overdue details.
2. `02_Progress_Update.xlsx` - Sales, collections, construction, and cost variance.
3. `03_Escalation_Summary.xlsx` - Red/Amber items requiring attention.
4. `04_Owner_Action_Plan.xlsx` - Consolidated tasks grouped by functional owners.
5. `05_Draft_Communications.xlsx` - Ready-to-send emails for stakeholders.
6. `06_Data_Quality_Report.xlsx` - Anomalies, missing data, and mismatches.
7. `07_Month_End_Site_Performance.xlsx` - Leadership KPI summary.

## Limitations & Assumptions
- **Fully Offline Processing:** No external AI APIs or LLMs are used.
- **Dataset Discrepancies:** There are known issues in the provided dataset (e.g., *Aster Grove Residences* actuals do not map to the provided AOP target projects). These are handled and flagged prominently in the `Data Quality Report`.
- **Data Completeness:** Several records are missing owners, carpet area, or valid reasons for delays. These are assessed and logged as data quality observations.

## Tools Used
- **Python** - Core programming language
- **pandas** - Data loading, cleaning, aggregation, merging
- **openpyxl** - Reading `.xlsx` input files
- **xlsxwriter** - Writing formatted Excel output with colours, headers
