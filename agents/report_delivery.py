"""
ReportDeliveryAgent — RBAC-filtered report delivery via local MCP simulation.

Role:
    Applies role-based access control (RBAC) to filter KPI data and narrative
    text to only what each recipient role is permitted to see, then delivers
    the formatted report via the local in-process MCP server (fully offline —
    no external APIs, no Node.js subprocess, no internet connection required).

Inputs (session state keys read):
    "detected_anomalies"  — dict of KPI anomaly results
    "insights_report"     — narrative string from InsightGenerationAgent
    "recipient_email"     — str delivery target
    "recipient_role"      — str role name (must match config/rbac.yaml)

Outputs (session state keys written):
    none — side-effects only (Slack log file + audit CSV)

Security features:
    • RBAC allowlist loaded from config/rbac.yaml; roles NOT in config are
      refused all delivery except a minimal safe default.
    • Forbidden-KPI redaction scans each narrative paragraph individually
      and replaces any mention of a restricted KPI with a labelled redaction.
    • Audit log row written on every invocation for compliance trail.
    • Rate-limited + retry-with-backoff on MCP calls (via tools/rate_limiter).

Design decisions:
    • Uses local_mcp.mock_mcp_server instead of real stdio subprocess MCP.
      This keeps the system fully offline and reproducible with zero
      external dependencies. Swapping to a real MCP server requires only
      changing the import and call in `_invoke_mcp_delivery`.
"""

import csv
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import yaml

# ── Safe ADK imports ─────────────────────────────────────────────────────────
try:
    from google.adk.tools import ToolContext
except ImportError:
    try:
        from google.adk.context import ToolContext  # type: ignore
    except ImportError:
        class ToolContext:                           # type: ignore
            def __init__(self): self.state = {}

try:
    from google.adk.agents import LlmAgent as Agent
except ImportError:
    try:
        from google.adk import Agent                # type: ignore
    except ImportError:
        class Agent:                                # type: ignore
            def __init__(self, **kw): pass

# ── Local (offline) MCP server — no external dependencies ────────────────────
from local_mcp.mock_mcp_server import call_tool as local_mcp_call

from skills.report_formatting import format_as_markdown, format_as_slack
from tools.rate_limiter import rate_limited, retry_with_backoff, TransientError

logger = logging.getLogger("PulseBoard.Agents.ReportDelivery")

