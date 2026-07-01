import argparse
import json
import os
import sys
from typing import Dict, Any

def format_as_markdown(data: Dict[str, Any]) -> str:
    """
    Formats the analysis and insights as a clean Markdown report.
    """
    recipient = data.get("recipient", "Valued Recipient")
    role = data.get("role", "General User")
    narrative = data.get("narrative", "No insights generated.")
    flagged = data.get("flagged_kpis", {})

    lines = []
    lines.append(f"# PulseBoard Executive Report")
    lines.append(f"**Recipient:** {recipient} ({role})")
    lines.append(f"**Generated:** {data.get('timestamp', 'N/A')}\n")
    
    lines.append("## Executive Summary & Insights")
    lines.append(f"{narrative}\n")

    lines.append("## KPI Flagged Statuses")
    if not flagged:
        lines.append("*No anomalies flagged for your role.*")
    else:
        lines.append("| KPI Name | Team | Latest Value | Rolling Mean | Z-Score | Status |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for kpi, details in flagged.items():
            val = details.get('latest_value', 0.0)
            mean = details.get('rolling_mean', 0.0)
            z = details.get('z_score', 0.0)
            status = details.get('status', 'Normal')
            team = details.get('team', 'General')
            
            # Highlight Critical status
            status_str = f"🔴 **{status}**" if status == "Critical" else (f"🟡 *{status}*" if status == "Watch" else f"🟢 {status}")
            lines.append(f"| {kpi} | {team} | {val:,.2f} | {mean:,.2f} | {z:+.2f} | {status_str} |")
    
    lines.append("\n---\n*Confidential - PulseBoard Audit-logged BI Distribution*")
    return "\n".join(lines)

def format_as_html(data: Dict[str, Any]) -> str:
    """
    Formats the analysis and insights as a styled HTML email report.
    """
    recipient = data.get("recipient", "Valued Recipient")
    role = data.get("role", "General User")
    narrative = data.get("narrative", "No insights generated.").replace("\n", "<br>")
    flagged = data.get("flagged_kpis", {})

    html = []
    html.append("<html>")
    html.append("<head>")
    html.append("<style>")
    html.append("body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 800px; margin: 20px auto; padding: 20px; }")
    html.append("h1 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }")
    html.append("h2 { color: #5f6368; margin-top: 30px; }")
    html.append("table { width: 100%; border-collapse: collapse; margin-top: 15px; }")
    html.append("th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }")
    html.append("th { background-color: #f1f3f4; color: #202124; font-weight: bold; }")
    html.append(".critical { color: #d93025; font-weight: bold; }")
    html.append(".watch { color: #f29900; font-style: italic; }")
    html.append(".normal { color: #188038; }")
    html.append(".footer { font-size: 0.85em; color: #70757a; margin-top: 40px; border-top: 1px solid #eee; padding-top: 15px; }")
    html.append("</style>")
    html.append("</head>")
    html.append("<body>")
    
    html.append("<h1>PulseBoard Executive Report</h1>")
    html.append(f"<p><strong>Recipient:</strong> {recipient} ({role})<br>")
    html.append(f"<strong>Generated:</strong> {data.get('timestamp', 'N/A')}</p>")
    
    html.append("<h2>Executive Summary & Insights</h2>")
    html.append(f"<p>{narrative}</p>")
    
    html.append("<h2>KPI Flagged Statuses</h2>")
    if not flagged:
        html.append("<p><em>No anomalies flagged for your role.</em></p>")
    else:
        html.append("<table>")
        html.append("<tr><th>KPI Name</th><th>Team</th><th>Latest Value</th><th>Rolling Mean</th><th>Z-Score</th><th>Status</th></tr>")
        for kpi, details in flagged.items():
            val = details.get('latest_value', 0.0)
            mean = details.get('rolling_mean', 0.0)
            z = details.get('z_score', 0.0)
            status = details.get('status', 'Normal')
            team = details.get('team', 'General')
            
            status_class = "critical" if status == "Critical" else ("watch" if status == "Watch" else "normal")
            html.append(f"<tr>")
            html.append(f"  <td><strong>{kpi}</strong></td>")
            html.append(f"  <td>{team}</td>")
            html.append(f"  <td>{val:,.2f}</td>")
            html.append(f"  <td>{mean:,.2f}</td>")
            html.append(f"  <td>{z:+.2f}</td>")
            html.append(f"  <td><span class='{status_class}'>{status}</span></td>")
            html.append(f"</tr>")
        html.append("</table>")
        
    html.append("<div class='footer'>Confidential - PulseBoard Audit-logged BI Distribution</div>")
    html.append("</body>")
    html.append("</html>")
    return "\n".join(html)

def format_as_slack(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the report for Slack Block Kit.
    """
    recipient = data.get("recipient", "Valued Recipient")
    role = data.get("role", "General User")
    narrative = data.get("narrative", "No insights generated.")
    flagged = data.get("flagged_kpis", {})

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 PulseBoard Executive Report",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Recipient:* {recipient} ({role})"},
                {"type": "mrkdwn", "text": f"*Generated:* {data.get('timestamp', 'N/A')}"}
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Executive Summary & Insights:*\n{narrative}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*KPI Flagged Statuses:*"
            }
        }
    ]

    if not flagged:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "_No anomalies flagged for your role._"
            }
        })
    else:
        kpi_fields = []
        for kpi, details in flagged.items():
            val = details.get('latest_value', 0.0)
            status = details.get('status', 'Normal')
            status_icon = "🔴" if status == "Critical" else ("🟡" if status == "Watch" else "🟢")
            
            kpi_fields.append({
                "type": "mrkdwn",
                "text": f"*{kpi}* ({details.get('team', 'General')})\nValue: {val:,.2f} | Status: {status_icon} *{status}*"
            })
            
            # Slack section fields can have max 10 elements. If we exceed, we split blocks.
            if len(kpi_fields) == 10:
                blocks.append({
                    "type": "section",
                    "fields": kpi_fields
                })
                kpi_fields = []
                
        if kpi_fields:
            blocks.append({
                "type": "section",
                "fields": kpi_fields
            })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "🔒 Confidential | PulseBoard Audit-logged BI Distribution"
            }
        ]
    })

    return {"blocks": blocks}

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(description="PulseBoard Report Formatting Skill")
    parser.add_argument("--report", required=True, help="Path to JSON report data file")
    parser.add_argument("--format", choices=["markdown", "html", "slack"], default="markdown", help="Target output format")
    parser.add_argument("--output", help="Optional path to save formatted output file")

    args = parser.parse_args()

    if not os.path.exists(args.report):
        print(f"Error: report file not found at {args.report}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.report, "r") as f:
            data = json.load(f)

        if args.format == "markdown":
            formatted = format_as_markdown(data)
        elif args.format == "html":
            formatted = format_as_html(data)
        elif args.format == "slack":
            formatted = json.dumps(format_as_slack(data), indent=2)
        else:
            raise ValueError(f"Unknown format: {args.format}")

        if args.output:
            with open(args.output, "w") as f_out:
                f_out.write(formatted)
            print(f"Formatted report successfully written to {args.output}")
        else:
            print(formatted)
            
    except Exception as e:
        print(f"Error during report formatting: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
