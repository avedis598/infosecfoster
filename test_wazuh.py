import asyncio
import asyncssh
import sys

from google.cloud import secretmanager
import os
os.environ["PROJECT_ID"] = "infosecfoster-5bb83"

async def get_ssh_conn():
    secret_id = f"ssh-key-avedis598"
    name = f"projects/infosecfoster-5bb83/secrets/{secret_id}/versions/latest"
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": name})
    private_key = response.payload.data.decode("UTF-8")
    key = asyncssh.import_private_key(private_key)
    return await asyncssh.connect("104.198.8.20", username="amlak-siem-admin", client_keys=[key], known_hosts=None)

async def run():
    async with await get_ssh_conn() as conn:
        res = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}'", check=False)
        pod_name = res.stdout.strip()
        print("Pod:", pod_name)
        if not pod_name:
            print("No master pod")
            return
            
        res2 = await conn.run(f"KUBECONFIG=$HOME/.kube/config kubectl exec -n aml-lab {pod_name} -c wazuh-manager -- /var/ossec/bin/agent_control -j -l", check=False)
        print("Agent control output:", res2.stdout)
        
        # Test OpenSearch Alerts (if we can)
        res3 = await conn.run(f"KUBECONFIG=$HOME/.kube/config kubectl exec -n aml-lab {pod_name} -c wazuh-manager -- curl -s -u admin:admin -k https://opensearch-coordinator.aml-lab.svc.cluster.local:9200/wazuh-alerts-*/_count", check=False)
        print("OpenSearch Alerts:", res3.stdout)

asyncio.run(run())
