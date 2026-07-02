import math
from typing import Dict, Any
import numpy as np
import pandas as pd

def detect_anomalies(df: pd.DataFrame, periods: int = 7,
                     threshold_watch: float = 1.5,
                     threshold_critical: float = 3.0) -> Dict[str, Dict[str, Any]]:
    # Expect columns: date, kpi_name, value
    required = {"date", "kpi_name", "value"}
    if not required.issubset(df.columns):
        raise ValueError(f"Input DataFrame must contain columns: {required}")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    results = {}
    for kpi, group in df.groupby("kpi_name"):
        values = group["value"].reset_index(drop=True)
        if len(values) < 2:
            # Not enough data; mark as Normal with NaNs
            results[kpi] = {
                "status": "Normal",
                "latest_value": float(values.iloc[-1]) if len(values) else None,
                "rolling_mean": None,
                "rolling_std": None,
                "z_score": None
            }
            continue

        latest_value = float(values.iloc[-1])
        # history = previous 'periods' values (exclude latest)
        history = values.iloc[:-1].tail(periods)
        rolling_mean = float(history.mean())
        # sample standard deviation (ddof=1) to match tests' expected ~1.29
        rolling_std = float(history.std(ddof=1))

        # handle zero std fallback
        if math.isclose(rolling_std, 0.0, abs_tol=1e-12) or np.isnan(rolling_std):
            # Use a large z-score when value deviates from perfectly flat history
            if latest_value == rolling_mean:
                z = 0.0
            else:
                z = 4.0 if latest_value > rolling_mean else -4.0
        else:
            z = (latest_value - rolling_mean) / rolling_std

        abs_z = abs(z)
        if abs_z >= threshold_critical:
            status = "Critical"
        elif abs_z >= threshold_watch:
            status = "Watch"
        else:
            status = "Normal"

        results[kpi] = {
            "status": status,
            "latest_value": latest_value,
            "rolling_mean": rolling_mean,
            "rolling_std": rolling_std,
            "z_score": z
        }

    return results
