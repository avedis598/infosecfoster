import json

EXECUTIVE_DASHBOARD = {
  "title": "Executive Dashboard",
  "uid": "executive",
  "schemaVersion": 38,
  "tags": ["client-facing"],
  "timezone": "browser",
  "refresh": "5m",
  "time": {"from": "now-30d", "to": "now"},
  "annotations": {"list": []},
  "templating": {"list": []},
  "panels": [
    {
      "type": "stat",
      "title": "Threats Blocked This Month",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "count"}],
          "query": "rule.level:>=10",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "OpenSearch"
    },
    {
      "type": "stat",
      "title": "Average Response Time",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "avg", "field": "response_time_median"}],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "SIEM-Telemetry"
    },
    {
      "type": "stat",
      "title": "Devices Protected",
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "max", "field": "active_agents"}],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "SIEM-Telemetry"
    },
    {
      "type": "stat",
      "title": "Security Posture Score",
      "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "avg", "field": "posture_score"}],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "SIEM-Telemetry"
    }
  ]
}

OPERATIONAL_DASHBOARD = {
  "title": "Operational Dashboard",
  "uid": "operational",
  "schemaVersion": 38,
  "tags": ["it-manager"],
  "timezone": "browser",
  "refresh": "30s",
  "time": {"from": "now-24h", "to": "now"},
  "annotations": {"list": []},
  "templating": {"list": []},
  "panels": [
    {
      "type": "stat",
      "title": "Open Critical Cases",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "max", "field": "open_critical_cases"}],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "SIEM-Telemetry"
    },
    {
      "type": "stat",
      "title": "Cases Awaiting Assignment",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "max", "field": "cases_awaiting_assignment"}],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "SIEM-Telemetry"
    },
    {
      "type": "stat",
      "title": "Agents Disconnected (1h)",
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "max", "field": "disconnected_agents"}],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "SIEM-Telemetry"
    },
    {
      "type": "stat",
      "title": "Failed Auth (1h)",
      "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
      "targets": [
        {
          "bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}],
          "metrics": [{"id": "1", "type": "count"}],
          "query": "rule.id:(>=5710 AND <=5763)",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": "OpenSearch"
    }
  ]
}

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    content = f.read()

import re
content = re.sub(r'EXECUTIVE_DASHBOARD = \{.*?\n\}\n', f"EXECUTIVE_DASHBOARD = {json.dumps(EXECUTIVE_DASHBOARD, indent=2)}\n", content, flags=re.DOTALL)
content = re.sub(r'OPERATIONAL_DASHBOARD = \{.*?\n\}\n', f"OPERATIONAL_DASHBOARD = {json.dumps(OPERATIONAL_DASHBOARD, indent=2)}\n", content, flags=re.DOTALL)

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(content)

print("grafana_assets updated.")
