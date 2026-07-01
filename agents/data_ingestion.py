import os
import csv
import logging
from typing import Optional, List, Dict, Any

# Safe imports for ADK components
try:
    from google.adk.tools import ToolContext
except ImportError:
    try:
        from google.adk.context import ToolContext
    except ImportError:
        try:
            from google.adk import ToolContext
        except ImportError:
            # Fallback for compilation
            class ToolContext:
                def __init__(self):
                    self.state = {}

try:
    from google.adk.agents import LlmAgent as Agent
except ImportError:
    try:
        from google.adk import Agent
    except ImportError:
        class Agent:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

from tools.validation import validate_kpi_row

logger = logging.getLogger("PulseBoard.Agents.DataIngestion")

def ingest_kpi_data(tool_context: ToolContext, csv_path: str = "tools/mock_kpis.csv") -> str:
    """
    Ingests raw KPI data from a CSV spreadsheet source, sanitizes the inputs
    against injection, and stores a structured schema in the shared session state.
    
    Args:
        csv_path: The file path to the KPI data CSV.
    """
    if not os.path.exists(csv_path):
        return f"Error: KPI source file not found at {csv_path}"

    cleaned_records = []
    malformed_count = 0
    errors = []

    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                try:
                    # Sanitize and validate
                    clean_row = validate_kpi_row(row)
                    cleaned_records.append(clean_row)
                except ValueError as ve:
                    malformed_count += 1
                    errors.append(f"Row {idx+1}: {ve}")
                    logger.warning(f"Integrity check failed: {ve}")

        # Store in session state
        tool_context.state["raw_kpi_data"] = cleaned_records
        
        status_msg = f"Data ingestion completed. Ingested {len(cleaned_records)} valid rows."
        if malformed_count > 0:
            status_msg += f" Flagged {malformed_count} malformed rows. Errors: {errors[:5]}"
            tool_context.state["ingestion_warnings"] = errors
            
        logger.info(status_msg)
        return status_msg
    except Exception as e:
        logger.error(f"Inexplicable error during CSV ingestion: {e}")
        return f"Data ingestion failed due to system error: {e}"

# Define the Agent
data_ingestion_agent = Agent(
    name="DataIngestionAgent",
    instruction=(
        "You are the Data Ingestion Agent. Your role is to connect to the raw KPI source, "
        "execute the 'ingest_kpi_data' tool, validate the schema, and store clean data in "
        "the session state for the rest of the pipeline."
    ),
    tools=[ingest_kpi_data]
)
