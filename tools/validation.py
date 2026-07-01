import re
from typing import Any, Dict, Union

# List of typical prompt injection indicator patterns (case-insensitive)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?prior\s+instructions",
    r"disregard\s+(?:all\s+)?previous\s+instructions",
    r"system\s+prompt",
    r"you\s+are\s+now\s+a\s+",
    r"override\s+instructions",
    r"new\s+role\s+:",
    r"ignore\s+above",
]

def sanitize_string(val: str) -> str:
    """
    Sanitizes string inputs to prevent formula injection and strip potential prompt injections.
    """
    if not val:
        return ""
    
    # 1. Prevent Formula Injection (CSV Injection)
    # Characters that Excel/Sheets interpret as formulas: =, +, -, @, \t, \r
    # We prepending a single quote to prevent execution in spreadsheet clients.
    if val.startswith(('=', '+', '-', '@')):
        val = "'" + val

    # 2. Block/Strip Prompt Injection indicators
    for pattern in PROMPT_INJECTION_PATTERNS:
        val = re.sub(pattern, "[REDACTED INJECTION ATTEMPT]", val, flags=re.IGNORECASE)

    # 3. Basic string escaping (escape backslashes, strip leading/trailing whitespace)
    val = val.strip()
    return val

def validate_kpi_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a KPI row from raw ingestion. Ensures data integrity and type safety.
    Raises ValueError if critical schema items are missing or invalid.
    """
    required_cols = {"date", "kpi_name", "value"}
    missing = required_cols - set(row.keys())
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    sanitized = {}
    
    # Ingest date
    date_val = str(row["date"]).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_val):
        raise ValueError(f"Invalid date format: '{date_val}'. Must be YYYY-MM-DD")
    sanitized["date"] = date_val

    # Ingest KPI name
    kpi_name = sanitize_string(str(row["kpi_name"]))
    if not kpi_name:
        raise ValueError("KPI name cannot be empty")
    # Normalize KPI names to alphanumeric + underscores
    kpi_name = re.sub(r"[^a-zA-Z0-9_]", "", kpi_name)
    sanitized["kpi_name"] = kpi_name

    # Ingest Value
    try:
        raw_val = row["value"]
        if raw_val is None or str(raw_val).strip() == "":
            raise ValueError("Value is empty")
        # Sanitize float input
        sanitized["value"] = float(str(raw_val).strip())
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid KPI value '{row.get('value')}': must be a float number. Detail: {e}")

    # Optional team info
    if "team" in row:
        team_val = str(row["team"]).strip()
        sanitized["team"] = sanitize_string(team_val) if team_val else "General"
    else:
        sanitized["team"] = "General"

    return sanitized
