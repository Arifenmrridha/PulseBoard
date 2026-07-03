# PulseBoard

**Autonomous KPI Monitoring & Executive Insight Agent Suite**
*AI Agents Intensive — Capstone Project | Track: Agents for Business*

---

## Problem

Business teams spend hours every week manually pulling KPI data from spreadsheets or warehouses, scanning for anomalies, and writing executive summaries. This process is slow, reactive, and error-prone — issues are often discovered days after they occur, by which point the impact has already compounded.

## Solution

PulseBoard is a multi-agent pipeline, built with Google's Agent Development Kit (ADK), that runs this entire workflow autonomously:

1. **DataIngestionAgent** — pulls KPI data from a source (Google Sheet / BigQuery), validates schema, flags malformed rows.
2. **AnomalyDetectionAgent** — compares each KPI against historical baselines and classifies it as Normal / Watch / Critical.
3. **InsightGenerationAgent** — turns flagged anomalies into a concise, business-friendly narrative with a recommended action.
4. **ReportDeliveryAgent** — delivers the report through an MCP server (Slack/Gmail), applying role-based access checks before sending.

Each agent has a narrow, well-defined responsibility, and state is passed between them via ADK's session management rather than ad hoc string concatenation.

## Architecture

```
 ┌──────────────────────┐
 │ DataIngestionAgent    │  → pulls & validates KPI data
 └──────────┬────────────┘
            ▼
 ┌──────────────────────┐
 │ AnomalyDetectionAgent │  → flags Normal / Watch / Critical
 └──────────┬────────────┘
            ▼
 ┌──────────────────────┐
 │ InsightGenerationAgent│  → generates narrative + recommendation
 └──────────┬────────────┘
            ▼
 ┌──────────────────────┐
 │ ReportDeliveryAgent   │  → RBAC check → MCP delivery → audit log
 └──────────────────────┘
```

See `ARCHITECTURE.md` for a detailed breakdown of data flow, state schema, and design rationale.

## Setup Instructions

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/pulseboard.git
cd pulseboard

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Fill in your own values in .env (never commit this file)

# 5. Run the pipeline
python agents/orchestrator.py
```

## MCP Configuration

PulseBoard uses an MCP server for report delivery (Slack by default). Configuration lives in `mcp_config/slack_mcp_config.json`. To use a different channel (e.g., Gmail or Sheets), swap the MCP server URL and credentials in `.env` and update the config accordingly. No credentials are stored in this repo — all secrets are loaded from environment variables at runtime.

## Security Notes

- **No hard-coded secrets** — all API keys and tokens are loaded via environment variables.
- **Role-based access control** — `ReportDeliveryAgent` checks a configurable allowlist so each recipient role only sees the KPIs they're authorized to view (e.g., Executive vs. Team Lead).
- **Input sanitization** — ingested spreadsheet data is validated and stripped of anything resembling embedded instructions, to guard against prompt injection via data cells.
- **Audit logging** — every delivered report is logged with timestamp, recipient, and flagged KPIs for traceability.

## Deployment (Cloud Run)

```bash
# Build and deploy
docker build -t pulseboard .
gcloud run deploy pulseboard --source . --platform managed --region <your-region>

# Schedule daily runs via Cloud Scheduler
gcloud scheduler jobs create http pulseboard-daily \
  --schedule="0 9 * * *" \
  --uri=<your-cloud-run-url> \
  --http-method=POST
```

See `deploy/cloudrun_deploy.sh` and `deploy/scheduler_config.yaml` for the full deployment scripts.

## Demo / Screenshots

<img width="1750" height="875" alt="Image" src="https://github.com/user-attachments/assets/a3288bc9-7721-47a1-99df-8142e59898e5" />

---

**Built with:** Google ADK · MCP · Python · Google Cloud Run
**Author:** Arifen
