# EY Candidate Matcher — Decision Support System

AI-powered platform that evaluates candidate CVs against job descriptions and produces structured hiring recommendations. Built for the **EY AI Challenge**.

## How it works

1. Recruiter uploads one or more CV PDFs and selects a target role
2. The platform extracts text from each PDF and sends it to an **n8n AI Agent** via webhook
3. The agent scores the candidate across 5 dimensions and returns a structured JSON analysis
4. Results are displayed with scores, decision, risk flags, and interview questions
5. Results are cached in SQLite to avoid redundant LLM calls

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS + HTML/CSS, served by Flask |
| Backend | Python 3 + Flask |
| AI Orchestration | n8n (self-hosted cloud) |
| PDF Extraction | pypdf |
| Database | SQLite |

## Setup

**Requirements:** Python 3.9+

```bash
git clone <repo-url>
cd ey-matching-dss
pip3 install -r requirements.txt
python3 app.py
```

Open **http://localhost:8080** in your browser.

> **Note:** Port 5000 is reserved by AirPlay on macOS — the app runs on 8080.

## Configuration

Edit the top of `operations.py` to point to your n8n instance:

```python
N8N_BASE_URL  = "https://your-instance.app.n8n.cloud"
WEBHOOK_KEY   = "your-webhook-uuid"
WEBHOOK_PATH  = "webhook-test"   # "webhook" for production (active workflow)
```

For production, set `WEBHOOK_PATH = "webhook"` and activate the workflow in n8n (toggle on the canvas). In test mode (`webhook-test`), you must click **"Execute workflow"** in n8n before each request.

## Project structure

```
ey-matching-dss/
├── app.py            # Flask server — serves frontend + /api/match endpoint
├── operations.py     # PDF extraction, n8n requests, SQLite CRUD
├── index.html        # Single-page UI
├── src/
│   └── main.js       # Frontend logic (upload, match, results, detail modal)
├── requirements.txt
└── db.db             # SQLite database (auto-created on first run)
```

## API

### `POST /api/match`

Multipart form data:

| Field | Type | Description |
|---|---|---|
| `job_name` | string | Role name (e.g. "Consulting") |
| `cv_files` | file[] | One or more PDF CVs |
| `force` | string | `"true"` to bypass cache and re-run |

Returns a JSON array, one object per CV, with the full agent evaluation.

### `POST /api/cache/clear`

JSON body: `{ "job_name": "Consulting" }` — clears cached results for that role. Omit `job_name` to clear everything.

## Scoring model

The AI agent scores each candidate out of 100:

| Dimension | Points |
|---|---|
| Technical match (skills vs requirements) | 30 |
| Title / Role match | 25 |
| Experience & seniority | 25 |
| Location match | 10 |
| Language match | 10 |

Candidates below 50% are automatically rejected. The agent also flags risks as **HARD STOP**, **AMBER**, or **LOW**.

## Caching

Results are stored in `db.db` keyed by `(job_name, cv_filename)`. To re-run an analysis, click **"🔄 Re-analisar"** in the results panel — this clears the cache for the current role and re-submits all CVs to the agent.
