# GenAI forecast assistant

A manager asks about the 2026 eligible sign-up forecast. The app sends the question to the model the user picks, the model calls the forecast tools, and the reply stays in plain words.

The model does not invent sign-ups, cost, revenue, profit, or headcount. Those numbers come from the tools. The simulator (step 03) and the staffing search (step 04) are stubs until those steps exist. World Bank GDP is an outside growth projection, not the sign-up forecast, and it stays off until it is turned on.

The app needs Python 3.10 or newer. `requirements-genai.txt` installs beside `requirements.txt` and does not replace it.

## Run the Streamlit app

From the repository root. `python3` on this machine is 3.9, so the virtual environment is created with `python3.12`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-genai.txt
streamlit run genai/app.py
```

Streamlit prints a local address, usually http://localhost:8501. Open that page.

1. Open **Options** in the sidebar.
2. Leave the provider on **Google Gemini** and the model on `gemini-3.5-flash-lite`, or type another model id such as `gemini-3.8-flash`.
3. Paste a Gemini API key. The key stays in this browser session and is not written to a file. It is sent only to the selected provider with each question.
4. Ask a question in the box at the bottom, for example: `What is the January forecast for Argentina?`
5. A working key returns the forecast in the chat. Argentina in January 2026 is 70.8 eligible sign-ups.

**Options** also holds:

- Extra tools. Check World Bank GDP when the question needs a 2026 growth projection.
- Simulator demand scale and countries. 1 keeps the forecast. 0.8 is lower sign-ups and 1.2 is higher. No country selection includes every country.
- Staffing bounds. The plan has to beat keeping January 2026 headcount all year.

**New conversation** clears the chat and starts a new thread. The key and the other options stay.

## What a turn can call

| Tool | When it is available | What it returns |
|---|---|---|
| `view_forecast` | Always | Eligible sign-ups and average budget from `data/clean/forecast_2026.csv` |
| `run_simulator` | Always | The simulator settings for this turn. Step 03 is not built, so it does not estimate profit. |
| `optimize_staffing` | Always | The staffing settings for this turn. Step 04 is not built, so it does not invent a headcount plan. |
| `world_bank_gdp` | Only when checked | World Bank Global Economic Prospects real GDP growth. Not the sign-up forecast. |

## Tests

From the repository root, with the same environment:

```bash
python -m unittest tests.test_gemini_connection -v
```

The tests check that a supplied key is posted to the Gemini API and is left out of the reply. Set `GEMINI_API_KEY` in the environment to also call Gemini itself.
