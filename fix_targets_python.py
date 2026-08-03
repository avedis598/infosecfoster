import sys
import json
import re

sys.path.append('.')
from aml_siem.steps.grafana_assets import UNIFIED_DASHBOARD_JSON, TELEMETRY_AGGREGATOR_SCRIPT, DASHBOARDS_YAML

dashboard = json.loads(UNIFIED_DASHBOARD_JSON)

for panel in dashboard.get("panels", []):
    if "targets" in panel:
        for target in panel["targets"]:
            if "bucketAggs" not in target:
                target["bucketAggs"] = [{"id": "2", "settings": {"interval": "auto"}, "type": "date_histogram"}]
            if "query" not in target:
                target["query"] = ""

updated_json = json.dumps(dashboard)
updated_json_string = json.dumps(updated_json)

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    content = f.read()

# Replace the variable
content = re.sub(
    r'UNIFIED_DASHBOARD_JSON = ".*?"\n',
    f'UNIFIED_DASHBOARD_JSON = {updated_json_string}\n',
    content
)

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(content)
