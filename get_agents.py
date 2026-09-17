import asyncio, asyncssh, json, os
async def run():
    with open('config.json', 'r') as f:
        conf = json.load(f)
    client = conf['clients']['legacy']
    username = client['user']
    ip = client['host']
    key_path = os.path.expanduser(client['key_path'])
    async with asyncssh.connect(ip, username=username, client_keys=[key_path], known_hosts=None) as conn:
        res = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=$HOME/.kube/config kubectl get pods -n aml-lab -l app=wazuh-manager -o jsonpath='{.items[0].metadata.name}') -c wazuh-manager -- /var/ossec/bin/agent_control -l")
        print("STDOUT", res.stdout)
        print("STDERR", res.stderr)
asyncio.run(run())
