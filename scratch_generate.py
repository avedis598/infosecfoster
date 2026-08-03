import json
import sys
sys.path.insert(0, ".")
from aml_siem.steps.grafana_assets import UNIFIED_DASHBOARD_JSON

original = json.loads(UNIFIED_DASHBOARD_JSON)

def make_sidebar(active):
    ov_style = "font-weight: bold; color: #fff;" if active == "overview" else "color: #999;"
    al_style = "font-weight: bold; color: #fff;" if active == "alerts" else "color: #999;"
    content = f"""<div style="padding: 15px; height: 100%; border-right: 1px solid #333; background: #181b1f;">
<h3 style="color: #4a90e2;">SIEM Menu</h3>
<br/>
<a href="/d/overview" style="text-decoration: none; font-size: 16px; {ov_style}">🏠 Overview</a> <br/><br/>
<a href="/d/alerts" style="text-decoration: none; font-size: 16px; {al_style}">🚨 Alerts</a>
</div>"""
    return {
        "type": "text",
        "title": "",
        "gridPos": {"h": 22, "w": 3, "x": 0, "y": 0},
        "options": {
            "content": content,
            "mode": "html"
        },
        "transparent": True
    }

# 1. OVERVIEW DASHBOARD
overview = json.loads(json.dumps(original))
overview["uid"] = "overview"
overview["title"] = "SIEM Overview"
sidebar_ov = make_sidebar("overview")

for p in overview["panels"]:
    if "gridPos" in p:
        old_w = p["gridPos"]["w"]
        old_x = p["gridPos"]["x"]
        if p["type"] == "row":
            p["gridPos"]["w"] = 21
            p["gridPos"]["x"] = 3
        else:
            # simple shift by 3, and reduce width to fit in 21
            if old_w == 6: new_w = 5
            elif old_w == 4: new_w = 4
            elif old_w == 14: new_w = 12
            elif old_w == 24: new_w = 21
            else: new_w = max(1, int(old_w * (21/24)))
            
            if old_w == 6:
                if old_x == 0: new_x = 3
                elif old_x == 6: new_x = 8
                elif old_x == 12: new_x = 13
                elif old_x == 18: new_x = 18
            elif old_w == 4:
                if old_x == 0: new_x = 3
                elif old_x == 4: new_x = 7
                elif old_x == 8: new_x = 11
                elif old_x == 12: new_x = 15
                elif old_x == 16: new_x = 19
            elif old_w == 14:
                if old_x == 10: new_x = 12
            else:
                new_x = 3 + int(old_x * (21/24))
            
            p["gridPos"]["w"] = new_w
            p["gridPos"]["x"] = new_x
            if p["gridPos"]["x"] + p["gridPos"]["w"] > 24:
                p["gridPos"]["w"] = 24 - p["gridPos"]["x"]
            
overview["panels"].insert(0, sidebar_ov)

# 2. ALERTS DASHBOARD
alerts = json.loads(json.dumps(original))
alerts["uid"] = "alerts"
alerts["title"] = "SIEM Alerts"
sidebar_al = make_sidebar("alerts")

alerts["panels"] = [
    sidebar_al,
    {
        "type": "logs",
        "title": "Wazuh Alerts Stream",
        "gridPos": {"h": 22, "w": 21, "x": 3, "y": 0},
        "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"},
        "targets": [
            {
                "query": "rule.level:>=5",
                "refId": "A",
                "timeField": "timestamp",
                "metrics": [{"type": "logs", "id": "1"}]
            }
        ],
        "options": {
            "showLabels": False,
            "showTime": True,
            "wrapLogMessage": True,
            "sortOrder": "Descending"
        }
    }
]

with open("dash_overview.json", "w") as f:
    json.dump(overview, f)
with open("dash_alerts.json", "w") as f:
    json.dump(alerts, f)
