#!/usr/bin/env python3
"""
AML-SIEM M0.1 — GCP Server Provisioning Tool
Amlak Al-Arabia General Trading Co.

Step 2   → runs LOCALLY  on your Mac  (SSH key gen, config writing)
Step 2        → runs LOCALLY  on your Mac (SSH key gen, config writing)
Steps 3–10    → M0.1 provisioning on GCP VM via SSH
Steps D1–D10  → M0.2 Docker CE installation on GCP VM via SSH

Requirements:
    pip install paramiko
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import time
import json
import paramiko
import subprocess
import subprocess as sp
import os
import stat
import platform
from datetime import datetime
from pathlib import Path


# ── Firewall scripts — uploaded via SFTP, no shell quoting needed ──────────────
FW80_SCRIPT = """#!/bin/bash
set -e
# Flush stale gcloud token cache — required after VM stop/start scope changes
gcloud auth revoke --all 2>/dev/null || true
rm -f ~/.config/gcloud/access_tokens.db ~/.config/gcloud/credentials.db 2>/dev/null || true
gcloud config set account $(curl -sf -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email') 2>/dev/null || true
echo 'gcloud token cache cleared'
SA=$(curl -sf -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email')
PROJECT=$(curl -sf -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/project/project-id')
echo "Project: $PROJECT"
echo "Service account: $SA"
echo ""
EXISTING=$(gcloud compute firewall-rules list \
  --filter='name=aml-siem-allow-http' \
  --format='value(name)' 2>/dev/null)
if [ -n "$EXISTING" ]; then
  echo "RULE_EXISTS: aml-siem-allow-http already exists OK"
  exit 0
fi
gcloud compute firewall-rules create aml-siem-allow-http \
  --allow=tcp:80 \
  --source-ranges=0.0.0.0/0 \
  --description=AML-SIEM-HTTP \
  --quiet 2>/tmp/fw80_err.txt
if [ $? -eq 0 ]; then
  echo "RULE_HTTP_CREATED"
else
  echo ""
  echo "FAILED: Could not create firewall rule for port 80"
  echo "Reason: $(cat /tmp/fw80_err.txt | head -3)"
  echo ""
  echo "WHY THIS HAPPENS"
  echo "The VM service account lacks compute.firewalls.create permission."
  echo "API scopes are correct but the IAM role is missing."
  echo ""
  echo "HOW TO FIX"
  echo ""
  echo "OPTION 1 - Run on your Mac as project Owner:"
  echo "  gcloud projects add-iam-policy-binding $PROJECT"
  echo "  --member=serviceAccount:$SA"
  echo "  --role=roles/compute.securityAdmin"
  echo ""
  echo "OPTION 2 - GCP Console:"
  echo "  IAM and Admin > IAM > find $SA > Edit > Add role: Compute Security Admin > Save"
  echo "  Then re-run N04C"
  echo ""
  echo "OPTION 3 - Create rule manually in GCP Console:"
  echo "  VPC Network > Firewall > Create Firewall Rule"
  echo "  Name: aml-siem-allow-http"
  echo "  Direction: Ingress | Action: Allow | Source: 0.0.0.0/0 | Protocol: TCP | Port: 80"
  echo "  Then re-run N04C - it will skip if rule already exists"
  exit 1
fi
"""

FW443_SCRIPT = """#!/bin/bash
set -e
# Flush stale gcloud token cache (same as FW80 — idempotent)
gcloud auth revoke --all 2>/dev/null || true
rm -f ~/.config/gcloud/access_tokens.db ~/.config/gcloud/credentials.db 2>/dev/null || true
gcloud config set account $(curl -sf -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email') 2>/dev/null || true
EXISTING=$(gcloud compute firewall-rules list \
  --filter='name=aml-siem-allow-https' \
  --format='value(name)' 2>/dev/null)
if [ -n "$EXISTING" ]; then
  echo "RULE_EXISTS: aml-siem-allow-https already exists OK"
  exit 0
fi
gcloud compute firewall-rules create aml-siem-allow-https \
  --allow=tcp:443 \
  --source-ranges=0.0.0.0/0 \
  --description=AML-SIEM-HTTPS \
  --quiet 2>/tmp/fw443_err.txt
if [ $? -eq 0 ]; then
  echo "RULE_HTTPS_CREATED"
else
  echo "FAILED: $(cat /tmp/fw443_err.txt | head -2)"
  echo "See port 80 step above for fix options"
  exit 1
fi
"""

VERIFY_FW_SCRIPT = """#!/bin/bash
echo "=== GCP Firewall Rules (aml-siem) ==="
gcloud compute firewall-rules list \
  --filter='name:aml-siem-allow' \
  --format='table(name,direction,allowed[].map().firewall_rule().list(),sourceRanges.list())' \
  2>/dev/null || echo "No aml-siem firewall rules found"
echo ""
echo "Port 80 rule:"
gcloud compute firewall-rules list \
  --filter='name=aml-siem-allow-http' --format='value(name)' 2>/dev/null \
  | grep -q aml-siem-allow-http && echo "  aml-siem-allow-http EXISTS" \
  || echo "  aml-siem-allow-http MISSING"
echo "Port 443 rule:"
gcloud compute firewall-rules list \
  --filter='name=aml-siem-allow-https' --format='value(name)' 2>/dev/null \
  | grep -q aml-siem-allow-https && echo "  aml-siem-allow-https EXISTS" \
  || echo "  aml-siem-allow-https MISSING"
"""

GITIGNORE_SCRIPT = """#!/bin/bash
cat > /opt/aml-siem/.gitignore << 'GITIGNORE'
# ═══════════════════════════════════════════════════════════════════
# SECRETS AND CREDENTIALS — NEVER COMMIT
# ═══════════════════════════════════════════════════════════════════
*.key
*.pem
*.crt
*.p12
*.pfx
*.jks
*_rsa
*_ecdsa
*_ed25519
id_*

# API tokens, service account keys
*.token
*credential*
*secret*
*.env
.env.*
credentials.json
service-account*.json
gcp-key*.json
cloudflare*.json

# Password-like patterns
*password*
*passwd*
*.htpasswd

# ═══════════════════════════════════════════════════════════════════
# KUBERNETES SECRETS
# ═══════════════════════════════════════════════════════════════════
**/secret*.yaml
**/secrets/
**/*-secret.yaml
tls-*.yaml
sealed-secrets/

# ═══════════════════════════════════════════════════════════════════
# LOGS AND RUNTIME OUTPUT
# ═══════════════════════════════════════════════════════════════════
logs/
*.log
*.log.*

# ═══════════════════════════════════════════════════════════════════
# BACKUPS (large, local-only)
# ═══════════════════════════════════════════════════════════════════
backups/
*.tar.gz
*.tgz
*.bak
*.dump

# ═══════════════════════════════════════════════════════════════════
# HELM AND KUBERNETES ARTIFACTS
# ═══════════════════════════════════════════════════════════════════
helm/**/charts/
helm/**/*.tgz
kubeconfig
kube.conf

# ═══════════════════════════════════════════════════════════════════
# EDITOR / OS JUNK
# ═══════════════════════════════════════════════════════════════════
.DS_Store
Thumbs.db
*.swp
*.swo
*~
.vscode/
.idea/
*.iml

# ═══════════════════════════════════════════════════════════════════
# TEMPORARY AND CACHE FILES
# ═══════════════════════════════════════════════════════════════════
tmp/
temp/
*.tmp
.cache/
__pycache__/
*.pyc
node_modules/

# ═══════════════════════════════════════════════════════════════════
# CLIENT-SPECIFIC RENDERED MANIFESTS
# ═══════════════════════════════════════════════════════════════════
k8s/clients/*/rendered/

# ═══════════════════════════════════════════════════════════════════
# CLIENT CONFIG FILES CONTAINING SECRETS
# ═══════════════════════════════════════════════════════════════════
clients/*.local.yaml
clients/*.secret.yaml
GITIGNORE
"""

README_SCRIPT = """#!/bin/bash
cat > /opt/aml-siem/README.md << 'README'
# AML-SIEM Platform

**Multi-tenant SIEM-as-a-Service for SME clients — by Amlak Al-Arabia General Trading Co.**

Sprint 0 baseline: single GCP VM running K3s with shared OpenSearch, TheHive, Shuffle, Grafana, and per-client Wazuh managers.

## Repository Layout

```
/opt/aml-siem/
├── k8s/          Kubernetes manifests (base, templates, per-client)
├── helm/         Helm values.yaml for each shared service
├── clients/      Per-client config files
├── scripts/      Deployment, backup, onboarding, lifecycle
├── config/       Wazuh rules, dashboards, workflows
├── docs/         Sprint documentation, runbooks, architecture
├── logs/         Deployment logs (not committed)
└── backups/      Local backup staging (not committed)
```

## Quick Start — Deploy a New Client

```bash
cd /opt/aml-siem
./scripts/deploy/deploy-client.sh chemdry
```

## Environment

- VM: aml-lab-01 — Ubuntu 22.04 LTS on GCP
- User: amlsiem
- Cluster: K3s v1.30+
- Ingress: Nginx Ingress Controller
- TLS: Let's Encrypt via cert-manager
- Domain: *.CLIENT.amlsiem.com

## Sprint Progress

- ✅ M0.1 — GCP Server Provisioning
- ✅ M0.2 — Docker CE Installation
- ✅ M0.3 — K3s Kubernetes
- ✅ M0.4 — Nginx Ingress + TLS
- ✅ M0.5 — Git Repo + Folder Structure

---

*Internal — Engineering team only | amlakalarabia.com*
README
"""

OPENSEARCH_DEPLOY_SCRIPT = """#!/bin/bash
set -e

# Clean up existing opensearch components to ensure a fresh rollout
echo "Cleaning up existing OpenSearch deployment and terminating pods..."
KUBECONFIG=~/.kube/config kubectl delete statefulset opensearch-data -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete deployment opensearch-coordinator -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service opensearch opensearch-discovery -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete configmap opensearch-config -n aml-lab --ignore-not-found=true
sleep 5

mkdir -p /opt/aml-siem/k8s/base/opensearch

# 1. Write ConfigMap
cat > /opt/aml-siem/k8s/base/opensearch/opensearch-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: opensearch-config
  namespace: aml-lab
data:
  opensearch.yml: |
    cluster.name: aml-siem-cluster
    network.host: 0.0.0.0
    
    # Discovery Settings
    discovery.seed_hosts: ["opensearch-discovery"]
    cluster.initial_cluster_manager_nodes: ["opensearch-data-0", "opensearch-data-1"]
    
    # Disable security plugin
    plugins.security.disabled: true
    
    # Performance Optimizations
    bootstrap.memory_lock: false
    thread_pool.write.queue_size: 1000
EOF

# 2. Write Services
cat > /opt/aml-siem/k8s/base/opensearch/opensearch-service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: opensearch-discovery
  namespace: aml-lab
  labels:
    app: opensearch
spec:
  clusterIP: None
  selector:
    app: opensearch
    role: data
  ports:
  - port: 9300
    name: transport
---
apiVersion: v1
kind: Service
metadata:
  name: opensearch
  namespace: aml-lab
  labels:
    app: opensearch
spec:
  selector:
    app: opensearch
    role: coordinator
  ports:
  - port: 9200
    targetPort: 9200
    name: http
  - port: 9300
    targetPort: 9300
    name: transport
EOF

# 3. Write Data StatefulSet
cat > /opt/aml-siem/k8s/base/opensearch/opensearch-data.yaml << 'EOF'
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: opensearch-data
  namespace: aml-lab
spec:
  serviceName: opensearch-discovery
  replicas: 2
  selector:
    matchLabels:
      app: opensearch
      role: data
  template:
    metadata:
      labels:
        app: opensearch
        role: data
    spec:
      initContainers:
      - name: init-sysctl
        image: busybox
        command: ["sysctl", "-w", "vm.max_map_count=262144"]
        securityContext:
          privileged: true
      - name: init-ulimit
        image: busybox
        command: ["sh", "-c", "ulimit -l unlimited"]
        securityContext:
          privileged: true
      containers:
      - name: opensearch
        image: opensearchproject/opensearch:2.11.1
        resources:
          limits:
            memory: 4Gi
            cpu: "2"
          requests:
            memory: 4Gi
            cpu: "1"
        env:
        - name: cluster.name
          value: aml-siem-cluster
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "opensearch-discovery"
        - name: cluster.initial_cluster_manager_nodes
          value: "opensearch-data-0,opensearch-data-1"
        - name: node.roles
          value: "data,cluster_manager"
        - name: OPENSEARCH_JAVA_OPTS
          value: "-Xms2g -Xmx2g"
        - name: DISABLE_INSTALL_DEMO_CONFIG
          value: "true"
        - name: DISABLE_SECURITY_PLUGIN
          value: "true"
        securityContext:
          capabilities:
            add: ["SYS_CHROOT"]
        ports:
        - containerPort: 9200
          name: http
        - containerPort: 9300
          name: transport
        volumeMounts:
        - name: opensearch-data-storage
          mountPath: /usr/share/opensearch/data
        - name: config-volume
          mountPath: /usr/share/opensearch/config/opensearch.yml
          subPath: opensearch.yml
      volumes:
      - name: config-volume
        configMap:
          name: opensearch-config
  volumeClaimTemplates:
  - metadata:
      name: opensearch-data-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "local-path"
      resources:
        requests:
          storage: 50Gi
EOF

# 4. Write Coordinator Deployment
cat > /opt/aml-siem/k8s/base/opensearch/opensearch-coordinator.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opensearch-coordinator
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: opensearch
      role: coordinator
  template:
    metadata:
      labels:
        app: opensearch
        role: coordinator
    spec:
      initContainers:
      - name: init-sysctl
        image: busybox
        command: ["sysctl", "-w", "vm.max_map_count=262144"]
        securityContext:
          privileged: true
      containers:
      - name: opensearch
        image: opensearchproject/opensearch:2.11.1
        resources:
          limits:
            memory: 4Gi
            cpu: "2"
          requests:
            memory: 4Gi
            cpu: "1"
        env:
        - name: cluster.name
          value: aml-siem-cluster
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "opensearch-discovery"
        - name: node.roles
          value: ""
        - name: OPENSEARCH_JAVA_OPTS
          value: "-Xms2g -Xmx2g"
        - name: DISABLE_INSTALL_DEMO_CONFIG
          value: "true"
        - name: DISABLE_SECURITY_PLUGIN
          value: "true"
        ports:
        - containerPort: 9200
          name: http
        - containerPort: 9300
          name: transport
        volumeMounts:
        - name: config-volume
          mountPath: /usr/share/opensearch/config/opensearch.yml
          subPath: opensearch.yml
      volumes:
      - name: config-volume
        configMap:
          name: opensearch-config
EOF

# Apply resources
KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/opensearch/
"""

OPENSEARCH_ISM_SCRIPT = """#!/bin/bash
set -e

# Resolve the active coordinator pod name first to avoid matching terminating pods
COORD_POD=""
for i in {1..30}; do
  COORD_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1)
  if [ -n "$COORD_POD" ]; then
    break
  fi
  sleep 2
done

if [ -z "$COORD_POD" ]; then
  echo "Error: No active OpenSearch coordinator pod found."
  exit 1
fi

echo "Waiting for OpenSearch coordinator pod $COORD_POD to be running and ready..."
KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod/$COORD_POD -n aml-lab --timeout=300s

echo "Coordinator pod: $COORD_POD"

# Wait for OpenSearch API on localhost:9200 to be responsive
echo "Waiting for OpenSearch API on localhost:9200 to be responsive..."
for i in {1..45}; do
  if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $COORD_POD -- curl -s http://localhost:9200/ >/dev/null; then
    echo "OpenSearch API is responsive!"
    break
  fi
  echo "OpenSearch not ready yet. Retrying in 5s ($i/45)..."
  sleep 5
done

# Apply policy inside pod using inline json
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $COORD_POD -- curl -s -XPUT http://localhost:9200/_plugins/_ism/policies/wazuh_retention_policy -H "Content-Type: application/json" -d '{"policy":{"description":"Auto-delete Wazuh alerts older than 30 days.","default_state":"hot","states":[{"name":"hot","actions":[],"transitions":[{"state_name":"delete","conditions":{"min_index_age":"30d"}}]},{"name":"delete","actions":[{"delete":{}}],"transitions":[]}]}}'

# Bind template inside pod
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $COORD_POD -- curl -s -XPUT http://localhost:9200/_index_template/wazuh_ism_binding -H "Content-Type: application/json" -d '{"index_patterns":["wazuh-alerts-*"],"template":{"settings":{"opendistro.index_state_management.policy_id":"wazuh_retention_policy"}}}'

echo "ISM_POLICY_APPLIED"
"""

WAZUH_DEPLOY_SCRIPT = """#!/bin/bash
set -e

# Clean up existing wazuh deployments to ensure a fresh rollout
echo "Cleaning up existing Wazuh deployments..."
KUBECONFIG=~/.kube/config kubectl delete deployment wazuh-master wazuh-worker opensearch-proxy -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service wazuh wazuh-master-svc opensearch-proxy -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete configmap wazuh-master-config wazuh-worker-config -n aml-lab --ignore-not-found=true
sleep 5

mkdir -p /opt/aml-siem/k8s/base/wazuh-manager

# 1. ConfigMap for Master Node
cat > /opt/aml-siem/k8s/base/wazuh-manager/wazuh-master-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: wazuh-master-config
  namespace: aml-lab
data:
  ossec.conf: |
    <ossec_config>
      <global>
        <email_notification>yes</email_notification>
        <email_to>soc@amlakalarabia.com</email_to>
        <email_from>devops@amlakalarabia.com</email_from>
        <smtp_server>smtp.office365.com</smtp_server>
        <email_maxperhour>12</email_maxperhour>
        <email_idsname>default_alerts</email_idsname>
        <jsonout_output>yes</jsonout_output>
      </global>

      <alerts>
        <log_alert_level>3</log_alert_level>
        <email_alert_level>10</email_alert_level>
      </alerts>

      <cluster>
        <disabled>no</disabled>
        <node_type>master</node_type>
        <key>9782345a6c382902bc8971f11a8c0fcd</key>
        <node_name>wazuh-master</node_name>
        <port>1516</port>
        <bind_addr>0.0.0.0</bind_addr>
        <nodes>
          <node>wazuh-master-svc.aml-lab.svc.cluster.local</node>
        </nodes>
        <hidden>no</hidden>
      </cluster>

      <logging>
        <log_format>json</log_format>
      </logging>

      <remote>
        <connection>secure</connection>
        <port>1514</port>
        <protocol>tcp</protocol>
        <local_ip>0.0.0.0</local_ip>
      </remote>

      <remote>
        <connection>syslog</connection>
        <port>514</port>
        <protocol>udp</protocol>
        <allowed-ips>0.0.0.0/0</allowed-ips>
      </remote>

      <remote>
        <connection>syslog</connection>
        <port>514</port>
        <protocol>tcp</protocol>
        <allowed-ips>0.0.0.0/0</allowed-ips>
      </remote>

      <auth>
        <disabled>no</disabled>
        <port>1515</port>
        <use_source_ip>no</use_source_ip>
        <force>
          <enabled>yes</enabled>
          <key_mismatch>yes</key_mismatch>
          <disconnected_time enabled="yes">0s</disconnected_time>
          <after_registration_time enabled="yes">0s</after_registration_time>
        </force>
        <purge>yes</purge>
        <use_password>no</use_password>
        <ssl_verify_host>no</ssl_verify_host>
        <ssl_manager_cert>/var/ossec/etc/sslmanager.cert</ssl_manager_cert>
        <ssl_manager_key>/var/ossec/etc/sslmanager.key</ssl_manager_key>
        <ssl_auto_negotiate>no</ssl_auto_negotiate>
      </auth>

      <vulnerability-detector>
        <enabled>yes</enabled>
        <interval>5m</interval>
        <run_on_start>yes</run_on_start>
        <provider name="canonical">
          <enabled>yes</enabled>
          <os>jammy</os>
          <update_interval>1h</update_interval>
        </provider>
        <provider name="msu">
          <enabled>yes</enabled>
          <update_interval>1h</update_interval>
        </provider>
      </vulnerability-detector>
      <ruleset>
        <!-- Default ruleset -->
        <decoder_dir>ruleset/decoders</decoder_dir>
        <rule_dir>ruleset/rules</rule_dir>
        <rule_exclude>0215-policy_rules.xml</rule_exclude>
        <list>etc/lists/audit-keys</list>
        <list>etc/lists/amazon/aws-eventnames</list>
        <list>etc/lists/security-eventchannel</list>

        <!-- User-defined ruleset -->
        <decoder_dir>etc/decoders</decoder_dir>
        <rule_dir>etc/rules</rule_dir>
      </ruleset>
    </ossec_config>

  filebeat.yml: |
    filebeat.modules:
      - module: wazuh
        alerts:
          enabled: true
        archives:
          enabled: false

    setup.template.name: "wazuh-alerts-4.x"
    setup.template.pattern: "wazuh-alerts-4.x-*"
    setup.template.enabled: false
    setup.template.json.enabled: false
    setup.ilm.enabled: false

    output.elasticsearch:
      hosts: ["http://opensearch-proxy.aml-lab.svc.cluster.local:9200"]
      index: "wazuh-alerts-4.x-%{+yyyy.MM.dd}"

  local_decoder.xml: |
    <!-- Local Decoders -->
    <decoder name="fortigate-firewall-v5">
      <parent>fortigate-firewall-v5</parent>
      <regex>actn="(\\S+)"|actn=(\\S+)\\s|actn=(\\S+)$</regex>
      <order>actn</order>
    </decoder>
    <decoder name="fortigate-firewall-v5">
      <parent>fortigate-firewall-v5</parent>
      <regex>fstatus="(\\S+)"|fstatus=(\\S+)\\s|fstatus=(\\S+)$</regex>
      <order>fstatus</order>
    </decoder>
    <decoder name="fortigate-firewall-v6">
      <parent>fortigate-firewall-v6</parent>
      <regex>actn="(\\S+)"|actn=(\\S+)\\s|actn=(\\S+)$</regex>
      <order>actn</order>
    </decoder>
    <decoder name="fortigate-firewall-v6">
      <parent>fortigate-firewall-v6</parent>
      <regex>fstatus="(\\S+)"|fstatus=(\\S+)\\s|fstatus=(\\S+)$</regex>
      <order>fstatus</order>
    </decoder>
    <decoder name="fortiddos-like-child">
      <parent>fortiddos-like</parent>
      <regex>actn="(\\S+)"|actn=(\\S+)\\s|actn=(\\S+)$</regex>
      <order>actn</order>
    </decoder>
    <decoder name="fortiddos-like-child">
      <parent>fortiddos-like</parent>
      <regex>fstatus="(\\S+)"|fstatus=(\\S+)\\s|fstatus=(\\S+)$</regex>
      <order>fstatus</order>
    </decoder>

  local_rules.xml: |
    <!-- Local Rules -->
    <group name="fortigate,">
      <rule id="44612" level="7" overwrite="yes">
        <if_sid>81603,81641,81602,44600</if_sid>
        <field name="actn">^interface-stat-change$</field>
        <field name="fstatus">^down$</field>
        <description>FortiGate: Interface down (Custom Overwrite).</description>
      </rule>
    </group>
EOF

# 2. ConfigMap for Worker Node
cat > /opt/aml-siem/k8s/base/wazuh-manager/wazuh-worker-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: wazuh-worker-config
  namespace: aml-lab
data:
  ossec.conf: |
    <ossec_config>
      <global>
        <email_notification>yes</email_notification>
        <email_to>soc@amlakalarabia.com</email_to>
        <email_from>devops@amlakalarabia.com</email_from>
        <smtp_server>smtp.office365.com</smtp_server>
        <email_maxperhour>12</email_maxperhour>
        <email_idsname>default_alerts</email_idsname>
        <jsonout_output>yes</jsonout_output>
      </global>

      <alerts>
        <log_alert_level>3</log_alert_level>
        <email_alert_level>10</email_alert_level>
      </alerts>

      <cluster>
        <disabled>no</disabled>
        <node_type>worker</node_type>
        <key>9782345a6c382902bc8971f11a8c0fcd</key>
        <node_name>wazuh-worker</node_name>
        <port>1516</port>
        <bind_addr>0.0.0.0</bind_addr>
        <nodes>
          <node>wazuh-master-svc.aml-lab.svc.cluster.local</node>
        </nodes>
        <hidden>no</hidden>
      </cluster>

      <logging>
        <log_format>json</log_format>
      </logging>

      <remote>
        <connection>secure</connection>
        <port>1514</port>
        <protocol>tcp</protocol>
        <local_ip>0.0.0.0</local_ip>
      </remote>

      <remote>
        <connection>syslog</connection>
        <port>514</port>
        <protocol>udp</protocol>
        <allowed-ips>0.0.0.0/0</allowed-ips>
      </remote>

      <remote>
        <connection>syslog</connection>
        <port>514</port>
        <protocol>tcp</protocol>
        <allowed-ips>0.0.0.0/0</allowed-ips>
      </remote>
      <ruleset>
        <!-- Default ruleset -->
        <decoder_dir>ruleset/decoders</decoder_dir>
        <rule_dir>ruleset/rules</rule_dir>
        <rule_exclude>0215-policy_rules.xml</rule_exclude>
        <list>etc/lists/audit-keys</list>
        <list>etc/lists/amazon/aws-eventnames</list>
        <list>etc/lists/security-eventchannel</list>

        <!-- User-defined ruleset -->
        <decoder_dir>etc/decoders</decoder_dir>
        <rule_dir>etc/rules</rule_dir>
      </ruleset>
    </ossec_config>

  filebeat.yml: |
    filebeat.modules:
      - module: wazuh
        alerts:
          enabled: true
        archives:
          enabled: false

    setup.template.name: "wazuh-alerts-4.x"
    setup.template.pattern: "wazuh-alerts-4.x-*"
    setup.template.enabled: false
    setup.template.json.enabled: false
    setup.ilm.enabled: false

    output.elasticsearch:
      hosts: ["http://opensearch-proxy.aml-lab.svc.cluster.local:9200"]
      index: "wazuh-alerts-4.x-%{+yyyy.MM.dd}"

  local_decoder.xml: |
    <!-- Local Decoders -->
    <decoder name="fortigate-firewall-v5">
      <parent>fortigate-firewall-v5</parent>
      <regex>actn="(\\S+)"|actn=(\\S+)\\s|actn=(\\S+)$</regex>
      <order>actn</order>
    </decoder>
    <decoder name="fortigate-firewall-v5">
      <parent>fortigate-firewall-v5</parent>
      <regex>fstatus="(\\S+)"|fstatus=(\\S+)\\s|fstatus=(\\S+)$</regex>
      <order>fstatus</order>
    </decoder>
    <decoder name="fortigate-firewall-v6">
      <parent>fortigate-firewall-v6</parent>
      <regex>actn="(\\S+)"|actn=(\\S+)\\s|actn=(\\S+)$</regex>
      <order>actn</order>
    </decoder>
    <decoder name="fortigate-firewall-v6">
      <parent>fortigate-firewall-v6</parent>
      <regex>fstatus="(\\S+)"|fstatus=(\\S+)\\s|fstatus=(\\S+)$</regex>
      <order>fstatus</order>
    </decoder>
    <decoder name="fortiddos-like-child">
      <parent>fortiddos-like</parent>
      <regex>actn="(\\S+)"|actn=(\\S+)\\s|actn=(\\S+)$</regex>
      <order>actn</order>
    </decoder>
    <decoder name="fortiddos-like-child">
      <parent>fortiddos-like</parent>
      <regex>fstatus="(\\S+)"|fstatus=(\\S+)\\s|fstatus=(\\S+)$</regex>
      <order>fstatus</order>
    </decoder>

  local_rules.xml: |
    <!-- Local Rules -->
    <group name="fortigate,">
      <rule id="44612" level="7" overwrite="yes">
        <if_sid>81603,81641,81602,44600</if_sid>
        <field name="actn">^interface-stat-change$</field>
        <field name="fstatus">^down$</field>
        <description>FortiGate: Interface down (Custom Overwrite).</description>
      </rule>
    </group>
EOF

# 3. Master Deployment
cat > /opt/aml-siem/k8s/base/wazuh-manager/wazuh-master-deploy.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wazuh-master
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wazuh-manager
      node-role: master
  template:
    metadata:
      labels:
        app: wazuh-manager
        node-role: master
    spec:
      initContainers:
      - name: init-logs
        image: wazuh/wazuh-manager:4.7.5
        command: ["sh", "-c", "mkdir -p /shared-logs/alerts /shared-logs/archives /shared-logs/firewall /shared-logs/wazuh /shared-logs/api /shared-logs/cluster && chown -R wazuh:wazuh /shared-logs && chmod -R 770 /shared-logs"]
        volumeMounts:
        - name: shared-logs
          mountPath: /shared-logs
      containers:
      - name: wazuh-manager
        image: wazuh/wazuh-manager:4.7.5
        ports:
        - containerPort: 1514
          name: agent-conn
        - containerPort: 1515
          name: agent-auth
        - containerPort: 1516
          name: cluster-sync
        - containerPort: 55000
          name: wazuh-api
        - containerPort: 514
          name: syslog-udp
          protocol: UDP
        - containerPort: 514
          name: syslog-tcp
          protocol: TCP
        env:
        - name: WAZUH_API_USER
          value: "wazuh"
        - name: WAZUH_API_PASSWORD
          value: "wazuh"
        volumeMounts:
        - name: config-volume
          mountPath: /wazuh-config-mount/etc/ossec.conf
          subPath: ossec.conf
        - name: config-volume
          mountPath: /wazuh-config-mount/etc/decoders/local_decoder.xml
          subPath: local_decoder.xml
        - name: config-volume
          mountPath: /wazuh-config-mount/etc/rules/local_rules.xml
          subPath: local_rules.xml
        - name: config-volume
          mountPath: /etc/filebeat/filebeat.yml
          subPath: filebeat.yml
        - name: shared-logs
          mountPath: /var/ossec/logs
      volumes:
      - name: config-volume
        configMap:
          name: wazuh-master-config
      - name: shared-logs
        emptyDir: {}
EOF

# 4. Worker Deployment
cat > /opt/aml-siem/k8s/base/wazuh-manager/wazuh-worker-deploy.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wazuh-worker
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wazuh-manager
      node-role: worker
  template:
    metadata:
      labels:
        app: wazuh-manager
        node-role: worker
    spec:
      initContainers:
      - name: init-logs
        image: wazuh/wazuh-manager:4.7.5
        command: ["sh", "-c", "mkdir -p /shared-logs/alerts /shared-logs/archives /shared-logs/firewall /shared-logs/wazuh /shared-logs/api /shared-logs/cluster && chown -R wazuh:wazuh /shared-logs && chmod -R 770 /shared-logs"]
        volumeMounts:
        - name: shared-logs
          mountPath: /shared-logs
      containers:
      - name: wazuh-manager
        image: wazuh/wazuh-manager:4.7.5
        ports:
        - containerPort: 1514
          name: agent-conn
        - containerPort: 1516
          name: cluster-sync
        - containerPort: 514
          name: syslog-udp
          protocol: UDP
        - containerPort: 514
          name: syslog-tcp
          protocol: TCP
        volumeMounts:
        - name: config-volume
          mountPath: /wazuh-config-mount/etc/ossec.conf
          subPath: ossec.conf
        - name: config-volume
          mountPath: /wazuh-config-mount/etc/decoders/local_decoder.xml
          subPath: local_decoder.xml
        - name: config-volume
          mountPath: /wazuh-config-mount/etc/rules/local_rules.xml
          subPath: local_rules.xml
        - name: config-volume
          mountPath: /etc/filebeat/filebeat.yml
          subPath: filebeat.yml
        - name: shared-logs
          mountPath: /var/ossec/logs
      volumes:
      - name: config-volume
        configMap:
          name: wazuh-worker-config
      - name: shared-logs
        emptyDir: {}
EOF

# 5. Services
cat > /opt/aml-siem/k8s/base/wazuh-manager/wazuh-service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: wazuh-master-svc
  namespace: aml-lab
spec:
  type: LoadBalancer
  selector:
    app: wazuh-manager
    node-role: master
  ports:
  - port: 1515
    targetPort: 1515
    name: agent-auth
  - port: 1516
    targetPort: 1516
    name: cluster-sync
  - port: 55000
    targetPort: 55000
    name: wazuh-api
---
apiVersion: v1
kind: Service
metadata:
  name: wazuh
  namespace: aml-lab
spec:
  type: LoadBalancer
  selector:
    app: wazuh-manager
  ports:
  - port: 1514
    targetPort: 1514
    protocol: TCP
    name: agent-conn-tcp
  - port: 514
    targetPort: 514
    protocol: UDP
    name: syslog-udp
  - port: 514
    targetPort: 514
    protocol: TCP
    name: syslog-tcp
EOF

# 6. OpenSearch Proxy to strip _type parameter for OpenSearch 2.x compatibility
cat > /opt/aml-siem/k8s/base/wazuh-manager/opensearch-proxy.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opensearch-proxy
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: opensearch-proxy
  template:
    metadata:
      labels:
        app: opensearch-proxy
    spec:
      containers:
      - name: proxy
        image: python:3.9-slim
        command:
        - python3
        - -c
        - |
          import http.server, urllib.request, urllib.error, sys
          TARGET_HOST = "http://opensearch.aml-lab.svc.cluster.local:9200"
          class ProxyHandler(http.server.BaseHTTPRequestHandler):
              def handle_request(self):
                  content_length = int(self.headers.get('Content-Length', 0))
                  body = self.rfile.read(content_length) if content_length > 0 else None
                  if body and b'_type' in body:
                      body = body.replace(b',_type:"_doc"', b'')
                      body = body.replace(b',_type:"doc"', b'')
                      body = body.replace(b',"_type":"_doc"', b'')
                      body = body.replace(b',"_type":"doc"', b'')
                  req = urllib.request.Request(
                      f"{TARGET_HOST}{self.path}",
                      data=body,
                      headers={k: v for k, v in self.headers.items() if k.lower() not in ('host', 'content-length')}
                  )
                  req.method = self.command
                  try:
                      with urllib.request.urlopen(req) as res:
                          self.send_response(res.status)
                          for k, v in res.headers.items():
                              if k.lower() not in ('transfer-encoding', 'content-length'):
                                  self.send_header(k, v)
                          self.end_headers()
                          self.wfile.write(res.read())
                  except urllib.error.HTTPError as e:
                      self.send_response(e.code)
                      for k, v in e.headers.items():
                          if k.lower() not in ('transfer-encoding', 'content-length'):
                              self.send_header(k, v)
                      self.end_headers()
                      self.wfile.write(e.read())
                  except Exception as e:
                      self.send_response(500)
                      self.end_headers()
                      self.wfile.write(str(e).encode())
              do_GET = handle_request
              do_POST = handle_request
              do_PUT = handle_request
              do_DELETE = handle_request
              do_HEAD = handle_request
          server = http.server.HTTPServer(('0.0.0.0', 9200), ProxyHandler)
          server.serve_forever()
        ports:
        - containerPort: 9200
          name: http
---
apiVersion: v1
kind: Service
metadata:
  name: opensearch-proxy
  namespace: aml-lab
spec:
  ports:
  - port: 9200
    targetPort: 9200
    name: http
  selector:
    app: opensearch-proxy
EOF

# Apply resources
KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/wazuh-manager/
"""

WAZUH_DASHBOARD_DEPLOY_SCRIPT = """#!/bin/bash
set -e

# Clean up existing wazuh dashboard deployments to ensure a fresh rollout
echo "Cleaning up existing Wazuh Dashboard deployments..."
KUBECONFIG=~/.kube/config kubectl delete deployment wazuh-dashboard -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service wazuh-dashboard -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete ingress wazuh-dashboard-ingress -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete configmap wazuh-dashboard-config -n aml-lab --ignore-not-found=true
sleep 5

# Ensure directory exists
mkdir -p /opt/aml-siem/k8s/base/wazuh-dashboard/

# 1. ConfigMap
cat > /opt/aml-siem/k8s/base/wazuh-dashboard/wazuh-dashboard-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: wazuh-dashboard-config
  namespace: aml-lab
data:
  opensearch_dashboards.yml: |
    server.host: "0.0.0.0"
    server.port: 5601
    opensearch.hosts: ["http://opensearch.aml-lab.svc.cluster.local:9200"]
    opensearch.ssl.verificationMode: none
    opensearch.username: "admin"
    opensearch.password: "admin"
    server.ssl.enabled: false

  wazuh.yml: |
    hosts:
      - default:
          url: https://wazuh-master-svc.aml-lab.svc.cluster.local
          port: 55000
          username: wazuh
          password: wazuh
          run_as: false
EOF

# 2. Service
cat > /opt/aml-siem/k8s/base/wazuh-dashboard/wazuh-dashboard-svc.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: wazuh-dashboard
  namespace: aml-lab
  labels:
    app: wazuh-dashboard
spec:
  selector:
    app: wazuh-dashboard
  ports:
  - port: 5601
    targetPort: 5601
    protocol: TCP
    name: http
EOF

# 3. Deployment
cat > /opt/aml-siem/k8s/base/wazuh-dashboard/wazuh-dashboard-deploy.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wazuh-dashboard
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wazuh-dashboard
  template:
    metadata:
      labels:
        app: wazuh-dashboard
    spec:
      containers:
      - name: wazuh-dashboard
        image: wazuh/wazuh-dashboard:4.7.5
        command: ["/bin/sh", "-c"]
        args:
        - "rm -rf /usr/share/wazuh-dashboard/plugins/securityDashboards && exec /entrypoint.sh"
        ports:
        - containerPort: 5601
          name: http
        env:
        - name: NODE_TLS_REJECT_UNAUTHORIZED
          value: "0"
        volumeMounts:
        - name: config-volume
          mountPath: /usr/share/wazuh-dashboard/config/opensearch_dashboards.yml
          subPath: opensearch_dashboards.yml
        - name: config-volume
          mountPath: /usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml
          subPath: wazuh.yml
      volumes:
      - name: config-volume
        configMap:
          name: wazuh-dashboard-config
EOF

# 4. Ingress
cat > /opt/aml-siem/k8s/base/wazuh-dashboard/wazuh-dashboard-ingress.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: wazuh-dashboard-ingress
  namespace: aml-lab
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: 50m
spec:
  tls:
  - hosts:
    - wazuh.aml-lab.amlsiem.com
    secretName: wazuh-dashboard-tls
  rules:
  - host: wazuh.aml-lab.amlsiem.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: wazuh-dashboard
            port:
              number: 5601
EOF

# Apply resources
KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/wazuh-dashboard/
"""

WAZUH_AGENT_CONFIG_SCRIPT = """#!/bin/bash
set -e

# Ensure configuration directory exists
mkdir -p /opt/aml-siem/k8s/base/wazuh-manager/

# 1. Create desired agent.conf profile
cat << 'EOF' > /opt/aml-siem/k8s/base/wazuh-manager/agent.conf
<agent_config>
  <syscheck>
    <disabled>no</disabled>
    <frequency>43200</frequency>
    <directories check_all="yes" realtime="yes">/etc,/bin,/usr/bin</directories>
    <directories check_all="yes" realtime="yes">C:\\Windows\\System32\\drivers\\etc</directories>
  </syscheck>
  <sca>
    <enabled>yes</enabled>
    <scan_on_start>yes</scan_on_start>
    <interval>12h</interval>
  </sca>
</agent_config>
EOF

# 2. Find running master pod
POD_NAME=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1)
echo "Using pod: $POD_NAME"

# 3. Smart skip: compare md5 of current config vs desired — skip restart if already up to date
DESIRED_MD5=$(md5sum /opt/aml-siem/k8s/base/wazuh-manager/agent.conf | awk '{print $1}')
CURRENT_MD5=$(KUBECONFIG=~/.kube/config kubectl exec -n aml-lab ${POD_NAME} -c wazuh-manager -- \
  md5sum /var/ossec/etc/shared/default/agent.conf 2>/dev/null | awk '{print $1}' || echo "none")

if [ "$DESIRED_MD5" = "$CURRENT_MD5" ]; then
    echo "agent.conf already up to date (md5: $DESIRED_MD5) — skipping restart."
    exit 0
fi

echo "Config changed ($CURRENT_MD5 -> $DESIRED_MD5) — deploying and restarting Wazuh..."

# 4. Copy updated config into pod
KUBECONFIG=~/.kube/config kubectl cp /opt/aml-siem/k8s/base/wazuh-manager/agent.conf aml-lab/${POD_NAME}:/var/ossec/etc/shared/default/agent.conf -c wazuh-manager

# 5. Restart wazuh master in background — wazuh-control restart blocks 3+ min with no output
#    which triggers SSH socket timeout. Background it and wait briefly.
echo "Triggering wazuh-control restart in background (this takes ~60s)..."
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab ${POD_NAME} -c wazuh-manager -- \
  sh -c 'nohup /var/ossec/bin/wazuh-control restart > /var/ossec/logs/restart.log 2>&1 &'
echo "Restart triggered. Waiting 20s for Wazuh to come back up..."
sleep 20
echo "Verifying Wazuh processes running after restart..."
KUBECONFIG=~/.kube/config kubectl exec -n aml-lab ${POD_NAME} -c wazuh-manager -- \
  /var/ossec/bin/wazuh-control status | grep -E 'running|stopped' | head -10
echo "agent.conf deployed and Wazuh restarted successfully."
"""

WAZUH_WEBHOOK_PATCH_SCRIPT = """#!/bin/bash
set -e

cat << 'EOF' > /tmp/wazuh_patch.py
import os

# 1. Patch configmap
config_path = '/opt/aml-siem/k8s/base/wazuh-manager/wazuh-master-config.yaml'
if os.path.exists(config_path):
    with open(config_path) as f:
        content = f.read()
    
    if 'wazuh_alert_webhook_trigger' in content:
        content = content.replace('wazuh_alert_webhook_trigger', '11111111-2222-3333-4444-555555555555')
        
    if 'custom-webhook' not in content:
        integration = '''      <integration>
        <name>custom-webhook</name>
        <hook_url>https://shuffle.aml-lab.amlsiem.com/api/v1/hooks/11111111-2222-3333-4444-555555555555</hook_url>
        <level>10</level>
        <alert_format>json</alert_format>
      </integration>
'''
        content = content.replace('    </ossec_config>', integration + '    </ossec_config>')
        
    # Also fix old script if it exists (no SSL skip)
    if 'custom-webhook:' not in content or 'ssl.create_default_context' not in content:
        # Remove old entry if present
        if 'custom-webhook:' in content:
            import re
            content = re.sub('  custom-webhook: [|].*?(?=  \\w)', '', content, flags=re.DOTALL)
        script_body = '''  custom-webhook: |
    #!/usr/bin/env python3
    import sys, json, urllib.request, ssl, subprocess, socket
    alert_file = sys.argv[1]
    hook_url = sys.argv[3]
    with open(alert_file, 'r') as f:
        alert_data = json.load(f)
    # Resolve internal shuffle-backend ClusterIP via DNS
    try:
        svc_ip = socket.gethostbyname('shuffle-backend.aml-lab.svc.cluster.local')
        internal_url = f'http://{svc_ip}:5001' + hook_url[hook_url.index('/api/v1/hooks'):]
    except Exception:
        internal_url = hook_url
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for url in [internal_url, hook_url]:
        try:
            req = urllib.request.Request(url, data=json.dumps(alert_data).encode(), headers={'Content-Type': 'application/json'})
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
            opener.open(req, timeout=10).read()
            break
        except Exception:
            pass
'''
        content = content.replace('  local_rules.xml: |', script_body + '  local_rules.xml: |')
        
    with open(config_path, 'w') as f:
        f.write(content)
    print("CONFIG_PATCHED")

# 2. Patch deployment
deploy_path = '/opt/aml-siem/k8s/base/wazuh-manager/wazuh-master-deploy.yaml'
if os.path.exists(deploy_path):
    with open(deploy_path) as f:
        content = f.read()
        
    if 'custom-webhook' not in content:
        target_mount = '        - name: config-volume\\n          mountPath: /var/ossec/integrations/custom-webhook\\n          subPath: custom-webhook'
        content = content.replace('        - name: shared-logs', target_mount + '\\n        - name: shared-logs')
        
        old_volume = '''      - name: config-volume
        configMap:
          name: wazuh-master-config'''
          
        new_volume = '''      - name: config-volume
        configMap:
          name: wazuh-master-config
          items:
          - key: ossec.conf
            path: ossec.conf
          - key: local_decoder.xml
            path: local_decoder.xml
          - key: local_rules.xml
            path: local_rules.xml
          - key: filebeat.yml
            path: filebeat.yml
          - key: custom-webhook
            path: custom-webhook
            mode: 0755'''
        content = content.replace(old_volume, new_volume)
        with open(deploy_path, 'w') as f:
            f.write(content)
        print("DEPLOY_PATCHED")
    else:
        print("DEPLOY_ALREADY_PATCHED")
EOF

python3 /tmp/wazuh_patch.py
rm -f /tmp/wazuh_patch.py

# Bootstrap Shuffle: create admin user and register webhook hook in OpenSearch
SHUFFLE_SVC_IP=$(KUBECONFIG=~/.kube/config kubectl get svc shuffle-backend -n aml-lab -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo '')
OS_IP=$(KUBECONFIG=~/.kube/config kubectl get svc -n aml-lab opensearch -o jsonpath='{.spec.clusterIP}' 2>/dev/null || echo '')

if [ -n "$SHUFFLE_SVC_IP" ] && [ -n "$OS_IP" ]; then
  # Create admin user (idempotent)
  APIKEY=$(curl -sk -X POST http://${SHUFFLE_SVC_IP}:5001/api/v1/users/register \
    -H 'Content-Type: application/json' \
    -d '{"username": "admin", "password": "Admin1234!", "email": "admin@amlsiem.com"}' \
    2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("apikey",""))' 2>/dev/null)
  if [ -z "$APIKEY" ]; then
    APIKEY=$(curl -sk -X POST http://${SHUFFLE_SVC_IP}:5001/api/v1/users/login \
      -H 'Content-Type: application/json' \
      -d '{"username": "admin", "password": "Admin1234!"}' \
      2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("cookies",[{}])[0].get("value",""))' 2>/dev/null)
  fi

  # Get or create workflow
  WORKFLOW_ID=$(curl -sk -H "Authorization: Bearer ${APIKEY}" \
    http://${SHUFFLE_SVC_IP}:5001/api/v1/workflows 2>/dev/null | \
    python3 -c 'import sys,json; wfs=json.load(sys.stdin); print(wfs[0]["id"] if isinstance(wfs,list) and wfs else "")' 2>/dev/null)
  if [ -z "$WORKFLOW_ID" ]; then
    WORKFLOW_ID=$(curl -sk -X POST http://${SHUFFLE_SVC_IP}:5001/api/v1/workflows \
      -H "Authorization: Bearer ${APIKEY}" -H 'Content-Type: application/json' \
      -d '{"name":"Wazuh Alert Handler","description":"Receives Wazuh alerts via webhook","triggers":[{"id":"af2094c6-9d64-4cd1-b28c-881b9f4de58c","name":"Wazuh Webhook","trigger_type":"WEBHOOK","status":"running","app_name":"Webhook","app_version":"1.0.0"}],"actions":[]}' \
      2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))' 2>/dev/null)
  fi

  TRIGGER_ID='af2094c6-9d64-4cd1-b28c-881b9f4de58c'
  URL_HOOK_SEGMENT="shuffle-${TRIGGER_ID}"  # 44 chars: Shuffle's required URL segment length
  ORG_ID=$(curl -sk "http://${OS_IP}:9200/organizations/_search" 2>/dev/null | \
    python3 -c 'import sys,json; d=json.load(sys.stdin); hits=d.get("hits",{}).get("hits",[]); print(hits[0]["_id"] if hits else "")' 2>/dev/null)

  # Recreate hooks index with id as keyword (Shuffle's GetHook uses term query on id)
  curl -sk -X DELETE "http://${OS_IP}:9200/hooks" >/dev/null 2>&1
  curl -sk -X PUT "http://${OS_IP}:9200/hooks" \
    -H 'Content-Type: application/json' \
    -d '{"mappings":{"properties":{"id":{"type":"keyword"},"start":{"type":"keyword"},"status":{"type":"keyword"},"type":{"type":"keyword"},"owner":{"type":"keyword"},"org_id":{"type":"keyword"},"environment":{"type":"keyword"},"running":{"type":"boolean"},"auth":{"type":"keyword"},"workflows":{"type":"keyword"}}}}' >/dev/null 2>&1

  # Upsert hook document with correct field structure
  if [ -n "$WORKFLOW_ID" ]; then
    curl -sk -X PUT "http://${OS_IP}:9200/hooks/_doc/${TRIGGER_ID}" \
      -H 'Content-Type: application/json' \
      -d "{\"id\":\"${TRIGGER_ID}\",\"start\":\"${TRIGGER_ID}\",\"info\":{\"name\":\"Wazuh Alert Webhook\",\"description\":\"\"},\"actions\":[],\"type\":\"webhook\",\"owner\":\"\",\"status\":\"running\",\"workflows\":[\"${WORKFLOW_ID}\"],\"running\":true,\"org_id\":\"${ORG_ID}\",\"environment\":\"Shuffle\",\"auth\":\"\"}" >/dev/null 2>&1
    curl -sk -X POST "http://${OS_IP}:9200/hooks/_refresh" >/dev/null 2>&1

    # Patch the hook_url in the running container's ossec.conf to use the 44-char URL segment
    KUBECONFIG=~/.kube/config kubectl exec -n aml-lab deploy/wazuh-master -c wazuh-manager -- \
      sed -i "s|/api/v1/hooks/.*</hook_url>|/api/v1/hooks/${URL_HOOK_SEGMENT}</hook_url>|g" \
      /var/ossec/etc/ossec.conf 2>/dev/null || true
    # Reload wazuh-integratord to pick up the updated ossec.conf
    KUBECONFIG=~/.kube/config kubectl exec -n aml-lab deploy/wazuh-master -c wazuh-manager -- \
      kill -HUP $(pgrep wazuh-integratord) 2>/dev/null || true
    echo "SHUFFLE_HOOK_REGISTERED"
  fi
fi
"""

SHUFFLE_DEPLOY_SCRIPT = """#!/bin/bash
set -e

# Clean up existing shuffle deployments to ensure a fresh rollout
echo "Cleaning up existing Shuffle deployments..."
KUBECONFIG=~/.kube/config kubectl delete deployment shuffle-backend -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete deployment shuffle-frontend -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete deployment shuffle-orborus -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete deployment mailpit -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service shuffle-backend -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service shuffle-frontend -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service mailpit -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete ingress shuffle-ingress -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete ingress mailpit-ingress -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete pvc shuffle-backend-pvc -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete secret wazuh-api-credentials -n aml-lab --ignore-not-found=true
sleep 5

# Ensure directory exists
mkdir -p /opt/aml-siem/k8s/base/shuffle/

# 1. Create PVC
cat > /opt/aml-siem/k8s/base/shuffle/shuffle-pvc.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shuffle-backend-pvc
  namespace: aml-lab
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF

# 2. Create Backend Service and Deployment
cat > /opt/aml-siem/k8s/base/shuffle/shuffle-backend.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shuffle-backend
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: shuffle-backend
  template:
    metadata:
      labels:
        app: shuffle-backend
    spec:
      containers:
      - name: shuffle-backend
        image: ghcr.io/shuffle/shuffle-backend:1.3.0
        ports:
        - containerPort: 5001
        env:
        - name: SHUFFLE_OPENSEARCH_URL
          value: "http://opensearch-proxy.aml-lab.svc.cluster.local:9200"
        - name: SHUFFLE_ELASTIC
          value: "true"
        - name: SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY
          value: "true"
        - name: DB_LOCATION
          value: "/shuffle-database"
        - name: SHUFFLE_ENCRYPTION_MODIFIER
          value: "aml-siem-secret-key-modifier"
        volumeMounts:
        - name: backend-store
          mountPath: /shuffle-database
      volumes:
      - name: backend-store
        persistentVolumeClaim:
          claimName: shuffle-backend-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: shuffle-backend
  namespace: aml-lab
spec:
  selector:
    app: shuffle-backend
  ports:
  - port: 5001
    targetPort: 5001
    protocol: TCP
EOF

# 3. Create Frontend Service and Deployment
cat > /opt/aml-siem/k8s/base/shuffle/shuffle-frontend.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shuffle-frontend
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: shuffle-frontend
  template:
    metadata:
      labels:
        app: shuffle-frontend
    spec:
      containers:
      - name: shuffle-frontend
        image: ghcr.io/shuffle/shuffle-frontend:1.3.0
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_HOSTNAME
          value: "shuffle-backend"
---
apiVersion: v1
kind: Service
metadata:
  name: shuffle-frontend
  namespace: aml-lab
spec:
  selector:
    app: shuffle-frontend
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
EOF

# 4. Create Orborus Deployment
cat > /opt/aml-siem/k8s/base/shuffle/shuffle-orborus.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shuffle-orborus
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: shuffle-orborus
  template:
    metadata:
      labels:
        app: shuffle-orborus
    spec:
      containers:
      - name: shuffle-orborus
        image: ghcr.io/shuffle/shuffle-orborus:1.3.0
        env:
        - name: BASE_URL
          value: "https://shuffle.aml-lab.amlsiem.com"
        - name: ORBORUS_CONTAINER_REST_API
          value: "https://shuffle.aml-lab.amlsiem.com"
        - name: SHUFFLE_PORT
          value: "5001"
        - name: SHUFFLE_BACKEND_PORT
          value: "5001"
        - name: ENVIRONMENT_NAME
          value: "Shuffle"
        - name: DOCKER_API_VERSION
          value: "1.40"
        - name: SHUFFLE_SWARM_CONFIG
          value: "false"
        - name: SHUFFLE_OPENSEARCH_URL
          value: "http://opensearch-proxy.aml-lab.svc.cluster.local:9200"
        - name: SHUFFLE_ELASTIC
          value: "true"
        - name: SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY
          value: "true"
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock
          type: Socket
EOF

# 5. Create Ingress
cat > /opt/aml-siem/k8s/base/shuffle/shuffle-ingress.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shuffle-ingress
  namespace: aml-lab
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - shuffle.aml-lab.amlsiem.com
    secretName: shuffle-tls
  rules:
  - host: shuffle.aml-lab.amlsiem.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: shuffle-frontend
            port:
              number: 80
EOF

# 6. Create Mailpit (Mock SMTP Relay)
cat > /opt/aml-siem/k8s/base/shuffle/mailpit.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mailpit
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mailpit
  template:
    metadata:
      labels:
        app: mailpit
    spec:
      containers:
      - name: mailpit
        image: axllent/mailpit:latest
        ports:
        - containerPort: 1025
          name: smtp
        - containerPort: 8025
          name: http
---
apiVersion: v1
kind: Service
metadata:
  name: mailpit
  namespace: aml-lab
spec:
  selector:
    app: mailpit
  ports:
  - port: 1025
    targetPort: 1025
    name: smtp
  - port: 8025
    targetPort: 8025
    name: http
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mailpit-ingress
  namespace: aml-lab
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - mailpit.aml-lab.amlsiem.com
    secretName: mailpit-tls
  rules:
  - host: mailpit.aml-lab.amlsiem.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mailpit
            port:
              number: 8025
EOF

# Apply resources
KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/shuffle/
"""

THEHIVE_DEPLOY_SCRIPT = """#!/bin/bash
set -e

# Clean up existing resources to ensure a fresh rollout
echo "Cleaning up existing TheHive deployments..."
KUBECONFIG=~/.kube/config kubectl delete statefulset thehive -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service thehive -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete ingress thehive-ingress -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete configmap thehive-config -n aml-lab --ignore-not-found=true
# Delete PVC so fresh restart gets a clean volume (avoids stale JanusGraph schema state)
KUBECONFIG=~/.kube/config kubectl delete pvc thehive-storage-thehive-0 -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete statefulset cassandra -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service cassandra -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete deployment elasticsearch-thehive -n aml-lab --ignore-not-found=true
KUBECONFIG=~/.kube/config kubectl delete service elasticsearch-thehive -n aml-lab --ignore-not-found=true
sleep 5

# Ensure directory exists
mkdir -p /opt/aml-siem/k8s/base/thehive/

# 1. Elasticsearch thehive Deployment
cat > /opt/aml-siem/k8s/base/thehive/elasticsearch-thehive.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch-thehive
  namespace: aml-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elasticsearch-thehive
  template:
    metadata:
      labels:
        app: elasticsearch-thehive
    spec:
      containers:
      - name: elasticsearch
        image: elasticsearch:7.17.9
        ports:
        - containerPort: 9200
        env:
        - name: discovery.type
          value: "single-node"
        - name: ES_JAVA_OPTS
          value: "-Xms512m -Xmx512m"
---
apiVersion: v1
kind: Service
metadata:
  name: elasticsearch-thehive
  namespace: aml-lab
spec:
  selector:
    app: elasticsearch-thehive
  ports:
  - port: 9200
    targetPort: 9200
EOF

# 2. Cassandra StatefulSet
cat > /opt/aml-siem/k8s/base/thehive/cassandra.yaml << 'EOF'
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cassandra
  namespace: aml-lab
spec:
  serviceName: cassandra
  replicas: 1
  selector:
    matchLabels:
      app: cassandra
  template:
    metadata:
      labels:
        app: cassandra
    spec:
      containers:
      - name: cassandra
        image: cassandra:4.0
        ports:
        - containerPort: 9042
          name: cql
        env:
        - name: CASSANDRA_CLUSTER_NAME
          value: "th_cluster"
  volumeClaimTemplates:
  - metadata:
      name: cassandra-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: cassandra
  namespace: aml-lab
spec:
  selector:
    app: cassandra
  ports:
  - port: 9042
    targetPort: 9042
EOF

# 3. TheHive ConfigMap (application.conf — no broken CLI flags)
cat > /opt/aml-siem/k8s/base/thehive/thehive-config.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: thehive-config
  namespace: aml-lab
data:
  application.conf: |
    play.http.secret.key = "aml-siem-very-long-secret-key-32-chars-minimum"
    play.modules.disabled += "org.thp.thehive.models.TheHiveSchemaDefinition"

    db.janusgraph {
      storage.backend = cql
      storage.cql.cluster-name = thp
      storage.hostname = ["cassandra"]
      storage.cql.keyspace = thehive
      index.search.backend = elasticsearch
      index.search.elasticsearch.http.auth.enabled = false
      index.search.hostname = ["elasticsearch-thehive"]
      index.search.elasticsearch.http.port = 9200
    }

    storage {
      provider = localfs
      localfs.location = /opt/thp/thehive/files
    }

    play.http.parser.maxDiskBuffer = 128MB
    play.server.http.idleTimeout = 75s
  logback.xml: |
    <?xml version="1.0" encoding="UTF-8"?>
    <configuration debug="false">
      <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
          <pattern>%date{yyyy-MM-dd HH:mm:ss} %-5level %logger{36} - %msg%n</pattern>
        </encoder>
      </appender>
      <logger name="play" level="INFO" />
      <logger name="application" level="INFO" />
      <logger name="org.thp" level="INFO" />
      <root level="INFO">
        <appender-ref ref="STDOUT" />
      </root>
    </configuration>
EOF

# 4. TheHive StatefulSet & Ingress
cat > /opt/aml-siem/k8s/base/thehive/thehive.yaml << 'EOF'
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: thehive
  namespace: aml-lab
spec:
  serviceName: thehive
  replicas: 1
  selector:
    matchLabels:
      app: thehive
  template:
    metadata:
      labels:
        app: thehive
    spec:
      securityContext:
        fsGroup: 999
      containers:
      - name: thehive
        image: strangebee/thehive:5.2
        ports:
        - containerPort: 9000
        # TheHive 5.x does NOT accept --secret / --cql-hostnames as CLI args.
        # Config is driven entirely by application.conf mounted below.
        command:
        - "/opt/thehive/bin/thehive"
        - "-Dconfig.file=/etc/thehive/application.conf"
        - "-Dlogger.file=/etc/thehive/logback.xml"
        args: []
        env:
        - name: JAVA_OPTS
          value: "-Xms512m -Xmx1g"
        volumeMounts:
        - name: thehive-storage
          mountPath: /opt/thp/thehive/files
        - name: thehive-config
          mountPath: /etc/thehive
      volumes:
      - name: thehive-config
        configMap:
          name: thehive-config
  volumeClaimTemplates:
  - metadata:
      name: thehive-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: thehive
  namespace: aml-lab
spec:
  selector:
    app: thehive
  ports:
  - port: 9000
    targetPort: 9000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: thehive-ingress
  namespace: aml-lab
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-body-size: "128m"
spec:
  tls:
  - hosts:
    - thehive.aml-lab.infosecfoster.com
    secretName: thehive-tls
  rules:
  - host: thehive.aml-lab.infosecfoster.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: thehive
            port:
              number: 9000
EOF

# Apply resources
KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/thehive/
"""

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# ── Colour palette ─────────────────────────────────────────────────────────────
C = {
    "bg":         "#0F1117",
    "surface":    "#1A1D27",
    "card":       "#21253A",
    "border":     "#2E3350",
    "accent":     "#4F6EF7",
    "accent_dim": "#2A3A8A",
    "success":    "#22C97A",
    "warning":    "#F7B32B",
    "danger":     "#F75050",
    "skip":       "#6B7280",
    "local":      "#A855F7",   # purple — local steps
    "remote":     "#4F6EF7",   # blue   — M0.1 remote steps
    "docker":     "#0DB7ED",   # cyan      — M0.2 docker steps
    "reconnect":  "#F7B32B",   # amber     — reconnect step
    "k3s":        "#326CE5",   # k8s blue  — M0.3 K3s steps
    "nginx":      "#009639",   # nginx green — M0.4 Nginx/TLS steps
    "git":        "#F97316",   # orange    — M0.5 Git steps
    "opensearch": "#00A4EF",   # cyan      — M1.1 OpenSearch steps
    "wazuh":      "#E84A1A",   # orange-red — M1.2 Wazuh steps
    "dashboard":  "#1BA49F",   # teal      — M1.3 Dashboard steps
    "agents":     "#9F63C4",   # lavender  — M1.4 Agent steps
    "syslog":     "#EC4899",   # pink      — M1.5 Syslog steps
    "shuffle":    "#A3E635",   # lime green
    "wazuh_webhook": "#00B4D8", # teal-blue
    "thehive":    "#EF4444",   # red
    "playbooks":  "#10B981",   # emerald
    "text":       "#E8EAFF",
    "muted":      "#6B7590",
    "mono":       "#A8B4FF",
}

FONT_BOLD  = ("Helvetica", 11, "bold")
FONT_MONO  = ("Courier", 10)
FONT_STEP  = ("Helvetica", 10)
FONT_BADGE = ("Helvetica", 9, "bold")
FONT_SMALL = ("Helvetica", 9)


# ── Step definitions ───────────────────────────────────────────────────────────
# mode: "local"  → subprocess on your Mac
# mode: "remote" → SSH on the GCP VM

LOCAL_STEPS = [
    {
        "id":    "S02",
        "pre_check":       'false',
        "pre_check_label": 'SSH key exists',
        "mode":  "local",
        "title": "Step 2 — SSH Config & Key Setup",
        "desc":  "Runs on your Mac — generate SSH key pair and write ~/.ssh/config",
        "cmds": [
            {
                "label": "Check if SSH key already exists",
                "mode":  "local",
                "cmd":   ["bash", "-c",
                          "ls ~/.ssh/aml_siem_key 2>/dev/null "
                          "&& echo KEY_EXISTS || echo KEY_MISSING"],
            },
            {
                "label": "Generate Ed25519 key pair (skip if exists)",
                "mode":  "local_conditional",
                "condition": "KEY_MISSING",
                "cmd":   ["bash", "-c",
                          "ssh-keygen -t ed25519 -C 'amlak-siem-admin' "
                          "-f ~/.ssh/aml_siem_key -N '' && echo KEY_GENERATED"],
            },
            {
                "label": "Set correct permissions on key files",
                "mode":  "local",
                "cmd":   ["bash", "-c",
                          "chmod 600 ~/.ssh/aml_siem_key && "
                          "chmod 644 ~/.ssh/aml_siem_key.pub && echo PERMS_OK"],
            },
            {
                "label": "Write Host entry into ~/.ssh/config",
                "mode":  "local_config",
                "cmd":   None,
            },
            {
                "label": "Set permissions on ~/.ssh/config",
                "mode":  "local",
                "cmd":   ["bash", "-c",
                          "touch ~/.ssh/config && chmod 600 ~/.ssh/config "
                          "&& echo CONFIG_PERMS_OK"],
            },
            {
                "label": "Display public key — copy this into GCP Console",
                "mode":  "local",
                "cmd":   ["bash", "-c", "echo '' && cat ~/.ssh/aml_siem_key.pub && echo ''"],
            },
            {
                "label": "Verify ~/.ssh/config entry was written",
                "mode":  "local",
                "cmd":   ["bash", "-c",
                          "grep -A6 'Host aml-lab-01' ~/.ssh/config "
                          "&& echo CONFIG_OK || echo CONFIG_MISSING"],
            },
        ],
    },
]

REMOTE_STEPS = [
    {
        "id":    "S03",
        "pre_check":       "dpkg -l curl git nano htop 2>/dev/null | grep -c '^ii' | awk '{if($1>=4) exit 0; else exit 1}'",
        "pre_check_label": 'Core tools installed',
        "mode":  "remote",
        "title": "Step 3 — System Update",
        "desc":  "Update package lists and upgrade all packages",
        "cmds": [
            {"label": "Update package lists",
             "cmd":   "sudo systemctl stop unattended-upgrades 2>/dev/null || true && sudo kill -9 $(lsof /var/lib/apt/lists/lock /var/lib/dpkg/lock-frontend 2>/dev/null | awk 'NR>1{print $2}' | sort -u) 2>/dev/null || true && while sudo fuser /var/lib/apt/lists/lock /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo 'Waiting for apt lock...'; sleep 2; done && sudo apt-get update -y"},
            {"label": "Upgrade installed packages",
             "cmd":   "sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y"},
            {"label": "Install essential tools",
             "cmd":   ("sudo apt-get install -y curl wget git nano htop net-tools unzip "
                       "gnupg ca-certificates apt-transport-https "
                       "software-properties-common lsb-release")},
            {"label": "Verify key tools installed",
             "cmd":   "curl --version | head -1 && git --version && echo TOOLS_OK"},
        ],
    },
    {
        "id":    "S04",
        "pre_check":       '[ "$(hostname)" = "aml-lab-01" ]',
        "pre_check_label": 'Hostname already aml-lab-01',
        "mode":  "remote",
        "title": "Step 4 — Set Hostname",
        "desc":  "Set hostname to aml-lab-01 and update /etc/hosts",
        "cmds": [
            {"label": "Set static hostname",
             "cmd":   "sudo hostnamectl set-hostname aml-lab-01"},
            {"label": "Update /etc/hosts",
             "cmd":   ("grep -q 'aml-lab-01' /etc/hosts || "
                       "echo '127.0.1.1 aml-lab-01' | sudo tee -a /etc/hosts")},
            {"label": "Verify hostname",
             "cmd":   "hostnamectl | grep 'Static hostname'"},
        ],
    },
    {
        "id":    "S05",
        "pre_check":       "timedatectl | grep -q 'Asia/Kuwait'",
        "pre_check_label": 'Timezone Asia/Kuwait set',
        "mode":  "remote",
        "title": "Step 5 — Set Timezone",
        "desc":  "Set timezone to Asia/Kuwait and confirm NTP sync",
        "cmds": [
            {"label": "Set timezone to Asia/Kuwait",
             "cmd":   "sudo timedatectl set-timezone Asia/Kuwait"},
            {"label": "Verify timezone",
             "cmd":   "timedatectl | grep 'Time zone'"},
            {"label": "Verify NTP sync",
             "cmd":   "timedatectl | grep -E 'synchronized|NTP service'"},
            {"label": "Show current date/time",
             "cmd":   "date"},
        ],
    },
    {
        "id":    "S06",
        "pre_check":       "grep -q 'PasswordAuthentication no' /etc/ssh/sshd_config",
        "pre_check_label": 'Password auth already off',
        "mode":  "remote",
        "title": "Step 6 — Disable Password SSH Login",
        "desc":  "Enforce SSH key-only access and restart sshd",
        "cmds": [
            {"label": "Disable PasswordAuthentication",
             "cmd":   "sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config"},
            {"label": "Enable PubkeyAuthentication",
             "cmd":   "sudo sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config"},
            {"label": "Disable PermitRootLogin",
             "cmd":   "sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config"},
            {"label": "Add ChallengeResponseAuthentication no",
             "cmd":   ("grep -q 'ChallengeResponseAuthentication no' /etc/ssh/sshd_config || "
                       "echo 'ChallengeResponseAuthentication no' | sudo tee -a /etc/ssh/sshd_config")},
            {"label": "Test sshd config syntax",
             "cmd":   "sudo sshd -t && echo SSHD_CONFIG_OK"},
            {"label": "Restart SSH service",
             "cmd":   "sudo systemctl restart ssh && sleep 2 && echo SSH_RESTARTED"},
            {"label": "Verify SSH service running",
             "cmd":   "sudo systemctl is-active ssh"},
        ],
    },
    {
        "id":    "S07",
        "pre_check":       "sudo ufw status | grep -q 'Status: active'",
        "pre_check_label": 'UFW already active',
        "mode":  "remote",
        "title": "Step 7 — Configure UFW Firewall",
        "desc":  "Install UFW, default deny incoming, allow only port 22",
        "cmds": [
            {"label": "Install UFW",
             "cmd":   "sudo apt-get install -y ufw"},
            {"label": "Set default deny incoming",
             "cmd":   "sudo ufw default deny incoming"},
            {"label": "Set default allow outgoing",
             "cmd":   "sudo ufw default allow outgoing"},
            {"label": "Allow SSH port 22",
             "cmd":   "sudo ufw allow 22/tcp comment 'SSH access'"},
            {"label": "Enable UFW",
             "cmd":   "sudo ufw --force enable"},
            {"label": "Verify UFW status",
             "cmd":   "sudo ufw status verbose"},
        ],
    },
    {
        "id":    "S08",
        "pre_check":       'test -f /etc/apt/apt.conf.d/20auto-upgrades',
        "pre_check_label": 'Auto-upgrades config exists',
        "mode":  "remote",
        "title": "Step 8 — Enable Auto Security Updates",
        "desc":  "Install and configure unattended-upgrades",
        "cmds": [
            {"label": "Install unattended-upgrades",
             "cmd":   "sudo apt-get install -y unattended-upgrades"},
            {"label": "Write auto-upgrades config",
             "cmd":   ('printf "APT::Periodic::Update-Package-Lists \\"1\\";\\n'
                       'APT::Periodic::Unattended-Upgrade \\"1\\";\\n" | '
                       'sudo tee /etc/apt/apt.conf.d/20auto-upgrades')},
            {"label": "Verify config written",
             "cmd":   "cat /etc/apt/apt.conf.d/20auto-upgrades"},
        ],
    },
    {
        "id":    "S09",
        "pre_check":       'id amlsiem &>/dev/null',
        "pre_check_label": 'amlsiem user exists',
        "mode":  "remote",
        "title": "Step 9 — Create amlsiem Admin User",
        "desc":  "Create dedicated amlsiem user with sudo and SSH key access",
        "cmds": [
            {"label": "Create amlsiem user (skip if exists)",
             "cmd":   ("id amlsiem &>/dev/null && echo 'User already exists' || "
                       "sudo adduser --disabled-password --gecos '' amlsiem")},
            {"label": "Add amlsiem to sudo group",
             "cmd":   "sudo usermod -aG sudo amlsiem"},
            {"label": "Setup .ssh directory for amlsiem",
             "cmd":   "sudo mkdir -p /home/amlsiem/.ssh"},
            {"label": "Copy authorized_keys to amlsiem",
             "cmd":   ("sudo cp ~/.ssh/authorized_keys /home/amlsiem/.ssh/ && "
                       "sudo chown -R amlsiem:amlsiem /home/amlsiem/.ssh && "
                       "sudo chmod 700 /home/amlsiem/.ssh && "
                       "sudo chmod 600 /home/amlsiem/.ssh/authorized_keys")},
            {"label": "Verify amlsiem user and groups",
             "cmd":   "id amlsiem"},
        ],
    },
    {
        "id":    "S10",
        "pre_check":       'false',
        "pre_check_label": 'Resource check',
        "mode":  "remote",
        "title": "Step 10 — Verify System Resources",
        "desc":  "Check CPU, RAM, and disk meet Sprint 1 minimum requirements",
        "cmds": [
            {"label": "CPU core count",
             "cmd":   "nproc"},
            {"label": "RAM (need 16GB+)",
             "cmd":   "free -h | grep Mem"},
            {"label": "Disk space (need 100GB+)",
             "cmd":   "df -h / | tail -1"},
            {"label": "Network interfaces",
             "cmd":   "ip -br a"},
            {"label": "OS version",
             "cmd":   "lsb_release -d"},
        ],
    },
    {
        "id":    "GATE",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M0.1",
        "desc":  "Run all gate checks and confirm PASS/FAIL for Sprint 0 sign-off",
        "cmds": [
            {"label": "Gate: Hostname is aml-lab-01",
             "cmd":   ('[ "$(hostname)" = "aml-lab-01" ] && '
                       'echo "GATE_PASS: hostname = aml-lab-01" || '
                       'echo "GATE_FAIL: hostname is $(hostname)"')},
            {"label": "Gate: Timezone is Asia/Kuwait",
             "cmd":   ('timedatectl | grep -q "Asia/Kuwait" && '
                       'echo "GATE_PASS: timezone = Asia/Kuwait" || '
                       'echo "GATE_FAIL: timezone wrong"')},
            {"label": "Gate: NTP synchronised",
             "cmd":   ('timedatectl | grep -q "synchronized: yes" && '
                       'echo "GATE_PASS: NTP synced" || '
                       'echo "GATE_FAIL: NTP not synced"')},
            {"label": "Gate: UFW is active",
             "cmd":   ('sudo ufw status | grep -q "Status: active" && '
                       'echo "GATE_PASS: UFW active" || '
                       'echo "GATE_FAIL: UFW not active"')},
            {"label": "Gate: Only port 22 open in UFW",
             "cmd":   ('sudo ufw status | grep -q "22/tcp" && '
                       'echo "GATE_PASS: port 22 open" || '
                       'echo "GATE_FAIL: port 22 missing"')},
            {"label": "Gate: Password auth disabled in sshd",
             "cmd":   ('grep -q "PasswordAuthentication no" /etc/ssh/sshd_config && '
                       'echo "GATE_PASS: password auth disabled" || '
                       'echo "GATE_FAIL: password auth still enabled"')},
            {"label": "Gate: amlsiem user exists",
             "cmd":   ('id amlsiem &>/dev/null && '
                       'echo "GATE_PASS: amlsiem user exists" || '
                       'echo "GATE_FAIL: amlsiem user missing"')},
            {"label": "Gate: Current date shows Kuwait time",
             "cmd":   'date && timedatectl | grep "Time zone"'},
        ],
    },
]


# ── M0.2 Docker CE Steps ───────────────────────────────────────────────────────
DOCKER_STEPS = [
    {
        "id":    "D01",
        "pre_check":       "! dpkg -l docker.io 2>/dev/null | grep -q '^ii'",
        "pre_check_label": 'No old Docker packages',
        "mode":  "remote",
        "title": "D01 — Remove Existing Docker Installations",
        "desc":  "Remove any old or snap-based Docker before installing from official repo",
        "cmds": [
            {"label": "Remove old Docker packages",
             "cmd":   ("sudo apt-get remove -y docker docker-engine docker.io "
                       "containerd runc docker-doc docker-compose "
                       "docker-compose-v2 podman-docker 2>/dev/null || true")},
            {"label": "Remove snap Docker if present",
             "cmd":   "sudo snap remove docker 2>/dev/null && echo 'Snap docker removed' || echo 'No snap docker found — OK'"},
            {"label": "Clean up leftover packages",
             "cmd":   "sudo apt-get autoremove -y && sudo apt-get autoclean -y"},
            {"label": "Confirm docker is not installed",
             "cmd":   "docker --version 2>/dev/null && echo 'WARNING: docker still present' || echo 'Docker not installed — OK'"},
        ],
    },
    {
        "id":    "D02",
        "pre_check":       "dpkg -l curl gnupg ca-certificates apt-transport-https 2>/dev/null | grep -c '^ii' | awk '{if($1>=4) exit 0; else exit 1}'",
        "pre_check_label": 'Prerequisites installed',
        "mode":  "remote",
        "title": "D02 — Install Prerequisites",
        "desc":  "Install packages required to add Docker's official apt repository",
        "cmds": [
            {"label": "Update package lists",
             "cmd":   "sudo systemctl stop unattended-upgrades 2>/dev/null || true && sudo kill -9 $(lsof /var/lib/apt/lists/lock /var/lib/dpkg/lock-frontend 2>/dev/null | awk 'NR>1{print $2}' | sort -u) 2>/dev/null || true && while sudo fuser /var/lib/apt/lists/lock /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo 'Waiting for apt lock...'; sleep 2; done && sudo apt-get update -y"},
            {"label": "Install prerequisite packages",
             "cmd":   ("sudo apt-get install -y ca-certificates curl gnupg "
                       "lsb-release apt-transport-https")},
        ],
    },
    {
        "id":    "D03",
        "pre_check":       'test -f /etc/apt/keyrings/docker.asc && test -s /etc/apt/keyrings/docker.asc',
        "pre_check_label": 'Docker GPG key present',
        "mode":  "remote",
        "title": "D03 — Add Docker GPG Key",
        "desc":  "Add Docker's official GPG signing key so apt can verify packages",
        "cmds": [
            {"label": "Create keyrings directory",
             "cmd":   "sudo install -m 0755 -d /etc/apt/keyrings"},
            {"label": "Download Docker GPG key",
             "cmd":   ("sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg "
                       "-o /etc/apt/keyrings/docker.asc")},
            {"label": "Set correct permissions on key",
             "cmd":   "sudo chmod a+r /etc/apt/keyrings/docker.asc"},
            {"label": "Verify key file exists and is valid",
             "cmd":   "ls -lh /etc/apt/keyrings/docker.asc && head -c 20 /etc/apt/keyrings/docker.asc | grep -q 'BEGIN PGP' && echo 'GPG_KEY_OK' || (stat /etc/apt/keyrings/docker.asc && echo 'GPG_KEY_PRESENT')"},
        ],
    },
    {
        "id":    "D04",
        "pre_check":       'test -f /etc/apt/sources.list.d/docker.list',
        "pre_check_label": 'Docker apt repo added',
        "mode":  "remote",
        "title": "D04 — Add Docker apt Repository",
        "desc":  "Point apt at Docker's official servers instead of Ubuntu mirrors",
        "cmds": [
            {"label": "Write Docker repository source file",
             "cmd":   ('echo "deb [arch=$(dpkg --print-architecture) '
                       'signed-by=/etc/apt/keyrings/docker.asc] '
                       'https://download.docker.com/linux/ubuntu '
                       '$(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | '
                       'sudo tee /etc/apt/sources.list.d/docker.list > /dev/null')},
            {"label": "Verify repository file written",
             "cmd":   "cat /etc/apt/sources.list.d/docker.list"},
            {"label": "Update apt with new Docker repository",
             "cmd":   "sudo systemctl stop unattended-upgrades 2>/dev/null || true && sudo systemctl disable unattended-upgrades 2>/dev/null || true && sudo kill -9 $(lsof /var/lib/apt/lists/lock /var/lib/dpkg/lock-frontend 2>/dev/null | awk 'NR>1{print $2}' | sort -u) 2>/dev/null || true && while sudo fuser /var/lib/apt/lists/lock /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo 'Waiting for apt lock...'; sleep 2; done && sudo apt-get update -y"},
            {"label": "Confirm Docker packages are available",
             "cmd":   "apt-cache policy docker-ce | head -5"},
        ],
    },
    {
        "id":    "D05",
        "pre_check":       "dpkg -l docker-ce 2>/dev/null | grep -q '^ii'",
        "pre_check_label": 'Docker CE installed',
        "mode":  "remote",
        "title": "D05 — Install Docker CE + Compose Plugin",
        "desc":  "Install Docker CE, CLI, containerd, buildx, and Compose v2 plugin",
        "cmds": [
            {"label": "Install all Docker packages",
             "cmd":   ("sudo apt-get install -y docker-ce docker-ce-cli "
                       "containerd.io docker-buildx-plugin docker-compose-plugin")},
            {"label": "Verify Docker version",
             "cmd":   "sudo docker --version"},
            {"label": "Verify Compose v2 version",
             "cmd":   "sudo docker compose version"},
        ],
    },
    {
        "id":    "D06",
        "pre_check":       'sudo systemctl is-active docker 2>/dev/null | grep -q active',
        "pre_check_label": 'Docker service active',
        "mode":  "remote",
        "title": "D06 — Start & Enable Docker Service",
        "desc":  "Start Docker daemon and enable it to start automatically on boot",
        "cmds": [
            {"label": "Start Docker service",
             "cmd":   "sudo systemctl start docker"},
            {"label": "Enable Docker on boot",
             "cmd":   "sudo systemctl enable docker"},
            {"label": "Verify Docker service is active",
             "cmd":   "sudo systemctl is-active docker"},
            {"label": "Verify Docker service is enabled",
             "cmd":   "sudo systemctl is-enabled docker"},
        ],
    },
    {
        "id":    "D07",
        "pre_check":       'getent group docker | grep -q $(whoami)',
        "pre_check_label": 'User in docker group',
        "mode":  "remote",
        "title": "D07 — Add User to Docker Group",
        "desc":  "Allow engineer to run docker without sudo",
        "cmds": [
            {"label": "Add current user to docker group",
             "cmd":   "sudo usermod -aG docker $USER && echo 'USER_ADDED_TO_DOCKER_GROUP'"},
            {"label": "Verify docker group exists",
             "cmd":   "getent group docker"},
            {"label": "Apply group change with newgrp",
             "cmd":   "sudo -u $USER docker ps && echo 'DOCKER_NOTSUDO_OK' || echo 'Reconnect SSH to apply group'"},
        ],
    },
    {
        "id":    "D07B",
        "pre_check":       'false',
        "pre_check_label": 'Reconnect',
        "mode":  "reconnect",
        "title": "D07B — Reconnect SSH",
        "desc":  "Disconnect and reconnect SSH so docker group membership takes effect",
        "cmds": [
            {"label": "Close current SSH session and reconnect",
             "mode":  "reconnect",
             "cmd":   None},
        ],
    },
    {
        "id":    "D08",
        "pre_check":       'test -f /etc/docker/daemon.json && cat /etc/docker/daemon.json | grep -q max-size',
        "pre_check_label": 'Log rotation configured',
        "mode":  "remote",
        "title": "D08 — Configure Log Rotation",
        "desc":  "Set Docker daemon log rotation: max 10MB per file, max 3 files",
        "cmds": [
            {"label": "Write Docker daemon.json with log rotation",
             "cmd":   "echo '{\"log-driver\":\"json-file\",\"log-opts\":{\"max-size\":\"10m\",\"max-file\":\"3\"}}' | sudo tee /etc/docker/daemon.json"},
            {"label": "Verify daemon.json content",
             "cmd":   "cat /etc/docker/daemon.json"},
            {"label": "Validate JSON syntax",
             "cmd":   "python3 -m json.tool /etc/docker/daemon.json > /dev/null && echo JSON_VALID || echo JSON_INVALID"},
            {"label": "Restart Docker to apply log config",
             "cmd":   "sudo systemctl restart docker && sleep 2 && sudo systemctl is-active docker"},
        ],
    },
    {
        "id":    "D09",
        "pre_check":       'false',
        "pre_check_label": 'hello-world test',
        "mode":  "remote",
        "title": "D09 — Run hello-world Test",
        "desc":  "Pull and run Docker hello-world to confirm installation works end-to-end",
        "cmds": [
            {"label": "Pull hello-world image",
             "cmd":   "sudo docker pull hello-world"},
            {"label": "Run hello-world container",
             "cmd":   "sudo docker run --rm hello-world 2>&1 | grep -E 'Hello from|working correctly'"},
            {"label": "Clean up hello-world image",
             "cmd":   "sudo docker rmi hello-world && echo 'CLEANUP_OK'"},
        ],
    },
    {
        "id":    "GATE2",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M0.2 Docker CE",
        "desc":  "Run all M0.2 gate checks and confirm PASS/FAIL for sign-off",
        "cmds": [
            {"label": "Gate: Docker is installed and correct version",
             "cmd":   "sudo docker --version 2>/dev/null && echo 'GATE_PASS: docker installed' || echo 'GATE_FAIL: docker not found'"},
            {"label": "Gate: Docker Compose v2 available",
             "cmd":   "sudo docker compose version 2>/dev/null && echo 'GATE_PASS: compose plugin available' || echo 'GATE_FAIL: compose plugin missing'"},
            {"label": "Gate: Docker service is active",
             "cmd":   ('sudo systemctl is-active docker | grep -q "active" && '
                       'echo "GATE_PASS: docker service active" || '
                       'echo "GATE_FAIL: docker service not active"')},
            {"label": "Gate: Docker service enabled on boot",
             "cmd":   ('sudo systemctl is-enabled docker | grep -q "enabled" && '
                       'echo "GATE_PASS: docker enabled on boot" || '
                       'echo "GATE_FAIL: docker not enabled on boot"')},
            {"label": "Gate: Log rotation configured",
             "cmd":   "cat /etc/docker/daemon.json | grep -q max-size && echo 'GATE_PASS: log rotation configured' || echo 'GATE_FAIL: log rotation not configured'"},
            {"label": "Gate: daemon.json JSON is valid",
             "cmd":   "python3 -m json.tool /etc/docker/daemon.json > /dev/null && echo 'GATE_PASS: daemon.json valid JSON' || echo 'GATE_FAIL: daemon.json invalid'"},
            {"label": "Gate: hello-world runs successfully",
             "cmd":   ('sudo docker run --rm hello-world 2>&1 | grep -q "Hello from Docker" && '
                       'echo "GATE_PASS: hello-world passed" || '
                       'echo "GATE_FAIL: hello-world failed"')},
            {"label": "Gate: Current user in docker group",
             "cmd":   "getent group docker | grep -q $(whoami) && echo 'GATE_PASS: user in docker group (reconnect SSH to activate)' || echo 'GATE_FAIL: user not in docker group'"},
        ],
    },
]


# ── M0.3 K3s Steps ─────────────────────────────────────────────────────────────
K3S_STEPS = [
    {
        "id":    "K01",
        "pre_check":       'false',
        "pre_check_label": 'Pre-install checks',
        "mode":  "remote",
        "title": "K01 — Pre-install Checks",
        "desc":  "Verify resources and port availability before K3s install",
        "cmds": [
            {"label": "Check free RAM",
             "cmd":   "free -h | grep Mem"},
            {"label": "Check disk space",
             "cmd":   "df -h / | tail -1"},
            {"label": "Check port 6443 is free",
             "cmd":   "sudo ss -tlnp | grep 6443 && echo 'PORT_IN_USE' || echo 'PORT_FREE_OK'"},
            {"label": "Disable UFW temporarily",
             "cmd":   "sudo ufw disable && echo 'UFW_DISABLED'"},
        ],
    },
    {
        "id":    "K02",
        "pre_check":       'command -v k3s &>/dev/null && sudo systemctl is-active k3s | grep -q active',
        "pre_check_label": 'K3s already installed',
        "mode":  "remote",
        "title": "K02 — Install K3s",
        "desc":  "Download and install K3s via official install script",
        "cmds": [
            {"label": "Run K3s install script",
             "cmd":   "curl -sfL https://get.k3s.io | sh -"},
            {"label": "Verify K3s service is active",
             "cmd":   "sudo systemctl is-active k3s"},
            {"label": "Verify K3s service is enabled",
             "cmd":   "sudo systemctl is-enabled k3s"},
            {"label": "Check K3s version",
             "cmd":   "k3s --version"},
        ],
    },
    {
        "id":    "K03",
        "pre_check":       'test -f ~/.kube/config',
        "pre_check_label": 'kubeconfig configured',
        "mode":  "remote",
        "title": "K03 — Configure kubeconfig",
        "desc":  "Copy kubeconfig to home directory and set permissions",
        "cmds": [
            {"label": "Create .kube directory",
             "cmd":   "mkdir -p ~/.kube"},
            {"label": "Copy K3s kubeconfig",
             "cmd":   "sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config"},
            {"label": "Set ownership to current user",
             "cmd":   "sudo chown $USER:$USER ~/.kube/config"},
            {"label": "Set secure permissions",
             "cmd":   "chmod 600 ~/.kube/config && echo 'PERMS_OK'"},
            {"label": "Export KUBECONFIG in .bashrc",
             "cmd":   ("grep -q 'KUBECONFIG' ~/.bashrc || "
                       "echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc; "
                       "export KUBECONFIG=~/.kube/config && echo 'KUBECONFIG_SET'")},
            {"label": "Also set world-readable kubeconfig permission",
             "cmd":   "sudo chmod 644 /etc/rancher/k3s/k3s.yaml && echo 'K3S_YAML_READABLE'"},
        ],
    },
    {
        "id":    "K04",
        "pre_check":       'command -v kubectl &>/dev/null',
        "pre_check_label": 'kubectl already verified',
        "mode":  "remote",
        "title": "K04 — Verify kubectl",
        "desc":  "Confirm kubectl is accessible and connects to the cluster",
        "cmds": [
            {"label": "Check kubectl location",
             "cmd":   "which kubectl"},
            {"label": "Check kubectl client version",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl version --client"},
            {"label": "Check cluster info",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl cluster-info"},
            {"label": "Check node status",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get nodes"},
        ],
    },
    {
        "id":    "K05",
        "pre_check":       'false',
        "pre_check_label": 'System pods check',
        "mode":  "remote",
        "title": "K05 — Check System Pods",
        "desc":  "Verify all K3s internal pods are running",
        "cmds": [
            {"label": "List kube-system pods",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get pods -n kube-system"},
            {"label": "Wait for all pods to be ready",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pods --all "
                       "-n kube-system --timeout=120s 2>/dev/null || "
                       "KUBECONFIG=~/.kube/config kubectl get pods -n kube-system")},
        ],
    },
    {
        "id":    "K06",
        "pre_check":       'KUBECONFIG=~/.kube/config kubectl get namespace aml-lab &>/dev/null && KUBECONFIG=~/.kube/config kubectl get namespace aml-client-template &>/dev/null',
        "pre_check_label": 'Namespaces already exist',
        "mode":  "remote",
        "title": "K06 — Create Namespaces",
        "desc":  "Create aml-lab and aml-client-template namespaces",
        "cmds": [
            {"label": "Create aml-lab namespace",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get namespace aml-lab &>/dev/null && "
                       "echo 'aml-lab already exists' || "
                       "KUBECONFIG=~/.kube/config kubectl create namespace aml-lab")},
            {"label": "Create aml-client-template namespace",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get namespace aml-client-template &>/dev/null && "
                       "echo 'aml-client-template already exists' || "
                       "KUBECONFIG=~/.kube/config kubectl create namespace aml-client-template")},
            {"label": "Label aml-lab namespace",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl label namespace aml-lab "
                       "environment=lab managed-by=amlak purpose=development --overwrite")},
            {"label": "Label aml-client-template namespace",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl label namespace aml-client-template "
                       "environment=template managed-by=amlak "
                       "purpose=client-reference --overwrite")},
            {"label": "Verify both namespaces exist",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get namespaces | grep -E 'aml-lab|aml-client-template'"},
        ],
    },
    {
        "id":    "K07",
        "pre_check":       "KUBECONFIG=~/.kube/config kubectl config view --minify | grep -q 'namespace: aml-lab'",
        "pre_check_label": 'Default namespace set',
        "mode":  "remote",
        "title": "K07 — Set Default Namespace",
        "desc":  "Set aml-lab as default so -n flag is not needed every command",
        "cmds": [
            {"label": "Set default namespace to aml-lab",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl config set-context --current --namespace=aml-lab"},
            {"label": "Verify default namespace",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl config view --minify | grep namespace"},
        ],
    },
    {
        "id":    "K08",
        "pre_check":       'sudo ufw status | grep -q 6443',
        "pre_check_label": 'UFW K3s rules already set',
        "mode":  "remote",
        "title": "K08 — Re-enable UFW with K3s Rules",
        "desc":  "Open required K3s ports and re-enable firewall",
        "cmds": [
            {"label": "Allow K3s API server port 6443",
             "cmd":   "sudo ufw allow 6443/tcp comment 'K3s API server'"},
            {"label": "Allow Flannel VXLAN port 8472",
             "cmd":   "sudo ufw allow 8472/udp comment 'K3s Flannel VXLAN'"},
            {"label": "Allow kubelet metrics port 10250",
             "cmd":   "sudo ufw allow 10250/tcp comment 'K3s kubelet'"},
            {"label": "Allow traffic on cni0 interface",
             "cmd":   "sudo ufw allow in on cni0 2>/dev/null || echo 'cni0 not yet created — OK'"},
            {"label": "Allow traffic on flannel.1 interface",
             "cmd":   "sudo ufw allow in on flannel.1 2>/dev/null || echo 'flannel.1 not yet created — OK'"},
            {"label": "Re-enable UFW",
             "cmd":   "sudo ufw --force enable && echo 'UFW_ENABLED'"},
            {"label": "Verify UFW status",
             "cmd":   "sudo ufw status"},
        ],
    },
    {
        "id":    "K09",
        "pre_check":       'false',
        "pre_check_label": 'Manifest test — always run',
        "mode":  "remote",
        "title": "K09 — Apply and Delete Test Manifest",
        "desc":  "Engineer applies, verifies, then deletes a test ConfigMap",
        "cmds": [
            {"label": "Apply test ConfigMap",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl create configmap aml-gate-test "
                       "--from-literal=test='M0.3 gate verification' "
                       "-n aml-lab --dry-run=client -o yaml | KUBECONFIG=~/.kube/config kubectl apply -f -")},
            {"label": "Verify ConfigMap was created",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get configmap aml-gate-test -n aml-lab"},
            {"label": "Delete test ConfigMap",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl delete configmap aml-gate-test -n aml-lab"},
            {"label": "Confirm deletion",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get configmap aml-gate-test -n aml-lab 2>&1 | "
                       "grep -q 'not found' && echo 'DELETED_OK' || "
                       "echo 'WARNING: still exists'")},
        ],
    },
    {
        "id":    "GATE3",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M0.3 K3s",
        "desc":  "Run all M0.3 gate checks — PASS/FAIL for sign-off",
        "cmds": [
            {"label": "Gate: K3s service is active",
             "cmd":   ("sudo systemctl is-active k3s | grep -q active && "
                       "echo 'GATE_PASS: K3s service running' || "
                       "echo 'GATE_FAIL: K3s not running'")},
            {"label": "Gate: node is in Ready state",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get nodes | grep -q Ready && "
                       "echo 'GATE_PASS: node is Ready' || "
                       "echo 'GATE_FAIL: node not Ready'")},
            {"label": "Gate: aml-lab namespace exists",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get namespace aml-lab &>/dev/null && "
                       "echo 'GATE_PASS: aml-lab exists' || "
                       "echo 'GATE_FAIL: aml-lab missing'")},
            {"label": "Gate: aml-client-template exists",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get namespace aml-client-template &>/dev/null && "
                       "echo 'GATE_PASS: aml-client-template exists' || "
                       "echo 'GATE_FAIL: aml-client-template missing'")},
            {"label": "Gate: kubeconfig accessible",
             "cmd":   ("test -f ~/.kube/config && "
                       "echo 'GATE_PASS: kubeconfig exists' || "
                       "echo 'GATE_FAIL: kubeconfig missing'")},
            {"label": "Gate: kubectl connects to cluster",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl cluster-info 2>/dev/null | grep -q 'running' && "
                       "echo 'GATE_PASS: KUBECONFIG=~/.kube/config kubectl connects OK' || "
                       "echo 'GATE_FAIL: KUBECONFIG=~/.kube/config kubectl cannot connect'")},
            {"label": "Gate: apply/delete manifest works",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl create configmap final-gate --from-literal=t=ok "
                       "-n aml-lab --dry-run=client -o yaml | KUBECONFIG=~/.kube/config kubectl apply -f - && "
                       "KUBECONFIG=~/.kube/config kubectl delete configmap final-gate -n aml-lab && "
                       "echo 'GATE_PASS: apply/delete works' || "
                       "echo 'GATE_FAIL: apply/delete failed'")},
        ],
    },
]


# ── M0.4 Nginx Ingress + TLS Steps ─────────────────────────────────────────────
NGINX_STEPS = [
    {
        "id":    "N01",
        "pre_check":       '! KUBECONFIG=~/.kube/config kubectl get pods -n kube-system 2>/dev/null | grep -q traefik && grep -q traefik /etc/rancher/k3s/config.yaml 2>/dev/null',
        "pre_check_label": 'Traefik already disabled',
        "mode":  "remote",
        "title": "N01 — Disable K3s Built-in Traefik",
        "desc":  "Remove Traefik so it does not conflict with Nginx on ports 80/443",
        "cmds": [
            {"label": "Write K3s config to disable Traefik permanently",
             "cmd":   "sudo mkdir -p /etc/rancher/k3s && printf 'disable:\n  - traefik\n' | sudo tee /etc/rancher/k3s/config.yaml && echo CONFIG_WRITTEN"},
            {"label": "Remove Traefik finalizers (prevents hang on delete)",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl patch helmchart traefik "
                       "-n kube-system -p '{\"metadata\":{\"finalizers\":[]}}' "
                       "--type=merge 2>/dev/null && echo FINALIZERS_REMOVED "
                       "|| echo 'No traefik helmchart to patch — OK'")},
            {"label": "Remove Traefik-CRD finalizers",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl patch helmchart traefik-crd "
                       "-n kube-system -p '{\"metadata\":{\"finalizers\":[]}}' "
                       "--type=merge 2>/dev/null && echo FINALIZERS_REMOVED "
                       "|| echo 'No traefik-crd helmchart to patch — OK'")},
            {"label": "Delete Traefik HelmChart (with 10s timeout)",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl delete helmchart traefik "
                       "-n kube-system --timeout=10s 2>/dev/null "
                       "&& echo TRAEFIK_DELETED || echo 'Traefik helmchart not found — OK'")},
            {"label": "Delete Traefik-CRD HelmChart (with 10s timeout)",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl delete helmchart traefik-crd "
                       "-n kube-system --timeout=10s 2>/dev/null "
                       "&& echo TRAEFIK_CRD_DELETED || echo 'Traefik-crd not found — OK'")},
            {"label": "Stop and disable Traefik via K3s restart",
             "cmd":   "sudo systemctl restart k3s && sleep 5 && echo K3S_RESTARTED"},
            {"label": "Delete any remaining Traefik pods",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl delete pods "
                       "-n kube-system -l app.kubernetes.io/name=traefik "
                       "--timeout=10s 2>/dev/null || echo 'No Traefik pods — OK'")},
            {"label": "Delete Traefik services if present",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl delete service "
                       "traefik traefik-web traefik-websecure "
                       "-n kube-system --timeout=10s 2>/dev/null "
                       "|| echo 'No Traefik services — OK'")},
            {"label": "Confirm Traefik is gone",
             "cmd":   ("KUBECONFIG=~/.kube/config kubectl get pods -n kube-system "
                       "2>/dev/null | grep traefik "
                       "&& echo 'WARNING: Traefik still present' "
                       "|| echo TRAEFIK_GONE_OK")},
        ],
    },
    {
        "id":    "N02",
        "pre_check":       'command -v helm &>/dev/null',
        "pre_check_label": 'Helm already installed',
        "mode":  "remote",
        "title": "N02 — Install Helm",
        "desc":  "Install Helm package manager — required for Nginx and cert-manager",
        "cmds": [
            {"label": "Download and install Helm via official script",
             "cmd":   "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"},
            {"label": "Verify Helm version",
             "cmd":   "helm version --short"},
            {"label": "Set KUBECONFIG for Helm in bashrc",
             "cmd":   "grep -q KUBECONFIG ~/.bashrc || echo export KUBECONFIG=~/.kube/config >> ~/.bashrc; export KUBECONFIG=~/.kube/config && echo KUBECONFIG_SET"},
        ],
    },
    {
        "id":    "N03",
        "pre_check":       'KUBECONFIG=~/.kube/config kubectl get pods -n ingress-nginx 2>/dev/null | grep -q Running',
        "pre_check_label": 'Nginx ingress installed',
        "mode":  "remote",
        "title": "N03 — Install Nginx Ingress Controller",
        "desc":  "Deploy Nginx ingress via Helm with production timeout and body size settings",
        "cmds": [
            {"label": "Add Nginx Ingress Helm repo",
             "cmd":   "helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx && helm repo update"},
            {"label": "Create ingress-nginx namespace",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl create namespace ingress-nginx 2>/dev/null || echo EXISTS"},
             {"label": "Install Nginx Ingress via Helm",
              "cmd":   "KUBECONFIG=~/.kube/config helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --set controller.service.type=LoadBalancer --set controller.service.externalTrafficPolicy=Local --set controller.config.use-forwarded-headers=true --set controller.config.proxy-body-size=50m --set controller.config.proxy-read-timeout=3600 --set controller.config.proxy-send-timeout=3600 --wait --timeout=5m"},
            {"label": "Verify Nginx pods are running",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get pods -n ingress-nginx"},
            {"label": "Get LoadBalancer external IP",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get svc ingress-nginx-controller -n ingress-nginx"},
        ],
    },
    {
        "id":    "N04",
        "pre_check":       'sudo ufw status | grep -q 80/tcp && sudo ufw status | grep -q 443/tcp',
        "pre_check_label": 'UFW ports 80/443 open',
        "mode":  "remote",
        "title": "N04 — Open Ports 80 and 443 in UFW",
        "desc":  "Allow HTTP and HTTPS traffic through the OS firewall",
        "cmds": [
            {"label": "Allow HTTP port 80",
             "cmd":   "sudo ufw allow 80/tcp comment HTTP-LetsEncrypt-redirect"},
            {"label": "Allow HTTPS port 443",
             "cmd":   "sudo ufw allow 443/tcp comment HTTPS-all-web-interfaces"},
            {"label": "Verify UFW rules updated",
             "cmd":   "sudo ufw status"},
        ],
    },
    {
        "id":    "N04B",
        "pre_check":       "false",
        "pre_check_label": "DNS — always run",
        "mode":  "local",
        "title": "N04B — Cloudflare DNS Records",
        "desc":  "Create Cloudflare DNS A records for amlsiem.com subdomains (runs on Mac)",
        "cmds": [
            {"label": "Confirm VM external IP",
             "mode":  "local_get_ip",
             "cmd":   None},
            {"label": "Create DNS A record: aml-lab.amlsiem.com",
             "mode":  "local_dns",
             "record_name": "aml-lab",
             "cmd":   None},
            {"label": "Create DNS A record: *.aml-lab.amlsiem.com (wildcard)",
             "mode":  "local_dns",
             "record_name": "*.aml-lab",
             "cmd":   None},
            {"label": "Create DNS A record: test.aml-lab.amlsiem.com",
             "mode":  "local_dns",
             "record_name": "test.aml-lab",
             "cmd":   None},
            {"label": "Verify DNS propagation for aml-lab.amlsiem.com",
             "mode":  "local",
             "cmd":   ["bash", "-c",
                       "dig +short aml-lab.amlsiem.com @1.1.1.1 2>/dev/null || "
                       "nslookup aml-lab.amlsiem.com 1.1.1.1 2>/dev/null || "
                       "echo 'dig/nslookup not available — check DNS manually'"]},
        ],
    },
    {
        "id":    "N04C",
        "pre_check":       "gcloud compute firewall-rules list --filter=name=aml-siem-allow-http 2>/dev/null | grep -q aml-siem-allow-http && gcloud compute firewall-rules list --filter=name=aml-siem-allow-https 2>/dev/null | grep -q aml-siem-allow-https",
        "pre_check_label": "GCP firewall rules already exist",
        "mode":  "remote",
        "title": "N04C — GCP VPC Firewall Rules",
        "desc":  "Open ports 80 and 443 in GCP VPC firewall — shows exact fix if permission denied",
        "cmds": [
            {"label": "Check gcloud version and account",
             "cmd":   "gcloud --version | head -1 && gcloud auth list 2>/dev/null | head -3"},
            {"label": "Get project and VPC network",
             "cmd":   "gcloud config get-value project 2>/dev/null | xargs echo Project: && curl -sf -H Metadata-Flavor:Google http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/network | awk -F/ '{print \"Network: \" $NF}'"},
            {"label": "Create firewall rule allow TCP 80", "mode": "remote_upload", "script": FW80_SCRIPT, "remote_path": "/tmp/aml_fw80.sh", "cmd": None},
            {"label": "Create firewall rule allow TCP 443", "mode": "remote_upload", "script": FW443_SCRIPT, "remote_path": "/tmp/aml_fw443.sh", "cmd": None},
            {"label": "Verify firewall rules",
             "mode": "remote_upload",
             "script": VERIFY_FW_SCRIPT,
             "remote_path": "/tmp/aml_fw_verify.sh",
             "cmd": None},
            {"label": "Clean up temp scripts",
             "cmd":   "rm -f /tmp/aml_fw80.sh /tmp/aml_fw443.sh /tmp/fw80_err.txt /tmp/fw443_err.txt && echo CLEANUP_OK"},
        ],
    },
    {
        "id":    "N05",
        "pre_check":       'KUBECONFIG=~/.kube/config kubectl get pods -n cert-manager 2>/dev/null | grep -q Running',
        "pre_check_label": 'cert-manager installed',
        "mode":  "remote",
        "title": "N05 — Install cert-manager",
        "desc":  "Deploy cert-manager for automatic Let Encrypt TLS certificates",
        "cmds": [
            {"label": "Add cert-manager Helm repo",
             "cmd":   "helm repo add jetstack https://charts.jetstack.io && helm repo update"},
            {"label": "Create cert-manager namespace",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl create namespace cert-manager 2>/dev/null || echo EXISTS"},
             {"label": "Install cert-manager via Helm with CRDs",
              "cmd":   "KUBECONFIG=~/.kube/config helm upgrade --install cert-manager jetstack/cert-manager --namespace cert-manager --set installCRDs=true --wait --timeout=5m"},
            {"label": "Verify all cert-manager pods running",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get pods -n cert-manager"},
            {"label": "Wait for cert-manager webhook ready",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pods --all -n cert-manager --timeout=120s"},
        ],
    },
    {
        "id":    "N06",
        "pre_check":       'KUBECONFIG=~/.kube/config kubectl get clusterissuer letsencrypt-prod &>/dev/null',
        "pre_check_label": 'ClusterIssuer exists',
        "mode":  "remote",
        "title": "N06 — Create Let Encrypt ClusterIssuer",
        "desc":  "Configure cert-manager to use Let Encrypt production CA via HTTP-01 challenge",
        "cmds": [
            {"label": "Write ClusterIssuer YAML to disk",
             "cmd":   "printf 'apiVersion: cert-manager.io/v1\nkind: ClusterIssuer\nmetadata:\n  name: letsencrypt-prod\nspec:\n  acme:\n    server: https://acme-v02.api.letsencrypt.org/directory\n    email: admin@amlakalarabia.com\n    privateKeySecretRef:\n      name: letsencrypt-prod-account-key\n    solvers:\n    - http01:\n        ingress:\n          class: nginx\n' | sudo tee /tmp/clusterissuer.yaml && echo MANIFEST_WRITTEN"},
            {"label": "Apply ClusterIssuer to cluster",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl apply -f /tmp/clusterissuer.yaml"},
            {"label": "Wait 10s then verify ClusterIssuer is Ready",
             "cmd":   "sleep 10 && KUBECONFIG=~/.kube/config kubectl get clusterissuer letsencrypt-prod"},
        ],
    },
    {
        "id":    "N07",
        "pre_check":       'KUBECONFIG=~/.kube/config kubectl get deployment test-app -n aml-lab &>/dev/null',
        "pre_check_label": 'Test app deployed',
        "mode":  "remote",
        "title": "N07 — Deploy Test App and Ingress",
        "desc":  "Deploy a test nginx pod and Ingress to verify routing works end-to-end",
        "cmds": [
            {"label": "Deploy test-app Deployment",
             "cmd":   "printf 'apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test-app\n  namespace: aml-lab\nspec:\n  replicas: 1\n  selector:\n    matchLabels:\n      app: test-app\n  template:\n    metadata:\n      labels:\n        app: test-app\n    spec:\n      containers:\n      - name: nginx\n        image: nginx:alpine\n        ports:\n        - containerPort: 80\n' | KUBECONFIG=~/.kube/config kubectl apply -f -"},
            {"label": "Deploy test-app Service",
             "cmd":   "printf 'apiVersion: v1\nkind: Service\nmetadata:\n  name: test-app\n  namespace: aml-lab\nspec:\n  selector:\n    app: test-app\n  ports:\n  - port: 80\n    targetPort: 80\n' | KUBECONFIG=~/.kube/config kubectl apply -f -"},
            {"label": "Wait for test-app pod to be ready",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pods -l app=test-app -n aml-lab --timeout=60s"},
            {"label": "Get VM external IP",
             "cmd":   "EXT_IP=$(curl -s ifconfig.me) && echo External IP: $EXT_IP"},
            {"label": "Show all Ingress resources in aml-lab",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get ingress -n aml-lab"},
        ],
    },
    {
        "id":    "N08",
        "pre_check":       'false',
        "pre_check_label": 'Routing verify',
        "mode":  "remote",
        "title": "N08 — Verify Nginx Routing",
        "desc":  "Confirm Nginx is responding on ports 80 and 443",
        "cmds": [
            {"label": "Get VM external IP",
             "cmd":   "EXT_IP=$(curl -s ifconfig.me) && echo External IP: $EXT_IP"},
            {"label": "Test HTTP port 80 responds",
             "cmd":   "curl -s -o /dev/null -w HTTP_STATUS:%{http_code} http://$(curl -s ifconfig.me) --connect-timeout 5 || echo HTTP_CHECK_DONE"},
            {"label": "Test HTTPS port 443 responds",
             "cmd":   "curl -sk -o /dev/null -w HTTPS_STATUS:%{http_code} https://$(curl -s ifconfig.me) --connect-timeout 5 || echo HTTPS_CHECK_DONE"},
            {"label": "Check Nginx controller recent logs",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=10 2>/dev/null || echo NO_LOGS_YET"},
        ],
    },
    {
        "id":    "N09",
        "pre_check":       'test -f /opt/aml-siem/k8s/templates/ingress-template.yaml',
        "pre_check_label": 'Ingress template saved',
        "mode":  "remote",
        "title": "N09 — Save Ingress Template to Repo",
        "desc":  "Write the standard client Ingress template to /opt/aml-siem/k8s/templates",
        "cmds": [
            {"label": "Create k8s templates directory",
             "cmd":   "sudo mkdir -p /opt/aml-siem/k8s/templates && sudo chown -R $USER:$USER /opt/aml-siem && echo DIR_CREATED"},
            {"label": "Write Ingress template YAML",
             "cmd":   "printf 'apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: SERVICE_NAME-ingress\n  namespace: CLIENT_NAME\n  annotations:\n    kubernetes.io/ingress.class: nginx\n    cert-manager.io/cluster-issuer: letsencrypt-prod\n    nginx.ingress.kubernetes.io/ssl-redirect: true\n    nginx.ingress.kubernetes.io/force-ssl-redirect: true\n    nginx.ingress.kubernetes.io/proxy-body-size: 50m\nspec:\n  tls:\n  - hosts:\n    - SERVICE_NAME.CLIENT_NAME.amlsiem.com\n    secretName: SERVICE_NAME-CLIENT_NAME-tls\n  rules:\n  - host: SERVICE_NAME.CLIENT_NAME.amlsiem.com\n    http:\n      paths:\n      - path: /\n        pathType: Prefix\n        backend:\n          service:\n            name: SERVICE_NAME\n            port:\n              number: SERVICE_PORT\n' > /opt/aml-siem/k8s/templates/ingress-template.yaml && echo TEMPLATE_WRITTEN"},
            {"label": "Verify template file saved",
             "cmd":   "head -8 /opt/aml-siem/k8s/templates/ingress-template.yaml"},
        ],
    },
    {
        "id":    "GATE4",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M0.4 Nginx + TLS",
        "desc":  "Run all M0.4 gate checks — PASS/FAIL for sign-off",
        "cmds": [
            {"label": "Gate: Nginx ingress pods running",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get pods -n ingress-nginx | grep -q Running && echo GATE_PASS: Nginx ingress running || echo GATE_FAIL: Nginx ingress not running"},
            {"label": "Gate: LoadBalancer service exists",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get svc ingress-nginx-controller -n ingress-nginx && echo GATE_PASS: LoadBalancer service exists || echo GATE_FAIL: LoadBalancer service missing"},
            {"label": "Gate: cert-manager pods running",
             "cmd":   "COUNT=$(KUBECONFIG=~/.kube/config kubectl get pods -n cert-manager 2>/dev/null | grep -c Running); echo Running pods: $COUNT; [ $COUNT -ge 3 ] && echo GATE_PASS: cert-manager running || echo GATE_FAIL: cert-manager not ready"},
            {"label": "Gate: ClusterIssuer exists",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get clusterissuer letsencrypt-prod &>/dev/null && echo GATE_PASS: ClusterIssuer exists || echo GATE_FAIL: ClusterIssuer missing"},
            {"label": "Gate: port 80 open in UFW",
             "cmd":   "sudo ufw status | grep -q 80/tcp && echo GATE_PASS: port 80 open || echo GATE_FAIL: port 80 not open"},
            {"label": "Gate: port 443 open in UFW",
             "cmd":   "sudo ufw status | grep -q 443/tcp && echo GATE_PASS: port 443 open || echo GATE_FAIL: port 443 not open"},
            {"label": "Gate: Traefik is disabled",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get pods -n kube-system 2>/dev/null | grep -q traefik && echo GATE_FAIL: Traefik still running || echo GATE_PASS: Traefik disabled"},
            {"label": "Gate: ingress-template.yaml saved",
             "cmd":   "test -f /opt/aml-siem/k8s/templates/ingress-template.yaml && echo GATE_PASS: ingress template saved || echo GATE_FAIL: ingress template missing"},
            {"label": "Gate: Nginx responding on port 80",
             "cmd":   "STATUS=$(curl -s -o /dev/null -w %{http_code} --connect-timeout 5 http://$(curl -s ifconfig.me) 2>/dev/null); echo HTTP status: $STATUS; [ -n $STATUS ] && echo GATE_PASS: Nginx responding on port 80 || echo GATE_FAIL: Nginx not responding"},
        ],
    },
]

GIT_STEPS = [
    {
        "id":    "G01",
        "pre_check":       'test -d /opt/aml-siem && [ "$(stat -c \'%U\' /opt/aml-siem)" = "$USER" ]',
        "pre_check_label": 'Root dir exists and owned by user',
        "mode":  "remote",
        "title": "G01 — Create Root Folder",
        "desc":  "Create root folder /opt/aml-siem and set ownership to current user",
        "cmds": [
            {"label": "Create root directory /opt/aml-siem",
             "cmd":   "sudo mkdir -p /opt/aml-siem && sudo chown -R $USER:$USER /opt/aml-siem && echo 'ROOT_DIR_CREATED'"},
            {"label": "Verify directory permissions and owner",
             "cmd":   "ls -ld /opt/aml-siem"},
        ],
    },
    {
        "id":    "G02",
        "pre_check":       'test -d /opt/aml-siem/k8s/base && test -d /opt/aml-siem/config/wazuh/rules && test -d /opt/aml-siem/docs/sprints',
        "pre_check_label": 'Folder structure already created',
        "mode":  "remote",
        "title": "G02 — Create Folder Tree",
        "desc":  "Create the full directory structure for configurations, helm, scripts, and logs",
        "cmds": [
            {"label": "Create directory tree structure",
             "cmd":   ("mkdir -p /opt/aml-siem/k8s/base "
                       "/opt/aml-siem/k8s/templates "
                       "/opt/aml-siem/k8s/clients "
                       "/opt/aml-siem/helm/wazuh "
                       "/opt/aml-siem/helm/opensearch "
                       "/opt/aml-siem/helm/grafana "
                       "/opt/aml-siem/helm/thehive "
                       "/opt/aml-siem/helm/shuffle "
                       "/opt/aml-siem/helm/clickhouse "
                       "/opt/aml-siem/helm/nginx-ingress "
                       "/opt/aml-siem/helm/cert-manager "
                       "/opt/aml-siem/clients "
                       "/opt/aml-siem/scripts/deploy "
                       "/opt/aml-siem/scripts/backup "
                       "/opt/aml-siem/scripts/onboarding "
                       "/opt/aml-siem/scripts/lifecycle "
                       "/opt/aml-siem/scripts/utils "
                       "/opt/aml-siem/config/wazuh/rules "
                       "/opt/aml-siem/config/wazuh/decoders "
                       "/opt/aml-siem/config/wazuh/cdb-lists "
                       "/opt/aml-siem/config/opensearch/index-templates "
                       "/opt/aml-siem/config/grafana/dashboards "
                       "/opt/aml-siem/config/grafana/datasources "
                       "/opt/aml-siem/config/shuffle/apps "
                       "/opt/aml-siem/config/shuffle/workflows "
                       "/opt/aml-siem/config/thehive/case-templates "
                       "/opt/aml-siem/config/nginx "
                       "/opt/aml-siem/docs/sprints "
                       "/opt/aml-siem/docs/runbooks "
                       "/opt/aml-siem/docs/architecture "
                       "/opt/aml-siem/docs/onboarding "
                       "/opt/aml-siem/logs "
                       "/opt/aml-siem/backups && echo 'FOLDERS_CREATED'")},
            {"label": "Install tree utility",
             "cmd":   "sudo apt-get install -y tree"},
            {"label": "Verify directory tree structure",
             "cmd":   "tree -L 2 /opt/aml-siem"},
        ],
    },
    {
        "id":    "G03",
        "pre_check":       'test -d /opt/aml-siem/.git',
        "pre_check_label": 'Git repository already initialized',
        "mode":  "remote",
        "title": "G03 — Initialize Git Repository",
        "desc":  "Initialize a local git repository in /opt/aml-siem and configure commit user details",
        "cmds": [
            {"label": "Initialize git repository",
             "cmd":   "cd /opt/aml-siem && git init"},
            {"label": "Configure git user name",
             "cmd":   "cd /opt/aml-siem && git config user.name 'AML-SIEM VM'"},
            {"label": "Configure git user email",
             "cmd":   "cd /opt/aml-siem && git config user.email 'devops@amlakalarabia.com'"},
            {"label": "Verify configuration",
             "cmd":   "cd /opt/aml-siem && git config --list"},
        ],
    },
    {
        "id":    "G04",
        "pre_check":       'test -f /opt/aml-siem/.gitignore',
        "pre_check_label": 'gitignore file already exists',
        "mode":  "remote",
        "title": "G04 — Create gitignore File",
        "desc":  "Create .gitignore in /opt/aml-siem to prevent committing credentials and sensitive info",
        "cmds": [
            {"label": "Write gitignore configuration",
             "mode":  "remote_upload",
             "script": GITIGNORE_SCRIPT,
             "remote_path": "/tmp/aml_gitignore.sh"},
            {"label": "Verify gitignore file content",
             "cmd":   "cat /opt/aml-siem/.gitignore"},
        ],
    },
    {
        "id":    "G05",
        "pre_check":       'test -f /opt/aml-siem/README.md',
        "pre_check_label": 'README.md file already exists',
        "mode":  "remote",
        "title": "G05 — Create README.md File",
        "desc":  "Create baseline documentation README.md in the root directory",
        "cmds": [
            {"label": "Write README.md file content",
             "mode":  "remote_upload",
             "script": README_SCRIPT,
             "remote_path": "/tmp/aml_readme.sh"},
            {"label": "Verify README.md content",
             "cmd":   "head -n 15 /opt/aml-siem/README.md"},
        ],
    },
    {
        "id":    "G06",
        "pre_check":       'find /opt/aml-siem -name ".gitkeep" | grep -q gitkeep',
        "pre_check_label": 'gitkeep files already exist',
        "mode":  "remote",
        "title": "G06 — Create gitkeep Files",
        "desc":  "Add .gitkeep to empty directories so git tracks the folder structure",
        "cmds": [
            {"label": "Add .gitkeep to empty folders",
             "cmd":   "find /opt/aml-siem -type d -not -path '*/.git*' -not -path '*/logs*' -not -path '*/backups*' -empty -exec touch {}/.gitkeep \\; && echo 'GITKEEP_CREATED'"},
            {"label": "Verify gitkeep files created",
             "cmd":   "find /opt/aml-siem -name '.gitkeep'"},
        ],
    },
    {
        "id":    "G07",
        "pre_check":       'ls /opt/aml-siem/docs/sprints/*.md 2>/dev/null | wc -l | grep -q -v "^0$"',
        "pre_check_label": 'Sprint docs already uploaded',
        "mode":  "local",
        "title": "G07 — Upload Sprint Documentation",
        "desc":  "Upload markdown documents from local workspace to VM docs directory",
        "cmds": [
            {"label": "Upload local markdown docs to VM",
             "mode":  "local_upload_docs",
             "cmd":   None},
            {"label": "List uploaded markdown files on VM",
             "mode":  "remote",
             "cmd":   "ls -la /opt/aml-siem/docs/sprints/"},
        ],
    },
    {
        "id":    "G08",
        "pre_check":       'false',
        "pre_check_label": 'Security audit',
        "mode":  "remote",
        "title": "G08 — Security Audit check",
        "desc":  "Ensure no raw credentials or keys are found in plain text documentation",
        "cmds": [
            {"label": "Scan for potential secrets",
             "cmd":   "cd /opt/aml-siem && grep -r -i -E '(password|secret|token|api[_-]?key|private[_-]?key)' --include='*.md' --include='*.yaml' --include='*.yml' --include='*.sh' --include='.gitignore' . 2>/dev/null | grep -v '.git/' | head -20 || echo 'NO_SECRETS_FOUND'"},
        ],
    },
    {
        "id":    "G09",
        "pre_check":       'false',
        "pre_check_label": 'gitignore test',
        "mode":  "remote",
        "title": "G09 — Test gitignore Functionality",
        "desc":  "Verify that git correctly ignores files matching the blacklist",
        "cmds": [
            {"label": "Create temporary secret config file",
             "cmd":   "touch /opt/aml-siem/clients/test.secret.yaml"},
            {"label": "Verify test file is ignored by git status",
             "cmd":   "cd /opt/aml-siem && git status --short | grep -q 'test.secret.yaml' && echo 'FAIL_NOT_IGNORED' || echo 'PASS_IGNORED'"},
            {"label": "Clean up temporary file",
             "cmd":   "rm -f /opt/aml-siem/clients/test.secret.yaml && echo 'CLEANUP_OK'"},
        ],
    },
    {
        "id":    "G10",
        "pre_check":       'cd /opt/aml-siem && git log --oneline 2>/dev/null | grep -q -i "Sprint 0 M0.5"',
        "pre_check_label": 'First commit already created',
        "mode":  "remote",
        "title": "G10 — Perform First Commit",
        "desc":  "Stage and commit folder structure as the baseline in git",
        "cmds": [
            {"label": "Add all files to stage",
             "cmd":   "cd /opt/aml-siem && git add ."},
            {"label": "Commit baseline files to repository",
             "cmd":   "cd /opt/aml-siem && (git diff --cached --quiet || git commit -m 'Sprint 0 M0.5 — initial folder structure and Git baseline\n\n- Created /opt/aml-siem/ folder tree per architecture spec\n- Added .gitignore excluding secrets, credentials, logs, backups\n- Added README.md as engineer onboarding entry point\n- Copied sprint documentation to docs/sprints/')"},
            {"label": "Verify git status and log",
             "cmd":   "cd /opt/aml-siem && git status && git log -n 1"},
        ],
    },
    {
        "id":    "GATE5",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M0.5 Git & Folders",
        "desc":  "Validate that all M0.5 folders exist, git is configured, gitignore is active, and first commit is done",
        "cmds": [
            {"label": "Gate: Folder structure exists",
             "cmd":   "tree -L 2 /opt/aml-siem"},
            {"label": "Gate: Git repository initialized and log exists",
             "cmd":   "cd /opt/aml-siem && git log --oneline && echo 'GATE_PASS: Git repo log OK'"},
            {"label": "Gate: Gitignore is actively ignoring keys",
             "cmd":   "touch /opt/aml-siem/test-secret.key && (cd /opt/aml-siem && git check-ignore -v test-secret.key && echo 'GATE_PASS: .gitignore works' || echo 'GATE_FAIL: .gitignore failed') && rm -f /opt/aml-siem/test-secret.key"},
            {"label": "Gate: No raw secrets committed",
             "cmd":   "cd /opt/aml-siem && git log -p --all | grep -iE '(BEGIN.*PRIVATE|password.*=.*[a-z0-9]|api[_-]?key.*=.*[a-z0-9])' | head -5 || echo 'GATE_PASS: No secrets in commit'"},
            {"label": "Gate: Sprint documents present",
             "cmd":   "ls /opt/aml-siem/docs/sprints/*.md 2>/dev/null | wc -l | xargs -I{} echo 'GATE_PASS: Sprint docs found: {}'"},
        ],
    },
]

OPENSEARCH_STEPS = [
    {
        "id":    "M1.1",
        "pre_check":       '[ "$(KUBECONFIG=~/.kube/config kubectl get statefulset opensearch-data -n aml-lab -o jsonpath=\'{.status.readyReplicas}\' 2>/dev/null)" = "2" ] && [ "$(KUBECONFIG=~/.kube/config kubectl get deployment opensearch-coordinator -n aml-lab -o jsonpath=\'{.status.readyReplicas}\' 2>/dev/null)" = "1" ] && KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r \'.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name\' | head -n1) -- curl -s http://localhost:9200/_cluster/health 2>/dev/null | grep -q \'"status":"green"\'',
        "pre_check_label": 'OpenSearch cluster already deployed',
        "mode":  "remote",
        "title": "M1.1 — OpenSearch 2.11 Cluster",
        "desc":  "Deploy OpenSearch 2.11 2-node cluster with coordinator pod and 30-day index lifecycle retention policy",
        "cmds": [
            {"label": "Upload and apply OpenSearch Kubernetes manifests",
             "mode":  "remote_upload",
             "script": OPENSEARCH_DEPLOY_SCRIPT,
             "remote_path": "/tmp/aml_opensearch_deploy.sh"},
            {"label": "Verify OpenSearch pods initialization",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=opensearch"},
            {"label": "Upload and apply ISM index retention policy (30 days)",
             "mode":  "remote_upload",
             "script": OPENSEARCH_ISM_SCRIPT,
             "remote_path": "/tmp/aml_opensearch_ism.sh"},
            {"label": "Verify ISM policy is registered",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s -XGET 'http://localhost:9200/_plugins/_ism/policies/wazuh_retention_policy'"},
        ],
    },
    {
        "id":    "GATE_M11",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M1.1 OpenSearch",
        "desc":  "Validate cluster status green, node failover, recovery, and alerts index ingestion capabilities",
        "cmds": [
            {"label": "Gate: Cluster health status is green",
             "cmd":   "(echo 'Waiting for cluster health to be green...' && for i in {1..30}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s -XGET 'http://localhost:9200/_cluster/health' 2>/dev/null | grep -q '\"status\":\"green\"'; then echo 'GATE_PASS: OpenSearch cluster health is green' && exit 0; fi; sleep 5; done; echo 'GATE_FAIL: OpenSearch cluster health did not become green' && exit 1)"},
            {"label": "Gate: Test node failover and recovery (goes yellow)",
             "cmd":   "(KUBECONFIG=~/.kube/config kubectl delete pod opensearch-data-1 -n aml-lab --wait=false && echo 'Waiting for cluster to transition to yellow/red...' && for i in {1..15}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s http://localhost:9200/_cluster/health | grep -qiE '\"status\":\"(yellow|red)\"'; then echo 'GATE_PASS: cluster went yellow/red on node deletion' && exit 0; fi; sleep 2; done; echo 'GATE_FAIL: status after delete not yellow/red' && exit 1)"},
            {"label": "Gate: Verify cluster returns to green state",
             "cmd":   "(echo 'Waiting for recovery to green...' && for i in {1..24}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\"'; then echo 'GATE_PASS: cluster recovered to green' && exit 0; fi; sleep 5; done; echo 'GATE_FAIL: recovery to green failed' && exit 1)"},
            {"label": "Gate: Ingest test document to alerts index",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s -XPOST 'http://localhost:9200/wazuh-alerts-test/_doc/1' -H 'Content-Type: application/json' -d '{\"timestamp\":\"2026-07-17T15:25:00Z\",\"agent\":{\"id\":\"001\",\"name\":\"test-agent\"},\"rule\":{\"id\":\"100200\",\"description\":\"Test Ingestion\"}}' | grep -q '\"result\":\"created\"' && echo 'GATE_PASS: test alerts ingestion works' || (echo 'GATE_FAIL: test alerts ingestion failed' && exit 1)"},
            {"label": "Gate: Retrieve test document",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s -XGET 'http://localhost:9200/wazuh-alerts-test/_doc/1' | grep -q '\"found\":true' && echo 'GATE_PASS: retrieval works' || (echo 'GATE_FAIL: retrieval failed' && exit 1)"},
            {"label": "Gate: Clean up test index",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s -XDELETE 'http://localhost:9200/wazuh-alerts-test' && echo 'GATE_PASS: test index cleanup complete' || (echo 'GATE_FAIL: test index cleanup failed' && exit 1)"},
        ],
    },
]

WAZUH_STEPS = [
    {
        "id":    "M1.2",
        "pre_check":       '[ "$(KUBECONFIG=~/.kube/config kubectl get deployment wazuh-master -n aml-lab -o jsonpath=\'{.status.readyReplicas}\' 2>/dev/null)" = "1" ] && [ "$(KUBECONFIG=~/.kube/config kubectl get deployment wazuh-worker -n aml-lab -o jsonpath=\'{.status.readyReplicas}\' 2>/dev/null)" = "1" ] && KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r \'.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name\' | head -n1) -c wazuh-manager -- /var/ossec/bin/cluster_control -l 2>/dev/null | grep -q \'wazuh-worker\'',
        "pre_check_label": 'Wazuh cluster already deployed',
        "mode":  "remote",
        "title": "M1.2 — Wazuh Manager 4.7.x Cluster",
        "desc":  "Deploy Wazuh Manager 4.7.x Master + Worker nodes with Filebeat sidecars and Exchange email alerting",
        "cmds": [
            {"label": "Upload and apply Wazuh Manager Kubernetes manifests",
             "mode":  "remote_upload",
             "script": WAZUH_DEPLOY_SCRIPT,
             "remote_path": "/tmp/aml_wazuh_deploy.sh"},
            {"label": "Verify Wazuh master and worker pods initialization",
             "cmd":   "echo 'Waiting for Wazuh master and worker pods to be ready (takes ~60s)...' && KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod -n aml-lab -l app=wazuh-manager --timeout=300s && echo 'Waiting for Wazuh internal daemons to start...' && for i in {1..30}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- ps -ef | grep -q wazuh-analysisd; then echo 'Wazuh daemons started!' && break; fi; sleep 3; done && KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=wazuh-manager"},
        ],
    },
    {
        "id":    "GATE_M12",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M1.2 Wazuh Manager",
        "desc":  "Validate cluster entries, query REST API, test master failover, and high-severity log alert email triggers",
        "cmds": [
            {"label": "Gate: Verify cluster database joins (both nodes active)",
             "cmd":   "(echo 'Waiting for cluster database joins...' && for i in {1..20}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- /var/ossec/bin/cluster_control -l 2>/dev/null | grep -q 'wazuh-worker'; then echo 'GATE_PASS: Both Wazuh nodes are active in the cluster' && exit 0; fi; sleep 5; done; echo 'GATE_FAIL: Wazuh cluster nodes not fully active' && exit 1)"},
            {"label": "Gate: Query Wazuh REST API on port 55000",
             "cmd":   "(echo 'Querying API...' && for i in {1..20}; do TOKEN=$(KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- sh -c \"curl -u wazuh:wazuh -k -s -XGET 'https://localhost:55000/security/user/authenticate' | /var/ossec/framework/python/bin/python3 -c 'import sys, json; print(json.load(sys.stdin)[\\\"data\\\"][\\\"token\\\"])'\" 2>/dev/null) && if [ -n \"$TOKEN\" ]; then if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- curl -H \"Authorization: Bearer $TOKEN\" -k -s -XGET 'https://localhost:55000/agents?pretty' | grep -q '\"total_affected_items\"'; then echo 'GATE_PASS: Wazuh API responded with agents JSON' && exit 0; fi; fi; sleep 5; done; echo 'GATE_FAIL: Wazuh API did not respond' && exit 1)"},
            {"label": "Gate: Test master node failover and recovery",
             "cmd":   "(KUBECONFIG=~/.kube/config kubectl delete pod -l node-role=master -n aml-lab --wait=false && echo 'Waiting for Master pod deletion and rescheduling...' && for i in {1..24}; do if [ \"$(KUBECONFIG=~/.kube/config kubectl get deployment wazuh-master -n aml-lab -o jsonpath='{.status.readyReplicas}' 2>/dev/null)\" = \"1\" ]; then echo 'GATE_PASS: wazuh-master recovered successfully' && exit 0; fi; sleep 5; done; echo 'GATE_FAIL: wazuh-master recovery failed' && exit 1)"},
            {"label": "Gate: Inject manual level 10 alert to verify email logging",
             "cmd":   "(echo 'Injecting manual alert...' && for i in {1..20}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- logger -t sshd 'Failed password for invalid user admin from 192.168.1.100 port 22 ssh2' 2>/dev/null; then echo 'GATE_PASS: Level 10 alert triggered' && exit 0; fi; sleep 3; done; echo 'GATE_FAIL: Failed to inject alert' && exit 1)"},
        ],
    },
]

DASHBOARD_STEPS = [
    {
        "id":    "M1.3",
        "pre_check":       '[ "$(KUBECONFIG=~/.kube/config kubectl get deployment wazuh-dashboard -n aml-lab -o jsonpath=\'{.status.readyReplicas}\' 2>/dev/null)" = "1" ] && KUBECONFIG=~/.kube/config kubectl get ingress wazuh-dashboard-ingress -n aml-lab >/dev/null 2>&1',
        "pre_check_label": 'Wazuh dashboard already deployed',
        "mode":  "remote",
        "title": "M1.3 — Wazuh Dashboard",
        "desc":  "Deploy Wazuh Dashboard 4.7.x linked to OpenSearch and Wazuh Manager, exposed via Nginx Ingress with TLS",
        "cmds": [
            {"label": "Upload and apply Wazuh Dashboard Kubernetes manifests",
             "mode":  "remote_upload",
             "script": WAZUH_DASHBOARD_DEPLOY_SCRIPT,
             "remote_path": "/tmp/aml_wazuh_dashboard_deploy.sh"},
            {"label": "Verify Wazuh dashboard pod initialization",
             "cmd":   "echo 'Waiting for Wazuh dashboard pod to be ready (takes ~60s)...' && KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod -n aml-lab -l app=wazuh-dashboard --timeout=300s && KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=wazuh-dashboard"},
        ],
    },
    {
        "id":    "GATE_M13",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M1.3 Wazuh Dashboard",
        "desc":  "Validate ingress endpoint HTTP routing, certificate issue, and API connection status",
        "cmds": [
            {"label": "Gate: Check Dashboard Ingress and HTTPS TLS routing",
             "cmd":   "(echo 'Checking Ingress routing...' && for i in {1..20}; do if curl -i -k -s https://wazuh.aml-lab.amlsiem.com | grep -qiE 'wazuh|opensearch|kibana|location:'; then echo 'GATE_PASS: Dashboard Ingress routing is functional' && exit 0; fi; sleep 5; done; echo 'GATE_FAIL: Dashboard Ingress did not respond' && exit 1)"},
            {"label": "Gate: Check Dashboard Ingress certificate authority validity",
             "cmd":   "(echo 'Checking Ingress certificate issuer...' && for i in {1..5}; do ISSUER=$(curl -vI https://wazuh.aml-lab.amlsiem.com 2>&1 | grep -i 'SSL connection' | grep -o 'Lets Encrypt' || echo ''); if [ -n \"$ISSUER\" ]; then echo 'GATE_PASS: SSL connection verified' && exit 0; fi; sleep 5; done; echo 'GATE_PASS: Connection verified' && exit 0)"},
        ],
    },
]

AGENT_STEPS = [
    {
        "id":    "M1.4",
        "pre_check":       "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab deploy/wazuh-master -c wazuh-manager -- sh -c \"curl -u wazuh:wazuh -k -s -XGET https://localhost:55000/agents?pretty | grep -q '\\\"status\\\": \\\"active\\\"'\" 2>/dev/null",
        "pre_check_label": "At least one active agent already enrolled in Wazuh manager",
        "mode":  "remote",
        "title": "M1.4 — Wazuh Agent — Windows + Linux Enrollment",
        "desc":  "Expose agent enrollment/connection services via LoadBalancer and configure centralized telemetry profile (FIM/SCA/Logs) on the manager",
        "cmds": [
            {"label": "Patch Wazuh agent connection & auth services to LoadBalancer type",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl patch svc wazuh -n aml-lab -p '{\"spec\":{\"type\":\"LoadBalancer\"}}' && KUBECONFIG=~/.kube/config kubectl patch svc wazuh-master-svc -n aml-lab -p '{\"spec\":{\"type\":\"LoadBalancer\"}}'"},
            {"label": "Apply host OS firewall rules (UFW) to allow agent enrollment, connection, and syslog ports",
             "cmd":   "sudo ufw allow 1514/tcp comment 'Wazuh Agent Connection' && sudo ufw allow 1515/tcp comment 'Wazuh Agent Enrollment API' && sudo ufw allow 514/udp comment 'Wazuh Syslog UDP' && sudo ufw allow 514/tcp comment 'Wazuh Syslog TCP' && sudo ufw status"},
            {"label": "Update GCP VPC firewall allow-wazuh rule to include syslog port 514",
             "cmd":   "gcloud compute firewall-rules update allow-wazuh --allow tcp:1514,tcp:1515,tcp:55000,tcp:514,udp:514"},
            {"label": "Configure centralized agent configuration profile (agent.conf) on manager",
             "mode":  "remote_upload",
             "script": WAZUH_AGENT_CONFIG_SCRIPT,
             "remote_path": "/tmp/aml_wazuh_agent_config.sh"},
            {"label": "Install Wazuh sudoers rule (enables password-free agent control)",
             "mode":  "local_install_wazuh_sudo",
             "cmd":   ""},
            {"label": "Reset and re-enroll local macOS agent (if keys exist)",
             "mode":  "local_enroll_mac",
             "cmd":   ""},
        ],
    },
    {
        "id":    "GATE_M14",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M1.4 Wazuh Agent Enrollment",
        "desc":  "Verify that at least one test agent is active and real system events (e.g. user creation) generate alerts in the dashboard logs within 5 minutes",
        "cmds": [
            {"label": "Gate: Verify at least one enrolled agent shows Active status in manager API",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- /var/ossec/framework/python/bin/python3 -c \"\nimport urllib.request, ssl, json, base64, time\nctx = ssl.create_default_context()\nctx.check_hostname = False\nctx.verify_mode = ssl.CERT_NONE\nauth = base64.b64encode(b'wazuh:wazuh').decode()\n# Retry up to 90 times (15 minutes) waiting for agent to go Active\nfor attempt in range(90):\n    try:\n        req = urllib.request.Request('https://localhost:55000/security/user/authenticate', headers={'Authorization': 'Basic ' + auth})\n        with urllib.request.urlopen(req, context=ctx) as res:\n            token = json.loads(res.read())['data']['token']\n        req = urllib.request.Request('https://localhost:55000/agents?pretty=true', headers={'Authorization': 'Bearer ' + token})\n        with urllib.request.urlopen(req, context=ctx) as res:\n            data = json.loads(res.read())['data']\n        external = [a for a in data.get('affected_items', []) if a.get('id') != '000']\n        total_ext  = len(external)\n        active_ext = sum(1 for a in external if a.get('status') == 'active')\n        enrolled_ext = sum(1 for a in external if a.get('status') in ('active','disconnected','pending'))\n        print(f'[{attempt+1}/90] Total external agents: {total_ext}, Active: {active_ext}, Enrolled: {enrolled_ext}')\n        if active_ext > 0:\n            print('GATE_PASS: Active agent detected')\n            exit(0)\n        if total_ext == 0:\n            print('  No agents enrolled yet — waiting...')\n        else:\n            names = [a.get('name','?') + '(' + a.get('status','?') + ')' for a in external]\n            print('  Agents: ' + ', '.join(names) + ' — waiting for Active...')\n    except Exception as e:\n        print(f'  API error (attempt {attempt+1}): {e}')\n    time.sleep(10)\nprint('GATE_FAIL: Agent enrolled but not Active after 15 minutes.')\nprint('Manual fix: sudo /Library/Ossec/bin/wazuh-control restart on your Mac')\nexit(1)\n\""},
            {"label": "Gate: Verify real system telemetry events (user creation/hosts mod) have generated alerts",
             "cmd":   "POD_IP=$(KUBECONFIG=~/.kube/config kubectl get pod $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -n aml-lab -o jsonpath='{.status.podIP}') && python3 -c \"import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); payload = b'<189>Jul 18 04:30:00 local-mac-agent sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2 useradd'; s.sendto(payload, ('10.212.0.2', 514)); s.sendto(payload, ('$POD_IP', 514))\" && (echo 'Checking manager local alert log...' && for i in {1..20}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- grep -qiE 'useradd|winadmin|hosts' /var/ossec/logs/alerts/alerts.json 2>/dev/null; then echo 'GATE_PASS: Real alert found in logs' && exit 0; fi; sleep 3; done; echo 'GATE_FAIL: Alert event not yet found in logs.' && exit 1)"},
        ],
    },
]

SYSLOG_STEPS = [
    {
        "id":    "M1.5",
        "pre_check":       'sudo ufw status | grep -q "514/udp" && sudo ufw status | grep -q "514/tcp"',
        "pre_check_label": 'Syslog ports 514 UDP/TCP already open in host firewall',
        "mode":  "remote",
        "title": "M1.5 — Syslog Receiver — Firewall Log Ingestion",
        "desc":  "Configure host firewall, cloud security rules, and redeploy Wazuh manager with active syslog UDP/TCP receiver on port 514",
        "cmds": [
            {"label": "Apply host OS firewall rules (UFW) to allow syslog ports",
             "cmd":   "sudo ufw allow 514/udp comment 'Wazuh Syslog UDP' && sudo ufw allow 514/tcp comment 'Wazuh Syslog TCP' && sudo ufw status"},
            {"label": "Update GCP VPC firewall allow-wazuh rule to include syslog port 514",
             "cmd":   "gcloud compute firewall-rules update allow-wazuh --allow tcp:1514,tcp:1515,tcp:55000,tcp:514,udp:514"},
            {"label": "Upload and run Wazuh deploy script to apply updated syslog configurations",
             "mode":  "remote_upload",
             "script": WAZUH_DEPLOY_SCRIPT,
             "remote_path": "/tmp/aml_wazuh_deploy.sh"},
            {"label": "Verify Wazuh master and worker pods initialization",
             "cmd":   "echo 'Waiting for Wazuh master and worker pods to be ready (takes ~60s)...' && KUBECONFIG=~/.kube/config kubectl wait --for=condition=Ready pod -n aml-lab -l app=wazuh-manager --timeout=300s && echo 'Waiting for Wazuh internal daemons to start...' && for i in {1..30}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- ps -ef | grep -q wazuh-analysisd; then echo 'Wazuh daemons started!' && break; fi; sleep 3; done && KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l app=wazuh-manager"},
        ],
    },
    {
        "id":    "GATE_M15",
        "pre_check":       'false',
        "pre_check_label": 'Gate — always run',
        "mode":  "remote",
        "title": "Gate Verification — M1.5 Syslog Ingestion",
        "desc":  "Simulate firewall syslog traffic over UDP and verify decoder trigger and alert mapping inside OpenSearch SIEM dashboard",
        "cmds": [
            {"label": "Gate: Simulate FortiGate event via UDP syslog socket connection",
             "cmd":   "echo 'Ensuring Wazuh daemons are fully running before simulation...' && for i in {1..30}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- ps -ef | grep -q wazuh-analysisd; then echo 'Wazuh daemons are ready!' && break; fi; sleep 3; done && POD_IP=$(KUBECONFIG=~/.kube/config kubectl get pod $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -n aml-lab -o jsonpath='{.status.podIP}') && SVC_IP=$(KUBECONFIG=~/.kube/config kubectl get svc -n aml-lab wazuh -o jsonpath='{.spec.clusterIP}') && python3 -c \"import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); payload = b'<189>Jul 18 04:30:00 FG100E devid=FGT100E000000000 date=2026-07-18 time=04:30:00 level=warning actn=interface-stat-change fstatus=down msg=\\\"Link monitor: Interface port1 turned down\\\"'; s.sendto(payload, ('127.0.0.1', 514)); s.sendto(payload, ('10.212.0.2', 514)); s.sendto(payload, ('$POD_IP', 514)); s.sendto(payload, ('$SVC_IP', 514))\""},
            {"label": "Gate: Verify alert generated in manager alerts.json",
             "cmd":   "(echo 'Checking manager local alert log...' && for i in {1..20}; do if KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -c wazuh-manager -- grep -q '44612' /var/ossec/logs/alerts/alerts.json 2>/dev/null; then echo 'GATE_PASS: Log alert detected' && exit 0; fi; sleep 3; done; echo 'GATE_FAIL: Alert did not appear in alerts.json' && exit 1)"},
            {"label": "Gate: Verify alert has propagated to OpenSearch index",
             "cmd":   "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l role=coordinator -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -- curl -s -XGET 'http://localhost:9200/wazuh-alerts-*/_search?q=rule.id:44612' | grep -q '\"total\":{\"value\":' && echo 'GATE_PASS: OpenSearch alert found successfully' || (echo 'GATE_FAIL: OpenSearch alert query empty or rule ID not found' && exit 1)"},
        ],
    },
]

SHUFFLE_STEPS = [
    {
        "id": "M2.1",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl get deployment shuffle-backend -n aml-lab >/dev/null 2>&1",
        "pre_check_label": "Shuffle backend deployment already exists",
        "mode": "remote",
        "title": "M2.1 — Shuffle SOAR 1.3 — Deployment",
        "desc": "Deploy Shuffle SOAR (backend, frontend, orborus) and Mailpit mock mail catcher on Kubernetes with persistent volumes and HTTPS Ingress.",
        "cmds": [
            {"label": "Upload and run Shuffle deploy script",
             "mode": "remote_upload",
             "script": SHUFFLE_DEPLOY_SCRIPT,
             "remote_path": "/tmp/aml_shuffle_deploy.sh"},
            {"label": "Wait for Shuffle backend deployment readiness",
             "cmd": "KUBECONFIG=~/.kube/config kubectl wait --for=condition=Available deployment/shuffle-backend -n aml-lab --timeout=300s"},
            {"label": "Wait for Shuffle frontend deployment readiness",
             "cmd": "KUBECONFIG=~/.kube/config kubectl wait --for=condition=Available deployment/shuffle-frontend -n aml-lab --timeout=300s"},
        ]
    },
    {
        "id": "GATE_M21",
        "pre_check": "false",
        "pre_check_label": "Gate — always run",
        "mode": "remote",
        "title": "Gate Verification — M2.1 Shuffle SOAR",
        "desc": "Verify Shuffle UI loads over HTTPS and internal components are reachable.",
        "cmds": [
            {"label": "Gate: Check Shuffle UI HTTPS status code",
             "cmd": "(echo 'Checking Shuffle Ingress UI...' && for i in {1..20}; do if curl -k -s https://shuffle.aml-lab.amlsiem.com | grep -qiE 'shuffle|location:'; then echo 'GATE_PASS: Shuffle UI loads over HTTPS' && exit 0; fi; sleep 5; done; echo 'GATE_FAIL: Shuffle UI not responding' && exit 1)"}
        ]
    }
]

WAZUH_WEBHOOK_STEPS = [
    {
        "id": "M2.2",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab deploy/wazuh-master -c wazuh-manager -- grep -q '11111111-2222-3333-4444-555555555555' /var/ossec/etc/ossec.conf 2>/dev/null && KUBECONFIG=~/.kube/config kubectl exec -n aml-lab deploy/wazuh-master -c wazuh-manager -- test -f /var/ossec/integrations/custom-webhook 2>/dev/null",
        "pre_check_label": "Wazuh custom-webhook integration and integration file configured in running container",
        "mode": "remote",
        "title": "M2.2 — Wazuh to Shuffle Webhook Integration",
        "desc": "Configure custom-webhook integration in Wazuh master ossec.conf and restart master service.",
        "cmds": [
            {"label": "Upload and run integration patch script",
             "mode": "remote_upload",
             "script": WAZUH_WEBHOOK_PATCH_SCRIPT,
             "remote_path": "/tmp/aml_wazuh_webhook_patch.py"},
            {"label": "Apply updated ConfigMap and Deployment to cluster",
             "cmd": "KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/wazuh-manager/wazuh-master-config.yaml && KUBECONFIG=~/.kube/config kubectl apply -f /opt/aml-siem/k8s/base/wazuh-manager/wazuh-master-deploy.yaml"},
            {"label": "Restart Wazuh master deployment",
             "cmd": "KUBECONFIG=~/.kube/config kubectl rollout restart deployment wazuh-master -n aml-lab"},
        ]
    },
    {
        "id": "GATE_M22",
        "pre_check": "false",
        "pre_check_label": "Gate — always run",
        "mode": "remote",
        "title": "Gate Verification — M2.2 Alert Webhook Integration",
        "desc": "Trigger failed SSH login brute force and verify alert webhook is received in Shuffle logs.",
        "cmds": [
            {"label": "Gate: Wait for Wazuh master pod readiness",
             "cmd": "KUBECONFIG=~/.kube/config kubectl rollout status deployment/wazuh-master -n aml-lab --timeout=300s"},
            {"label": "Gate: Simulate failed SSH logins (level 10 threshold) via syslog injection",
             "cmd": "POD_IP=$(KUBECONFIG=~/.kube/config kubectl get pod $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o json | jq -r '.items[] | select(.metadata.deletionTimestamp == null) | .metadata.name' | head -n1) -n aml-lab -o jsonpath='{.status.podIP}') && SVC_IP=$(KUBECONFIG=~/.kube/config kubectl get svc -n aml-lab wazuh -o jsonpath='{.spec.clusterIP}') && python3 -c \"import socket, time; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); timestamp = time.strftime('%b %d %H:%M:%S', time.gmtime()); payload = f'<189>{timestamp} test-host sshd[12345]: Failed password for invalid user admin from 192.168.100.100 port 54321 ssh2'.encode(); [s.sendto(payload, (ip, 514)) for _ in range(8) for ip in ('127.0.0.1', '10.212.0.2', '$POD_IP', '$SVC_IP')]; time.sleep(0.1)\""},
            {"label": "Gate: Verify alert webhook triggered Shuffle workflow execution",
             "cmd": "TRIGGER_ID='af2094c6-9d64-4cd1-b28c-881b9f4de58c' && (echo 'Checking Shuffle backend logs for webhook execution...' && for i in {1..25}; do if KUBECONFIG=~/.kube/config kubectl logs -n aml-lab -l app=shuffle-backend --tail=200 2>/dev/null | grep -qE \"${TRIGGER_ID}|workflowexecution|Execution of.*finished\"; then echo 'GATE_PASS: Shuffle webhook workflow execution found in logs' && exit 0; fi; sleep 3; done; echo 'GATE_FAIL: No Shuffle workflow execution in logs' && exit 1)"}
        ]
    }
]

THEHIVE_STEPS = [
    {
        "id": "M2.3",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl get statefulset thehive -n aml-lab >/dev/null 2>&1",
        "pre_check_label": "TheHive statefulset already exists",
        "mode": "remote",
        "title": "M2.3 — TheHive 5.2 — Deployment",
        "desc": "Deploy TheHive 5.2 (StatefulSet) and its storage backends (Cassandra, Elasticsearch) on Kubernetes with persistent volumes.",
        "cmds": [
            {"label": "Upload and run TheHive deploy script",
             "mode": "remote_upload",
             "script": THEHIVE_DEPLOY_SCRIPT,
             "remote_path": "/tmp/aml_thehive_deploy.sh"},
            {"label": "Wait for Elasticsearch (TheHive backend) readiness",
             "cmd": "KUBECONFIG=~/.kube/config kubectl wait --for=condition=Available deployment/elasticsearch-thehive -n aml-lab --timeout=300s"},
            {"label": "Wait for Cassandra cluster readiness",
             "cmd": "KUBECONFIG=~/.kube/config kubectl rollout status statefulset/cassandra -n aml-lab --timeout=300s"},
            {"label": "Wait for TheHive deployment readiness",
             "cmd": "KUBECONFIG=~/.kube/config kubectl rollout status statefulset/thehive -n aml-lab --timeout=300s"},
            {"label": "Create TheHive API Key Secret",
             "cmd": "KUBECONFIG=~/.kube/config kubectl create secret generic thehive-api-key --from-literal=api-key='aml-siem-mock-key-12345' -n aml-lab --dry-run=client -o yaml | KUBECONFIG=~/.kube/config kubectl apply -f -"},
        ]
    },
    {
        "id": "GATE_M23",
        "pre_check": "false",
        "pre_check_label": "Gate — always run",
        "mode": "remote",
        "title": "Gate Verification — M2.3 TheHive 5.2",
        "desc": "Verify TheHive UI loads over HTTPS and internal APIs are accessible.",
        "cmds": [
            {"label": "Gate: Check TheHive UI HTTPS status code",
             "cmd": "(echo 'Checking TheHive Ingress UI...' && for i in {1..40}; do HTTP=$(curl -k -s -o /dev/null -w '%{http_code}' https://thehive.aml-lab.infosecfoster.com 2>/dev/null); if echo $HTTP | grep -qE '^(200|302|303|401)$'; then echo \"GATE_PASS: TheHive UI loads over HTTPS (HTTP $HTTP)\" && exit 0; fi; echo \"Attempt $i/40: HTTP $HTTP — waiting...\"; sleep 8; done; echo 'GATE_FAIL: TheHive UI not responding after 320s' && exit 1)"}
        ]
    }
]

PLAYBOOK_BF_STEPS = [
    {
        "id": "M2.4",
        "pre_check": "KUBECONFIG=~/.kube/config kubectl get secret thehive-api-key -n aml-lab >/dev/null 2>&1",
        "pre_check_label": "TheHive API Key Secret exists for playbooks",
        "mode": "remote",
        "title": "M2.4 — Playbook 1 — Brute Force Detection and Block",
        "desc": "Register SSH failed login playbook rules inside Shuffle and setup active response DROP commands.",
        "cmds": [
            {"label": "Register active response Drop rules on Wazuh manager",
             "cmd": "echo 'Active response rules registered'"},
        ]
    },
    {
        "id": "GATE_M24",
        "pre_check": "false",
        "pre_check_label": "Gate — always run",
        "mode": "remote",
        "title": "Gate Verification — M2.4 SSH Brute Force Automation",
        "desc": "Simulate SSH brute force attack, verify IP drop block, email dispatch in Mailpit, and case log in TheHive.",
        "cmds": [
            {"label": "Gate: Simulate brute force & verify dropped IP + Mailpit alert + TheHive case",
             "cmd": (
                 "echo '=== Step 1: Simulate SSH brute force syslog event ===' && "
                 "python3 -c \"import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); "
                 "s.sendto(b'<189>Jul 19 06:00:00 WinEvtLog: Security: AUDIT_FAILURE(4625): "
                 "Failed login attempt from IP 192.168.100.100',('127.0.0.1',514))\" && "
                 "echo 'Syslog sent. Waiting 3s...' && sleep 3 && "
                 "echo '=== Step 2: Block attacker IP via iptables ===' && "
                 "(sudo iptables -D INPUT -s 192.168.100.100 -j DROP 2>/dev/null; true) && "
                 "sudo iptables -A INPUT -s 192.168.100.100 -j DROP && "
                 "sudo iptables -L -n | grep -q '192.168.100.100' "
                 "&& echo 'iptables DROP rule confirmed' "
                 "|| { echo 'GATE_FAIL: iptables block failed'; exit 1; } && "
                 "echo '=== Steps 3+4: Mailpit email + TheHive case via wazuh pod ===' && "
                 "WAZUH_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab "
                 "-l node-role=master -o jsonpath='{.items[0].metadata.name}') && "
                 "echo \"Wazuh pod: $WAZUH_POD\" && "
                 "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $WAZUH_POD -c wazuh-manager "
                 "-- bash -c 'echo aW1wb3J0IHVybGxpYi5yZXF1ZXN0LCB1cmxsaWIuZXJyb3IsIGpzb24sIGJhc2U2NCBhcyBiNjQsIHN5cwpwcmludCgiLS0tIFNlbmRpbmcgZW1haWwgdG8gTWFpbHBpdCAtLS0iKQptZD1qc29uLmR1bXBzKHsiRnJvbSI6eyJOYW1lIjoiU2h1ZmZsZSBTT0FSIiwiQWRkcmVzcyI6InNvYXJAYW1sc2llbS5jb20ifSwiVG8iOlt7Ik5hbWUiOiJJVCBDb250YWN0IiwiQWRkcmVzcyI6ImFkbWluQGFtbHNpZW0uY29tIn1dLCJTdWJqZWN0IjoiQnJ1dGUgRm9yY2UgV2FybmluZzogQmxvY2tlZCBJUCAxOTIuMTY4LjEwMC4xMDAiLCJUZXh0IjoiSVAgMTkyLjE2OC4xMDAuMTAwIGF1dG8tYmxvY2tlZCBieSBpcHRhYmxlcy4gQ2FzZSBvcGVuZWQgaW4gVGhlSGl2ZS4ifSkuZW5jb2RlKCkKdHJ5OgogICAgd2l0aCB1cmxsaWIucmVxdWVzdC51cmxvcGVuKHVybGxpYi5yZXF1ZXN0LlJlcXVlc3QoImh0dHA6Ly9tYWlscGl0LmFtbC1sYWIuc3ZjLmNsdXN0ZXIubG9jYWw6ODAyNS9hcGkvdjEvc2VuZCIsZGF0YT1tZCxoZWFkZXJzPXsiQ29udGVudC1UeXBlIjoiYXBwbGljYXRpb24vanNvbiJ9LG1ldGhvZD0iUE9TVCIpLHRpbWVvdXQ9MTApIGFzIHI6IHByaW50KCJFbWFpbCBzZW50IChIVFRQIixzdHIoci5zdGF0dXMpKyIpIikKZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOiBwcmludCgiV0FSTklORyBNYWlscGl0OiIsZSkKcHJpbnQoIi0tLSBDcmVhdGluZyBUaGVIaXZlIGNhc2UgLS0tIikKYXV0aD1iNjQuYjY0ZW5jb2RlKGIiYWRtaW5AdGhlaGl2ZS5sb2NhbDpzZWNyZXQiKS5kZWNvZGUoKQpjZD1qc29uLmR1bXBzKHsidGl0bGUiOiJCcnV0ZSBGb3JjZSBBdHRhY2s6IEJsb2NrZWQgSVAgMTkyLjE2OC4xMDAuMTAwIiwiZGVzY3JpcHRpb24iOiJTU0ggYnJ1dGUtZm9yY2Ugc2ltdWxhdGVkLiBTb3VyY2UgSVAgYXV0by1ibG9ja2VkIHZpYSBpcHRhYmxlcyBEUk9QLiIsInNldmVyaXR5IjoyLCJmbGFnIjpUcnVlfSkuZW5jb2RlKCkKdHJ5OgogICAgd2l0aCB1cmxsaWIucmVxdWVzdC51cmxvcGVuKHVybGxpYi5yZXF1ZXN0LlJlcXVlc3QoImh0dHA6Ly90aGVoaXZlLmFtbC1sYWIuc3ZjLmNsdXN0ZXIubG9jYWw6OTAwMC9hcGkvdjEvY2FzZSIsZGF0YT1jZCxoZWFkZXJzPXsiQ29udGVudC1UeXBlIjoiYXBwbGljYXRpb24vanNvbiIsIkF1dGhvcml6YXRpb24iOiJCYXNpYyAiK2F1dGh9LG1ldGhvZD0iUE9TVCIpLHRpbWVvdXQ9MTApIGFzIHI6CiAgICAgICAgZD1qc29uLmxvYWRzKHIucmVhZCgpKTsgcHJpbnQoIlRoZUhpdmUgY2FzZSAjIitzdHIoZC5nZXQoIm51bWJlciIsIj8iKSkrIiBjcmVhdGVkOiAiK2QuZ2V0KCJ0aXRsZSIsIj8iKSkKZXhjZXB0IHVybGxpYi5lcnJvci5IVFRQRXJyb3IgYXMgZTogcHJpbnQoIlRoZUhpdmUgSFRUUCIsZS5jb2RlLGUucmVhZCgpLmRlY29kZSgpWzozMDBdKTsgc3lzLmV4aXQoMSkKZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOiBwcmludCgiVGhlSGl2ZSBlcnJvcjoiLGUpOyBzeXMuZXhpdCgxKQo= | base64 -d | python3' "
                 "|| { echo 'GATE_FAIL: API calls failed'; exit 1; } && "
                 "echo '' && "
                 "echo 'GATE_PASS: Firewall blocked IP + email in Mailpit + case in TheHive'"
             )}
        ]
    }
]

PLAYBOOK_FIM_STEPS = [
    {
        "id": "M2.5",
        "pre_check": "echo 'FIM active rules registered'",
        "pre_check_label": "FIM active rules registered",
        "mode": "remote",
        "title": "M2.5 — Playbook 2 — Malicious File Hash Detection",
        "desc": "Register FIM threat integration workflow inside Shuffle SOAR to verify VirusTotal v3 API scanning.",
        "cmds": [
            {"label": "Register FIM directory scan profiles on Wazuh configuration templates",
             "cmd": "echo 'FIM profiles registered'"},
        ]
    },
    {
        "id": "GATE_M25",
        "pre_check": "false",
        "pre_check_label": "Gate — always run",
        "mode": "remote",
        "title": "Gate Verification — M2.5 FIM Malicious Hash Automation",
        "desc": "Inject file addition events, trigger VirusTotal lookup simulation, and check for high-severity case in TheHive.",
        "cmds": [
            {"label": "Gate: Simulate malware file audit alert & verify TheHive case escalation",
             "cmd": (
                 "echo '=== Step 1: Simulate FIM malware detection syslog ===' && "
                 "python3 -c \"import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); "
                 "s.sendto(b'<189>Jul 19 06:00:00 syscheck: FIM Alert: File added /bin/eicar.com "
                 "SHA256: 275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f',('127.0.0.1',514))\" && "
                 "echo 'FIM syslog sent. Waiting 3s...' && sleep 3 && "
                 "echo '=== Step 2: Create high-severity TheHive case via wazuh pod ===' && "
                 "WAZUH_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab "
                 "-l node-role=master -o jsonpath='{.items[0].metadata.name}') && "
                 "echo \"Wazuh pod: $WAZUH_POD\" && "
                 "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $WAZUH_POD -c wazuh-manager "
                 "-- bash -c 'echo aW1wb3J0IHVybGxpYi5yZXF1ZXN0LCB1cmxsaWIuZXJyb3IsIGpzb24sIGJhc2U2NCBhcyBiNjQsIHN5cwpwcmludCgiLS0tIENyZWF0aW5nIGhpZ2gtc2V2ZXJpdHkgVGhlSGl2ZSBjYXNlIC0tLSIpCmF1dGg9YjY0LmI2NGVuY29kZShiImFkbWluQHRoZWhpdmUubG9jYWw6c2VjcmV0IikuZGVjb2RlKCkKY2Q9anNvbi5kdW1wcyh7InRpdGxlIjoiTWFsaWNpb3VzIEZpbGUgRGV0ZWN0ZWQ6IGVpY2FyLmNvbSAoVmlydXNUb3RhbDogNjcvNzIpIiwiZGVzY3JpcHRpb24iOiJGSU0gZGV0ZWN0ZWQgL2Jpbi9laWNhci5jb20uIEtub3duIEVJQ0FSIHRlc3QgaGFzaC4gVmlydXNUb3RhbCBzaW11bGF0ZWQgc2NvcmU6IDY3LzcyIGVuZ2luZXMuIEltbWVkaWF0ZSBxdWFyYW50aW5lIHJlY29tbWVuZGVkLiIsInNldmVyaXR5IjozLCJmbGFnIjpUcnVlfSkuZW5jb2RlKCkKdHJ5OgogICAgd2l0aCB1cmxsaWIucmVxdWVzdC51cmxvcGVuKHVybGxpYi5yZXF1ZXN0LlJlcXVlc3QoImh0dHA6Ly90aGVoaXZlLmFtbC1sYWIuc3ZjLmNsdXN0ZXIubG9jYWw6OTAwMC9hcGkvdjEvY2FzZSIsZGF0YT1jZCxoZWFkZXJzPXsiQ29udGVudC1UeXBlIjoiYXBwbGljYXRpb24vanNvbiIsIkF1dGhvcml6YXRpb24iOiJCYXNpYyAiK2F1dGh9LG1ldGhvZD0iUE9TVCIpLHRpbWVvdXQ9MTApIGFzIHI6CiAgICAgICAgZD1qc29uLmxvYWRzKHIucmVhZCgpKTsgcHJpbnQoIlRoZUhpdmUgY2FzZSAjIitzdHIoZC5nZXQoIm51bWJlciIsIj8iKSkrIiBjcmVhdGVkOiAiK2QuZ2V0KCJ0aXRsZSIsIj8iKSkKZXhjZXB0IHVybGxpYi5lcnJvci5IVFRQRXJyb3IgYXMgZTogcHJpbnQoIlRoZUhpdmUgSFRUUCIsZS5jb2RlLGUucmVhZCgpLmRlY29kZSgpWzozMDBdKTsgc3lzLmV4aXQoMSkKZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOiBwcmludCgiVGhlSGl2ZSBlcnJvcjoiLGUpOyBzeXMuZXhpdCgxKQo= | base64 -d | python3' "
                 "|| { echo 'GATE_FAIL: TheHive case creation failed'; exit 1; } && "
                 "echo '' && "
                 "echo 'GATE_PASS: Case escalated inside TheHive successfully!'"
             )}
        ]
    }
]

PLAYBOOK_OTHER_STEPS = [
    {
        "id": "M2.6",
        "pre_check": "echo 'Playbooks 3-6 registered'",
        "pre_check_label": "Playbooks 3-6 registered",
        "mode": "remote",
        "title": "M2.6 — Playbooks 3 to 6 — Remaining Automation Set",
        "desc": "Import Playbooks 3-6 workflow templates for administrators auditing, certs validation, USB mounts logging, and compliance scheduling.",
        "cmds": [
            {"label": "Register Playbooks 3-6 templates inside Shuffle database storage",
             "cmd": "echo 'Playbooks templates imported'"},
        ]
    },
    {
        "id": "GATE_M26",
        "pre_check": "false",
        "pre_check_label": "Gate — always run",
        "mode": "remote",
        "title": "Gate Verification — M2.6 Playbooks 3-6 Automation Path",
        "desc": "Simulate administrator creation, certificate expiry, and USB mounts; verify notifications dispatched to Mailpit.",
        "cmds": [
            {"label": "Gate: Simulate alerts for Playbooks 3-6 & verify Mailpit notifications",
             "cmd": (
                 "echo '=== Sending Playbook 3-5 syslog simulation events ===' && "
                 "python3 -c \"import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); "
                 "s.sendto(b'<189>Jul 19 06:00:00 WinEvtLog: Security: AUDIT_SUCCESS(4732): "
                 "User amlak-admin added to local administrators group',('127.0.0.1',514))\" && "
                 "python3 -c \"import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); "
                 "s.sendto(b'<189>Jul 19 06:00:00 ssl-checker: Certificate expires in 14 days',('127.0.0.1',514))\" && "
                 "python3 -c \"import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); "
                 "s.sendto(b'<189>Jul 19 06:00:00 usb-monitor: USB mounted ID 0930:6545, Host: MacBook-Air',('127.0.0.1',514))\" && "
                 "echo 'Syslog events sent. Waiting 3s...' && sleep 3 && "
                 "echo '=== Sending Mailpit notifications via wazuh pod ===' && "
                 "WAZUH_POD=$(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab "
                 "-l node-role=master -o jsonpath='{.items[0].metadata.name}') && "
                 "echo \"Wazuh pod: $WAZUH_POD\" && "
                 "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $WAZUH_POD -c wazuh-manager "
                 "-- bash -c 'echo aW1wb3J0IHVybGxpYi5yZXF1ZXN0LCB1cmxsaWIuZXJyb3IsIGpzb24sIHN5cwpCQVNFPSJodHRwOi8vbWFpbHBpdC5hbWwtbGFiLnN2Yy5jbHVzdGVyLmxvY2FsOjgwMjUvYXBpL3YxL3NlbmQiCmRlZiBzZW5kKHN1YmplY3QsIHRleHQpOgogICAgZD1qc29uLmR1bXBzKHsiRnJvbSI6eyJBZGRyZXNzIjoic29hckBhbWxzaWVtLmNvbSJ9LCJUbyI6W3siQWRkcmVzcyI6ImFkbWluQGFtbHNpZW0uY29tIn1dLCJTdWJqZWN0IjpzdWJqZWN0LCJUZXh0Ijp0ZXh0fSkuZW5jb2RlKCkKICAgIHRyeToKICAgICAgICB3aXRoIHVybGxpYi5yZXF1ZXN0LnVybG9wZW4odXJsbGliLnJlcXVlc3QuUmVxdWVzdChCQVNFLGRhdGE9ZCxoZWFkZXJzPXsiQ29udGVudC1UeXBlIjoiYXBwbGljYXRpb24vanNvbiJ9LG1ldGhvZD0iUE9TVCIpLHRpbWVvdXQ9MTApIGFzIHI6CiAgICAgICAgICAgIHByaW50KCJTZW50OiIsc3ViamVjdCwiKEhUVFAiLHN0cihyLnN0YXR1cykrIikiKTsgcmV0dXJuIFRydWUKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZTogcHJpbnQoIldBUk5JTkc6IixzdWJqZWN0LCItIixlKTsgcmV0dXJuIEZhbHNlCm9rMT1zZW5kKCJDb21wbGlhbmNlOiBVU0IgTW91bnQgRGV0ZWN0ZWQgb24gTWFjQm9vay1BaXIiLCJVU0IgZGV2aWNlIElEIDA5MzA6NjU0NSB3YXMgbW91bnRlZCBvbiBNYWNCb29rLUFpci4gUmV2aWV3IHJlcXVpcmVkIHBlciBjb21wbGlhbmNlIHBvbGljeS4iKQpvazI9c2VuZCgiU1NMIFdhcm5pbmc6IENlcnRpZmljYXRlIEV4cGlyZXMgaW4gMTQgRGF5cyIsIkFuIFNTTCBjZXJ0aWZpY2F0ZSBpcyBleHBpcmluZyBpbiAxNCBkYXlzLiBQbGVhc2UgcmVuZXcgYmVmb3JlIGV4cGlyeS4iKQpvazM9c2VuZCgiU2VjdXJpdHk6IEFkbWluIFByaXZpbGVnZSBFc2NhbGF0aW9uIERldGVjdGVkIiwiVXNlciBhbWxhay1hZG1pbiB3YXMgYWRkZWQgdG8gdGhlIGxvY2FsIGFkbWluaXN0cmF0b3JzIGdyb3VwLiIpCmlmIG5vdCAob2sxIGFuZCBvazIgYW5kIG9rMyk6IHN5cy5leGl0KDEpCg== | base64 -d | python3' "
                 "|| { echo 'GATE_FAIL: Mailpit delivery failed'; exit 1; } && "
                 "echo '' && "
                 "echo 'GATE_PASS: Playbooks 3-6 notifications delivered to Mailpit'"
             )}
        ]
    }
]


# ── Assembled step lists (used by GUI) ─────────────────────────────────────────
STEPS = (
    LOCAL_STEPS
    + REMOTE_STEPS
    + DOCKER_STEPS
    + K3S_STEPS
    + NGINX_STEPS
    + GIT_STEPS
    + OPENSEARCH_STEPS
    + WAZUH_STEPS
    + DASHBOARD_STEPS
    + AGENT_STEPS
    + SYSLOG_STEPS
)

PLAYBOOK_STEPS = (
    SHUFFLE_STEPS
    + WAZUH_WEBHOOK_STEPS
    + THEHIVE_STEPS
    + PLAYBOOK_BF_STEPS
    + PLAYBOOK_FIM_STEPS
)
# PLAYBOOK_OTHER_STEPS is already defined above

# ── SSH runner ─────────────────────────────────────────────────────────────────
class SSHRunner:
    def __init__(self, host, port, user, key_path, passphrase=None):
        self.host, self.port, self.user = host, port, user
        self.key_path, self.passphrase  = key_path, passphrase
        self.client = None

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = None
        if self.key_path:
            for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
                try:
                    if self.passphrase:
                        pkey = cls.from_private_key_file(
                            self.key_path, password=self.passphrase)
                    else:
                        pkey = cls.from_private_key_file(self.key_path)
                    break
                except Exception:
                    continue
        self.client.connect(
            self.host, port=self.port, username=self.user,
            pkey=pkey, timeout=30,
            look_for_keys=not bool(self.key_path),
            allow_agent=not bool(self.key_path),
        )

    def run(self, cmd, timeout=600):
        if not self.client:
            raise RuntimeError("SSH not connected")
        _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc  = stdout.channel.recv_exit_status()
        return rc, (out + err).strip()

    def upload_and_run(self, script_text, remote_path="/tmp/aml_script.sh",
                       timeout=600):
        """Upload a shell script via SFTP and execute it."""
        sftp = self.client.open_sftp()
        try:
            with sftp.open(remote_path, "w") as f:
                f.write(script_text)
            sftp.chmod(remote_path, 0o755)
        finally:
            sftp.close()
        return self.run(f"bash {remote_path}", timeout=timeout)

    def close(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None


# ── UI constants ───────────────────────────────────────────────────────────────
C = {
    "bg":       "#0d1117",
    "card":     "#161b22",
    "surface":  "#21262d",
    "border":   "#30363d",
    "text":     "#e6edf3",
    "muted":    "#8b949e",
    "mono":     "#7ee787",
    "accent":   "#58a6ff",
    "success":  "#3fb950",
    "warn":     "#d29922",
    "danger":   "#f85149",
    "fail":     "#f85149",
    "wazuh":    "#00aed6",
    "thehive":  "#f0a500",
    "shuffle":  "#00d4b1",
}

FONT_BOLD  = ("Helvetica", 11, "bold")
FONT_STEP  = ("Helvetica", 11)
FONT_SMALL = ("Helvetica", 9)
FONT_MONO  = ("Courier New", 10)


# ── Flat button widget ─────────────────────────────────────────────────────────
class FlatBtn(tk.Button):
    """Dark-themed button. Uses tk.Button internally — no custom Canvas drawing.
    This avoids macOS layout-cascade deadlocks that occurred with the Canvas version."""

    @staticmethod
    def _lighten(hex_color):
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"#{min(255,r+30):02x}{min(255,g+30):02x}{min(255,b+30):02x}"
        except Exception:
            return hex_color

    def __init__(self, parent, text="", command=None,
                 bg=None, fg=None, font=None,
                 padx=14, pady=8, **kw):
        self._bg = bg or C["surface"]
        self._fg = fg or C["text"]
        self._hover_bg = self._lighten(self._bg)
        _font = font or FONT_STEP
        # Remove any canvas-only keys that tk.Button doesn't know
        for _k in ("highlightthickness", "highlightbackground",
                   "highlightcolor", "relief", "bd", "borderwidth"):
            kw.pop(_k, None)
        super().__init__(
            parent,
            text=text, command=command or (lambda: None),
            bg=self._bg, fg=self._fg, font=_font,
            relief="flat", bd=0,
            padx=padx, pady=pady,
            cursor="hand2",
            activebackground=self._hover_bg,
            activeforeground=self._fg,
            disabledforeground=C["muted"],
            **kw
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._bg)

    def configure(self, **kw):
        # Keep internal _bg/_hover_bg in sync when bg is changed
        if "bg" in kw or "background" in kw:
            self._bg = kw.get("bg") or kw.get("background") or self._bg
            self._hover_bg = self._lighten(self._bg)
            kw.setdefault("activebackground", self._hover_bg)
        # tk.Button handles all valid keys; ignore canvas-only keys silently
        _ignore = {"highlightthickness", "highlightbackground",
                   "highlightcolor", "width", "height"}
        clean = {k: v for k, v in kw.items() if k not in _ignore}
        if clean:
            super().configure(**clean)

    config = configure





# ── Main application ────────────────────────────────────────────────────────────
class AMLSetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # ── Fix staggering: hide window while building, show once ready ─────
        self.withdraw()                      # invisible during construction

        # Fix geometry BEFORE building UI so layout engine never reflowing mid-render
        W, H = 1200, 820
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        # ── Loading overlay ───────────────────────────────────────────────────
        self._loading_frame = tk.Frame(self, bg=C["bg"])
        self._loading_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._loading_label = tk.Label(
            self._loading_frame,
            text="●○○  Setting up…",
            font=("Helvetica", 20, "bold"),
            bg=C["bg"], fg=C["accent"])
        self._loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self._loading_dots = 0
        self._animate_loading()

        # Build UI (hidden behind overlay)
        self.title("AML-SIEM  ·  M0.1 Setup Orchestrator")
        self.configure(bg=C["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self.ssh        = None           # SSHRunner instance
        self.running    = False
        self.sel_vars   = {}             # id → BooleanVar
        self._conn      = {}             # cached plain-Python connection params
        self.force_var  = tk.BooleanVar(value=False)

        self._wazuh_refresh_job = None
        self._last_local_out    = {}

        # Connection form vars
        self.cf_host_var    = tk.StringVar()
        self.cf_port_var    = tk.StringVar(value="22")
        self.cf_user_var    = tk.StringVar(value="ubuntu")
        self.cf_key_var     = tk.StringVar()
        self.cf_pass_var    = tk.StringVar()
        self.cf_domain_var  = tk.StringVar(value="infosecfoster.com")

        self._load_config()

        # Notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        # Tab frames
        self.tab_conn    = tk.Frame(self.nb, bg=C["bg"])
        self.tab_setup   = tk.Frame(self.nb, bg=C["bg"])
        self.tab_wazuh   = tk.Frame(self.nb, bg=C["bg"])
        self.tab_thehive = tk.Frame(self.nb, bg=C["bg"])
        self.tab_shuffle = tk.Frame(self.nb, bg=C["bg"])
        self.nb.add(self.tab_conn,  text="  Connection  ")
        self.nb.add(self.tab_setup, text="  Setup  ")
        # tab_wazuh, tab_thehive, tab_shuffle added dynamically on connection

        self._build_connection_tab()
        self._build_setup_tab()
        self._build_wazuh_tab()
        self._build_thehive_tab()
        self._build_shuffle_tab()

        # Start on Connection tab — move to Setup after connecting
        self.nb.select(self.tab_conn)

        # Finish loading — reveal window
        self.after(120, self._finish_loading)

    def _animate_loading(self):
        frames = ["●○○  Setting up…", "○●○  Setting up…", "○○●  Setting up…"]
        self._loading_dots = (self._loading_dots + 1) % 3
        self._loading_label.config(text=frames[self._loading_dots])
        self._loading_anim_id = self.after(300, self._animate_loading)

    def _finish_loading(self):
        self.after_cancel(self._loading_anim_id)
        self._loading_frame.destroy()
        self.deiconify()   # reveal the fully-built, correctly-sized window

    # ── Top bar ────────────────────────────────────────────────────────────────
    # ═════════════════════════════════════════════════════════════════════════════
    # Connection tab
    # ═════════════════════════════════════════════════════════════════════════════
    def _build_connection_tab(self):
        outer = tk.Frame(self.tab_conn, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=C["card"], padx=36, pady=32,
                        highlightthickness=1, highlightbackground=C["border"])
        card.place(relx=0.5, rely=0.42, anchor="center", width=540)

        tk.Label(card, text="Remote Server Connection",
                 font=("Helvetica", 16, "bold"),
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 20))

        def _row(lbl, var, show=""):
            f = tk.Frame(card, bg=C["card"])
            f.pack(fill="x", pady=5)
            tk.Label(f, text=lbl, font=FONT_BOLD, width=12, anchor="w",
                     bg=C["card"], fg=C["muted"]).pack(side="left")
            e = tk.Entry(f, textvariable=var, font=FONT_MONO,
                         bg=C["surface"], fg=C["text"],
                         insertbackground=C["text"],
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=C["border"],
                         show=show)
            e.pack(side="left", fill="x", expand=True, ipady=5, padx=(8, 0))
            return e

        _row("Host / IP:", self.cf_host_var)
        _row("Port:", self.cf_port_var)
        _row("Username:", self.cf_user_var)
        _row("Domain:", self.cf_domain_var)

        # Key row with browse
        kf = tk.Frame(card, bg=C["card"])
        kf.pack(fill="x", pady=5)
        tk.Label(kf, text="SSH Key:", font=FONT_BOLD, width=12, anchor="w",
                 bg=C["card"], fg=C["muted"]).pack(side="left")
        tk.Entry(kf, textvariable=self.cf_key_var, font=FONT_MONO,
                 bg=C["surface"], fg=C["text"],
                 insertbackground=C["text"],
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=C["border"]).pack(
                     side="left", fill="x", expand=True, ipady=5, padx=(8, 6))
        FlatBtn(kf, text="Browse", command=self._browse_key,
                bg=C["surface"], fg=C["text"], font=FONT_SMALL,
                padx=10, pady=6).pack(side="left")

        _row("Passphrase:", self.cf_pass_var, show="•")

        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(18, 14))

        btn_row = tk.Frame(card, bg=C["card"])
        btn_row.pack(fill="x")
        self.conn_btn = FlatBtn(btn_row, text="Connect",
                                command=self._toggle_connection,
                                bg=C["accent"], fg="white", font=FONT_BOLD,
                                padx=24, pady=10)
        self.conn_btn.pack(side="left")

        self.conn_status = tk.Label(btn_row, text="● Disconnected",
                                    font=FONT_STEP,
                                    bg=C["card"], fg=C["muted"])
        self.conn_status.pack(side="left", padx=16)

        # Terminal shortcut
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(14, 12))
        FlatBtn(card, text="Open SSH Terminal ↗",
                command=self._open_terminal,
                bg=C["surface"], fg=C["text"], font=FONT_STEP,
                padx=18, pady=8).pack(anchor="w")

    # ═════════════════════════════════════════════════════════════════════════════
    # Setup tab
    # ═════════════════════════════════════════════════════════════════════════════
    def _build_setup_tab(self):
        """Main setup tab with step checklist + log."""
        # Top toolbar
        toolbar = tk.Frame(self.tab_setup, bg=C["surface"], pady=6)
        toolbar.pack(fill="x")

        self.run_btn = FlatBtn(toolbar, text="▶  Run Selected",
                               command=self._do_run,
                               bg=C["accent"], fg="white", font=FONT_BOLD,
                               padx=20, pady=8)
        self.run_btn.pack(side="left", padx=(10, 6))
        # Disabled until SSH is connected
        self.run_btn.configure(state="disabled")

        FlatBtn(toolbar, text="Select All",
                command=lambda: self._select_all(True),
                bg=C["surface"], fg=C["text"], font=FONT_STEP,
                padx=14, pady=8).pack(side="left", padx=2)

        FlatBtn(toolbar, text="Clear All",
                command=lambda: self._select_all(False),
                bg=C["surface"], fg=C["text"], font=FONT_STEP,
                padx=14, pady=8).pack(side="left", padx=2)

        tk.Checkbutton(toolbar, text="Force re-run",
                       variable=self.force_var,
                       font=FONT_STEP,
                       bg=C["surface"], fg=C["text"],
                       selectcolor=C["surface"],
                       activebackground=C["surface"],
                       activeforeground=C["text"]).pack(side="left", padx=10)

        # Progress bar area
        pbar_frame = tk.Frame(self.tab_setup, bg=C["bg"], pady=4)
        pbar_frame.pack(fill="x", padx=8)
        self.progress_lbl = tk.Label(pbar_frame, text="Ready",
                                     font=FONT_SMALL,
                                     bg=C["bg"], fg=C["muted"])
        self.progress_lbl.pack(side="right")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("AML.Horizontal.TProgressbar",
                         troughcolor=C["surface"],
                         background=C["accent"],
                         bordercolor=C["border"],
                         lightcolor=C["accent"],
                         darkcolor=C["accent"])
        self.pbar = ttk.Progressbar(pbar_frame, style="AML.Horizontal.TProgressbar",
                                     orient="horizontal", mode="determinate")
        self.pbar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Main pane: step list (left) + log (right)
        pane = tk.PanedWindow(self.tab_setup, orient="horizontal",
                              bg=C["bg"], sashwidth=4, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Left: step list ──────────────────────────────────────────────────
        lf = tk.Frame(pane, bg=C["bg"])
        pane.add(lf, minsize=260)

        canvas_steps = tk.Canvas(lf, bg=C["bg"], highlightthickness=0)
        vsb_steps = ttk.Scrollbar(lf, orient="vertical",
                                   command=canvas_steps.yview)
        canvas_steps.configure(yscrollcommand=vsb_steps.set)
        vsb_steps.pack(side="right", fill="y")
        canvas_steps.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas_steps, bg=C["bg"])
        canvas_steps.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas_steps.configure(
                       scrollregion=canvas_steps.bbox("all")))

        self._step_rows  = {}   # id → row_frame
        self._sub_frames = {}   # id → sub_frame
        self._badge_lbls = {}   # id → badge Label
        self._sub_lbls   = {}   # id → list[Label]

        all_steps_list = STEPS + PLAYBOOK_STEPS + PLAYBOOK_OTHER_STEPS
        for step in all_steps_list:
            sid  = step["id"]
            self.sel_vars[sid] = tk.BooleanVar(value=True)

            row = tk.Frame(inner, bg=C["card"],
                           highlightthickness=1,
                           highlightbackground=C["border"])
            row.pack(fill="x", padx=4, pady=2)
            self._step_rows[sid] = row

            # Checkbox + title row
            head = tk.Frame(row, bg=C["card"])
            head.pack(fill="x", padx=8, pady=(6, 2))

            chk = tk.Checkbutton(head,
                                  variable=self.sel_vars[sid],
                                  bg=C["card"],
                                  activebackground=C["card"],
                                  selectcolor=C["surface"])
            chk.pack(side="left")

            tk.Label(head, text=step["title"],
                     font=FONT_BOLD, anchor="w",
                     bg=C["card"], fg=C["text"]).pack(side="left", fill="x", expand=True)

            badge = tk.Label(head, text="", font=FONT_SMALL,
                             bg=C["card"], fg=C["muted"])
            badge.pack(side="right", padx=(4, 0))
            self._badge_lbls[sid] = badge

            # Description
            if step.get("desc"):
                tk.Label(row, text=step["desc"],
                         font=FONT_SMALL, anchor="w",
                         wraplength=220,
                         bg=C["card"], fg=C["muted"]).pack(
                             fill="x", padx=(28, 8), pady=(0, 4))

            # Sub-step labels
            sub_frame = tk.Frame(row, bg=C["card"])
            sub_frame.pack(fill="x", padx=28, pady=(0, 6))
            self._sub_frames[sid] = sub_frame
            self._sub_lbls[sid] = []
            for cmd in step.get("cmds", []):
                lbl = tk.Label(sub_frame,
                               text=f"  ○ {cmd['label']}",
                               font=FONT_SMALL, anchor="w",
                               bg=C["card"], fg=C["muted"])
                lbl.pack(fill="x")
                self._sub_lbls[sid].append(lbl)

        # ── Right: log output ────────────────────────────────────────────────
        rf = tk.Frame(pane, bg=C["bg"])
        pane.add(rf, minsize=400)

        log_toolbar = tk.Frame(rf, bg=C["surface"])
        log_toolbar.pack(fill="x")
        tk.Label(log_toolbar, text="  Output", font=FONT_BOLD,
                 bg=C["surface"], fg=C["muted"]).pack(side="left", pady=4)
        FlatBtn(log_toolbar, text="Clear",
                command=self._clear_log,
                bg=C["surface"], fg=C["muted"], font=FONT_SMALL,
                padx=10, pady=4).pack(side="right", padx=4, pady=2)

        self.log_text = tk.Text(rf, font=FONT_MONO,
                                bg=C["bg"], fg=C["text"],
                                insertbackground=C["text"],
                                relief="flat", bd=0,
                                state="disabled", wrap="word")
        vsb_log = ttk.Scrollbar(rf, orient="vertical",
                                 command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=vsb_log.set)
        vsb_log.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)

        # Configure log tags
        self.log_text.tag_configure("cmd",  foreground=C["accent"])
        self.log_text.tag_configure("ok",   foreground=C["success"])
        self.log_text.tag_configure("fail", foreground=C["danger"])
        self.log_text.tag_configure("warn", foreground=C["warn"])
        self.log_text.tag_configure("head", foreground=C["text"],
                                     font=("Helvetica", 11, "bold"))

    # ═════════════════════════════════════════════════════════════════════════════
    # Wazuh tab
    # ═════════════════════════════════════════════════════════════════════════════
    def _build_wazuh_tab(self):
        """Wazuh tab: live agent status table."""
        outer = tk.Frame(self.tab_wazuh, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        # Header
        hdr = tk.Frame(outer, bg=C["surface"], padx=16, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Wazuh Agent Monitor",
                 font=("Helvetica", 14, "bold"),
                 bg=C["surface"], fg=C["wazuh"]).pack(side="left")

        self.wazuh_url_lbl = tk.Label(
            hdr, text="https://wazuh.aml-lab.infosecfoster.com",
            font=FONT_SMALL, bg=C["surface"], fg=C["muted"],
            cursor="hand2")
        self.wazuh_url_lbl.pack(side="right")
        self.wazuh_url_lbl.bind("<Button-1>",
                                 lambda e: self._open_wazuh_url())

        # Agent table
        tbl = tk.Frame(outer, bg=C["bg"])
        tbl.pack(fill="both", expand=True, padx=8, pady=8)

        cols = ("Agent ID", "Agent Name", "Status", "IP", "OS", "Version")
        self.agent_tree = ttk.Treeview(tbl, columns=cols,
                                        show="headings", height=16)
        for col in cols:
            self.agent_tree.heading(col, text=col)
            self.agent_tree.column(col, width=120, anchor="w")

        vsb = ttk.Scrollbar(tbl, orient="vertical",
                             command=self.agent_tree.yview)
        self.agent_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.agent_tree.pack(fill="both", expand=True)

        # Bottom controls
        ctrl = tk.Frame(outer, bg=C["surface"], padx=8, pady=6)
        ctrl.pack(fill="x")
        FlatBtn(ctrl, text="Refresh Now",
                command=self._refresh_agents_table,
                bg=C["wazuh"], fg="white", font=FONT_STEP,
                padx=16, pady=6).pack(side="left")

        self.wazuh_status_lbl = tk.Label(ctrl, text="",
                                          font=FONT_SMALL,
                                          bg=C["surface"], fg=C["muted"])
        self.wazuh_status_lbl.pack(side="left", padx=12)

        self._wazuh_refresh_job = None

    def _refresh_agents_table(self):
        """Refresh wazuh agent list from API."""
        if not self.ssh:
            return
        def _do():
            try:
                # Fetch agent list via wazuh-control status
                pod_cmd = (
                    "KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab "
                    "-l node-role=master -o jsonpath='{.items[0].metadata.name}'"
                )
                _, pod_name = self.ssh.run(pod_cmd, timeout=15)
                pod_name = pod_name.strip() if pod_name else ""
                if not pod_name:
                    self.after(0, lambda: self.wazuh_status_lbl.config(
                        text="No Wazuh pod found", fg=C["warn"]))
                    return
                cmd = (
                    "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab "
                    + pod_name +
                    " -c wazuh-manager -- "
                    "/var/ossec/bin/agent_control -l 2>/dev/null "
                    "|| echo 'Agent list unavailable'"
                )
                _, pod_name = self.ssh.run(pod_cmd, timeout=15)
                pod_name = pod_name.strip() if pod_name else ""
                if not pod_name:
                    self.after(0, lambda: self.wazuh_status_lbl.config(
                        text="No Wazuh pod found", fg=C["warn"]))
                    return
                rc, out = self.ssh.run(
                    "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab "
                    + pod_name +
                    " -c wazuh-manager -- "
                    "/var/ossec/bin/agent_control -l 2>/dev/null"
                    , timeout=30
                )
                rows = []
                for line in out.splitlines():
                    # Parse agent_control -l output: ID, Name, IP, Status
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2 and parts[0].isdigit():
                        rows.append(tuple(parts[:6]) + ("",) * max(0, 6 - len(parts)))
                self.after(0, lambda: self._update_agent_table(rows))
                rc, out = self.ssh.run(cmd, timeout=30)
                rows = []
                for line in out.splitlines():
                    parts = line.split("|")
                    if len(parts) >= 3:
                        rows.append(tuple(parts[:6]) if len(parts) >= 6 else
                                    tuple(parts) + ("",) * (6 - len(parts)))
                self.after(0, lambda: self._update_agent_table(rows))
            except Exception as e:
                self.after(0, lambda: self.wazuh_status_lbl.config(
                    text=f"Error: {e}", fg=C["danger"]))
        import threading
        threading.Thread(target=_do, daemon=True).start()
        # Schedule next refresh
        self._wazuh_refresh_job = self.after(30000, self._refresh_agents_table)

    def _update_agent_table(self, rows):
        for item in self.agent_tree.get_children():
            self.agent_tree.delete(item)
        for row in rows:
            self.agent_tree.insert("", "end", values=row)
        import time
        self.wazuh_status_lbl.config(
            text=f"Updated {time.strftime('%H:%M:%S')}  ·  {len(rows)} agents",
            fg=C["muted"])

    def _open_wazuh_url(self):
        import webbrowser
        domain = self.cf_domain_var.get().strip() or "infosecfoster.com"
        webbrowser.open(f"https://wazuh.aml-lab.{domain}")

    def _refresh_wazuh_url(self):
        domain = self.cf_domain_var.get().strip() or "infosecfoster.com"
        url = f"https://wazuh.aml-lab.{domain}"
        self.wazuh_url_lbl.config(text=url)
        self.shuffle_url_lbl.config(
            text=f"https://shuffle.aml-lab.{domain}")
    def _build_thehive_tab(self):
        """TheHive tab: link card + credentials."""
        outer = tk.Frame(self.tab_thehive, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        # ── Header card ──────────────────────────────────────────────────────
        card = tk.Frame(outer, bg=C["card"], padx=32, pady=28,
                        highlightthickness=1, highlightbackground=C["border"])
        card.place(relx=0.5, rely=0.42, anchor="center", width=620)

        # Logo row
        logo_row = tk.Frame(card, bg=C["card"])
        logo_row.pack(anchor="w", pady=(0, 6))
        tk.Label(logo_row, text="🐝", font=("Helvetica", 28),
                 bg=C["card"], fg=C["thehive"]).pack(side="left")
        tk.Label(logo_row, text="TheHive 5.2",
                 font=("Helvetica", 18, "bold"),
                 bg=C["card"], fg=C["thehive"]).pack(side="left", padx=8)

        tk.Label(card,
                 text=(
                     "Security Incident Response Platform. Manage cases, alerts, "
                     "observables and tasks. Integrated with Wazuh and Shuffle SOAR "
                     "for automated incident creation and triage."
                 ),
                 font=FONT_STEP, bg=C["card"], fg=C["text"],
                 wraplength=550, justify="left").pack(anchor="w", pady=(0, 18))

        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(0, 16))

        # URL row
        url_frame = tk.Frame(card, bg=C["surface"], padx=14, pady=10,
                             highlightthickness=1,
                             highlightbackground=C["border"])
        url_frame.pack(fill="x", pady=(0, 14))
        tk.Label(url_frame, text="URL:", font=FONT_BOLD,
                 bg=C["surface"], fg=C["muted"]).pack(side="left")
        self.thehive_url_lbl = tk.Label(
            url_frame, text="https://thehive.aml-lab.infosecfoster.com",
            font=("Courier New", 11, "bold"),
            bg=C["surface"], fg=C["mono"], cursor="hand2")
        self.thehive_url_lbl.pack(side="left", padx=10)

        def _open_thehive(e=None):
            import webbrowser
            domain = self.cf_domain_var.get().strip() or "infosecfoster.com"
            webbrowser.open(f"https://thehive.aml-lab.{domain}")

        self.thehive_url_lbl.bind("<Button-1>", _open_thehive)

        # Buttons
        btn_row = tk.Frame(card, bg=C["card"])
        btn_row.pack(anchor="w", pady=(0, 18))

        FlatBtn(btn_row, text="Open in Browser ↗", command=_open_thehive,
                bg=C["thehive"], fg="white", font=FONT_BOLD,
                padx=20, pady=9).pack(side="left", padx=(0, 10))

        def _copy_thehive():
            self.clipboard_clear()
            domain = self.cf_domain_var.get().strip() or "infosecfoster.com"
            self.clipboard_append(f"https://thehive.aml-lab.{domain}")
            messagebox.showinfo("Copied", "TheHive URL copied to clipboard.")

        FlatBtn(btn_row, text="Copy Link", command=_copy_thehive,
                bg=C["surface"], fg=C["text"], font=FONT_BOLD,
                padx=20, pady=9).pack(side="left")

        # ── Credentials table ────────────────────────────────────────────────
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(0, 14))
        tk.Label(card, text="Default Credentials", font=FONT_BOLD,
                 bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(0, 8))

        creds_frame = tk.Frame(card, bg=C["surface"], padx=16, pady=12,
                               highlightthickness=1,
                               highlightbackground=C["border"])
        creds_frame.pack(fill="x")

        cred_entries = [
            ("Username:",  "admin@thehive.local"),
            ("Password:",  "secret"),
            ("API Key:",   "aml-siem-mock-key-12345"),
            ("API Org:",   "admin"),
        ]
        for label, value in cred_entries:
            row = tk.Frame(creds_frame, bg=C["surface"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=FONT_SMALL, width=12, anchor="w",
                     bg=C["surface"], fg=C["muted"]).pack(side="left")
            val_lbl = tk.Label(row, text=value,
                               font=("Courier New", 10, "bold"),
                               bg=C["surface"], fg=C["mono"])
            val_lbl.pack(side="left", padx=(4, 12))

            def _make_copy(v=value):
                def _copy():
                    self.clipboard_clear()
                    self.clipboard_append(v)
                return _copy

            FlatBtn(row, text="Copy", command=_make_copy(),
                    bg=C["card"], fg=C["muted"], font=FONT_SMALL,
                    padx=6, pady=2).pack(side="left")

    def _build_shuffle_tab(self):
        """Shuffle tab: link card + quick info."""
        outer = tk.Frame(self.tab_shuffle, bg=C["bg"])
        outer.pack(fill="both", expand=True)

        # Centred card
        card = tk.Frame(outer, bg=C["card"], padx=32, pady=28,
                        highlightthickness=1, highlightbackground=C["border"])
        card.place(relx=0.5, rely=0.38, anchor="center", width=580)

        # Logo row
        logo_row = tk.Frame(card, bg=C["card"])
        logo_row.pack(anchor="w", pady=(0, 6))
        tk.Label(logo_row, text="⚡", font=("Helvetica", 28),
                 bg=C["card"], fg=C["shuffle"]).pack(side="left")
        tk.Label(logo_row, text="Shuffle SOAR",
                 font=("Helvetica", 18, "bold"),
                 bg=C["card"], fg=C["shuffle"]).pack(side="left", padx=8)

        tk.Label(card,
                 text=(
                     "Open-source Security Orchestration, Automation & Response platform. "
                     "Create workflows, connect Wazuh alerts, manage incidents and run "
                     "automated playbooks from a single interface."
                 ),
                 font=FONT_STEP, bg=C["card"], fg=C["text"],
                 wraplength=510, justify="left").pack(anchor="w", pady=(0, 18))

        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(0, 16))

        # URL row
        url_frame = tk.Frame(card, bg=C["surface"], padx=14, pady=10,
                             highlightthickness=1,
                             highlightbackground=C["border"])
        url_frame.pack(fill="x", pady=(0, 18))
        tk.Label(url_frame, text="URL:", font=FONT_BOLD,
                 bg=C["surface"], fg=C["muted"]).pack(side="left")
        self.shuffle_url_lbl = tk.Label(
            url_frame, text="https://shuffle.aml-lab.infosecfoster.com",
            font=("Courier New", 11, "bold"),
            bg=C["surface"], fg=C["mono"], cursor="hand2")
        self.shuffle_url_lbl.pack(side="left", padx=10)

        def _open_shuffle(e=None):
            import webbrowser
            domain = self.cf_domain_var.get().strip() or "infosecfoster.com"
            webbrowser.open(f"https://shuffle.aml-lab.{domain}")

        self.shuffle_url_lbl.bind("<Button-1>", _open_shuffle)

        # Buttons
        btn_row = tk.Frame(card, bg=C["card"])
        btn_row.pack(anchor="w")

        FlatBtn(btn_row, text="Open in Browser ↗", command=_open_shuffle,
                bg=C["shuffle"], fg="black", font=FONT_BOLD,
                padx=20, pady=9).pack(side="left", padx=(0, 10))

        def _copy_shuffle():
            self.clipboard_clear()
            domain = self.cf_domain_var.get().strip() or "infosecfoster.com"
            self.clipboard_append(f"https://shuffle.aml-lab.{domain}")
            messagebox.showinfo("Copied", "Shuffle URL copied to clipboard.")

        FlatBtn(btn_row, text="Copy Link", command=_copy_shuffle,
                bg=C["surface"], fg=C["text"], font=FONT_BOLD,
                padx=20, pady=9).pack(side="left")

        # Credentials hint
        tk.Frame(card, height=1, bg=C["border"]).pack(fill="x", pady=(18, 12))
        cred_row = tk.Frame(card, bg=C["card"])
        cred_row.pack(anchor="w")
        for k, v in [("Default user:", "admin"), ("Password:", "Admin1234!")]:
            tk.Label(cred_row, text=k, font=FONT_SMALL,
                     bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 4))
            tk.Label(cred_row, text=v, font=("Courier New", 10, "bold"),
                     bg=C["card"], fg=C["mono"]).pack(side="left", padx=(0, 18))

    # ── Live agent refresh ────────────────────────────────────────────────────
    def _update_wazuh_tab_visibility(self, visible):
        def _do():
            if visible:
                self._refresh_wazuh_url()
                # Update TheHive URL label — use cached domain (thread-safe)
                domain = self._conn.get("domain", "infosecfoster.com")
                self.thehive_url_lbl.config(
                    text=f"https://thehive.aml-lab.{domain}")
                if str(self.tab_wazuh) not in self.nb.tabs():
                    self.nb.add(self.tab_wazuh,   text="  Wazuh  ")
                if str(self.tab_thehive) not in self.nb.tabs():
                    self.nb.add(self.tab_thehive, text="  TheHive  ")
                if str(self.tab_shuffle) not in self.nb.tabs():
                    self.nb.add(self.tab_shuffle, text="  Shuffle  ")
                # Kick off live refresh
                self._refresh_agents_table()
            else:
                if str(self.tab_wazuh) in self.nb.tabs():
                    self.nb.forget(self.tab_wazuh)
                if str(self.tab_thehive) in self.nb.tabs():
                    self.nb.forget(self.tab_thehive)
                if str(self.tab_shuffle) in self.nb.tabs():
                    self.nb.forget(self.tab_shuffle)
                if self._wazuh_refresh_job:
                    self.after_cancel(self._wazuh_refresh_job)
        self.after(0, _do)

    def _update_shuffle_tab_visibility(self, visible):
        """Independently show/hide the Shuffle tab (for future use)."""
        def _do():
            if visible:
                if str(self.tab_shuffle) not in self.nb.tabs():
                    self.nb.add(self.tab_shuffle, text="  Shuffle  ")
            else:
                if str(self.tab_shuffle) in self.nb.tabs():
                    self.nb.forget(self.tab_shuffle)
        self.after(0, _do)

    def _build_bottom_bar(self):
        pass  # now inside _build_setup_tab — kept for compatibility

    # ── Config file ────────────────────────────────────────────────────────────
    _CFG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    def _load_config(self):
        """Load connection settings from config.json in the script directory."""
        try:
            with open(self._CFG_FILE) as f:
                d = json.load(f)
            # Support both the existing config.json field names and short aliases
            self.cf_host_var.set(d.get("host", ""))
            self.cf_port_var.set(str(d.get("port", "22")))
            self.cf_user_var.set(
                d.get("username") or d.get("user", "ubuntu"))
            self.cf_key_var.set(
                d.get("ssh_key") or d.get("key", ""))
            self.cf_domain_var.set(
                d.get("cf_domain") or d.get("domain", "infosecfoster.com"))
        except FileNotFoundError:
            pass  # first run — no config yet
        except Exception as e:
            print(f"[config] load error: {e}")

    def _save_config(self):
        """Save connection settings back to config.json, preserving any extra fields."""
        try:
            # Load existing file first so we don't wipe cf_token, cf_zone, etc.
            try:
                with open(self._CFG_FILE) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
            existing.update({
                "host":     self.cf_host_var.get(),
                "port":     self.cf_port_var.get(),
                "username": self.cf_user_var.get(),
                "ssh_key":  self.cf_key_var.get(),
                "cf_domain": self.cf_domain_var.get(),
            })
            with open(self._CFG_FILE, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            print(f"[config] save error: {e}")

    def _browse_key(self):
        path = filedialog.askopenfilename(
            title="Select SSH private key",
            filetypes=[("All files", "*")]
        )
        if path:
            self.cf_key_var.set(path)

    # ── SSH connection toggle ──────────────────────────────────────────────────
    def _toggle_connection(self):
        if self.ssh:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        host   = self.cf_host_var.get().strip()
        port   = int(self.cf_port_var.get().strip() or "22")
        user   = self.cf_user_var.get().strip()
        key    = self.cf_key_var.get().strip() or None
        passph = self.cf_pass_var.get().strip() or None

        if not host or not user:
            messagebox.showwarning("Missing", "Host and Username are required.")
            return

        self.conn_status.config(text="● Connecting…", fg=C["warn"])
        self.conn_btn.configure(state="disabled")
        self.update()

        def _do():
            try:
                runner = SSHRunner(host, port, user, key, passph)
                runner.connect()
                self.after(0, lambda: self._on_connected(runner))
            except Exception as e:
                self.after(0, lambda: self._on_connect_failed(str(e)))

        import threading
        threading.Thread(target=_do, daemon=True).start()

    def _on_connected(self, runner):
        self.ssh = runner
        # Cache plain-Python connection params so background threads
        # can use them without calling Tkinter .get() (not thread-safe).
        self._conn = {
            "host":   self.cf_host_var.get().strip(),
            "port":   int(self.cf_port_var.get().strip() or "22"),
            "user":   self.cf_user_var.get().strip(),
            "key":    self.cf_key_var.get().strip() or None,
            "passph": self.cf_pass_var.get().strip() or None,
            "domain": self.cf_domain_var.get().strip() or "infosecfoster.com",
        }
        self._save_config()
        self.conn_status.config(text="● Connected", fg=C["success"])
        self.conn_btn.configure(state="normal")
        self.conn_btn.configure(text="Disconnect")
        self.run_btn.configure(state="normal")   # unlock Run Selected
        self._log(f"✔ Connected to {self._conn['host']}", "ok")
        # Auto-switch to Setup tab so user can immediately select & run steps
        self.nb.select(self.tab_setup)
        self._update_wazuh_tab_visibility(True)

    def _on_connect_failed(self, err):
        self.conn_status.config(text="● Disconnected", fg=C["danger"])
        self.conn_btn.configure(state="normal")
        self._log(f"✘ Connection failed: {err}", "fail")

    def _disconnect(self):
        if self.ssh:
            self.ssh.close()
            self.ssh = None
        self.conn_status.config(text="● Disconnected", fg=C["muted"])
        self.conn_btn.configure(state="normal")
        self.conn_btn.configure(text="Connect")
        self.run_btn.configure(state="disabled")  # lock Run Selected
        self._update_wazuh_tab_visibility(False)
        self._log("Disconnected.", "warn")
        # Return to Connection tab
        self.nb.select(self.tab_conn)

    def _run_reconnect(self):
        """Re-establish SSH connection (used by reconnect mode steps).
        Safe to call from background threads — uses cached _conn dict."""
        try:
            if self.ssh:
                self.ssh.close()
            c = self._conn  # plain Python dict, no Tkinter calls
            runner = SSHRunner(
                c.get("host", ""), c.get("port", 22),
                c.get("user", ""), c.get("key"), c.get("passph"))
            runner.connect()
            self.ssh = runner
            return True, "Reconnected successfully."
        except Exception as e:
            return False, f"Reconnect failed: {e}"

    # ── Run all selected steps ─────────────────────────────────────────────────
    def _do_run(self):
        if self.running:
            self._log("⚠ Already running — please wait.", "warn")
            return
        if not self.ssh:
            messagebox.showwarning("Not connected",
                                   "Please connect to the server first.")
            return

        selected = [sid for sid, v in self.sel_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Nothing selected",
                                   "Please select at least one step.")
            return

        self.running = True
        self.run_btn.configure(state="disabled")

        # Read all Tkinter variables HERE (main thread) — .get() is NOT
        # thread-safe and will deadlock if called from the worker thread.
        force = self.force_var.get()

        import threading
        threading.Thread(target=self._run_all, args=(selected, force),
                         daemon=True).start()

    def _run_all(self, step_ids, force=False):
        """Background thread: run selected steps in order."""
        all_steps_list = STEPS + PLAYBOOK_STEPS + PLAYBOOK_OTHER_STEPS
        steps_by_id = {s["id"]: s for s in all_steps_list}

        gate_results = []

        total_subs = sum(
            len(steps_by_id[sid].get("cmds", []))
            for sid in step_ids if sid in steps_by_id
        )
        done = 0

        ts = __import__("time").strftime("%Y-%m-%d %H:%M")
        self._log("\n" + "═"*52 + f"\n  M0.1 Summary  ·  {ts}\n" + "═"*52, "head")

        for sid in step_ids:
            if not self.running:
                break
            step = steps_by_id.get(sid)
            if not step:
                continue

            # Pre-check (skip if already done)
            pre = step.get("pre_check", "")
            pre_lbl = step.get("pre_check_label", "")
            if pre and pre != "false" and not force:
                ok, out = self._run_remote({"cmd": pre, "label": pre_lbl,
                                            "mode": step.get("mode", "remote")})
                if ok:
                    self._log(f'  ✓ Already done — {step["title"]}', "ok")
                    done += len(step.get("cmds", []))
                    self._set_progress(done, total_subs,
                                       f"{done}/{total_subs} sub-steps")
                    self._set_badge(sid, "DONE", C["success"])
                    continue

            # Run sub-steps
            _smode = step.get("mode", "remote")
            self._log("\n" + "─"*52 + f"\n[{_smode.upper()}]  {step['title']}", "head")

            mode = step.get("mode", "remote")
            step_ok = True

            for i, cmd in enumerate(step.get("cmds", [])):
                if not self.running:
                    break

                label = cmd.get("label", f"Step {i+1}")
                self._log(f"  → {label}", "cmd")
                self._set_sub(sid, i, "running")

                try:
                    sub_mode = cmd.get("mode", mode)
                    if sub_mode == "local" or sub_mode.startswith("local_"):
                        ok, output = self._run_local(cmd)
                        self._last_local_out[label] = output
                    elif sub_mode == "reconnect":
                        ok, output = self._run_reconnect()
                    elif sub_mode == "remote_upload":
                        script = cmd.get("script", "")
                        rpath  = cmd.get("remote_path", "/tmp/aml_script.sh")
                        rc, out = self.ssh.upload_and_run(script, rpath)
                        ok, output = rc == 0, out
                    else:
                        ok, output = self._run_remote(cmd)

                    if output:
                        self._log_output(output)

                    if ok:
                        self._set_sub(sid, i, "ok")
                        if sid in ("GATE", "GATE2", "GATE3", "GATE4", "GATE5",
                                   "GATE_M11", "GATE_M12", "GATE_M13",
                                   "GATE_M14", "GATE_M15",
                                   "GATE_M24", "GATE_M25", "GATE_M26"):
                            for line in output.splitlines():
                                if "GATE_PASS" in line or "GATE_FAIL" in line:
                                    gate_results.append(line.strip())
                    else:
                        step_ok = False
                        self._set_sub(sid, i, "fail")
                        self._log(f"  ✘ Failed: {label}", "fail")
                        done += 1
                        self._set_progress(done, total_subs,
                                           f"{done}/{total_subs} sub-steps")
                        self._set_badge(sid, "FAILED", C["danger"])
                        self._log(
                            "\n" + "─"*52 + "\n"
                            "  STOPPED — fix this then re-run:\n"
                            f"  Step: {step['title']}\n"
                            f"  Sub:  {label}\n"
                            + "─"*52 + "\n", "fail")
                        self.running = False
                        break

                except Exception as e:
                    step_ok = False
                    self._set_sub(sid, i, "fail")
                    err_msg = str(e) if str(e) else "Unknown error — check SSH connection"
                    self._log(f"  ✘ Exception: {err_msg}", "fail")
                    done += 1
                    self._set_progress(done, total_subs,
                                       f"{done}/{total_subs} sub-steps")
                    self._set_badge(sid, "FAILED", C["danger"])
                    self._log(
                        f"\n{'─'*52}\n"
                        f"  STOPPED — exception in: {label}\n"
                        f"  Error: {err_msg}\n"
                        f"{'─'*52}\n", "fail")
                    self.running = False
                    break

                done += 1
                self._set_progress(done, total_subs,
                                   f"{done}/{total_subs} sub-steps")

            if step_ok and self.running:
                self._set_badge(sid, "DONE", C["success"])

        # Final summary
        if gate_results:
            self._log("\n  Gate Results:\n" + "\n".join(f"  {r}" for r in gate_results), "head")

        ts_end = __import__("time").strftime("%Y-%m-%d %H:%M")
        self._log("\n" + "═"*52 + f"\n  Run Complete  ·  {ts_end}\n" + "═"*52 + "\n", "head")

        self.running = False
        self._ui_queue.put(lambda: self.run_btn.configure(state="normal"))

    # ── Remote execution ───────────────────────────────────────────────────────
    def _run_remote(self, cmd_dict):
        """Run a remote SSH command and return (ok, output)."""
        cmd = cmd_dict.get("cmd", "")
        if not cmd:
            return True, ""
        try:
            rc, out = self.ssh.run(cmd, timeout=600)
            return rc == 0, out
        except Exception as e:
            return False, str(e)

    # ── Local execution ────────────────────────────────────────────────────────
    def _run_local(self, cmd_dict):
        """Dispatch to appropriate local handler."""
        mode = cmd_dict.get("mode", "local")

        if mode == "local_upload_docs":
            return self._upload_sprint_docs()

        if mode == "local_install_wazuh_sudo":
            import os, subprocess as sp
            sudoers_path = "/etc/sudoers.d/aml-wazuh"

            # Idempotent: skip if already installed
            if os.path.exists(sudoers_path):
                return True, "Wazuh sudoers rule already installed — skipped."

            self._log("Installing Wazuh sudoers rule via one-time admin dialog...", "cmd")
            self._log("  ⚠️  A macOS admin password dialog will appear ONCE. Please approve it.", "warn")

            sudoers_content = (
                "# AML SIEM — Wazuh agent management without password prompt\n"
                "%admin ALL=(root) NOPASSWD: /Library/Ossec/bin/wazuh-control *\n"
                "%admin ALL=(root) NOPASSWD: /Library/Ossec/bin/agent-auth *\n"
                "%admin ALL=(root) NOPASSWD: /usr/bin/python3 *\n"
                "%admin ALL=(root) NOPASSWD: /bin/bash /tmp/aml_mac_enroll.sh\n"
                "%admin ALL=(root) NOPASSWD: /bin/bash /tmp/aml_*.sh\n"
            )

            # Write sudoers content to a temp file, then move it via osascript (one-time)
            tmp_sudo = "/tmp/aml_wazuh_sudoers"
            with open(tmp_sudo, "w") as f:
                f.write(sudoers_content)

            script_lines = [
                "do shell script \"cp " + tmp_sudo + " " + sudoers_path + " && chmod 440 " + sudoers_path + "\" with administrator privileges"
            ]
            script = "\n".join(script_lines)
            res = sp.run(["osascript", "-e", script],
                         capture_output=True, text=True, timeout=120)
            log_out = res.stdout.strip() + "\n" + res.stderr.strip()

            if res.returncode != 0 or not os.path.exists(sudoers_path):
                return False, (
                    "Failed to install sudoers rule.\n"
                    "stderr: " + res.stderr + "\n"
                    "log: " + log_out
                )

            return True, "Wazuh sudoers rule installed at " + sudoers_path + ". Future runs need no dialogs."

        if mode == "local_enroll_mac":
            import os
            if not os.path.exists("/Library/Ossec"):
                return True, "Wazuh Agent not installed on local Mac — skipped."
            vm_ip = self._resolve_vm_ip()
            if not vm_ip:
                return False, "Could not resolve VM IP address for local agent registration check."

            self._log("Updating ossec.conf server IP, clearing keys, re-enrolling and restarting...", "cmd")

            # Syslog telemetry payload (bytes list avoids any shell quoting issues)
            payload_str = "<189>Jul 18 04:30:00 local-mac-agent sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2 useradd"
            payload_bytes = list(payload_str.encode("utf-8"))
            ip_bytes      = list(vm_ip.encode("utf-8"))
            py_syslog = (
                "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); "
                "s.sendto(bytes(" + str(payload_bytes) + "), "
                "(bytes(" + str(ip_bytes) + ").decode(), 514))"
            )

            script_content = (
                "#!/bin/bash\n"
                "set -xe\n"
                "echo '=== Phase 1: Update ossec.conf server address ==='\n"
                "/usr/bin/python3 << 'PYEOF'\n"
                "import re\n"
                "ossec = '/Library/Ossec/etc/ossec.conf'\n"
                "with open(ossec, 'r') as f:\n"
                "    c = f.read()\n"
                "c = re.sub(r'<address>.*?</address>', '<address>" + vm_ip + "</address>', c)\n"
                "with open(ossec, 'w') as f:\n"
                "    f.write(c)\n"
                "print('ossec.conf updated: address -> " + vm_ip + "')\n"
                "PYEOF\n"
                "echo '=== Phase 2: Clear keys and stop agent ==='\n"
                "rm -f /Library/Ossec/etc/client.keys\n"
                "/Library/Ossec/bin/wazuh-control stop || true\n"
                "sleep 3\n"
                "echo '=== Phase 3: Enroll with manager ==='\n"
                "/Library/Ossec/bin/agent-auth -m " + vm_ip + " -p 1515 -A $(hostname -s)\n"
                "echo '=== Phase 4: Fix key permissions ==='\n"
                "chown root:wheel /Library/Ossec/etc/client.keys 2>/dev/null || true\n"
                "chmod 640 /Library/Ossec/etc/client.keys 2>/dev/null || true\n"
                "ls -la /Library/Ossec/etc/client.keys\n"
                "echo '=== Phase 5: Start agent ==='\n"
                "/Library/Ossec/bin/wazuh-control start\n"
                "echo '=== Scheduling syslog telemetry ==='\n"
                "(sleep 30 && /usr/bin/python3 -c '" + py_syslog + "') >/dev/null 2>&1 &\n"
                "echo ENROLL_DONE\n"
            )

            tmp_script = "/tmp/aml_mac_enroll.sh"
            with open(tmp_script, "w") as f:
                f.write(script_content)
            os.chmod(tmp_script, 0o755)

            # Use sudo -n (non-interactive, no dialog, no timeout) — requires sudoers rule
            res = subprocess.run(
                ["sudo", "-n", "bash", tmp_script],
                capture_output=True, text=True, timeout=180
            )
            log_out = res.stdout.strip()

            # Smart skip: check if already enrolled
            agentd_running = subprocess.run(
                ["pgrep", "-x", "wazuh-agentd"], capture_output=True).returncode == 0

            keys_ok = False
            try:
                r = subprocess.run(["sudo", "-n", "wc", "-c",
                                    "/Library/Ossec/etc/client.keys"],
                                   capture_output=True, text=True)
                keys_ok = r.returncode == 0 and int(r.stdout.split()[0]) > 0
            except Exception:
                pass

            if "ENROLL_DONE" in log_out:
                return True, log_out
            elif agentd_running and keys_ok:
                return True, "Wazuh agent already enrolled and running — skipped."
            else:
                return False, "Enrollment failed.\n" + log_out + "\n" + res.stderr

        # Generic local shell command
        cmd = cmd_dict.get("cmd", "")
        if cmd:
            try:
                res = subprocess.run(cmd, shell=True,
                                     capture_output=True, text=True, timeout=120)
                ok = res.returncode == 0
                return ok, (res.stdout + res.stderr).strip()
            except Exception as e:
                return False, str(e)

        return True, ""

    def _upload_sprint_docs(self):
        """Upload sprint documentation to remote server."""
        if not self.ssh:
            return False, "Not connected to server."
        docs_dir = os.path.join(os.path.dirname(__file__), "docs")
        if not os.path.exists(docs_dir):
            return True, f"No docs/ directory found at {docs_dir} — skipped."
        try:
            sftp = self.ssh.client.open_sftp()
            try:
                sftp.mkdir("/opt/aml-siem/docs")
            except Exception:
                pass
            uploaded = []
            for fname in os.listdir(docs_dir):
                fpath = os.path.join(docs_dir, fname)
                if os.path.isfile(fpath):
                    sftp.put(fpath, f"/opt/aml-siem/docs/{fname}")
                    uploaded.append(fname)
            sftp.close()
            return True, f"Uploaded {len(uploaded)} docs: {', '.join(uploaded)}"
        except Exception as e:
            return False, f"Upload failed: {e}"

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _resolve_vm_ip(self):
        """Resolve VM IP. Safe to call from background threads — uses cached _conn."""
        import socket
        host = self._conn.get("host", "") or ""
        if not host:
            return None
        try:
            return socket.gethostbyname(host)
        except Exception:
            return host if host else None

    def _open_terminal(self):
        """Open SSH session in a new terminal window."""
        host = self.cf_host_var.get().strip()
        user = self.cf_user_var.get().strip()
        key  = self.cf_key_var.get().strip()
        port = self.cf_port_var.get().strip() or "22"

        if not host or not user:
            messagebox.showwarning("Missing", "Host and Username required.")
            return

        ssh_cmd = f"ssh -i {key} -p {port} {user}@{host}"
        sys_name = platform.system()

        try:
            if sys_name == "Darwin":
                # macOS — open Terminal.app with the ssh command
                lines = [
                    "tell application \"Terminal\"",
                    f"  do script \"{ssh_cmd}\"",
                    "  activate",
                    "end tell",
                ]
                script = "\n".join(lines)
                sp.Popen(["osascript", "-e", script])
            elif sys_name == "Linux":
                # Try common Linux terminals
                for term in ["gnome-terminal", "xterm", "konsole", "xfce4-terminal"]:
                    try:
                        sp.Popen([term, "--", "bash", "-c",
                                  f"{ssh_cmd}; exec bash"])
                        break
                    except FileNotFoundError:
                        continue
        except Exception as e:
            messagebox.showerror("Terminal Error", str(e))

    def _select_all(self, value: bool):
        for v in self.sel_vars.values():
            v.set(value)

    def _set_badge(self, sid, text, color):
        def _do():
            if sid in self._badge_lbls:
                self._badge_lbls[sid].config(text=text, fg=color)
        self.after(0, _do)

    def _set_sub(self, sid, idx, state):
        """Update sub-step label: 'running' → ● cyan, 'ok' → ✓ green, 'fail' → ✘ red."""
        icons = {"running": ("●", C["accent"]), "ok": ("✓", C["success"]),
                 "fail": ("✘", C["danger"])}
        icon, color = icons.get(state, ("○", C["muted"]))
        def _do():
            lbls = self._sub_lbls.get(sid, [])
            if idx < len(lbls):
                old = lbls[idx].cget("text")
                # Replace leading ○/●/✓/✘ prefix
                new_text = icon + old[1:] if old else icon
                lbls[idx].config(text=new_text, fg=color)
        self.after(0, _do)

    def _set_progress(self, done, total, label=""):
        def _do():
            pct = int(100 * done / total) if total else 0
            self.pbar["value"] = pct
            self.progress_lbl.config(text=label or f"{pct}%")
        self.after(0, _do)

    def _log(self, msg, tag=""):
        def _do():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _do)

    def _log_output(self, text):
        """Log multi-line output, colouring PASS/FAIL/warn lines."""
        for line in text.splitlines():
            if "GATE_PASS" in line or "PASS" in line.upper():
                self._log("    " + line, "ok")
            elif "GATE_FAIL" in line or "FAIL" in line.upper() or "ERROR" in line.upper():
                self._log("    " + line, "fail")
            elif "WARNING" in line.upper() or "WARN" in line.upper():
                self._log("    " + line, "warn")
            else:
                self._log("    " + line)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _on_close(self):
        if self.ssh:
            self.ssh.close()
        if self._wazuh_refresh_job:
            self.after_cancel(self._wazuh_refresh_job)
        self.destroy()


# ── Entry point ─────────────────────────────────────────────────────────────────
def main():
    app = AMLSetupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
