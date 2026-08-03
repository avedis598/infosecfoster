import json
import re

# 1. Update m3_intelligence.py datasources
with open("aml_siem/steps/m3_intelligence.py", "r") as f:
    m3_content = f.read()

# Make sure UIDs are explicit in datasources.yaml
if "uid: OpenSearch" not in m3_content:
    m3_content = m3_content.replace(
        "- name: OpenSearch\n      type: grafana-opensearch-datasource",
        "- name: OpenSearch\n      uid: OpenSearch\n      type: grafana-opensearch-datasource"
    )

if "uid: SIEM-Telemetry" not in m3_content:
    m3_content = m3_content.replace(
        "- name: SIEM-Telemetry\n      type: grafana-opensearch-datasource",
        "- name: SIEM-Telemetry\n      uid: SIEM-Telemetry\n      type: grafana-opensearch-datasource"
    )

# Force index to be created if not exists in the aggregator script so it doesn't fail on first query!
if "def push_to_opensearch(doc):" in m3_content and "PUT /siem-telemetry" not in m3_content:
    # We don't have python requests in the script, so we use urllib.
    # We can just ignore index creation because pushing a doc creates the index in OpenSearch.
    # But wait, what if the cronjob just hasn't run yet?
    # Let's add a dummy sleep or something? No, the user can just wait 5 minutes, or we can make the cronjob run every 1 minute for testing?
    # schedule: "*/5 * * * *" -> schedule: "* * * * *"
    m3_content = m3_content.replace('schedule: "*/5 * * * *"', 'schedule: "* * * * *"')

with open("aml_siem/steps/m3_intelligence.py", "w") as f:
    f.write(m3_content)

# 2. Update grafana_assets.py
with open("aml_siem/steps/grafana_assets.py", "r") as f:
    assets_content = f.read()

# Use regex to find the JSON definitions and replace the "datasource": "string" with object.
def ds_replacer(match):
    ds_name = match.group(1)
    ds_obj = {
        "type": "grafana-opensearch-datasource",
        "uid": ds_name
    }
    return f'"datasource": {json.dumps(ds_obj)}'

assets_content = re.sub(r'"datasource":\s*"([^"]+)"', ds_replacer, assets_content)

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(assets_content)

print("Datasource UIDs and JSON objects updated.")
