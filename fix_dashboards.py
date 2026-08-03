import json

with open("dash.json") as f:
    dash = json.load(f)

# Filter out the sidebar and rows
panels = []
for p in dash.get("panels", []):
    if p.get("type") == "text" and p.get("gridPos", {}).get("w") == 3 and p.get("gridPos", {}).get("x") == 0:
        continue # skip old sidebar
    if p.get("type") == "row":
        continue # skip rows, they break vertical sidebars
    panels.append(p)

# Sort panels by their current y, then x
panels.sort(key=lambda p: (p["gridPos"]["y"], p["gridPos"]["x"]))

def make_sidebar(active):
    ov_style = "font-weight: bold; color: #4a90e2;" if active == "overview" else "color: #999;"
    al_style = "font-weight: bold; color: #4a90e2;" if active == "alerts" else "color: #999;"
    content = f"""<div style="padding: 15px; height: 100%; border-right: 1px solid #333; background: #181b1f;">
<h3 style="color: #fff; margin-top: 0;">SIEM Navigation</h3>
<hr style="border-color: #333; margin-bottom: 20px;"/>
<a href="/d/unified" style="text-decoration: none; font-size: 16px; display: block; margin-bottom: 15px; {ov_style}">🏠 Overview</a>
<a href="/d/alerts" style="text-decoration: none; font-size: 16px; display: block; margin-bottom: 15px; {al_style}">🚨 Alerts</a>
</div>"""
    return {
        "type": "text",
        "title": "",
        "gridPos": {"h": 40, "w": 4, "x": 0, "y": 0}, # using w=4 for a slightly wider sidebar
        "options": {
            "content": content,
            "mode": "html"
        },
        "transparent": True
    }

# 1. OVERVIEW DASHBOARD
overview = json.loads(json.dumps(dash))
overview["uid"] = "unified"
overview["title"] = "Unified SIEM Dashboard"

# Let's repack the panels into w=20 (since sidebar is w=4)
# We will just sequentially place them.
# Executive View (4 stats): each w=5 (4*5 = 20)
# Wazuh Agents (5 stats): each w=4 (5*4 = 20)
# OpenSearch Alerts (4 stats): each w=5 (4*5 = 20)
# TheHive (Open cases w=4, Pie w=6, Recent w=10) total 20

y_offset = 0
x_offset = 4

for p in panels:
    # Resize width slightly to fit 20 columns
    old_w = p["gridPos"]["w"]
    if old_w == 6: p["gridPos"]["w"] = 5
    elif old_w == 4: p["gridPos"]["w"] = 4
    elif old_w == 12 or old_w == 14: p["gridPos"]["w"] = 10
    elif old_w == 5: p["gridPos"]["w"] = 5
    elif old_w == 10: p["gridPos"]["w"] = 10
    else: p["gridPos"]["w"] = max(1, int(old_w * (20/24)))
    
    if p["title"] == "Open Cases by Severity": p["gridPos"]["w"] = 6
    if p["title"] == "Recent Cases": p["gridPos"]["w"] = 10
    
    w = p["gridPos"]["w"]
    h = p["gridPos"]["h"]
    
    if x_offset + w > 24:
        x_offset = 4
        y_offset += 6 # safe jump for next row, Grafana will pull them up if there's space
        
    p["gridPos"]["x"] = x_offset
    p["gridPos"]["y"] = y_offset
    x_offset += w

overview["panels"] = [make_sidebar("overview")] + panels

# 2. ALERTS DASHBOARD
alerts = json.loads(json.dumps(dash))
alerts["uid"] = "alerts"
alerts["title"] = "SIEM Alerts"

alerts["panels"] = [
    make_sidebar("alerts"),
    {
        "type": "logs",
        "title": "Wazuh Alerts Stream",
        "gridPos": {"h": 40, "w": 20, "x": 4, "y": 0},
        "datasource": {"type": "grafana-opensearch-datasource", "uid": "OpenSearch"},
        "targets": [
            {
                "query": "rule.level:>=5",
                "refId": "A",
                "timeField": "timestamp",
                "metrics": [{"type": "logs", "id": "1"}],
                "bucketAggs": [
                    {
                        "id": "2",
                        "type": "date_histogram",
                        "settings": {
                            "interval": "auto",
                            "min_doc_count": 0
                        }
                    }
                ]
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
