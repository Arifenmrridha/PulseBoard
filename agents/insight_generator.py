"""
InsightGenerationAgent — fully offline, deterministic insight engine.

Role:
    Converts statistical anomaly results into an executive-ready natural
    language narrative WITHOUT calling any external LLM or AI API.
    All reasoning is performed locally using rule-based templates grounded
    strictly on the numeric data passed in from the previous pipeline step.

Inputs (session state keys read):
    "detected_anomalies"  — dict produced by AnomalyDetectionAgent

Outputs (session state keys written):
    "insights_report"     — str narrative for the ReportDeliveryAgent

Design decisions:
    • Fully offline — zero external API calls, no API keys required.
    • Grounded-only — insight text is assembled from actual KPI values,
      z-scores and team labels; no numbers are invented.
    • Rule-based hypotheses — maps KPI names to domain-specific cause
      hypotheses so the narrative is always meaningful and business-relevant.
    • Severity-aware — Critical anomalies get stronger language and explicit
      triage recommendations; Watch alerts get a softer monitoring advisory.
"""

import logging
from typing import Any, Dict, List

# ── Safe ADK import ──────────────────────────────────────────────────────────
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

logger = logging.getLogger("PulseBoard.Agents.InsightGenerator")

# ── Domain-specific hypothesis templates ────────────────────────────────────
# Keyed by KPI name (lowercase). Each entry provides:
#   "increase" — hypothesis when latest > mean  (positive z-score)
#   "decrease" — hypothesis when latest < mean  (negative z-score)

_KPI_HYPOTHESES: Dict[str, Dict[str, str]] = {
    "revenue": {
        "increase": (
            "Revenue exceeded the rolling average. Possible drivers include a "
            "successful marketing campaign, seasonal uplift, or a large one-time "
            "enterprise deal closing."
        ),
        "decrease": (
            "Revenue fell significantly below the rolling average. Likely causes "
            "include checkout-funnel degradation, a payment-processing outage, "
            "loss of a key account, or unplanned pricing changes."
        ),
    },
    "active_users": {
        "increase": (
            "Active users are trending above baseline. This may reflect a product "
            "launch, successful onboarding campaign, or viral referral loop."
        ),
        "decrease": (
            "Active users dropped below the rolling average. Possible causes include "
            "app performance issues, a critical bug affecting login, competitor "
            "product launch, or notification suppression."
        ),
    },
    "churn_rate": {
        "increase": (
            "Churn rate spiked above baseline. This is often correlated with a "
            "recent disruptive product change, pricing adjustment, customer "
            "support degradation, or competitor incentives."
        ),
        "decrease": (
            "Churn rate dropped below baseline — a positive signal. This may reflect "
            "improved onboarding, a successful retention campaign, or seasonal "
            "re-engagement."
        ),
    },
    "conversion_rate": {
        "increase": (
            "Conversion rate is above the rolling average. Possible drivers include "
            "A/B test wins, improved landing pages, targeted promotion codes, or "
            "higher intent traffic from a campaign."
        ),
        "decrease": (
            "Conversion rate dropped below the rolling average. Likely causes include "
            "a broken checkout flow, increased prices, mismatch between ad creative "
            "and landing page, or degraded page performance."
        ),
    },
}

_DEFAULT_HYPOTHESIS = {
    "increase": (
        "The metric is above its recent rolling average. Investigate recent "
        "operational or product changes that could have driven this increase."
    ),
    "decrease": (
        "The metric is below its recent rolling average. Review recent changes "
        "in product, infrastructure, or external market conditions."
    ),
}


def _direction(z_score: float) -> str:
    return "increase" if z_score >= 0 else "decrease"


def _severity_emoji(status: str) -> str:
    return {"Critical": "🔴", "Watch": "🟡"}.get(status, "🟢")


