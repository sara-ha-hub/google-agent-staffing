# Google Agent Staffing Optimization

DADS 5250: Generative AI in Practice · Module 7 Hackathon

## About the project

Google uses support agents to help new advertisers get started, but only advertisers whose projected annual budget is above their country's threshold qualify for this help. This project plans how many agents Google should have in each of 22 countries for every month of 2026. We clean the 2024 and 2025 sign-up data, keep only eligible advertisers, and forecast eligible sign-ups for each country and month of 2026. A Beer Game style simulator then turns any staffing plan into cost, revenue, profit, and service rate, and an integer programming optimizer picks the monthly hires and releases with the highest modeled profit, with an optional 98% service target (SLA). The plan must beat keeping the January 2026 headcount all year, and it is tested again with 20% lower and 20% higher demand. Finally, a Streamlit app lets a manager ask questions in plain English: a LangGraph agent calls the forecast, simulator, and optimizer as tools and explains the answer without inventing numbers.

**Objectives:**
- Forecast eligible advertiser sign-ups for every country and month of 2026.
- Find the monthly staffing plan with the highest modeled profit, with or without a 98% service target.
- Beat the "keep current staff" plan and check that the result holds when demand changes.
- Explain the results to a manager through a GenAI app.

## Project steps

| Step | Task | Main file | Owner | Status |
|---|---|---|---|---|
| 01 | Prepare the data | `notebooks/01_data_preparation.ipynb` | Sara | Done |
| 02 | Forecast demand | `notebooks/02_forecast_demand.ipynb` | Sara | Done |
| 03 | Build the simulator | `notebooks/03_simulator_optimized.ipynb`| Michael | Done |
| 04 | Find the staffing plan | `notebooks/04_Find_Staffing_Plan.ipynb`| Michael & Vinh | Done |
| 05 | Test other demand | `notebooks/05_Test_Other_Demand.ipynb` | Vinh | Done |
| 06 | Build the GenAI layer | `genai/app.py` (Streamlit app) | Jay | Done |

Full step descriptions: [`docs/project_steps.pdf`](docs/project_steps.pdf)

## Folder structure

```
google-agent-staffing/
├── data/
│   ├── raw/                  original workbook (do not edit)
│   └── clean/                clean CSV files made by the notebooks
├── notebooks/                one notebook per step, numbered 01 to 05
├── staffing_engine/          simulator and optimizer from notebooks 03-05, as a Python package
├── genai/                    step 06: LangGraph agent, tools, and Streamlit app (app.py)
├── frontend/                 optional web page (HTML + FastAPI) for the same agent
├── tests/                    automated tests for the engine and the Gemini connection
├── docs/                     project brief
├── .streamlit/               Streamlit settings
├── requirements.txt          packages for the notebooks
├── requirements-genai.txt    packages for the GenAI app
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
| `data/clean/monthly_results.csv` | Step 03 | Monthly simulation results: staffing, hires, releases, sign-ups served, backlog, revenue, costs, and profit for the selected country |
| `data/clean/policy_comparison.csv` | Step 03 | Performance comparison of manual, rule-based, GenAI (if enabled), and optimized staffing strategies |
| `data/clean/decision_audit.csv` | Step 03 | Decision history, observed simulation state, proposed staffing actions, applied actions, and GenAI guardrail adjustments |
| `data/clean/profit_maximizing_staffing_plan.csv` | Step 03 | Monthly optimized hiring and release plans for the selected country under profit-only and profit-with-SLA strategies |
| `data/clean/optimization_solver_audit.csv` | Step 03 | Optimization status, solver diagnostics, objective values, and validation metrics |
| `data/clean/all_22_countries_optimized_plans.csv` | Step 03 | Optimized monthly hiring and release plans for all 22 countries under both optimization strategies |
| `data/clean/country_profit_service_comparison.csv` | Step 03 | Country-level profit, revenue, staffing costs, hiring, and service-rate comparisons |
| `data/clean/all_country_profit_summary.csv` | Step 03 | Aggregated profit, revenue, cost, hiring, and service performance across all 22 countries |
| `data/clean/all_country_optimizer_audit.csv` | Step 03 | Solver results and validation metrics for all 44 country-level optimization runs |
| `data/clean/staffing_plan_98_sla.csv` | Step 04 | Monthly hiring and release plan targeting at least 98% annual service in each country |
| `data/clean/staffing_plan_profit.csv` | Step 04 | Monthly hiring and release plan maximizing modeled profit without a minimum service target |
| `data/clean/demand_sensitivily_analysis_results.csv` | Step 05 | Detailed profit, service, abandonment, and backlog results by country, demand scenario, and mode |
| `data/clean/demand_sensitivily_analysis_summary.csv` | Step 05 | Overall profit and service comparison across low, base, and high demand for all three modes |

**Inputs for Step 03:** `countries.csv` and `forecast_2026.csv`.

## How to run

**Notebooks**

1. Install the packages:
   ```
   pip install -r requirements.txt
   ```
2. Notebooks 01 and 02 run locally from the `notebooks/` folder. Paths are relative to that folder, for example `../data/clean/`.
3. Notebooks 03 to 05 were built for Google Colab. When you run them, upload `data/clean/countries.csv` and `data/clean/forecast_2026.csv` when the notebook asks.

**GenAI app (step 06)**

1. From the repository root, install the packages (Python 3.10 or newer):
   ```
   pip install -r requirements-genai.txt
   ```
2. Start the app:
   ```
   streamlit run genai/app.py
   ```
3. Open the local address Streamlit prints (usually http://localhost:8501), paste a Gemini API key under **Options**, and ask a question, for example: `What is the best staffing plan for USA in 2026?`

More details, including the tools and tests, are in [`genai/README.md`](genai/README.md).

## Team rules

- Put each new notebook in `notebooks/` with its step number, for example `03_simulator.ipynb`.
- Save outputs to `data/clean/` and add the file to the **Data files** table above.
- Never edit files in `data/raw/`.
- Run your notebook top to bottom before you commit, so the saved outputs are up to date.

## Deliverables

Executed notebook · short report · 3-minute demo video
