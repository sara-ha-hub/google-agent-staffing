# Google Agent Staffing Optimization

DADS 5250: Generative AI in Practice · Module 7 Hackathon

**Goal:** pick the number of agents for every country and month of 2026 that gives Google the highest profit, beat the "keep current staff" plan, and explain the result to a manager with a GenAI app.

## Project steps

| Step | Task | Notebook | Owner | Status |
|---|---|---|---|---|
| 01 | Prepare the data | `notebooks/01_data_preparation.ipynb` | Sara | Done |
| 02 | Forecast demand | `notebooks/02_forecast_demand.ipynb` | Sara | Done |
| 03 | Build the simulator | `notebooks/03_simulator_optimized.ipynb`| Michael | Done |
| 04 | Find the staffing plan | `notebooks/04_Find_Staffing_Plan.ipynb`| Michael & Vinh | Done |
| 05 | Test other demand | `notebooks/05_Test_Other_Demand.ipynb` | Vinh | Done |
| 06 | Build the GenAI layer | | Jay | To do |

Full step descriptions: [`docs/project_steps.pdf`](docs/project_steps.pdf)

## Folder structure

```
google-agent-staffing/
├── data/
│   ├── raw/          original workbook (do not edit)
│   └── clean/        clean CSV files made by the notebooks
├── notebooks/        one notebook per step, numbered 01 to 06
├── docs/             project brief
├── requirements.txt
└── README.md
```

## Data files

| File | Made by | What it holds |
|---|---|---|
| `data/raw/DADS5250_Hackathon_Google_Data.xlsx` | Course | Original workbook: README, salaries and thresholds, advertiser sign-ups, existing staff |
| `data/clean/countries.csv` | Step 01 | One row per country: salary, eligibility threshold, existing agents (Jan 2026) |
| `data/clean/eligible_signups.csv` | Step 01 | One row per eligible advertiser sign-up (2024 and 2025) |
| `data/clean/monthly_eligible_demand.csv` | Step 01 | Per country and month: eligible sign-ups and their average budget |
| `data/clean/forecast_2026.csv` | Step 02 | Per country and month of 2026: forecast eligible sign-ups and the country's average budget |
| `outputs/step03_beergame_genai/monthly_results.csv` | Step 03 | Monthly simulation results: staffing, hires, releases, sign-ups served, backlog, revenue, costs, and profit for the selected country |
| `outputs/step03_beergame_genai/policy_comparison.csv` | Step 03 | Performance comparison of manual, rule-based, GenAI (if enabled), and optimized staffing strategies |
| `outputs/step03_beergame_genai/decision_audit.csv` | Step 03 | Decision history, observed simulation state, proposed staffing actions, applied actions, and GenAI guardrail adjustments |
| `outputs/step03_beergame_genai/profit_maximizing_staffing_plan.csv` | Step 03 | Monthly optimized hiring and release plans for the selected country under profit-only and profit-with-SLA strategies |
| `outputs/step03_beergame_genai/optimization_solver_audit.csv` | Step 03 | Optimization status, solver diagnostics, objective values, and validation metrics |
| `outputs/step03_beergame_genai/all_22_countries_optimized_plans.csv` | Step 03 | Optimized monthly hiring and release plans for all 22 countries under both optimization strategies |
| `outputs/step03_beergame_genai/country_profit_service_comparison.csv` | Step 03 | Country-level profit, revenue, staffing costs, hiring, and service-rate comparisons |
| `outputs/step03_beergame_genai/all_country_profit_summary.csv` | Step 03 | Aggregated profit, revenue, cost, hiring, and service performance across all 22 countries |
| `outputs/step03_beergame_genai/all_country_optimizer_audit.csv` | Step 03 | Solver results and validation metrics for all 44 country-level optimization runs |
| `data/clean/staffing_plan_98_sla.csv` | Step 04 | Monthly hiring and release plan targeting at least 98% annual service in each country |
| `data/clean/staffing_plan_profit.csv` | Step 04 | Monthly hiring and release plan maximizing modeled profit without a minimum service target |
| `data/clean/demand_sensitivily_analysis_results.csv` | Step 05 | 	Detailed profit, service, abandonment, and backlog results by country, demand scenario, and mode |
| `data/clean/demand_sensitivily_analysis_summary.csv` | Step 05 | Overall profit and service comparison across low, base, and high demand for all three modes |

**Inputs for Step 03:** `countries.csv` and `forecast_2026.csv`.

## How to run

1. Install the packages:
   ```
   pip install -r requirements.txt
   ```
2. Open the notebooks from the `notebooks/` folder and run them in order (01, 02, ...). Paths are relative to that folder, for example `../data/clean/`.

## Team rules

- Put each new notebook in `notebooks/` with its step number, for example `03_simulator.ipynb`.
- Save outputs to `data/clean/` and add the file to the **Data files** table above.
- Never edit files in `data/raw/`.
- Run your notebook top to bottom before you commit, so the saved outputs are up to date.

## Deliverables

Executed notebook · short report · 3-minute demo video
