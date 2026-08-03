import json

DASHBOARDS_YAML = """apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
"""

TELEMETRY_AGGREGATOR_SCRIPT = """import urllib.request
import urllib.error
import json
import base64
import os
import ssl
import time
from datetime import datetime, timezone

def push_to_opensearch(doc):
    url = "http://opensearch.aml-lab.svc.cluster.local:9200/siem-telemetry/_doc"
    req = urllib.request.Request(url, data=json.dumps(doc).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error pushing to OpenSearch: {e}")

def get_thehive_stats():
    # TheHive API
    stats = {"open_critical": 0, "awaiting_assignment": 0, "response_time_median": 0}
    try:
        # Mock logic or real logic if API key provided
        pass
    except Exception as e:
        print(f"TheHive Error: {e}")
    return stats

def get_wazuh_stats():
    # Wazuh API
    stats = {"active_agents": 0, "disconnected_agents": 0}
    try:
        pass
    except Exception as e:
        print(f"Wazuh Error: {e}")
    return stats

def main():
    th_stats = get_thehive_stats()
    wz_stats = get_wazuh_stats()
    
    # Calculate posture score
    posture_score = 85 # Mock
    money_saved = 45000 * 3 # Mock KWD
    
    doc = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "posture_score": posture_score,
        "money_saved": money_saved,
        "open_critical_cases": th_stats["open_critical"],
        "cases_awaiting_assignment": th_stats["awaiting_assignment"],
        "response_time_median": th_stats["response_time_median"],
        "active_agents": wz_stats["active_agents"],
        "disconnected_agents": wz_stats["disconnected_agents"]
    }
    push_to_opensearch(doc)

if __name__ == "__main__":
    main()
"""

# Very simplified versions of the Grafana JSON models to avoid massive files.
# In a real environment, you'd export these from Grafana.
EXECUTIVE_DASHBOARD = {
  "title": "Executive Dashboard",
  "uid": "executive",
  "schemaVersion": 38,
  "tags": [
    "client-facing"
  ],
  "timezone": "browser",
  "refresh": "5m",
  "time": {
    "from": "now-30d",
    "to": "now"
  },
  "annotations": {
    "list": []
  },
  "templating": {
    "list": []
  },
  "panels": [
    {
      "type": "stat",
      "title": "Threats Blocked This Month",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "count"
            }
          ],
          "query": "rule.level:>=10",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"}
    },
    {
      "type": "stat",
      "title": "Average Response Time",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 6,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "avg",
              "field": "response_time_median"
            }
          ],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Devices Protected",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 12,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "max",
              "field": "active_agents"
            }
          ],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Security Posture Score",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 18,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "avg",
              "field": "posture_score"
            }
          ],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    }
  ]
}

OPERATIONAL_DASHBOARD = {
  "title": "Operational Dashboard",
  "uid": "operational",
  "schemaVersion": 38,
  "tags": [
    "it-manager"
  ],
  "timezone": "browser",
  "refresh": "30s",
  "time": {
    "from": "now-24h",
    "to": "now"
  },
  "annotations": {
    "list": []
  },
  "templating": {
    "list": []
  },
  "panels": [
    {
      "type": "stat",
      "title": "Open Critical Cases",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 0,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "max",
              "field": "open_critical_cases"
            }
          ],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Cases Awaiting Assignment",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 6,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "max",
              "field": "cases_awaiting_assignment"
            }
          ],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Agents Disconnected (1h)",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 12,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "max",
              "field": "disconnected_agents"
            }
          ],
          "query": "",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}
    },
    {
      "type": "stat",
      "title": "Failed Auth (1h)",
      "gridPos": {
        "h": 4,
        "w": 6,
        "x": 18,
        "y": 0
      },
      "targets": [
        {
          "bucketAggs": [
            {
              "id": "2",
              "settings": {
                "interval": "auto"
              },
              "type": "date_histogram"
            }
          ],
          "metrics": [
            {
              "id": "1",
              "type": "count"
            }
          ],
          "query": "rule.id:(>=5710 AND <=5763)",
          "refId": "A",
          "timeField": "timestamp"
        }
      ],
      "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"}
    }
  ]
}

EXECUTIVE_DASHBOARD_JSON = json.dumps(EXECUTIVE_DASHBOARD)
OPERATIONAL_DASHBOARD_JSON = json.dumps(OPERATIONAL_DASHBOARD)