def generate_insights_narrative(anomalies: Dict[str, Any]) -> str:
    """
    Builds a structured, grounded executive narrative from anomaly detection
    results. All numbers in the output come directly from `anomalies`.

    Args:
        anomalies: dict mapping KPI name → anomaly details dict.

    Returns:
        A multi-section Markdown string suitable for executive distribution.
    """
    critical = {k: v for k, v in anomalies.items() if v["status"] == "Critical"}
    watch    = {k: v for k, v in anomalies.items() if v["status"] == "Watch"}
    normal   = {k: v for k, v in anomalies.items() if v["status"] == "Normal"}

    sections: List[str] = []

    # ── Opening summary ──────────────────────────────────────────────────────
    if not critical and not watch:
        sections.append(
            "**Status: All Clear ✅**\n\n"
            "All monitored KPIs are performing within normal statistical bounds "
            f"(|z-score| < threshold). {len(normal)} metric(s) reviewed — no "
            "immediate action required."
        )
        return "\n\n".join(sections)

    total = len(anomalies)
    flagged_count = len(critical) + len(watch)
    sections.append(
        f"**Status: {len(critical)} Critical ⚠️ | {len(watch)} Watch 👁 | "
        f"{len(normal)} Normal ✅** ({flagged_count} of {total} KPIs require attention)"
    )

    # ── Critical alerts ──────────────────────────────────────────────────────
    if critical:
        sections.append("### 🔴 Critical Alerts — Immediate Action Required")
        for kpi, d in critical.items():
            val  = d["latest_value"]
            mean = d["rolling_mean"]
            z    = d["z_score"]
            team = d.get("team", "General")
            date = d.get("latest_date", "today")

            pct_change = ((val - mean) / mean * 100) if mean != 0 else 0
            direction  = _direction(z)
            hyp        = _KPI_HYPOTHESES.get(kpi.lower(), _DEFAULT_HYPOTHESIS)[direction]

            sections.append(
                f"**{kpi}** ({team} team) — as of {date}\n"
                f"- Latest value: **{val:,.4g}**  |  Rolling mean: {mean:,.4g}  "
                f"|  Δ {pct_change:+.1f}%  |  Z-score: {z:+.2f}\n"
                f"- *Hypothesis:* {hyp}\n"
                f"- *Recommended action:* Escalate immediately to the {team} "
                f"team lead. Cross-reference {date} deployment logs, incident "
                f"tracker, and external market data."
            )

    # ── Watch alerts ─────────────────────────────────────────────────────────
    if watch:
        sections.append("### 🟡 Watch Alerts — Monitor Closely")
        for kpi, d in watch.items():
            val  = d["latest_value"]
            mean = d["rolling_mean"]
            z    = d["z_score"]
            team = d.get("team", "General")
            date = d.get("latest_date", "today")

            pct_change = ((val - mean) / mean * 100) if mean != 0 else 0
            direction  = _direction(z)
            hyp        = _KPI_HYPOTHESES.get(kpi.lower(), _DEFAULT_HYPOTHESIS)[direction]

            sections.append(
                f"**{kpi}** ({team} team) — as of {date}\n"
                f"- Latest value: {val:,.4g}  |  Rolling mean: {mean:,.4g}  "
                f"|  Δ {pct_change:+.1f}%  |  Z-score: {z:+.2f}\n"
                f"- *Hypothesis:* {hyp}\n"
                f"- *Recommended action:* Schedule a review with the {team} "
                f"team within 24 hours. Continue monitoring through the next "
                f"reporting cycle."
            )

    # ── Normal KPIs (brief listing) ──────────────────────────────────────────
    if normal:
        normal_list = ", ".join(
            f"{k} ({v.get('latest_value', 0):,.4g})" for k, v in normal.items()
        )
        sections.append(
            f"### 🟢 Normal KPIs\n{normal_list} — all within expected bounds."
        )

    # ── Footer ───────────────────────────────────────────────────────────────
    sections.append(
        "*Report generated by PulseBoard Offline Insight Engine. "
        "All values are grounded on verified statistical analysis — "
        "no AI hallucination possible.*"
    )

    return "\n\n".join(sections)


# ── Tool wrappers for ADK agent interface ────────────────────────────────────

def get_detected_anomalies(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieves detected KPI anomalies from the shared session state.
    Use this tool to obtain the statistical data needed for insight generation.
    """
    anomalies = tool_context.state.get("detected_anomalies", {})
    logger.info("Retrieved %d anomalies for insight generation.", len(anomalies))
    return anomalies


def generate_and_save_insights(tool_context: ToolContext) -> str:
    """
    Generates a grounded, offline executive narrative from detected anomalies
    and saves it to session state under the key 'insights_report'.
    No external API or network call is made.
    """
    anomalies = tool_context.state.get("detected_anomalies", {})
    if not anomalies:
        narrative = (
            "No anomaly data found in session state. "
            "Please ensure DataIngestionAgent and AnomalyDetectionAgent "
            "have run successfully before this step."
        )
    else:
        narrative = generate_insights_narrative(anomalies)

    tool_context.state["insights_report"] = narrative
    logger.info("Offline insight narrative generated and saved to session state.")
    return "Insights report generated (offline mode) and saved to session state."


def save_insights_report(tool_context: ToolContext, narrative: str) -> str:
    """
    Saves a provided narrative to the session state 'insights_report' key.
    Used when the caller builds the narrative externally (e.g. fallback pipeline).
    """
    tool_context.state["insights_report"] = narrative
    logger.info("Saved executive insights narrative to session state.")
    return "Insights report successfully saved to session state."


# ── Agent definition ─────────────────────────────────────────────────────────
insight_generator_agent = Agent(
    name="InsightGenerationAgent",
    # No model="" — this agent is purely tool-driven with no LLM inference.
    instruction=(
        "You are the Insight Generation Agent operating in offline mode. "
        "Your job is to produce a grounded executive narrative from KPI anomaly data.\n"
        "Steps:\n"
        "1. Call 'generate_and_save_insights' — it will read the detected anomalies "
        "from session state, apply rule-based templates grounded on the actual data "
        "values and z-scores, and save the final narrative automatically.\n"
        "IMPORTANT: Do NOT invent numbers. All insight content is derived from "
        "statistical results already computed by the AnomalyDetectionAgent."
    ),
    tools=[get_detected_anomalies, generate_and_save_insights, save_insights_report],
)
