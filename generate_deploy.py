import sys
from aml_siem.steps.grafana_assets import UNIFIED_DASHBOARD_JSON, TELEMETRY_AGGREGATOR_SCRIPT

yaml = f'''apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards-json
  namespace: aml-lab
data:
  unified-dashboard.json: |
{chr(10).join('    ' + line for line in UNIFIED_DASHBOARD_JSON.splitlines())}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: telemetry-aggregator-script
  namespace: aml-lab
data:
  telemetry_aggregator.py: |
{chr(10).join('    ' + line for line in TELEMETRY_AGGREGATOR_SCRIPT.splitlines())}
'''
print(yaml)
