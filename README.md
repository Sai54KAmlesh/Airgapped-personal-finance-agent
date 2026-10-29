Personal Finance Agent
An Offline, Privacy-Preserving SMS-Based Financial Intelligence System
100% offline · No cloud, no API keys, no internet · All inference on 127.0.0.1

A fully local FinTech agent that ingests bank SMS messages from Indian banks (HDFC, SBI, Axis, ICICI), extracts transactions using a two-tier pipeline (Regex + Tiny LLM), stores them in SQLite, forecasts month-end spending with ML, and serves insights through a glassmorphic React dashboard.

Domain: FinTech · NLP · Machine Learning
Course: Industry Immersion Program (IIP) - October 2026

✨ Key Features
Two-Tier Parsing: Fast compiled Regex (Tier 1) + Local Qwen 2.5 0.5B via Ollama (Tier 2) with 5-layer safety validation
Privacy by Architecture: SQLite WAL mode, Flask on localhost:5000, React on localhost:5173 — data never leaves the device
ML Forecasting: Blended SGDRegressor forecast that mixes this month's trend with historical averages
Budget Alerts: Category-wise overspend prediction sorted by severity
Human-in-the-Loop: Correct a category once → agent saves rule in rules_memory and retroactively relabels all past transactions
Zero Heavy Dependencies: Hand-crafted inline SVG charts, pure CSS glassmorphism, no Chart.js/Recharts
🏗️ Architecture
CSV (sms_1000.csv) 
  → pipeline.py (dedupe via UNIQUE constraint)
  → Tier 1: regex_parser.py (5 bank patterns, ~μs)
  → Pending Queue ──┐
                    └→ Tier 2: llm_parser.py (Ollama + Qwen 2.5:0.5B) + hallucination guard
  → SQLite (finance.db - WAL mode)
  → analytics.py (forecast + alerts + backtest)
  → Flask REST API (api.py - 7 endpoints, CORS)
  → React Dashboard (Vite + React 19 - NexusBank theme)
📦 Tech Stack
Layer	Tech	Purpose
Backend	Python 3.13, Pandas, Flask, scikit-learn, NumPy	Pipeline, API, ML
Regex	Python re stdlib	Tier-1 extraction
LLM	Ollama + Qwen 2.5 0.5B	Tier-2 fallback
DB	SQLite 3 (WAL)	Single-file storage
Frontend	React 19.3.1, Vite 8.3.5, Pure CSS, Inline SVG	Dashboard
Font	Outfit (Google Fonts)	Typography
📁 Project Structure
IIP/
├── backend/
│   ├── pipeline.py       # Orchestrator: CSV → Regex → LLM → DB
│   ├── regex_parser.py   # Tier-1: compiled patterns + categorize()
│   ├── llm_parser.py     # Tier-2: Ollama Qwen 2.5 + 5-layer validation
│   ├── db.py             # Schema, CRUD, rule memory, budgets
│   ├── analytics.py      # Forecasting, alerts, backtesting
│   └── api.py            # Flask REST API (7 endpoints)
├── data/
│   ├── sms_1000.csv      # 1000 labeled SMS (ground truth)
│   └── finance.db        # SQLite DB (auto-created, WAL mode)
├── frontend/
│   ├── src/
│   │   ├── App.jsx       # 238 lines, 7 components
│   │   ├── main.jsx      # React 19 entry
│   │   └── index.css     # 472-line glassmorphic theme
│   ├── index.html
│   └── package.json
├── analyze.py            # Analytics demo & backtest runner
└── evaluate.py           # Regex accuracy evaluator
✅ Prerequisites
Python 3.10+ (tested on 3.13)
Node.js 18+ & npm
Ollama (optional but recommended for Tier-2) - https://ollama.com
No internet required after setup
🚀 Setup & Installation
1. Clone & Backend Setup
git clone <your-repo-url>
cd IIP
# Create venv (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
# Install dependencies
pip install pandas flask flask-cors scikit-learn numpy requests
# or if you have requirements.txt:
# pip install -r requirements.txt
2. Ollama Setup (for Tier-2 LLM)
# Install Ollama from https://ollama.com
# Then:
ollama pull qwen2.5:0.5b
ollama serve  # runs on http://127.0.0.1:11434
# Verify:
curl http://127.0.0.1:11434/api/tags
Note: If Ollama is not running, the pipeline gracefully skips Tier-2. Only Tier-1 regex will be used.

3. Frontend Setup
cd frontend
npm install
cd ..
4. Dataset
Place your sms_1000.csv inside data/ with columns:
id, timestamp, sender, body, true_type, true_amount, true_merchant, true_category

The true_* columns are only used by evaluate.py and ignored by the pipeline.

▶️ How to Run
Step 1: Ingest SMS & Build Database
This runs the full pipeline: CSV → Regex → LLM (if available) → SQLite

python -c "from backend.pipeline import run; print(run('data/sms_1000.csv'))"
# Expected output: {'regex': 750, 'llm': 120, 'skipped': 80, 'duplicate': 50}
The DB data/finance.db is auto-created with WAL mode and default budgets (90% of avg spend per category).

