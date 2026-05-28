# Market Watch

An AI-powered real estate market intelligence dashboard.  
Monitors 12 cities across Ohio, New York, Ontario, and Alberta using live public data, then uses AI to explain — in plain English — whether each market is heating up or cooling down, and why.

---

## What You Need Before Starting

Install these two things if you don't have them already:

1. **Python 3.11 or newer** → [Download here](https://www.python.org/downloads/)  
   During installation, **check the box that says "Add Python to PATH"**. This is important.

2. **Node.js 18 or newer** → [Download here](https://nodejs.org/)  
   Pick the version marked **"LTS"** (the big green button).

To check if they're already installed, open a terminal and run:
```
python --version
node --version
```
If both show version numbers, you're good.

> **How to open a terminal:**  
> - **Windows:** Press `Win + R`, type `cmd`, press Enter.  
> - **Mac:** Press `Cmd + Space`, type `Terminal`, press Enter.

---

## Step 1 — Get Your API Keys (free)

You need 3 API keys. All are free. Here's exactly how to get each one:

### FRED Key (US housing data)
1. Go to [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
2. Click **"Request API Key"**
3. Create an account (or log in)
4. Copy the key it gives you — save it somewhere

### Gemini Key (AI interpretation)
1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with a Google account
3. Click **"Create API Key"**
4. Copy the key — save it somewhere

### NewsAPI Key (news headlines)
1. Go to [https://newsapi.org/register](https://newsapi.org/register)
2. Fill in the form and register
3. Your key will be shown on screen — copy it and save it

---

## Step 2 — Set Up Your Keys

1. Open the `market-watch` folder
2. Find the file called `.env.example` in the root folder
3. **Make a copy** of it and put the copy inside the `backend` folder
4. **Rename** the copy to `.env` (just `.env`, no other name)
5. Open `.env` in any text editor (Notepad works fine) and paste your keys:

```
FRED_API_KEY=paste_your_fred_key_here
GEMINI_API_KEY=paste_your_gemini_key_here
NEWS_API_KEY=paste_your_newsapi_key_here
```

Replace the placeholder text with your actual keys. No quotes. No spaces around the `=`.

---

## Step 3 — Start the Backend

Open a terminal, then run these commands **one at a time**:

```
cd market-watch/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

You should see output ending with something like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Leave this terminal open.** The backend is now running.

> If `pip` doesn't work, try `pip3` instead.  
> If `uvicorn` doesn't work, try `python -m uvicorn main:app --reload`.

---

## Step 4 — Start the Frontend

Open a **second terminal** (keep the first one running), then:

```
cd market-watch/frontend
npm install
npm run dev
```

You should see:
```
Local: http://localhost:5173/
```

---

## Step 5 — Open the Dashboard

Open your web browser and go to:

**[http://localhost:5173](http://localhost:5173)**

That's it. The dashboard will load. On first launch, it takes 30–60 seconds to fetch data for all 12 cities in the background.

---

## What You're Looking At

- **4 region tabs** at the top — click to switch between Ohio, New York, Ontario, Alberta
- **City cards** show the AI signal: HEATING (market getting hotter), COOLING (slowing down), or STABLE
- **Click any city card** to open a detail view with:
  - Full market stats (price, inventory, days on market, interest rates)
  - The AI's reasoning trace — step-by-step explanation of how it reached its conclusion
  - A **What-If Simulation Sandbox** where you can type a custom headline (like *"Tesla announces new factory in Columbus"*) and see how the AI reinterprets the market
- **Right sidebar** shows the latest notable news events across all markets

---

## Data Sources

All data is fetched live from public APIs. Nothing is fake.

| Source | What It Provides | Covers |
|--------|-----------------|--------|
| **FRED** (Federal Reserve) | Median listing price, inventory, days on market, mortgage rates | US cities |
| **Statistics Canada** | Housing price index, building permits, unemployment | Canadian cities |
| **CMHC** | Housing starts, completions, absorption rates | Canadian cities |
| **Bank of Canada** | Overnight policy interest rate | Canada-wide |
| **NewsAPI** | Real estate and economic news headlines | All cities |
| **Gemini AI** | Interprets all of the above into plain-English market signals | All cities |

> **Note on Canadian data:** Statistics Canada and CMHC public endpoints are rate-limited. If they're unavailable at fetch time, the system uses cached baseline figures so the dashboard never breaks. The README in `backend/ingest/` has full details.

> **Note on MLS/CREA:** Direct MLS feeds and CREA data require licensed broker credentials and are not publicly available APIs. Market Watch uses publicly accessible government data sources (FRED, StatCan, CMHC) as documented alternatives.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python: command not found` | Reinstall Python and check **"Add to PATH"** during install |
| `pip: command not found` | Try `pip3 install -r requirements.txt` instead |
| `uvicorn: command not found` | Try `python -m uvicorn main:app --reload` |
| `node: command not found` | Reinstall Node.js from [nodejs.org](https://nodejs.org) |
| Dashboard shows no data | Wait 60 seconds — initial data fetch runs in the background on first start |
| All cities say "STABLE / low confidence" | Check that your API keys are correct in `backend/.env` |
| Backend crashes on start | Make sure `.env` is inside the `backend/` folder, not the project root |

---

## Stopping It

- Press `Ctrl + C` in each terminal to stop the backend and frontend.
- Nothing is permanently running. Next time you want to use it, just repeat Steps 3–5.
