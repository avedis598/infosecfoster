import asyncio
import asyncssh
from google.cloud import secretmanager

async def test():
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/infosecfoster-5bb83/secrets/mock-ssh-key/versions/1"
    response = client.access_secret_version(request={"name": name})
    private_key = response.payload.data.decode("UTF-8")
    
    async with asyncssh.connect("104.198.8.20", username="amlak-siem-admin", client_keys=[asyncssh.import_private_key(private_key)], known_hosts=None) as conn:
        res = await conn.run("sudo k3s kubectl get pods -A --no-headers | awk '{print $1\"/\"$2\",\"$4}'")
        print("EXIT CODE:", res.exit_status)
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)

asyncio.run(test())
