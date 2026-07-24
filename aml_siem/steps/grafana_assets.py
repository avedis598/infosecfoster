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
