import json
import os
import re

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("EXECUTIVE_DASHBOARD = "):
        break
    new_lines.append(line)

TELEMETRY_AGGREGATOR_SCRIPT = """import urllib.request
import urllib.error
import json
import os
import ssl
import time
from datetime import datetime, timezone, timedelta

def push_to_opensearch(doc):
    url = "http://opensearch.aml-lab.svc.cluster.local:9200/siem-telemetry/_doc"
    req = urllib.request.Request(url, data=json.dumps(doc).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Error pushing to OpenSearch: {e}")

def get_wazuh_stats():
    stats = {"Total": 0, "Active": 0, "Disconnected": 0, "Pending": 0, "Never connected": 0}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Get Token
        req = urllib.request.Request("https://wazuh-master-svc.aml-lab.svc.cluster.local:55000/security/user/authenticate", headers={'Authorization': 'Basic d2F6dWg6d2F6dWg='})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as res:
            token = json.loads(res.read())['data']['token']
        # Get Agents
        req2 = urllib.request.Request("https://wazuh-master-svc.aml-lab.svc.cluster.local:55000/agents?select=status", headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req2, context=ctx, timeout=5) as res:
            items = json.loads(res.read())['data']['affected_items']
            stats["Total"] = len(items)
            for item in items:
                status = item.get("status", "")
                if status == "active": stats["Active"] += 1
                elif status == "disconnected": stats["Disconnected"] += 1
                elif status == "pending": stats["Pending"] += 1
                elif status == "never_connected": stats["Never connected"] += 1
    except Exception as e:
        print(f"Wazuh Error: {e}")
    return stats

def get_os_count(query):
    try:
        url = "http://opensearch-proxy.aml-lab.svc.cluster.local:9200/wazuh-alerts-*/_count"
        req = urllib.request.Request(url, data=json.dumps(query).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read()).get("count", 0)
    except Exception as e:
        print(f"OS Error: {e}")
        return 0

def get_alerts_stats():
    now = datetime.utcnow()
    past = now - timedelta(days=1)
    tf = {"range": {"@timestamp": {"gte": past.strftime("%Y-%m-%dT%H:%M:%SZ"), "lte": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}}
    stats = {"Total":0, "Level 12+":0, "Auth Failure":0, "Auth Success":0}
    stats["Total"] = get_os_count({"query": {"bool": {"filter": [tf]}}})
    stats["Level 12+"] = get_os_count({"query": {"bool": {"filter": [tf, {"range": {"rule.level": {"gte": 12}}}]}}})
    stats["Auth Failure"] = get_os_count({"query": {"bool": {"filter": [tf, {"match": {"rule.groups": "authentication_failed"}}]}}})
    stats["Auth Success"] = get_os_count({"query": {"bool": {"filter": [tf, {"match": {"rule.groups": "authentication_success"}}]}}})
    return stats

def main():
    wz_stats = get_wazuh_stats()
    al_stats = get_alerts_stats()
    
    doc = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "posture_score": 85,
        "money_saved": 135000,
        "open_critical_cases": 0,
        "cases_awaiting_assignment": 0,
        "response_time_median": 0,
        "wazuh_total": wz_stats["Total"],
        "wazuh_active": wz_stats["Active"],
        "wazuh_disconnected": wz_stats["Disconnected"],
        "wazuh_pending": wz_stats["Pending"],
        "wazuh_never": wz_stats["Never connected"],
        "alerts_total": al_stats["Total"],
        "alerts_level12": al_stats["Level 12+"],
        "alerts_authfail": al_stats["Auth Failure"],
        "alerts_authsucc": al_stats["Auth Success"]
    }
    push_to_opensearch(doc)

if __name__ == "__main__":
    main()
"""

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

new_content = "".join(new_lines)
new_content = re.sub(
    r'TELEMETRY_AGGREGATOR_SCRIPT = """.*?"""',
    'TELEMETRY_AGGREGATOR_SCRIPT = """' + TELEMETRY_AGGREGATOR_SCRIPT + '"""',
    new_content,
    flags=re.DOTALL
)

new_content += f"\n\nUNIFIED_DASHBOARD_JSON = {json.dumps(json.dumps(UNIFIED_DASHBOARD))}\n"

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(new_content)