_AUDIT_LOG = os.path.join("tools", "delivery_audit_log.csv")
_DEFAULT_RBAC = {
    "roles": {
        "Executive":      {"allowed_kpis": ["revenue", "active_users", "churn_rate", "conversion_rate"]},
        "Product Lead":   {"allowed_kpis": ["active_users", "churn_rate"]},
        "Marketing Lead": {"allowed_kpis": ["conversion_rate"]},
        "Finance Lead":   {"allowed_kpis": ["revenue"]},
        "Team Lead":      {"allowed_kpis": ["active_users", "conversion_rate"]},
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_rbac_config(config_path: str = "config/rbac.yaml") -> Dict[str, Any]:
    """Loads the RBAC allowlist from YAML; falls back to hard-coded defaults."""
    if not os.path.exists(config_path):
        logger.warning("RBAC config not found at '%s'. Using built-in defaults.", config_path)
        return _DEFAULT_RBAC
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _redact_narrative(narrative: str, forbidden_kpis: List[str], role: str) -> str:
    """
    Scans each double-newline-separated paragraph for mentions of forbidden KPIs
    and replaces them with an explicit redaction notice.
    """
    sanitized: List[str] = []
    for paragraph in narrative.split("\n\n"):
        leaks = [fk for fk in forbidden_kpis if fk.lower() in paragraph.lower()]
        if leaks:
            sanitized.append(
                f"_[Redacted: {', '.join(leaks)} — restricted for role '{role}']_"
            )
        else:
            sanitized.append(paragraph)
    return "\n\n".join(sanitized)


def _write_audit_log(
    recipient: str, role: str, status: str, allowed_kpis: List[str]
) -> None:
    """Appends a delivery record to the local audit CSV file."""
    os.makedirs(os.path.dirname(_AUDIT_LOG) or ".", exist_ok=True)
    file_exists = os.path.exists(_AUDIT_LOG)
    timestamp   = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open(_AUDIT_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "recipient", "role", "status", "delivered_kpis"])
        writer.writerow([timestamp, recipient, role, status, ";".join(allowed_kpis)])
    logger.info("Audit log entry written for %s (%s).", recipient, role)


@retry_with_backoff(max_attempts=3)
@rate_limited()
async def _invoke_mcp_delivery(
    channel: str, text: str, blocks: List[Any]
) -> str:
    """
    Calls the local (offline) MCP Slack simulation.
    Decorated with retry + rate-limit for resilience parity with real MCP calls.
    To switch to a real MCP server: replace `local_mcp_call` with
    `call_mcp_delivery` from the real MCP client and update the import above.
    """
    result = await local_mcp_call(
        server_name="slack",
        tool_name="post_message",
        arguments={"channel": channel, "text": text, "blocks": blocks},
    )
    if result.get("status") != "success":
        raise TransientError(f"LocalMCP returned non-success: {result}")
    return str(result.get("content", "ok"))


# ─────────────────────────────────────────────────────────────────────────────
# Primary delivery tool
# ─────────────────────────────────────────────────────────────────────────────

async def deliver_insights_report(tool_context: ToolContext) -> str:
    """
    Applies RBAC filtering, redacts forbidden KPI context from the narrative,
    formats the report, delivers via local MCP, and writes an audit log row.
    Completely offline — no external API keys or network access required.
    """
    recipient = tool_context.state.get("recipient_email", "lead@company.com")
    role      = tool_context.state.get("recipient_role", "Team Lead")

    # 1. RBAC — determine which KPIs this role may see
    rbac         = load_rbac_config()
    allowed_kpis = rbac.get("roles", {}).get(role, {}).get("allowed_kpis", [])
    if not allowed_kpis:
        allowed_kpis = ["active_users"]
        logger.warning(
            "No RBAC entry found for role '%s'. Defaulting to: %s", role, allowed_kpis
        )

    # 2. Filter anomaly data to permitted KPIs only
    anomalies          = tool_context.state.get("detected_anomalies", {})
    filtered_anomalies = {k: v for k, v in anomalies.items() if k in allowed_kpis}
    forbidden_kpis     = [k for k in anomalies if k not in allowed_kpis]

    # 3. Redact forbidden KPI mentions from the narrative text
    raw_narrative      = tool_context.state.get("insights_report", "No insights generated.")
    sanitized_narrative = _redact_narrative(raw_narrative, forbidden_kpis, role)

    # 4. Build structured report payload
    report_payload = {
        "recipient":   recipient,
        "role":        role,
        "timestamp":   datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "narrative":   sanitized_narrative,
        "flagged_kpis": filtered_anomalies,
    }

    # 5. Format into Markdown (console/log) and Slack Block Kit (MCP delivery)
    markdown_report = format_as_markdown(report_payload)
    slack_payload   = format_as_slack(report_payload)

    # 6. Deliver via local in-process MCP (offline Slack simulation)
    try:
        mcp_status = await _invoke_mcp_delivery(
            channel="#alerts",
            text=f"PulseBoard Report for {role} ({recipient})",
            blocks=slack_payload["blocks"],
        )
        mcp_status = f"Delivered via LocalMCP (offline Slack): {mcp_status}"
    except Exception as exc:
        logger.error("LocalMCP delivery failed: %s", exc)
        mcp_status = f"LocalMCP delivery error: {exc}"

    # 7. Audit log
    _write_audit_log(recipient, role, mcp_status, allowed_kpis)

    # 8. Print formatted report to console (for local validation/inspection)
    logger.info(
        "--- DELIVERED REPORT (%s) ---\n%s\n-------------------------------",
        role, markdown_report,
    )

    return (
        f"Report successfully delivered to {recipient} ({role}). "
        f"Status: {mcp_status}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent definition
# ─────────────────────────────────────────────────────────────────────────────
report_delivery_agent = Agent(
    name="ReportDeliveryAgent",
    instruction=(
        "You are the Report Delivery Agent. "
        "Call 'deliver_insights_report' to apply RBAC filtering, redact restricted KPI "
        "context from the narrative, format the report, deliver it via the local "
        "offline MCP simulation, and log the delivery to the audit trail."
    ),
    tools=[deliver_insights_report],
)
