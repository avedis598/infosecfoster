import re

with open("aml_siem/steps/m3_intelligence.py", "r") as f:
    content = f.read()

# 1. Update GF_INSTALL_PLUGINS
content = content.replace(
    'value: grafana-opensearch-datasource,grafana-clickhouse-datasource,marcusolsson-json-datasource',
    'value: grafana-opensearch-datasource,grafana-clickhouse-datasource,marcusolsson-json-datasource,yesoreyeram-infinity-datasource'
)

# 2. Inject THEHIVE_API_KEY environment variable
env_var_to_inject = """        - name: GF_AUTH_ANONYMOUS_ORG_ROLE
          value: Admin
        - name: THEHIVE_API_KEY
          valueFrom:
            secretKeyRef:
              name: thehive-api-key
              key: api-key"""
content = content.replace(
    '        - name: GF_AUTH_ANONYMOUS_ORG_ROLE\n          value: Admin',
    env_var_to_inject
)

# 3. Update grafana-datasources ConfigMap
datasource_to_inject = """    - name: SIEM-Telemetry
      uid: SIEM-Telemetry
      type: grafana-opensearch-datasource
      url: http://opensearch.aml-lab.svc.cluster.local:9200
      access: proxy
      jsonData:
        database: "siem-telemetry"
        timeField: "timestamp"
        version: "2.13.0"
    - name: TheHive
      uid: TheHive
      type: yesoreyeram-infinity-datasource
      url: http://thehive.aml-lab.svc.cluster.local:9000/api/v1
      access: proxy
      secureJsonData:
        httpHeaderValue1: "Bearer ${THEHIVE_API_KEY}"
      jsonData:
        httpHeaderName1: "Authorization"
        global_queries: []"""
content = content.replace(
    """    - name: SIEM-Telemetry
      uid: SIEM-Telemetry
      type: grafana-opensearch-datasource
      url: http://opensearch.aml-lab.svc.cluster.local:9200
      access: proxy
      jsonData:
        database: "siem-telemetry"
        timeField: "timestamp"
        version: "2.13.0\"""",
    datasource_to_inject
)

with open("aml_siem/steps/m3_intelligence.py", "w") as f:
    f.write(content)
