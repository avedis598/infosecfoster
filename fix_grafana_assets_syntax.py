import json
import re

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    content = f.read()

# Grab the whole file content up to UNIFIED_DASHBOARD_JSON
content_before = content.split("UNIFIED_DASHBOARD_JSON =")[0]

dashboard = {
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
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_total"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Active",
      "gridPos": {"h": 4, "w": 4, "x": 4, "y": 6},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_active"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Disconnected",
      "gridPos": {"h": 4, "w": 4, "x": 8, "y": 6},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_disconnected"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Pending",
      "gridPos": {"h": 4, "w": 4, "x": 12, "y": 6},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_pending"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Never Connected",
      "gridPos": {"h": 4, "w": 4, "x": 16, "y": 6},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_never"}], "refId": "A", "timeField": "timestamp", "query": ""}],
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
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_total"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Level 12+",
      "gridPos": {"h": 4, "w": 6, "x": 6, "y": 11},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_level12"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Auth Failure",
      "gridPos": {"h": 4, "w": 6, "x": 12, "y": 11},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_authfail"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Auth Success",
      "gridPos": {"h": 4, "w": 6, "x": 18, "y": 11},
      "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_authsucc"}], "refId": "A", "timeField": "timestamp", "query": ""}],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "row",
      "title": "Incident Response - TheHive",
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 15}
    },
    {
      "type": "stat",
      "title": "Open Cases",
      "gridPos": {"h": 6, "w": 4, "x": 0, "y": 16},
      "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"},
      "targets": [
        {
          "type": "json",
          "url": "/query?range=all",
          "global_query_id": "",
          "refId": "A",
          "format": "table",
          "source": "url",
          "url_options": {
            "method": "POST",
            "data": json.dumps({"query": [{"_name": "listCase"}, {"_name": "filter", "_field": "status", "_value": "Open"}]})
          },
          "root_selector": "",
          "columns": []
        }
      ],
      "transformations": [
        {
          "id": "reduce",
          "options": {
            "reducers": ["count"]
          }
        }
      ]
    },
    {
      "type": "piechart",
      "title": "Open Cases by Severity",
      "gridPos": {"h": 6, "w": 6, "x": 4, "y": 16},
      "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"},
      "targets": [
        {
          "type": "json",
          "url": "/query?range=all",
          "refId": "A",
          "format": "table",
          "source": "url",
          "url_options": {
            "method": "POST",
            "data": json.dumps({"query": [{"_name": "listCase"}, {"_name": "filter", "_field": "status", "_value": "Open"}]})
          },
          "root_selector": "",
          "columns": [
            {"selector": "severity", "text": "severity", "type": "number"}
          ]
        }
      ],
      "transformations": [
        {
          "id": "groupingToMatrix",
          "options": {
            "columnField": "severity",
            "rowField": "severity",
            "valueField": "severity"
          }
        }
      ]
    },
    {
      "type": "table",
      "title": "Recent Cases",
      "gridPos": {"h": 6, "w": 14, "x": 10, "y": 16},
      "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"},
      "targets": [
        {
          "type": "json",
          "url": "/query?range=all",
          "refId": "A",
          "format": "table",
          "source": "url",
          "url_options": {
            "method": "POST",
            "data": json.dumps({"query": [{"_name": "listCase"}, {"_name": "sort", "_fields": [{"_createdAt": "desc"}]}, {"_name": "page", "from": 0, "to": 20}]})
          },
          "root_selector": "",
          "columns": [
            {"selector": "caseId", "text": "ID", "type": "number"},
            {"selector": "title", "text": "Title", "type": "string"},
            {"selector": "severity", "text": "Severity", "type": "number"},
            {"selector": "status", "text": "Status", "type": "string"},
            {"selector": "assignee", "text": "Assignee", "type": "string"},
            {"selector": "_createdAt", "text": "Created", "type": "timestamp"}
          ]
        }
      ]
    }
  ]
}

# Dump to a single line JSON string for m3_intelligence.py
single_line_json = json.dumps(dashboard)
# We must enclose it in triple quotes to avoid quoting issues, OR encode it properly.
# The safest way is to use a python raw literal or triple quoted string
escaped_json = json.dumps(single_line_json) # this gives a valid python string literal

final_content = content_before + "UNIFIED_DASHBOARD_JSON = " + escaped_json + "\n"

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(final_content)
