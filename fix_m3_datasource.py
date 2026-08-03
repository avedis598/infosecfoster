import re

with open("aml_siem/steps/m3_intelligence.py", "r") as f:
    content = f.read()

# Check if SIEM-Telemetry is already there
if "name: SIEM-Telemetry" not in content:
    replacement = """    - name: SIEM-Telemetry
      type: grafana-opensearch-datasource
      url: http://opensearch.aml-lab.svc.cluster.local:9200
      access: proxy
      jsonData:
        database: "siem-telemetry"
        timeField: "timestamp"
        version: "OpenSearch"
INNER"""
    content = content.replace("INNER", replacement, 1)

with open("aml_siem/steps/m3_intelligence.py", "w") as f:
    f.write(content)

print("m3_intelligence.py updated.")
