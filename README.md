# PulseBoard

**Autonomous KPI Monitoring and Executive Insight Agent Suite**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-Agent%20Pipeline-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![MCP](https://img.shields.io/badge/MCP-Delivery%20Server-111827?style=for-the-badge)](https://modelcontextprotocol.io/)
[![Cloud Run](https://img.shields.io/badge/Google%20Cloud%20Run-Deployable-34A853?style=for-the-badge&logo=googlecloud&logoColor=white)](https://cloud.google.com/run)

> Built for **AI Agents Intensive - Capstone Project**  
> Track: **Agents for Business**  
> Author: **Arifen**

PulseBoard is a multi-agent business monitoring pipeline that autonomously ingests KPI data, detects anomalies, writes executive-ready insights, and delivers reports through an MCP-powered channel such as Slack or Gmail.

Instead of making business teams manually pull spreadsheets, scan charts, and write status updates, PulseBoard turns KPI monitoring into a reliable agent workflow.

---

## Why PulseBoard?

Business teams often discover KPI issues days after they begin. Revenue drops, rising churn, inventory gaps, or campaign underperformance can compound before anyone has time to investigate.

PulseBoard solves this by running a daily autonomous workflow:

- Pull KPI data from Google Sheets or BigQuery.
- Validate schema and flag malformed rows.
- Compare current metrics against historical baselines.
- Classify each KPI as `Normal`, `Watch`, or `Critical`.
- Generate a concise executive summary with recommended actions.
- Deliver the report through an MCP server after role-based access checks.
- Store an audit log for traceability.

---

## Agent Pipeline

| Agent | Responsibility | Output |
| --- | --- | --- |
| `DataIngestionAgent` | Pulls KPI data, validates schema, and sanitizes suspicious input. | Clean KPI records plus validation warnings. |
| `AnomalyDetectionAgent` | Compares KPIs against historical baselines. | Severity labels: `Normal`, `Watch`, or `Critical`. |
| `InsightGenerationAgent` | Converts anomalies into business-friendly summaries. | Narrative insight and recommended action. |
| `ReportDeliveryAgent` | Checks recipient permissions and sends the report through MCP. | Delivered report plus audit log entry. |

State is passed through **Google ADK session management**, keeping each agent focused and avoiding fragile string-passing between steps.

---

## Architecture

```text
KPI Source
Google Sheets / BigQuery
        |
        v
+-------------------------+
| DataIngestionAgent      |
| Pull, validate, sanitize|
+-----------+-------------+
            |
            v
+-------------------------+
| AnomalyDetectionAgent   |
| Baselines and severity  |
+-----------+-------------+
            |
            v
+-------------------------+
| InsightGenerationAgent  |
| Narrative and action    |
+-----------+-------------+
            |
            v
+-------------------------+
| ReportDeliveryAgent     |
| RBAC, MCP, audit log    |
+-----------+-------------+
            |
            v
Slack / Gmail / Sheets
```

For deeper implementation details, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Key Features

- **Autonomous KPI monitoring**: Runs the full workflow without manual report preparation.
- **Multi-agent design**: Each agent has a narrow, testable responsibility.
- **Schema validation**: Malformed rows are flagged before they affect analysis.
- **Prompt-injection defense**: Spreadsheet cells are sanitized before reaching LLM-powered steps.
- **Severity classification**: KPIs are labeled as `Normal`, `Watch`, or `Critical`.
- **Executive summaries**: Output is concise, business-friendly, and action-oriented.
- **Role-based access control**: Recipients only receive KPIs they are authorized to view.
- **MCP delivery**: Reports can be delivered through Slack, Gmail, or another configured MCP server.
- **Audit logging**: Every delivery records timestamp, recipient, and flagged KPIs.
- **Cloud Run ready**: Designed for scheduled daily execution in Google Cloud.

---

## Capstone Requirements Coverage

| Key Concept | Where It Is Demonstrated | Evidence |
| --- | --- | --- |
| Agent / Multi-agent system with ADK | Code | The pipeline is split into specialized agents: `DataIngestionAgent`, `AnomalyDetectionAgent`, `InsightGenerationAgent`, and `ReportDeliveryAgent`. |
| MCP Server | Code | Report delivery is handled through the MCP configuration in `mcp_config/slack_mcp_config.json`. |
| Antigravity | Video | The demo video should show the project running inside Antigravity and explain the agent workflow. |
| Security features | Code and video | Environment variables, RBAC checks, input sanitization, and audit logging are built into the workflow. |
| Deployability | Video | The demo video should show or explain Cloud Run deployment and Cloud Scheduler automation. |
| Agent skills, such as Agents CLI | Code or video | The implementation and demo can highlight how agent tools/skills are used to complete ingestion, analysis, insight generation, and delivery. |

---

## Demo

<img width="1750" height="875" alt="PulseBoard demo screenshot" src="https://github.com/user-attachments/assets/a3288bc9-7721-47a1-99df-8142e59898e5" />

---

## Project Structure

```text
pulseboard/
  agents/
    orchestrator.py
    data_ingestion_agent.py
    anomaly_detection_agent.py
    insight_generation_agent.py
    report_delivery_agent.py
  mcp_config/
    slack_mcp_config.json
  deploy/
    cloudrun_deploy.sh
    scheduler_config.yaml
  tests/
  .env.example
  ARCHITECTURE.md
  Dockerfile
  requirements.txt
  README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/pulseboard.git
cd pulseboard
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Fill in your own values in `.env`.

```env
GOOGLE_API_KEY=
GOOGLE_SHEET_ID=
BIGQUERY_PROJECT_ID=
SLACK_MCP_SERVER_URL=
SLACK_BOT_TOKEN=
REPORT_RECIPIENTS=
```

No credentials should be committed to the repository.

### 5. Run the pipeline

```bash
python agents/orchestrator.py
```

---

## MCP Configuration

PulseBoard uses an MCP server for report delivery. Slack is the default delivery channel.

Configuration lives in:

```text
mcp_config/slack_mcp_config.json
```

To use Gmail, Sheets, or another channel:

1. Update the MCP server URL.
2. Add the required credentials to `.env`.
3. Adjust the delivery target in the MCP config.
4. Confirm recipient permissions in the RBAC allowlist.

---

## Security

PulseBoard is designed with business-data safety in mind.

| Control | Purpose |
| --- | --- |
| Environment variables | Keeps API keys and tokens out of source control. |
| Role-based access control | Ensures recipients only receive authorized KPI data. |
| Input sanitization | Reduces prompt-injection risk from spreadsheet cells. |
| Schema validation | Prevents malformed rows from entering the agent workflow. |
| Audit logging | Creates a traceable record of report delivery events. |

---

## Deployment

### Cloud Run

```bash
docker build -t pulseboard .
gcloud run deploy pulseboard --source . --platform managed --region <your-region>
```

### Daily Schedule

```bash
gcloud scheduler jobs create http pulseboard-daily \
  --schedule="0 9 * * *" \
  --uri=<your-cloud-run-url> \
  --http-method=POST
```

See:

- [`deploy/cloudrun_deploy.sh`](deploy/cloudrun_deploy.sh)
- [`deploy/scheduler_config.yaml`](deploy/scheduler_config.yaml)

---

## Example Report Output

```text
PulseBoard Daily KPI Brief

Status: Critical

Revenue dropped 18% below the 30-day baseline, driven primarily by lower
conversion from paid campaigns. Churn is also in Watch status after rising
6% week over week.

Recommended action:
Review paid campaign targeting and pause the lowest-performing segments.
Customer Success should inspect churned accounts from the last 7 days for
common cancellation reasons.
```

---

## Built With

- **Google Agent Development Kit (ADK)** for multi-agent orchestration.
- **Model Context Protocol (MCP)** for report delivery integrations.
- **Python** for pipeline implementation.
- **Google Cloud Run** for deployment.
- **Cloud Scheduler** for automated daily execution.

---

## License

This project is prepared for the AI Agents Intensive Capstone submission. Add your preferred license before publishing publicly.
