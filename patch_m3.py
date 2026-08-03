import re

with open("aml_siem/steps/m3_intelligence.py", "r") as f:
    content = f.read()

# Add import at the top
if "from .grafana_assets" not in content:
    content = content.replace("M3_STEPS = [", "from .grafana_assets import DASHBOARDS_YAML, TELEMETRY_AGGREGATOR_SCRIPT, EXECUTIVE_DASHBOARD_JSON, OPERATIONAL_DASHBOARD_JSON\n\nM3_STEPS = [")

pattern = r'(\s*"id": "3\.M3\.3".*?"cmds": \[)(.*?)(^\s*\}\,\n\s*\{\n\s*"id": "3\.GATE_M33")'

replacement = r'''\1
            {
                "label": "Deploy Grafana Data Sources ConfigMap",
                "cmd": """KUBECONFIG=~/.kube/config kubectl apply -f - <<'INNER'
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: aml-lab
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
    - name: OpenSearch
      type: grafana-opensearch-datasource
      url: http://opensearch.aml-lab.svc.cluster.local:9200
      access: proxy
      jsonData:
        database: "[wazuh-alerts-4.x-]YYYY.MM.DD"
        timeField: "timestamp"
        version: "OpenSearch"
INNER
"""
            },
            {
                "label": "Deploy Grafana Dashboards ConfigMaps",
                "cmd": f"""KUBECONFIG=~/.kube/config kubectl apply -f - <<'INNER'
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards-provider
  namespace: aml-lab
data:
  dashboards.yaml: |
{chr(10).join('    ' + line for line in DASHBOARDS_YAML.splitlines())}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards-json
  namespace: aml-lab
data:
  executive-dashboard.json: |
{chr(10).join('    ' + line for line in EXECUTIVE_DASHBOARD_JSON.splitlines())}
  operational-dashboard.json: |
{chr(10).join('    ' + line for line in OPERATIONAL_DASHBOARD_JSON.splitlines())}
INNER
"""
            },
            {
                "label": "Deploy SIEM Telemetry Aggregator",
                "cmd": f"""KUBECONFIG=~/.kube/config kubectl apply -f - <<'INNER'
apiVersion: v1
kind: ConfigMap
metadata:
  name: telemetry-aggregator-script
  namespace: aml-lab
data:
  telemetry_aggregator.py: |
{chr(10).join('    ' + line for line in TELEMETRY_AGGREGATOR_SCRIPT.splitlines())}
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: siem-telemetry-cronjob
  namespace: aml-lab
spec:
  schedule: "*/5 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: aggregator
            image: python:3.9-slim
            command: ["python", "/scripts/telemetry_aggregator.py"]
            volumeMounts:
            - name: script-vol
              mountPath: /scripts
          volumes:
          - name: script-vol
            configMap:
              name: telemetry-aggregator-script
          restartPolicy: OnFailure
INNER
"""
            },
            {
                "label": "Deploy Grafana",
                "cmd": """KUBECONFIG=~/.kube/config kubectl apply -f - <<'INNER'
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: aml-lab
spec:
  type: LoadBalancer
  ports:
  - port: 3000
    targetPort: 3000
  selector:
    app: grafana
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.3.3
        ports:
        - containerPort: 3000
        env:
        - name: GF_INSTALL_PLUGINS
          value: grafana-opensearch-datasource,grafana-clickhouse-datasource,marcusolsson-json-datasource
        - name: GF_AUTH_ANONYMOUS_ENABLED
          value: "true"
        - name: GF_AUTH_ANONYMOUS_ORG_ROLE
          value: Admin
        volumeMounts:
        - name: grafana-datasources
          mountPath: /etc/grafana/provisioning/datasources/datasources.yaml
          subPath: datasources.yaml
        - name: grafana-dashboards-provider
          mountPath: /etc/grafana/provisioning/dashboards/dashboards.yaml
          subPath: dashboards.yaml
        - name: grafana-dashboards-json
          mountPath: /var/lib/grafana/dashboards
      volumes:
      - name: grafana-datasources
        configMap:
          name: grafana-datasources
      - name: grafana-dashboards-provider
        configMap:
          name: grafana-dashboards-provider
      - name: grafana-dashboards-json
        configMap:
          name: grafana-dashboards-json
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: aml-lab
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - grafana.aml-lab.infosecfoster.com
    - grafana.aml-lab.amlsiem.com
    secretName: grafana-tls
  rules:
  - host: grafana.aml-lab.infosecfoster.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
  - host: grafana.aml-lab.amlsiem.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
INNER
"""
            }
        ]\3'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.MULTILINE)

with open("aml_siem/steps/m3_intelligence.py", "w") as f:
    f.write(new_content)

print("Patched!")
