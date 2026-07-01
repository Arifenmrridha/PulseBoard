"""
PulseBoard Pipeline Orchestrator — fully offline, no external API keys required.

Runs the four-agent SequentialAgent pipeline:
  DataIngestionAgent → AnomalyDetectionAgent → InsightGenerationAgent → ReportDeliveryAgent

All agents, MCP delivery, and insight generation operate entirely in-process.
No internet connection, no Gemini/OpenAI/Vertex API key is needed.

Usage:
  python main.py --recipient exec@company.com --role Executive
  python main.py --recipient lead@company.com --role "Product Lead"
  python main.py --role "Finance Lead"  --data tools/mock_kpis.csv
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

# ── UTF-8 console on Windows (supports status emojis) ────────────────────────
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# ── Load .env if present (optional) ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("PulseBoard.Orchestrator")

# ── Agent tool imports ────────────────────────────────────────────────────────
from agents.data_ingestion  import ingest_kpi_data
from agents.anomaly_detector import run_anomaly_detection
from agents.insight_generator import generate_and_save_insights, save_insights_report, generate_insights_narrative, get_detected_anomalies
from agents.report_delivery  import deliver_insights_report

# ── Offline MockToolContext (no ADK Runner / no API key needed) ───────────────
class OfflineContext:
    """
    Lightweight stand-in for ADK's InvocationContext / ToolContext.
    Provides a shared state dict that all agent tools read/write to,
    replicating the behaviour of ADK session state without any network calls.
    """
    def __init__(self, initial_state: dict | None = None):
        self.state: dict = initial_state or {}


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline runner
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(csv_path: str, recipient: str, role: str) -> str:
    """
    Executes the full four-step PulseBoard pipeline in sequence, sharing state
    through an OfflineContext.  No LLM API, no external MCP server, no key.

    Returns:
        A status string summarising the delivery outcome.
    """
    logger.info("=" * 60)
    logger.info("PulseBoard — Offline Multi-Agent Pipeline")
    logger.info("Recipient : %s", recipient)
    logger.info("Role      : %s", role)
    logger.info("Data file : %s", csv_path)
    logger.info("=" * 60)

    ctx = OfflineContext({
        "recipient_email": recipient,
        "recipient_role":  role,
        "csv_path":        csv_path,
    })

    # ── Step 1: DataIngestionAgent ────────────────────────────────────────────
    logger.info("[1/4] DataIngestionAgent — ingesting & validating KPI data...")
    ingest_result = ingest_kpi_data(ctx, csv_path=csv_path)
    logger.info("      Result: %s", ingest_result)
    if "Error" in ingest_result:
        logger.error("Ingestion failed. Aborting pipeline.")
        return ingest_result

    # ── Step 2: AnomalyDetectionAgent ────────────────────────────────────────
    logger.info("[2/4] AnomalyDetectionAgent — computing z-scores & classifying KPIs...")
    anomaly_result = run_anomaly_detection(ctx)
    logger.info("      Result: %s", anomaly_result)

    # ── Step 3: InsightGenerationAgent (offline, deterministic) ──────────────
    logger.info("[3/4] InsightGenerationAgent — building grounded narrative (offline)...")
    insight_result = generate_and_save_insights(ctx)
    logger.info("      Result: %s", insight_result)

    # ── Step 4: ReportDeliveryAgent ───────────────────────────────────────────
    logger.info("[4/4] ReportDeliveryAgent — applying RBAC, formatting, delivering...")
    delivery_result = await deliver_insights_report(ctx)
    logger.info("      Result: %s", delivery_result)

    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("=" * 60)
    return delivery_result


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="PulseBoard — Offline Multi-Agent KPI Intelligence Pipeline"
    )
    parser.add_argument(
        "--recipient", default="executive@company.com",
        help="Report recipient e-mail address",
    )
    parser.add_argument(
        "--role", default="Executive",
        help="Recipient role: Executive / Product Lead / Marketing Lead / Finance Lead / Team Lead",
    )
    parser.add_argument(
        "--data", default="tools/mock_kpis.csv",
        help="Path to raw KPI data CSV file",
    )
    args = parser.parse_args()

    try:
        result = await run_pipeline(args.data, args.recipient, args.role)
        sys.exit(0)
    except Exception as exc:
        logger.error("Pipeline encountered an unhandled error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
