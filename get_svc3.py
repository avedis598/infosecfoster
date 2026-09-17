import asyncio, asyncssh, json, os
async def run():
    with open('config.json', 'r') as f:
        conf = json.load(f)
    client = conf['clients']['legacy']
    username = client['user']
    ip = client['host']
    key_path = os.path.expanduser(client['key_path'])
    async with asyncssh.connect(ip, username=username, client_keys=[key_path], known_hosts=None) as conn:
        res = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get svc -n aml-lab wazuh -o yaml")
        print(res.stdout)
asyncio.run(run())
