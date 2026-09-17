import asyncio, asyncssh, json
async def run():
    with open('config.json', 'r') as f:
        conf = json.load(f)
    client = conf['clients'][0]
    username = client['cloud']['ssh_username']
    ip = client['cloud']['ip']
    key_path = client['cloud']['ssh_key_path']
    async with asyncssh.connect(ip, username=username, client_keys=[key_path], known_hosts=None) as conn:
        res = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get svc -n aml-lab wazuh -o yaml")
        print(res.stdout)
asyncio.run(run())
