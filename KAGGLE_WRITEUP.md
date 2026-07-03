# PulseBoard Kaggle Write-up

## Project Title

**PulseBoard: Autonomous KPI Monitoring and Executive Insight Agent Suite**

## One-line Summary

PulseBoard is a multi-agent business monitoring system that ingests KPI data, detects anomalies, generates executive insights, and delivers reports through an MCP-powered communication channel.

---

## 1. Problem Statement

Business teams depend on KPI reports to understand revenue, churn, conversions, operational performance, and customer health. In many organizations, this workflow is still manual:

- Analysts pull data from spreadsheets or warehouses.
- Teams scan dashboards for unusual movements.
- Managers write summaries for leadership.
- Reports are sent through Slack, Gmail, or shared documents.

This process is slow and reactive. Important changes can be missed until several days later, allowing the impact to grow before anyone responds.

PulseBoard solves this problem by turning KPI monitoring into an autonomous agent workflow.

---

## 2. Proposed Solution

PulseBoard uses a multi-agent pipeline built around Google ADK concepts. Each agent owns one clear responsibility, and the workflow passes structured state from one step to the next.

The system:

1. Ingests KPI data from a source such as Google Sheets or BigQuery.
2. Validates the incoming schema and flags malformed rows.
3. Compares current KPI values against historical baselines.
4. Classifies KPI status as `Normal`, `Watch`, or `Critical`.
5. Generates a concise executive summary with recommended actions.
6. Applies role-based access checks.
7. Delivers the final report through an MCP server such as Slack or Gmail.
8. Records an audit log for traceability.

The result is a business-ready reporting agent suite that can run daily without manual report preparation.

---

## 3. Why This Matters

KPI monitoring is valuable only when it is timely. A revenue drop, churn spike, campaign issue, or operational bottleneck becomes more expensive the longer it remains hidden.

PulseBoard helps teams move from delayed reporting to proactive monitoring.

Key benefits:

- Faster anomaly discovery.
- Less manual reporting work.
- Consistent executive summaries.
- Better security through role-based delivery.
- Easier deployment through Cloud Run and Cloud Scheduler.
- Clear audit logs for accountability.

---

## 4. System Architecture

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
| Baseline comparison     |
+-----------+-------------+
            |
            v
+-------------------------+
| InsightGenerationAgent  |
| Summary and action      |
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

Each agent has a narrow responsibility. This keeps the system easier to test, debug, and extend.

---

## 5. Agent Design

| Agent | Main Job | Business Value |
| --- | --- | --- |
| `DataIngestionAgent` | Loads KPI data and validates the schema. | Prevents bad data from entering the pipeline. |
| `AnomalyDetectionAgent` | Detects unusual KPI movement against historical baselines. | Helps teams spot problems earlier. |
| `InsightGenerationAgent` | Writes a short business-friendly explanation. | Turns raw signals into executive-ready context. |
| `ReportDeliveryAgent` | Checks access rules and sends the report through MCP. | Delivers the right information to the right people. |

This multi-agent structure avoids one large, overloaded agent. Instead, each step is focused and easier to reason about.

---

## 6. Data and KPI Flow

PulseBoard is designed to work with KPI tables containing fields such as:

- Date
- KPI name
- Current value
- Historical baseline
- Business unit
- Owner or recipient role
- Threshold configuration

Example KPI categories:

- Revenue
- Conversion rate
- Customer churn
- Active users
- Support ticket volume
- Inventory availability
- Campaign performance

The pipeline validates each row before anomaly detection. If a row is missing required fields or contains suspicious text, it is flagged instead of being silently processed.

---

## 7. Anomaly Classification

The anomaly detection step classifies each KPI into one of three states:

| Status | Meaning | Example |
| --- | --- | --- |
| `Normal` | KPI is within expected range. | Revenue is close to the 30-day average. |
| `Watch` | KPI is drifting and should be monitored. | Churn is slightly higher than normal. |
| `Critical` | KPI is materially outside the baseline. | Conversion dropped 20% below expected range. |

This makes the final report easy to scan. Leaders can immediately focus on the most urgent issues.

---

## 8. Example Output

```text
PulseBoard Daily KPI Brief

Overall Status: Critical

Revenue dropped 18% below the 30-day baseline, mainly driven by lower
conversion from paid campaigns. Churn is also in Watch status after rising
6% week over week.

Recommended Action:
Review paid campaign targeting and pause the lowest-performing segments.
Customer Success should inspect churned accounts from the last 7 days for
common cancellation reasons.
```

The output is intentionally concise. It is written for business users, not only technical analysts.

---

## 9. MCP Integration

PulseBoard uses an MCP server for report delivery.

The default configuration targets Slack, but the same delivery pattern can be adapted for:

- Gmail
- Google Sheets
- Internal dashboards
- Other MCP-compatible business tools

This separates the report-generation logic from the delivery channel. The agents can produce the same structured report while the MCP layer handles where it goes.

---

## 10. Security Features

PulseBoard includes several safety features because KPI reports can contain sensitive business data.

| Security Feature | Purpose |
| --- | --- |
| Environment variables | Keeps tokens and API keys out of source code. |
| Role-based access control | Ensures recipients only receive KPIs they are authorized to view. |
| Input sanitization | Reduces risk from malicious or instruction-like text inside spreadsheet cells. |
| Schema validation | Blocks malformed rows from affecting the report. |
| Audit logging | Records report delivery details for traceability. |

Security is part of the workflow rather than an afterthought.

---

## 11. Deployability

PulseBoard is designed for scheduled cloud execution.

Recommended deployment:

1. Package the project with Docker.
2. Deploy it to Google Cloud Run.
3. Trigger daily execution with Cloud Scheduler.
4. Send output through the configured MCP delivery server.

This allows the system to run automatically every morning before leadership meetings or daily standups.

---

## 12. Capstone Concept Coverage

| Key Concept | Where It Is Demonstrated |
| --- | --- |
| Agent / multi-agent system with ADK | Code implementation of the four-agent pipeline. |
| MCP Server | Delivery configuration and report handoff. |
| Antigravity | Demo video showing the project workflow. |
| Security features | Code and demo explanation. |
| Deployability | Demo video showing Cloud Run and scheduler readiness. |
| Agent skills / Agents CLI | Code or video walkthrough of tool-based agent execution. |

---

## 13. What Makes PulseBoard Different

PulseBoard is not only a dashboard. A dashboard still requires a human to open it, inspect charts, interpret changes, and write an update.

PulseBoard acts more like a monitoring teammate:

- It checks the data.
- It notices unusual movement.
- It explains the likely business impact.
- It recommends action.
- It sends the report to the right audience.

This makes it useful for teams that need speed, consistency, and accountability in business reporting.

---

## 14. Future Improvements

Possible next steps:

- Add more advanced forecasting models.
- Support multiple departments and custom KPI thresholds.
- Add a web dashboard for reviewing historical anomaly reports.
- Include confidence scores for generated insights.
- Add human approval before sending critical reports.
- Expand MCP delivery options beyond Slack and Gmail.

---

## 15. Conclusion

PulseBoard demonstrates how agentic systems can improve real business workflows. By combining ADK-style multi-agent orchestration, MCP-based delivery, anomaly detection, role-based security, and cloud deployability, it turns KPI monitoring from a manual reporting task into an autonomous insight pipeline.

The project is practical, extensible, and designed around a clear business need: helping teams detect important KPI changes earlier and respond with better context.
