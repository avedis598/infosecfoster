import re
import json

UNIFIED_DASHBOARD = {
  "title": "Unified SIEM Dashboard",
  "uid": "unified",
  "schemaVersion": 38,
  "timezone": "browser",
  "refresh": "30s",
  "time": {
    "from": "now-24h",
    "to": "now"
  },
  "panels": [
    {
      "type": "row",
      "title": "Executive View",
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0}
    },
    {
      "type": "stat",
      "title": "Threats Blocked This Month",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 1},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "count"}], "query": "rule.level:>=10", "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"}
    },
    {
      "type": "stat",
      "title": "Average Response Time",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 1},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "avg", "field": "response_time_median"}], "query": "", "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Devices Protected",
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 1},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_total"}], "query": "", "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Security Posture Score",
      "gridPos": {"h": 4, "w": 6, "x": 18, "y": 1},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "avg", "field": "posture_score"}], "query": "", "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    
    {
      "type": "row",
      "title": "Operational View - Wazuh Agents",
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 5}
    },
    {
      "type": "stat",
      "title": "Total Agents",
      "gridPos": {"h": 4, "w": 4, "x": 0, "y": 6},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "wazuh_total"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Active",
      "gridPos": {"h": 4, "w": 4, "x": 4, "y": 6},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "wazuh_active"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Disconnected",
      "gridPos": {"h": 4, "w": 4, "x": 8, "y": 6},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "wazuh_disconnected"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Pending",
      "gridPos": {"h": 4, "w": 4, "x": 12, "y": 6},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "wazuh_pending"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Never Connected",
      "gridPos": {"h": 4, "w": 4, "x": 16, "y": 6},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "wazuh_never"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    
    {
      "type": "row",
      "title": "Operational View - OpenSearch Alerts",
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 10}
    },
    {
      "type": "stat",
      "title": "Total Alerts",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 11},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "alerts_total"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Level 12+",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 11},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "alerts_level12"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Auth Failure",
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 11},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "alerts_authfail"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Auth Success",
      "gridPos": {"h": 4, "w": 6, "x": 18, "y": 11},
      "targets": [{"metrics": [{"id": "1", "type": "max", "field": "alerts_authsucc"}], "refId": "A", "timeField": "timestamp"}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    }
  ]
}

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    content = f.read()

# Replace EXECUTIVE_DASHBOARD and OPERATIONAL_DASHBOARD vars with UNIFIED_DASHBOARD
content = re.sub(r'EXECUTIVE_DASHBOARD = \{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'EXECUTIVE_DASHBOARD_JSON = json\.dumps\(EXECUTIVE_DASHBOARD\)', '', content)
content = re.sub(r'OPERATIONAL_DASHBOARD = \{.*?\}', '', content, flags=re.DOTALL)
content = re.sub(r'OPERATIONAL_DASHBOARD_JSON = json\.dumps\(OPERATIONAL_DASHBOARD\)', '', content)

content += f"\n\nUNIFIED_DASHBOARD = {json.dumps(UNIFIED_DASHBOARD, indent=2)}\n"
content += "UNIFIED_DASHBOARD_JSON = json.dumps(UNIFIED_DASHBOARD)\n"

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(content)
