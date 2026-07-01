import pytest
import pandas as pd
from skills.anomaly_detection import detect_anomalies

def test_anomaly_detection_normal_vs_critical():
    # 7 days of normal data around 100, then a massive drop on day 8
    data = {
        "date": [
            "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04",
            "2026-06-05", "2026-06-06", "2026-06-07", "2026-06-08"
        ],
        "kpi_name": ["revenue"] * 8,
        "value": [100.0, 101.0, 99.0, 100.0, 102.0, 98.0, 100.0, 50.0],
        "team": ["Finance"] * 8
    }
    df = pd.DataFrame(data)
    
    # Calculate anomalies (rolling period = 7)
    results = detect_anomalies(df, periods=7)
    
    assert "revenue" in results
    kpi_res = results["revenue"]
    assert kpi_res["status"] == "Critical"  # 50 is far below the mean of ~100
    assert kpi_res["latest_value"] == 50.0
    assert kpi_res["rolling_mean"] == 100.0
    assert kpi_res["rolling_std"] == pytest.approx(1.29, abs=0.1)
    assert kpi_res["z_score"] < -3.0

def test_anomaly_detection_watch():
    # Z-score between 1.5 and 3.0
    data = {
        "date": [
            "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04",
            "2026-06-05", "2026-06-06", "2026-06-07", "2026-06-08"
        ],
        "kpi_name": ["conversion_rate"] * 8,
        "value": [0.050, 0.051, 0.049, 0.050, 0.052, 0.048, 0.050, 0.0475],
        "team": ["Marketing"] * 8
    }
    df = pd.DataFrame(data)
    
    results = detect_anomalies(df, periods=7, threshold_watch=1.5, threshold_critical=3.0)
    
    assert "conversion_rate" in results
    kpi_res = results["conversion_rate"]
    assert kpi_res["status"] == "Watch"  # 0.045 should flag as watch
    assert kpi_res["z_score"] < -1.5
    assert kpi_res["z_score"] > -3.0

def test_anomaly_detection_constant_history():
    # If the history is perfectly flat, std deviation is 0.
    # An increase should trigger an anomaly.
    data = {
        "date": ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"],
        "kpi_name": ["churn_rate"] * 4,
        "value": [0.02, 0.02, 0.02, 0.08],
        "team": ["Product"] * 4
    }
    df = pd.DataFrame(data)
    
    results = detect_anomalies(df, periods=3)
    
    assert "churn_rate" in results
    kpi_res = results["churn_rate"]
    assert kpi_res["status"] == "Critical"
    assert kpi_res["z_score"] == 4.0  # constant history fallback z-score
