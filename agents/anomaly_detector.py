import pandas as pd
import logging
from typing import Dict, Any

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

from skills.anomaly_detection import detect_anomalies

logger = logging.getLogger("PulseBoard.Agents.AnomalyDetector")

def run_anomaly_detection(
    tool_context: ToolContext,
    periods: int = 7,
    threshold_watch: float = 1.5,
    threshold_critical: float = 3.0
) -> str:
    """
    Retrieves the raw KPI data from the session state, executes the anomaly detection
    skill to calculate rolling z-scores, and saves the classification results to session state.
    
    Args:
        periods: The rolling window period size (N periods).
        threshold_watch: Z-score threshold for Watch classification.
        threshold_critical: Z-score threshold for Critical classification.
    """
    raw_data = tool_context.state.get("raw_kpi_data", [])
    if not raw_data:
        return "Error: No raw KPI data found in session state. Please run DataIngestionAgent first."

    try:
        # Convert to DataFrame
        df = pd.DataFrame(raw_data)
        
        # Run anomaly detection skill
        results = detect_anomalies(
            df=df,
            periods=periods,
            threshold_watch=threshold_watch,
            threshold_critical=threshold_critical
        )
        
        # Save to session state
        tool_context.state["detected_anomalies"] = results
        
        # Summarize classifications
        watch_kpis = [k for k, v in results.items() if v["status"] == "Watch"]
        critical_kpis = [k for k, v in results.items() if v["status"] == "Critical"]
        
        summary = (
            f"Anomaly detection finished. Analyzed {len(results)} KPIs. "
            f"Watch: {len(watch_kpis)} ({', '.join(watch_kpis) if watch_kpis else 'None'}), "
            f"Critical: {len(critical_kpis)} ({', '.join(critical_kpis) if critical_kpis else 'None'})."
        )
        
        logger.info(summary)
        return summary
    except Exception as e:
        logger.error(f"Error executing anomaly detection: {e}")
        return f"Anomaly detection failed: {e}"

# Define the Agent
anomaly_detector_agent = Agent(
    name="AnomalyDetectionAgent",
    instruction=(
        "You are the Anomaly Detection Agent. Your role is to take raw KPI data from the session state, "
        "execute the 'run_anomaly_detection' tool to flag Watch/Critical anomalies, "
        "and record details back to the session state."
    ),
    tools=[run_anomaly_detection]
)
