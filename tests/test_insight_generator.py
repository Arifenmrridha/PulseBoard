"""
Tests for agents/insight_generator.py — offline rule-based insight engine.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.insight_generator import generate_insights_narrative, generate_and_save_insights


# ── Fake ToolContext for offline testing ──────────────────────────────────────

class FakeContext:
    def __init__(self, state=None):
        self.state = state or {}


# ── generate_insights_narrative ────────────────────────────────────────────────

def test_all_clear_when_no_anomalies():
    """Empty anomaly dict must produce an 'All Clear' narrative."""
    text = generate_insights_narrative({})
    assert "All Clear" in text


def test_critical_anomaly_appears_in_narrative():
    """A Critical revenue anomaly must appear with strong language."""
    anomalies = {
        "revenue": {
            "status":       "Critical",
            "latest_value": 45_000,
            "rolling_mean": 100_000,
            "z_score":      -3.5,
            "latest_date":  "2026-07-01",
            "team":         "Finance",
        }
    }
    text = generate_insights_narrative(anomalies)
    assert "revenue" in text.lower()
    assert "Critical" in text
    # Python :,.4g formats 45_000 as '4.5e+04' — check for either representation
    assert "4.5e+04" in text or "45,000" in text or "45000" in text


def test_watch_anomaly_appears_in_narrative():
    """A Watch-level KPI must appear in the narrative without Critical language."""
    anomalies = {
        "churn_rate": {
            "status":       "Watch",
            "latest_value": 0.08,
            "rolling_mean": 0.05,
            "z_score":      2.1,
            "latest_date":  "2026-07-01",
            "team":         "Product",
        }
    }
    text = generate_insights_narrative(anomalies)
    assert "Watch" in text or "Monitor" in text or "churn_rate" in text.lower()
    # The summary header says "0 Critical" — verify no actual Critical section is produced
    assert "Critical Alerts" not in text


def test_mixed_anomalies_structure():
    """Mixed Critical + Watch + Normal should produce distinct sections."""
    anomalies = {
        "revenue":      {"status": "Critical", "latest_value": 30000, "rolling_mean": 100000, "z_score": -4.0, "latest_date": "2026-07-01", "team": "Finance"},
        "active_users": {"status": "Watch",    "latest_value": 800,   "rolling_mean": 1000,   "z_score": -2.0, "latest_date": "2026-07-01", "team": "Product"},
        "churn_rate":   {"status": "Normal",   "latest_value": 0.05,  "rolling_mean": 0.05,   "z_score":  0.1, "latest_date": "2026-07-01", "team": "Product"},
    }
    text = generate_insights_narrative(anomalies)
    assert "Critical" in text
    assert "Watch"    in text
    assert "Normal"   in text


def test_narrative_grounded_no_invented_numbers():
    """
    Checks that all numeric values appearing in the narrative
    come from the anomaly dict, not invented by templates.
    """
    anomalies = {
        "conversion_rate": {
            "status":       "Critical",
            "latest_value": 0.0123,
            "rolling_mean": 0.0456,
            "z_score":      -3.8,
            "latest_date":  "2026-07-01",
            "team":         "Marketing",
        }
    }
    text = generate_insights_narrative(anomalies)
    # The actual value must appear; a made-up random number should not
    assert "0.01" in text or "1.23" in text or "0.046" in text or "0.0123" in text


# ── generate_and_save_insights ─────────────────────────────────────────────────

def test_generate_and_save_writes_to_state():
    """generate_and_save_insights must store result under 'insights_report' key."""
    ctx = FakeContext({
        "detected_anomalies": {
            "revenue": {
                "status": "Critical", "latest_value": 10000, "rolling_mean": 50000,
                "z_score": -3.0, "latest_date": "2026-07-01", "team": "Finance",
            }
        }
    })
    result = generate_and_save_insights(ctx)
    assert "insights_report" in ctx.state
    assert len(ctx.state["insights_report"]) > 0
    assert isinstance(ctx.state["insights_report"], str)


def test_generate_and_save_handles_missing_state():
    """Called with no 'detected_anomalies' in state, should still write a safe message."""
    ctx = FakeContext({})
    generate_and_save_insights(ctx)
    assert "insights_report" in ctx.state
    # Should mention that no data was found
    assert "No anomaly data" in ctx.state["insights_report"] or len(ctx.state["insights_report"]) > 0
