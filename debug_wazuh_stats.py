import json
from aml_siem.core.ssh_runner import SSHRunner
from aml_siem.core.config import get_active_client_config

cfg = get_active_client_config()
ssh = SSHRunner(cfg.get("host"), "22", cfg.get("user"), cfg.get("ssh_key"))
ok, msg = ssh.connect()
if not ok:
    print(f"SSH Connect Error: {msg}")
    exit(1)

script = """
import subprocess, urllib.request, json, ssl, traceback

stats = {"agents": {"Total": "0", "Active": "0", "Disconnected": "0", "Pending": "0", "Never connected": "0"},
         "alerts": {"Total": "0", "Level 12+": "0", "Auth Failure": "0", "Auth Success": "0"},
         "errors": []}

try:
    out = subprocess.check_output(["/var/ossec/bin/agent_control", "-s"]).decode()
    for line in out.split("\\n"):
        line = line.strip()
        for k in stats["agents"].keys():
            if line.startswith(f"{k} agents:"):
                stats["agents"][k] = line.split(":")[1].strip()
        if line.startswith("Total agents:"):
            stats["agents"]["Total"] = line.split(":")[1].strip()
except Exception as e:
    stats["agents"]["Total"] = "Err1"
    stats["errors"].append("Agent error: " + traceback.format_exc())

import datetime
now = datetime.datetime.utcnow()
past = now - datetime.timedelta(days=1)
time_filter = {"range": {"@timestamp": {"gte": past.strftime("%Y-%m-%dT%H:%M:%SZ"), "lte": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}}

os_url = "http://opensearch-proxy.aml-lab.svc.cluster.local:9200/wazuh-alerts-*/_count"

def get_count(query):
    try:
        req = urllib.request.Request(os_url, data=json.dumps(query).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=5) as res:
            return str(json.loads(res.read()).get("count", 0))
    except Exception as e:
        stats["errors"].append("Alert error: " + traceback.format_exc())
        return "Err2"

stats["alerts"]["Total"] = get_count({"query": {"bool": {"filter": [time_filter]}}})

print(json.dumps(stats))
"""

cmd = f"KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{{.items[0].metadata.name}}') -c wazuh-manager -- python3 -c '{script}'"
ok, out = ssh.run(cmd)
print("OK:", ok)
print("OUT:", out)
ssh.close()
