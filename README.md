# Google Agent Staffing Optimization

DADS 5250: Generative AI in Practice · Module 7 Hackathon

**Goal:** pick the number of agents for every country and month of 2026 that gives Google the highest profit, beat the "keep current staff" plan, and explain the result to a manager with a GenAI app.

## Project steps

| Step | Task | Notebook | Owner | Status |
|---|---|---|---|---|
| 01 | Prepare the data | `notebooks/01_data_preparation.ipynb` | Sara | Done |
| 02 | Forecast demand | `notebooks/02_forecast_demand.ipynb` | Sara | Done |
| 03 | Build the simulator | | Michael | To do |
| 04 | Find the staffing plan | | Vinh | To do |
| 05 | Test other demand | | Vinh | To do |
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
