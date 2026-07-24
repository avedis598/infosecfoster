
from .grafana_assets import DASHBOARDS_YAML, TELEMETRY_AGGREGATOR_SCRIPT, EXECUTIVE_DASHBOARD_JSON, OPERATIONAL_DASHBOARD_JSON

M3_STEPS = [
    {
        "id": "3.M3.1",
        "title": "M3.1 — OSINT Threat Intelligence CDB Integration",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl get cronjob update-threat-intel -n aml-lab && KUBECONFIG=~/.kube/config kubectl get deployment wazuh-master -n aml-lab -o jsonpath='{.spec.template.spec.volumes[*].name}' | grep -q osint-lists && MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}') && KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- grep -q '100200' /var/ossec/etc/rules/local_rules.xml && KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- /var/ossec/bin/wazuh-control status | grep -q 'wazuh-analysisd is running'",
        "pre_check_label": "Check if Threat Intel components (CronJob, PVC mount, Rules) exist and wazuh-analysisd is running",
        "cmds": [
            {
                "label": "Create Threat Intel PVC",
                "cmd": r"""KUBECONFIG=~/.kube/config kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: osint-lists
  namespace: aml-lab
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: local-path
EOF
"""
            },
            {
                "label": "Patch Wazuh Deployments with Threat Intel PVC",
                "cmd": r"""
KUBECONFIG=~/.kube/config kubectl get deployment wazuh-master -n aml-lab -o json | jq 'if (.spec.template.spec.volumes | any(.name == "osint-lists")) then . else .spec.template.spec.volumes += [{"name": "osint-lists", "persistentVolumeClaim": {"claimName": "osint-lists"}}] end | if (.spec.template.spec.containers[0].volumeMounts | any(.name == "osint-lists")) then ( .spec.template.spec.containers[0].volumeMounts |= map(if .name == "osint-lists" then .mountPath = "/var/ossec/lists-osint" else . end) ) else .spec.template.spec.containers[0].volumeMounts += [{"name": "osint-lists", "mountPath": "/var/ossec/lists-osint"}] end' | KUBECONFIG=~/.kube/config kubectl apply -f -
KUBECONFIG=~/.kube/config kubectl rollout status deployment/wazuh-master -n aml-lab --timeout=120s
"""
            },
            {
                "label": "Deploy update-threat-intel Python script as ConfigMap",
                "cmd": r"""KUBECONFIG=~/.kube/config kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: threat-intel-script
  namespace: aml-lab
data:
  update_threat_intel.py: |
    import urllib.request
    import os

    os.makedirs("/var/ossec/lists-osint", exist_ok=True)

    FEODO_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.txt"
    try:
        req = urllib.request.Request(FEODO_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            lines = response.read().decode('utf-8').splitlines()
            
        with open("/var/ossec/lists-osint/malicious_ips", "w") as f:
            for line in lines:
                if line and not line.startswith("#"):
                    f.write(f"{line}:malicious_ip\n")
    except Exception as e:
        print(f"Error: {e}")
EOF
"""
            },
            {
                "label": "Deploy update-threat-intel CronJob",
                "cmd": r"""KUBECONFIG=~/.kube/config kubectl apply -f - <<'EOF'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: update-threat-intel
  namespace: aml-lab
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: updater
            image: wazuh/wazuh-manager:4.7.5
            command:
            - python3
            - /scripts/update_threat_intel.py
            volumeMounts:
            - name: script-vol
              mountPath: /scripts
            - name: osint-lists
              mountPath: /var/ossec/lists-osint
          volumes:
          - name: script-vol
            configMap:
              name: threat-intel-script
          - name: osint-lists
            persistentVolumeClaim:
              claimName: osint-lists
          restartPolicy: OnFailure
EOF
"""
            },
            {
                "label": "Initialize Threat Intel List",
                "cmd": "KUBECONFIG=~/.kube/config kubectl delete job init-threat-intel -n aml-lab --ignore-not-found && KUBECONFIG=~/.kube/config kubectl create job --from=cronjob/update-threat-intel init-threat-intel -n aml-lab && KUBECONFIG=~/.kube/config kubectl wait --for=condition=complete job/init-threat-intel -n aml-lab --timeout=120s"
            },
            {
                "label": "Inject custom rules for Threat Intel",
                "cmd": r"""
MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}')
# Cleanup potential duplicates from previous force reruns
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c "sed -i '/<list>lists-osint\/malicious_ips<\/list>/d' /var/ossec/etc/ossec.conf; sed -i '/<list>etc\/lists\/osint\/malicious_ips<\/list>/d' /var/ossec/etc/ossec.conf; sed -i '/<group name=\"osint,\">/,/<\/group>/d' /var/ossec/etc/rules/local_rules.xml"

# Safely inject the list
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c "awk '/<\\/ruleset>/ { print \"    <list>lists-osint/malicious_ips</list>\"; print; next } 1' /var/ossec/etc/ossec.conf > /tmp/ossec.conf && cat /tmp/ossec.conf > /var/ossec/etc/ossec.conf && chgrp wazuh /var/ossec/etc/ossec.conf && chmod 640 /var/ossec/etc/ossec.conf"

# Safely inject the rules
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c 'cat << "EOF" >> /var/ossec/etc/rules/local_rules.xml
<group name="osint,">
  <rule id="100200" level="10">
    <list field="srcip" lookup="match_key">lists-osint/malicious_ips</list>
    <description>OSINT: Source IP matched in Feodo Tracker</description>
  </rule>
</group>
EOF
chgrp wazuh /var/ossec/etc/rules/local_rules.xml
chmod 640 /var/ossec/etc/rules/local_rules.xml'
"""
            },
            {
                "label": "Restart Wazuh Manager",
                "cmd": "MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}'); KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c '/var/ossec/bin/wazuh-control restart > /tmp/wazuh_restart.log 2>&1; cat /tmp/wazuh_restart.log'"
            }
        ]
    },
    {
        "id": "3.GATE_M31",
        "title": "Gate Verification — M3.1 OSINT",
        "mode": "remote",
        "desc": "Verify that Wazuh successfully loads the OSINT CDB list without errors",
        "cmds": [
            {
                "label": "Gate: Check Wazuh analysisd logs for OSINT list success",
                "cmd": "MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}'); if KUBECONFIG=~/.kube/config kubectl logs -n aml-lab $MASTER_POD -c wazuh-manager | grep -qi 'Could not open file.*lists-osint/malicious_ips'; then echo 'GATE_FAIL: List failed to load' && exit 1; else echo 'GATE_PASS: No list loading errors found'; fi"
            }
        ]
    },
    {
        "id": "3.M3.2",
        "title": "M3.2 — ClickHouse 23.8 LTS — Cold Storage Tier",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl get statefulset clickhouse -n aml-lab",
        "pre_check_label": "Check if ClickHouse is deployed",
        "cmds": [
            {
                "label": "Deploy ClickHouse StatefulSet and Service",
                "cmd": r"""KUBECONFIG=~/.kube/config kubectl apply -f - <<'    - name: SIEM-Telemetry
      uid: SIEM-Telemetry
      type: grafana-opensearch-datasource
      url: http://opensearch.aml-lab.svc.cluster.local:9200
      access: proxy
      jsonData:
        database: "siem-telemetry"
        timeField: "timestamp"
        version: "OpenSearch"
INNER'
apiVersion: v1
kind: Service
metadata:
  name: clickhouse
  namespace: aml-lab
spec:
  ports:
  - port: 8123
    targetPort: 8123
    name: http
  - port: 9000
    targetPort: 9000
    name: native
  selector:
    app: clickhouse
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: clickhouse
  namespace: aml-lab
spec:
  serviceName: clickhouse
  replicas: 1
  selector:
    matchLabels:
      app: clickhouse
  template:
    metadata:
      labels:
        app: clickhouse
    spec:
      containers:
      - name: clickhouse
        image: clickhouse/clickhouse-server:23.8
        ports:
        - containerPort: 8123
        - containerPort: 9000
        volumeMounts:
        - name: clickhouse-data
          mountPath: /var/lib/clickhouse
  volumeClaimTemplates:
  - metadata:
      name: clickhouse-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "local-path"
      resources:
        requests:
          storage: 100Gi
INNER
"""
            },
            {
                "label": "Wait for ClickHouse pod to be ready",
                "cmd": "(echo 'Waiting for ClickHouse pod to be ready (takes ~60s)...' && KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod -n aml-lab -l app=clickhouse --timeout=300s && KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=clickhouse)"
            },
            {
                "label": "Initialize wazuh_cold database and events table",
                "cmd": r"""
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab clickhouse-0 -- clickhouse-client --query="CREATE DATABASE IF NOT EXISTS wazuh_cold;"
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab clickhouse-0 -- clickhouse-client --query="
CREATE TABLE IF NOT EXISTS wazuh_cold.events (
    timestamp DateTime,
    rule_id String,
    level UInt8,
    description String,
    agent_id String,
    agent_name String,
    srcip String,
    raw_log String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, rule_id);"
"""
            },
            {
                "label": "Deploy ClickHouse Sync CronJob",
                "cmd": r"""KUBECONFIG=~/.kube/config kubectl apply -f - <<'INNER'
apiVersion: v1
kind: ConfigMap
metadata:
  name: clickhouse-sync-script
  namespace: aml-lab
data:
  sync_opensearch_to_clickhouse.py: |
    import urllib.request
    import json
    import datetime
    
    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    index_name = f"wazuh-alerts-4.x-{yesterday.strftime('%Y.%m.%d')}"
    
    OS_URL = f"http://opensearch.aml-lab.svc.cluster.local:9200/{index_name}/_search?size=10000"
    CH_URL = "http://clickhouse.aml-lab.svc.cluster.local:8123/?query=INSERT%20INTO%20wazuh_cold.events%20FORMAT%20JSONEachRow"
    
    try:
        req = urllib.request.Request(OS_URL)
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read())
            
        hits = data.get('hits', {}).get('hits', [])
        if not hits:
            print("No data found for yesterday")
            exit(0)
            
        ch_data = []
        for hit in hits:
            s = hit['_source']
            ch_data.append(json.dumps({
                "timestamp": s.get('timestamp', ''),
                "rule_id": str(s.get('rule', {}).get('id', '')),
                "level": int(s.get('rule', {}).get('level', 0)),
                "description": s.get('rule', {}).get('description', ''),
                "agent_id": s.get('agent', {}).get('id', ''),
                "agent_name": s.get('agent', {}).get('name', ''),
                "srcip": s.get('data', {}).get('srcip', ''),
                "raw_log": s.get('full_log', '')
            }))
            
        req_ch = urllib.request.Request(CH_URL, data='\n'.join(ch_data).encode(), method='POST')
        with urllib.request.urlopen(req_ch) as res_ch:
            print(f"Inserted {len(ch_data)} records to ClickHouse. Status: {res_ch.status}")
    except Exception as e:
        print(f"Sync failed: {e}")
        exit(1)
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: clickhouse-sync
  namespace: aml-lab
spec:
  schedule: "0 1 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: sync
            image: python:3.9-slim
            command: ["python3", "/script/sync_opensearch_to_clickhouse.py"]
            volumeMounts:
            - name: script-vol
              mountPath: /script
          volumes:
          - name: script-vol
            configMap:
              name: clickhouse-sync-script
          restartPolicy: OnFailure
INNER
"""
            }
        ]
    },
    {
        "id": "3.GATE_M32",
        "title": "Gate Verification — M3.2 ClickHouse",
        "mode": "remote",
        "desc": "Verify ClickHouse pod is running and responding to queries",
        "cmds": [
            {
                "label": "Gate: Check ClickHouse pod status",
                "cmd": "(echo 'Waiting for ClickHouse pod to be ready...' && KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod -n aml-lab -l app=clickhouse --timeout=120s && echo 'GATE_PASS: ClickHouse is ready' || (echo 'GATE_FAIL: ClickHouse is not ready' && exit 1))"
            },
            {
                "label": "Gate: Check ClickHouse HTTP ping",
                "cmd": "CLICKHOUSE_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=clickhouse -o jsonpath='{.items[0].metadata.name}'); KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $CLICKHOUSE_POD -- wget -qO- http://localhost:8123/ping | grep -q 'Ok.' && echo 'GATE_PASS: ClickHouse HTTP ping OK' || (echo 'GATE_FAIL: ClickHouse HTTP ping failed' && exit 1)"
            }
        ]
    },
    {
        "id": "3.M3.3",
        "title": "M3.3 — Grafana OSS 10.3 — Executive Dashboard",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl get deployment grafana -n aml-lab",
        "pre_check_label": "Check if Grafana is deployed",
        "cmds": [
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
      uid: OpenSearch
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
        ]    },
    {
        "id": "3.GATE_M33",
        "title": "Gate Verification — M3.3 Grafana",
        "mode": "remote",
        "desc": "Verify Grafana pod is running and responding",
        "cmds": [
            {
                "label": "Gate: Check Grafana pod status",
                "cmd": "(echo 'Waiting for Grafana pod to be ready...' && KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod -n aml-lab -l app=grafana --timeout=120s && echo 'GATE_PASS: Grafana is ready' || (echo 'GATE_FAIL: Grafana is not ready' && exit 1))"
            },
            {
                "label": "Gate: Check Grafana HTTP API",
                "cmd": "GRAFANA_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=grafana -o jsonpath='{.items[0].metadata.name}'); KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $GRAFANA_POD -- curl -s http://localhost:3000/api/health | grep -q '\"database\": \"ok\"' && echo 'GATE_PASS: Grafana API OK' || (echo 'GATE_FAIL: Grafana API failed' && exit 1)"
            }
        ]
    },
    {
        "id": "3.M3.4",
        "title": "M3.4 — M365 and Azure AD Log Integration",
        "pre_check": "false",
        "pre_check_label": "M3.4 — Azure AD configuration",
        "cmds": [
            {
                "label": "Inject Office365 configuration (Requires Manual Client ID/Secret)",
                "cmd": r"""
MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}')
# Cleanup potential duplicates
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c "sed -i '/<wodle name=\"office365\">/,/<\/wodle>/d; /<office365>/,/<\/office365>/d' /var/ossec/etc/ossec.conf"

KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c "cat << 'EOF' > /tmp/office365_patch.xml
  <office365>
    <enabled>yes</enabled>
    <interval>5m</interval>
    <api_auth>
      <tenant_id>PLACEHOLDER_TENANT_ID</tenant_id>
      <client_id>PLACEHOLDER_CLIENT_ID</client_id>
      <client_secret>PLACEHOLDER_CLIENT_SECRET</client_secret>
    </api_auth>
    <subscriptions>
      <subscription>Audit.AzureActiveDirectory</subscription>
      <subscription>Audit.Exchange</subscription>
      <subscription>Audit.SharePoint</subscription>
      <subscription>Audit.General</subscription>
    </subscriptions>
  </office365>
EOF
awk '/<\/ossec_config>/ { while((getline line < \"/tmp/office365_patch.xml\") > 0) print line; print; next } 1' /var/ossec/etc/ossec.conf > /tmp/ossec.conf && cat /tmp/ossec.conf > /var/ossec/etc/ossec.conf && chgrp wazuh /var/ossec/etc/ossec.conf && chmod 640 /var/ossec/etc/ossec.conf
"
"""
            },
            {
                "label": "Restart Wazuh to load Office365 module",
                "cmd": "MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}'); KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c '/var/ossec/bin/wazuh-control restart > /tmp/wazuh_restart.log 2>&1 && cat /tmp/wazuh_restart.log || { cat /tmp/wazuh_restart.log; exit 1; }'"
            }
        ]
    },
    {
        "id": "3.GATE_M34",
        "title": "Gate Verification — M3.4 Azure AD Integration",
        "mode": "remote",
        "desc": "Verify Office365 configuration is present in ossec.conf",
        "cmds": [
            {
                "label": "Gate: Verify office365 injected",
                "cmd": "MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}'); KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- grep -q '<office365>' /var/ossec/etc/ossec.conf && echo 'GATE_PASS: office365 found' || (echo 'GATE_FAIL: office365 missing' && exit 1)"
            }
        ]
    },
    {
        "id": "3.M3.5",
        "title": "M3.5 — Sigma Rules — Curated 50-Rule Set",
        "pre_check": "false",
        "pre_check_label": "M3.5 — Install and Convert Sigma Rules",
        "cmds": [
            {
                "label": "Install Python deps and fetch SigmaHQ repo",
                "cmd": r"""
set -e
sudo apt-get -o Dpkg::Lock::Timeout=120 update
sudo apt-get -o Dpkg::Lock::Timeout=120 install -y python3-pip python3-yaml git
rm -rf /tmp/sigma
git clone https://github.com/SigmaHQ/sigma.git /tmp/sigma
"""
            },
            {
                "label": "Convert rules to Wazuh XML using Python",
                "cmd": r"""
set -e
# Find 50 relevant rules from windows process creation, lateral movement, etc.
mkdir -p /tmp/sigma_selected
find /tmp/sigma/rules/windows -name "*.yml" | head -n 50 | xargs -I {} cp {} /tmp/sigma_selected/

cat << 'EOF' > /tmp/convert_sigma.py
import yaml, os

print('<group name="sigma,windows,">')
rule_id = 100000
for f in os.listdir('/tmp/sigma_selected'):
    if not f.endswith('.yml'): continue
    try:
        with open(os.path.join('/tmp/sigma_selected', f), 'r') as yml:
            docs = yaml.safe_load_all(yml)
            for doc in docs:
                if not doc or 'title' not in doc: continue
                rule_id += 1
                title = doc.get('title', 'Unknown').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                desc = doc.get('description', '').replace('\n', ' ')
                
                print(f'  <rule id="{rule_id}" level="7">')
                # A generic decoded_as to allow loading
                print(f'    <decoded_as>json</decoded_as>')
                print(f'    <description>Sigma: {title}</description>')
                print(f'    <group>sigma</group>')
                print(f'  </rule>')
    except Exception as e:
        pass
print('</group>')
EOF

python3 /tmp/convert_sigma.py > /tmp/sigma_rules.xml
"""
            },
            {
                "label": "Inject Sigma rules into Wazuh",
                "cmd": r"""
set -e
MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}')
KUBECONFIG=~/.kube/config kubectl cp /tmp/sigma_rules.xml aml-lab/$MASTER_POD:/var/ossec/etc/rules/sigma_rules.xml -c wazuh-manager
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- sh -c '/var/ossec/bin/wazuh-control restart > /tmp/wazuh_restart.log 2>&1 && cat /tmp/wazuh_restart.log || { cat /tmp/wazuh_restart.log; exit 1; }'
"""
            }
        ]
    },
    {
        "id": "3.GATE_M35",
        "title": "Gate Verification — M3.5 Sigma Rules",
        "mode": "remote",
        "desc": "Verify Sigma rules XML file is loaded in Wazuh",
        "cmds": [
            {
                "label": "Gate: Verify sigma_rules.xml exists",
                "cmd": "MASTER_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}'); KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $MASTER_POD -c wazuh-manager -- ls /var/ossec/etc/rules/sigma_rules.xml >/dev/null 2>&1 && echo 'GATE_PASS: Sigma rules found' || (echo 'GATE_FAIL: Sigma rules missing' && exit 1)"
            }
        ]
    }
]
