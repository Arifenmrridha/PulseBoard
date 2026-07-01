import argparse
import json
import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, Any, List

def detect_anomalies(
    df: pd.DataFrame,
    kpi_col: str = "kpi_name",
    val_col: str = "value",
    date_col: str = "date",
    team_col: str = "team",
    periods: int = 7,
    threshold_watch: float = 1.5,
    threshold_critical: float = 3.0
) -> Dict[str, Any]:
    """
    Detects statistical anomalies on KPI time series data.
    Assumes data is sorted by date ascending.
    Calculates rolling mean and rolling std deviation over last N periods for each KPI.
    
    Returns a dictionary of analysis results.
    """
    # Verify columns exist
    for col in [kpi_col, val_col, date_col]:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in DataFrame.")

    # Convert date to datetime and sort
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=[kpi_col, date_col]).reset_index(drop=True)

    results = {}
    kpis = df[kpi_col].unique()

    for kpi in kpis:
        kpi_df = df[df[kpi_col] == kpi].copy()
        if len(kpi_df) == 0:
            continue
            
        # Get team name
        team = kpi_df[team_col].iloc[-1] if team_col in kpi_df.columns else "General"

        # Calculate rolling statistics
        kpi_df["rolling_mean"] = kpi_df[val_col].shift(1).rolling(window=periods, min_periods=min(3, periods)).mean()
        kpi_df["rolling_std"] = kpi_df[val_col].shift(1).rolling(window=periods, min_periods=min(3, periods)).std()

        # Fill NaNs where rolling std cannot be calculated (e.g. not enough data)
        # If we have only 1-2 points, rolling_std is NaN. We default rolling_mean to the previous point, and rolling_std to 0.
        kpi_df["rolling_mean"] = kpi_df["rolling_mean"].ffill().fillna(kpi_df[val_col])
        kpi_df["rolling_std"] = kpi_df["rolling_std"].fillna(0.0)

        # Get latest data point
        latest = kpi_df.iloc[-1]
        latest_val = float(latest[val_col])
        mean_val = float(latest["rolling_mean"])
        std_val = float(latest["rolling_std"])
        latest_date = latest[date_col].strftime("%Y-%m-%d")

        # Z-score calculation
        # Handle zero standard deviation
        if std_val == 0.0:
            if latest_val == mean_val:
                z_score = 0.0
            else:
                # If value changed but std is 0 (constant history), flag it.
                # If it went up, z_score is positive; if down, negative.
                z_score = 4.0 if latest_val > mean_val else -4.0
        else:
            z_score = (latest_val - mean_val) / std_val

        # Classification
        abs_z = abs(z_score)
        if abs_z >= threshold_critical:
            classification = "Critical"
        elif abs_z >= threshold_watch:
            classification = "Watch"
        else:
            classification = "Normal"

        results[str(kpi)] = {
            "kpi_name": str(kpi),
            "team": str(team),
            "latest_date": latest_date,
            "latest_value": latest_val,
            "rolling_mean": mean_val,
            "rolling_std": std_val,
            "z_score": float(z_score),
            "status": classification,
            "history": kpi_df[[date_col, val_col]].tail(periods + 1).to_dict(orient="records")
        }
        # Format dates in history
        for record in results[str(kpi)]["history"]:
            record[date_col] = record[date_col].strftime("%Y-%m-%d")

    return results

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(description="Statistical KPI Anomaly Detection Skill")
    parser.add_argument("--data", required=True, help="Path to CSV containing KPI data")
    parser.add_argument("--kpi-col", default="kpi_name", help="KPI name column")
    parser.add_argument("--val-col", default="value", help="KPI value column")
    parser.add_argument("--date-col", default="date", help="Date column (YYYY-MM-DD)")
    parser.add_argument("--team-col", default="team", help="Team column")
    parser.add_argument("--periods", type=int, default=7, help="Rolling window size (N periods)")
    parser.add_argument("--threshold-watch", type=float, default=1.5, help="Z-score threshold for Watch")
    parser.add_argument("--threshold-critical", type=float, default=3.0, help="Z-score threshold for Critical")
    
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"Error: file not found at {args.data}", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(args.data)
        results = detect_anomalies(
            df=df,
            kpi_col=args.kpi_col,
            val_col=args.val_col,
            date_col=args.date_col,
            team_col=args.team_col,
            periods=args.periods,
            threshold_watch=args.threshold_watch,
            threshold_critical=args.threshold_critical
        )
        # Print JSON output to stdout
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error during anomaly detection: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