OVERVIEW_DASHBOARD_JSON = r"""{"title": "Unified SIEM Dashboard", "uid": "unified", "schemaVersion": 38, "timezone": "browser", "refresh": "30s", "time": {"from": "now-24h", "to": "now"}, "panels": [{"type": "text", "title": "", "gridPos": {"h": 40, "w": 4, "x": 0, "y": 0}, "options": {"content": "<div style=\"padding: 15px; height: 100%; border-right: 1px solid #333; background: #181b1f;\">\n<h3 style=\"color: #fff; margin-top: 0;\">SIEM Navigation</h3>\n<hr style=\"border-color: #333; margin-bottom: 20px;\"/>\n<a href=\"/d/unified\" style=\"text-decoration: none; font-size: 16px; display: block; margin-bottom: 15px; font-weight: bold; color: #4a90e2;\">\ud83c\udfe0 Overview</a>\n<a href=\"/d/alerts\" style=\"text-decoration: none; font-size: 16px; display: block; margin-bottom: 15px; color: #999;\">\ud83d\udea8 Alerts</a>\n</div>", "mode": "html"}, "transparent": true}, {"type": "stat", "title": "Threats Blocked This Month", "gridPos": {"h": 4, "w": 5, "x": 4, "y": 0}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "count"}], "query": "rule.level:>=10", "refId": "A", "timeField": "timestamp"}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"}}, {"type": "stat", "title": "Average Response Time", "gridPos": {"h": 4, "w": 5, "x": 9, "y": 0}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "avg", "field": "response_time_median"}], "query": "", "refId": "A", "timeField": "timestamp"}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Devices Protected", "gridPos": {"h": 4, "w": 5, "x": 14, "y": 0}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_total"}], "query": "", "refId": "A", "timeField": "timestamp"}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Security Posture Score", "gridPos": {"h": 4, "w": 5, "x": 19, "y": 0}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "avg", "field": "posture_score"}], "query": "", "refId": "A", "timeField": "timestamp"}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Total Agents", "gridPos": {"h": 4, "w": 4, "x": 4, "y": 6}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_total"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Active", "gridPos": {"h": 4, "w": 4, "x": 8, "y": 6}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_active"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Disconnected", "gridPos": {"h": 4, "w": 4, "x": 12, "y": 6}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_disconnected"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Pending", "gridPos": {"h": 4, "w": 4, "x": 16, "y": 6}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_pending"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Never Connected", "gridPos": {"h": 4, "w": 4, "x": 20, "y": 6}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "wazuh_never"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Total Alerts", "gridPos": {"h": 4, "w": 5, "x": 4, "y": 12}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_total"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Level 12+", "gridPos": {"h": 4, "w": 5, "x": 9, "y": 12}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_level12"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Auth Failure", "gridPos": {"h": 4, "w": 5, "x": 14, "y": 12}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_authfail"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Auth Success", "gridPos": {"h": 4, "w": 5, "x": 19, "y": 12}, "targets": [{"bucketAggs": [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}], "metrics": [{"id": "1", "type": "max", "field": "alerts_authsucc"}], "refId": "A", "timeField": "timestamp", "query": ""}], "datasource": {"type": "grafana-opensearch-datasource", "uid": "SIEM-Telemetry"}}, {"type": "stat", "title": "Open Cases", "gridPos": {"h": 6, "w": 4, "x": 4, "y": 18}, "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"}, "targets": [{"type": "json", "url": "/query?range=all", "global_query_id": "", "refId": "A", "format": "table", "source": "url", "url_options": {"method": "POST", "data": "{\"query\": [{\"_name\": \"listCase\"}, {\"_name\": \"filter\", \"_field\": \"status\", \"_value\": \"Open\"}]}"}, "root_selector": "", "columns": []}], "transformations": [{"id": "reduce", "options": {"reducers": ["count"]}}]}, {"type": "piechart", "title": "Open Cases by Severity", "gridPos": {"h": 6, "w": 6, "x": 8, "y": 18}, "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"}, "targets": [{"type": "json", "url": "/query?range=all", "refId": "A", "format": "table", "source": "url", "url_options": {"method": "POST", "data": "{\"query\": [{\"_name\": \"listCase\"}, {\"_name\": \"filter\", \"_field\": \"status\", \"_value\": \"Open\"}]}"}, "root_selector": "", "columns": [{"selector": "severity", "text": "severity", "type": "number"}]}], "transformations": [{"id": "groupingToMatrix", "options": {"columnField": "severity", "rowField": "severity", "valueField": "severity"}}]}, {"type": "table", "title": "Recent Cases", "gridPos": {"h": 6, "w": 10, "x": 14, "y": 18}, "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"}, "targets": [{"type": "json", "url": "/query?range=all", "refId": "A", "format": "table", "source": "url", "url_options": {"method": "POST", "data": "{\"query\": [{\"_name\": \"listCase\"}, {\"_name\": \"sort\", \"_fields\": [{\"_createdAt\": \"desc\"}]}, {\"_name\": \"page\", \"from\": 0, \"to\": 20}]}"}, "root_selector": "", "columns": [{"selector": "caseId", "text": "ID", "type": "number"}, {"selector": "title", "text": "Title", "type": "string"}, {"selector": "severity", "text": "Severity", "type": "number"}, {"selector": "status", "text": "Status", "type": "string"}, {"selector": "assignee", "text": "Assignee", "type": "string"}, {"selector": "_createdAt", "text": "Created", "type": "timestamp"}]}]}]}"""
ALERTS_DASHBOARD_JSON = r"""{"title": "SIEM Alerts", "uid": "alerts", "schemaVersion": 38, "timezone": "browser", "refresh": "30s", "time": {"from": "now-24h", "to": "now"}, "panels": [{"type": "text", "title": "", "gridPos": {"h": 40, "w": 4, "x": 0, "y": 0}, "options": {"content": "<div style=\"padding: 15px; height: 100%; border-right: 1px solid #333; background: #181b1f;\">\n<h3 style=\"color: #fff; margin-top: 0;\">SIEM Navigation</h3>\n<hr style=\"border-color: #333; margin-bottom: 20px;\"/>\n<a href=\"/d/unified\" style=\"text-decoration: none; font-size: 16px; display: block; margin-bottom: 15px; color: #999;\">\ud83c\udfe0 Overview</a>\n<a href=\"/d/alerts\" style=\"text-decoration: none; font-size: 16px; display: block; margin-bottom: 15px; font-weight: bold; color: #4a90e2;\">\ud83d\udea8 Alerts</a>\n</div>", "mode": "html"}, "transparent": true}, {"type": "logs", "title": "Wazuh Alerts Stream", "gridPos": {"h": 40, "w": 20, "x": 4, "y": 0}, "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"}, "targets": [{"query": "rule.level:>=5", "refId": "A", "timeField": "timestamp", "metrics": [{"type": "logs", "id": "1"}], "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto", "min_doc_count": 0}}]}], "options": {"showLabels": false, "showTime": true, "wrapLogMessage": true, "sortOrder": "Descending"}}]}"""