Step 2: Start Flask API (Backend)
# Normal mode
python backend/api.py
# API runs at http://127.0.0.1:5000
# Demo mode (pins date to 2026-10-28 for realistic forecast):
TODAY=2026-10-28 python backend/api.py
# Windows PowerShell:
# $env:TODAY="2026-10-28"; python backend/api.py
Step 3: Start React Dashboard (Frontend)
In a new terminal:

cd frontend
npm run dev
# Dashboard runs at http://127.0.0.1:5173
Open the URL — you should see the NexusBank glassmorphic dashboard with stats, chart, alerts, transactions, and learned rules.

Step 4: Evaluate Regex Parser (Optional)
python evaluate.py
# Shows coverage, accuracy, noise rejection, sample misses
Step 5: Run Analytics Demo & Backtest
python analyze.py
# Example:
# Backtest on September 2026:
# day  5: forecast  82,400  actual  86,310  accuracy 95.5%
# day 10: forecast  84,100  actual  86,310  accuracy 97.4%
🔌 API Endpoints
Method	Endpoint	Body / Query	Description
GET	/api/overview	—	Dashboard summary: today, forecast, budget, alerts, categories, daily[]
GET	/api/transactions?limit=40	?limit	Latest transactions desc by date
POST	/api/transactions	{date, type, amount, merchant, category?}	Add manual transaction (cash)
POST	/api/transactions/:id/correct	{category}	Correct category → learns rule + relabels history
GET	/api/categories	—	List of valid categories
GET	/api/rules	—	All learned merchant → category rules
GET	/api/budgets	—	Budget limits per category
CORS: Enabled for * so Vite dev server (5173) can call Flask (5000).

Manual transaction validation:

date: YYYY-MM-DD
type: debit | credit
amount: >0 and ≤1,00,00,000
merchant: required, max 60 chars
category: auto-detected if omitted
🧠 How It Works
Tier-1 Regex (Fast Path)
Shared amount fragment: (?:Rs\.?|INR)\s?([\d,]+(?:\.\d{1,2})?)

Bank	Type	Pattern
HDFC	Debit	{AMT} debited from A/c XX#### on DATE to VPA ... (MERCHANT)
SBI	Debit	{AMT} spent on your SBI Card XX#### at MERCHANT on DATE
Axis	Debit	{AMT} debited from Axis Bank A/c XX#### on DATE Info: UPI/MERCHANT.
ICICI	Debit	Acct XX#### debited for {AMT} on DATE; MERCHANT credited
All	Credit	{AMT} credited to A/c XX#### on DATE by/Info: REFUND/MERCHANT
Tier-2 LLM (Smart Fallback)
Model: Qwen 2.5 0.5B (~400MB RAM, 1-3s on CPU)
Prompt: One-shot JSON extraction with {"type": "none"} escape for OTPs/offers
5-Layer Safety:
Extract {...} via regex (strips chatter)
json.loads() validation
Type must be debit/credit
Amount >0 and merchant non-empty
Hallucination guard: Amount must appear as digits in original SMS
Forecasting
w = today.day / days_in_month
rate_blended = w * rate_observed + (1-w) * rate_prior
forecast = spent_so_far + max(rate_blended, 0) * days_left
Early month → trusts history, Late month → trusts current pace
SGDRegressor(penalty=None, fit_intercept=False, eta0=0.05, max_iter=5000)
Human-in-the-Loop
POST /api/transactions/:id/correct → INSERT INTO rules_memory + UPDATE transactions WHERE merchant LIKE %pattern%

📊 Database Schema
raw_sms(id, ts, body, parsed) — UNIQUE(ts, body)
transactions(id, sms_id FK, date, type, amount, merchant, category, parser) — parser = regex/llm/manual
rules_memory(id, pattern UNIQUE, category) — persistent memory
budgets(category PK, monthly_limit) — auto-generated at 90% of avg
WAL mode allows concurrent read (dashboard) + write (pipeline).

🐛 Troubleshooting
Issue	Fix
Ollama not running	ollama serve in another terminal, then ollama pull qwen2.5:0.5b
CORS error	Ensure Flask is on 5000 and after_request adds Access-Control-Allow-Origin
DB locked	Ensure WAL mode: PRAGMA journal_mode=WAL in db.py
Forecast looks off	Set TODAY=2026-10-28 if your dataset ends on that date
Port 5000/5173 busy	lsof -i :5000 → kill, or change port in vite.config.js / api.py
📸 Screenshots
Add your running dashboard screenshots in /screenshots/:

Full overview (header + stats + chart)
Budget alerts + progress bars
Transaction table with category edit + parser chips
Add transaction form + learned rules
🔮 Future Work
Live SMS ingestion via Android Termux / companion app
More banks: Kotak, Yes, Federal, BOB + international formats
Configurable models: Qwen 2.5 3B / Llama 3.2 1B
Recurring detection (Netflix, rent, EMI)
Multi-account unified view
PDF/CSV export for tax filing
PWA packaging + Voice input
