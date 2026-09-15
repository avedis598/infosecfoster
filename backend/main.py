from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import firebase_admin
from firebase_admin import firestore
from google.cloud import secretmanager
from pydantic import BaseModel

# Initialize Firebase Admin
try:
    firebase_admin.initialize_app()
    db = firestore.client()
except Exception as e:
    print(f"Warning: Firebase Admin init failed: {e}")

app = FastAPI(title="AML SIEM Cloud Deployer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = "infosecfoster-5bb83"

class SecretPayload(BaseModel):
    client_id: str
    private_key: str

@app.get("/")
def health_check():
    return {"status": "AML SIEM Backend is running!"}

@app.get("/api/modules")
def get_modules():
    """Return the entire deployment hierarchy for the UI."""
    try:
        from steps.m0_foundation import M0_STEPS
        from steps.m1_detection import M1_STEPS
        from steps.m2_automation import M2_STEPS
        from steps.m3_intelligence import M3_STEPS
        
        # Format it exactly how the React tree view will need it
        hierarchy = [
            {"id": "M0", "name": "Sprint 0 — Environment Foundation", "steps": M0_STEPS},
            {"id": "M1", "name": "Sprint 1 — Core Detection", "steps": M1_STEPS},
            {"id": "M2", "name": "Sprint 2 — Automation", "steps": M2_STEPS},
            {"id": "M3", "name": "Sprint 3 — Intelligence", "steps": M3_STEPS},
        ]
        return {"status": "success", "modules": hierarchy}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/secrets")
async def store_ssh_key(payload: SecretPayload):
    """
    Securely store the raw SSH private key into Google Secret Manager.
    Returns the Secret Version Reference Name.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{PROJECT_ID}"
        secret_id = f"ssh-key-{payload.client_id.lower().replace(' ', '-')}"
        
        # 1. Create the secret if it doesn't exist
        try:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except Exception as e:
            # It likely already exists, which is fine.
            pass
            
        # 2. Add a new version with the actual key payload
        secret_name = f"{parent}/secrets/{secret_id}"
        version = client.add_secret_version(
            request={
                "parent": secret_name, 
                "payload": {"data": payload.private_key.encode("UTF-8")}
            }
        )
        return {"status": "success", "secret_version": version.name}
    except Exception as e:
        if "default credentials were not found" in str(e).lower():
            print("\n[MOCK MODE] Local development detected without gcloud credentials.")
            print(f"Would have stored secret for {payload.client_id} to {PROJECT_ID}.")
            return {"status": "mock_success", "secret_version": f"projects/{PROJECT_ID}/secrets/mock-ssh-key/versions/1"}
        raise e

import asyncio
import asyncssh

from orchestrator import CloudOrchestrator

@app.websocket("/api/deploy/{client_id}")
async def deploy_siem(websocket: WebSocket, client_id: str, ip: str, username: str, steps: str = "", force: str = "false", debug: str = "false"):
    await websocket.accept()
    
    # 1. Fetch the SSH key from Secret Manager
    secret_id = f"ssh-key-{client_id.lower().replace(' ', '-')}"
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        private_key = response.payload.data.decode("UTF-8")
    except Exception as e:
        if "default credentials were not found" in str(e).lower():
            await websocket.send_text("\r\n\x1b[31m[MOCK MODE] Local development detected without Google Cloud credentials. Cannot run deployment.\x1b[0m\r\n")
            await websocket.close()
            return
        else:
            await websocket.send_text(f"\r\n\x1b[31m[ERROR] Failed to fetch SSH key: {e}\x1b[0m\r\n")
            await websocket.close()
            return

    step_list = [s.strip() for s in steps.split(",") if s.strip()]
    is_force = force.lower() == "true"
    
    await websocket.send_text(f"\r\n\x1b[35m[SYSTEM] Authenticating to {ip} for deployment (force={is_force})...\x1b[0m\r\n")
    
    try:
        key = asyncssh.import_private_key(private_key)
        async with asyncssh.connect(ip, username=username, client_keys=[key], known_hosts=None) as conn:
            await websocket.send_text("\r\n\x1b[32m[SUCCESS] Connected! Initializing Cloud Orchestrator...\x1b[0m\r\n")
            
            orchestrator = CloudOrchestrator(ws=websocket, conn=conn, client_id=client_id)
            await orchestrator.run_steps(step_list, is_force, debug=(debug.lower() == 'true'))
            
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31m[ERROR] Deployment failed: {str(e)}\x1b[0m\r\n")
    finally:
        await websocket.close()

@app.websocket("/api/ssh/{client_id}")
async def ssh_terminal(websocket: WebSocket, client_id: str, ip: str, username: str):
    await websocket.accept()
    
    # 1. Fetch the SSH key from Secret Manager
    secret_id = f"ssh-key-{client_id.lower().replace(' ', '-')}"
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        private_key = response.payload.data.decode("UTF-8")
    except Exception as e:
        if "default credentials were not found" in str(e).lower():
            await websocket.send_text("\r\n[MOCK MODE] Local development detected.\r\nWould connect to: " + ip + "\r\n")
            private_key = None
        else:
            await websocket.send_text(f"\r\n[ERROR] Failed to fetch SSH key: {e}\r\n")
            await websocket.close()
            return

    # If mock mode, just echo back characters for testing
    if not private_key:
        await websocket.send_text(f"{username}@{ip}:~$ ")
        try:
            while True:
                data = await websocket.receive_text()
                # Mock echo (handles basic typing)
                if data == '\r':
                    await websocket.send_text(f"\r\n{username}@{ip}:~$ ")
                else:
                    await websocket.send_text(data)
        except Exception:
            pass
        return

    # 2. Establish SSH connection using asyncssh
    await websocket.send_text(f"\r\n[SYSTEM] Authenticating to {ip} as {username}...\r\n")
    try:
        # Load the private key from string
        key = asyncssh.import_private_key(private_key)
        
        async with asyncssh.connect(ip, username=username, client_keys=[key], known_hosts=None) as conn:
            await websocket.send_text("\r\n[SUCCESS] Connected! Opening secure shell...\r\n")
            
            # Open interactive terminal session
            async with conn.create_process(term_type='xterm') as process:
                
                # Task to read from SSH and send to WebSocket
                async def read_from_ssh():
                    try:
                        while not process.stdout.at_eof():
                            data = await process.stdout.read(4096)
                            if data:
                                await websocket.send_text(data)
                    except Exception:
                        pass

                # Task to read from WebSocket and send to SSH
                async def write_to_ssh():
                    try:
                        while True:
                            data = await websocket.receive_text()
                            process.stdin.write(data)
                    except Exception:
                        pass
                
                # Run both concurrently
                await asyncio.gather(read_from_ssh(), write_to_ssh())
                
    except Exception as e:
        await websocket.send_text(f"\r\n[ERROR] SSH Connection failed: {str(e)}\r\n")
    finally:
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


class MonitorPayload(BaseModel):
    client_id: str
    ip: str
    username: str

async def get_ssh_conn(client_id: str, ip: str, username: str):
    secret_id = f"ssh-key-{client_id.lower().replace(' ', '-')}"
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": name})
    private_key = response.payload.data.decode("UTF-8")
    
    key = asyncssh.import_private_key(private_key)
    return await asyncssh.connect(ip, username=username, client_keys=[key], known_hosts=None)

@app.post("/api/monitor/overview")
async def monitor_overview(payload: MonitorPayload):
    try:
        async with await get_ssh_conn(payload.client_id, payload.ip, payload.username) as conn:
            # Get Pods
            res_pods = await conn.run("sudo k3s kubectl get pods -A --no-headers | awk '{print $1"/"$2","$4}'", check=False)
            pods = []
            if res_pods.exit_status == 0 and res_pods.stdout:
                for line in res_pods.stdout.strip().split('\n'):
                    parts = line.split(',')
                    if len(parts) == 2:
                        pods.append({"name": parts[0], "status": parts[1]})

            # Get Images
            res_img = await conn.run("sudo k3s kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{\"\\n\"}{end}'", check=False)
            images = []
            if res_img.exit_status == 0 and res_img.stdout:
                img_set = set()
                for line in res_img.stdout.strip().split('\n'):
                    for img in line.split():
                        img_set.add(img)
                for img in img_set:
                    parts = img.split(':')
                    name = parts[0].split('/')[-1]
                    tag = parts[1] if len(parts) > 1 else 'latest'
                    images.append({"name": name, "tag": tag})
                    
            return {"status": "success", "pods": pods, "images": images}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/monitor/wazuh")
async def monitor_wazuh(payload: MonitorPayload):
    try:
        async with await get_ssh_conn(payload.client_id, payload.ip, payload.username) as conn:
            # We will mock the OpenSearch alerts and Wazuh agent counts since it requires complex queries.
            # In a real environment, we would query the OpenSearch REST API.
            
            return {
                "status": "success", 
                "agents": {"total": 4, "active": 3, "disconnected": 1, "pending": 0},
                "alerts": {"total": 1254, "high": 12, "auth": 432}
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/monitor/thehive")
async def monitor_thehive(payload: MonitorPayload):
    # Mocking for now - would query TheHive API
    return {"status": "success", "cases": {"total": 42, "critical": 2, "open": 5}}

@app.post("/api/monitor/shuffle")
async def monitor_shuffle(payload: MonitorPayload):
    return {"status": "success", "workflows": {"active": 14, "failed": 0, "executions": 1205}}

@app.post("/api/monitor/grafana")
async def monitor_grafana(payload: MonitorPayload):
    return {"status": "success", "dashboards": 8, "alerts": 0}


class KeyPayload(BaseModel):
    private_key: str


@app.post("/api/clients/{client_id}/secret/{secret_type}")
async def upload_secret(client_id: str, secret_type: str, payload: KeyPayload):
    try:
        prefix = "ssh-key" if secret_type == "ssh" else "cf-token"
        secret_id = f"{prefix}-{client_id.lower().replace(' ', '-')}"
        parent = f"projects/{PROJECT_ID}"
        client = secretmanager.SecretManagerServiceClient()
        
        try:
            client.get_secret(request={"name": f"{parent}/secrets/{secret_id}"})
            exists = True
        except Exception:
            exists = False
            
        if not exists:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            
        client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_id}",
                "payload": {"data": payload.private_key.encode("UTF-8")},
            }
        )
        return {"status": "success", "message": f"{secret_type.upper()} successfully stored."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/clients/{client_id}/secret/{secret_type}/status")
async def check_secret(client_id: str, secret_type: str):
    try:
        prefix = "ssh-key" if secret_type == "ssh" else "cf-token"
        secret_id = f"{prefix}-{client_id.lower().replace(' ', '-')}"
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
        client = secretmanager.SecretManagerServiceClient()
        client.access_secret_version(request={"name": name})
        return {"status": "success", "exists": True}
    except Exception as e:
        return {"status": "success", "exists": False}

