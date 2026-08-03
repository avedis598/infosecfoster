import json
import re
import sys
sys.path.insert(0, ".")
from aml_siem.steps.grafana_assets import UNIFIED_DASHBOARD_JSON

dash = json.loads(UNIFIED_DASHBOARD_JSON)

sidebar = {
    "type": "text",
    "title": "",
    "gridPos": {"h": 22, "w": 3, "x": 0, "y": 0},
    "options": {
        "content": "<div style=\"padding: 10px; height: 100%; border-right: 1px solid #333;\">\n\n### Menu\n\n<br/>\n\n[🏠 Overview](#) <br/><br/>\n[🚨 Alerts](#) \n\n</div>",
        "mode": "html"
    },
    "transparent": True
}

for p in dash["panels"]:
    if "gridPos" in p:
        old_w = p["gridPos"]["w"]
        old_x = p["gridPos"]["x"]
        
        if p["type"] == "row":
            new_w = 21
            new_x = 3
        else:
            new_w = int(old_w * (21/24))
            if new_w < 1: new_w = 1
            if old_w == 6: new_w = 5
            elif old_w == 14: new_w = 12
            elif old_w == 4: new_w = 4
            
            new_x = 3 + int(old_x * (21/24))
            if old_w == 6 and old_x == 6: new_x = 8
            if old_w == 6 and old_x == 12: new_x = 13
            if old_w == 6 and old_x == 18: new_x = 18
            if old_w == 4 and old_x == 4: new_x = 7
            if old_w == 4 and old_x == 8: new_x = 11
            if old_w == 4 and old_x == 12: new_x = 15
            if old_w == 4 and old_x == 16: new_x = 19
            if old_w == 14 and old_x == 10: new_x = 12
            
            p["gridPos"]["w"] = new_w
            p["gridPos"]["x"] = new_x
            if p["gridPos"]["x"] + p["gridPos"]["w"] > 24:
                p["gridPos"]["w"] = 24 - p["gridPos"]["x"]

# Check if sidebar already exists
has_sidebar = any(p.get("type") == "text" and p.get("gridPos", {}).get("w") == 3 for p in dash["panels"])
if not has_sidebar:
    dash["panels"].insert(0, sidebar)

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    content = f.read()

new_json_str = json.dumps(dash).replace('\\\\', '\\\\\\\\').replace('"', '\\"')

parts = content.split('UNIFIED_DASHBOARD_JSON = "')
new_content = parts[0] + 'UNIFIED_DASHBOARD_JSON = "' + new_json_str + '"\n'

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(new_content)

with open("dash.json", "w") as f:
    json.dump(dash, f)
