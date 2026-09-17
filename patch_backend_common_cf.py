import re

with open("backend/main.py", "r") as f:
    c = f.read()

# Add the new endpoint
new_endpoint = """
@app.get("/api/secrets/cf/common")
async def get_common_cf_token():
    try:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{PROJECT_ID}"
        for secret in client.list_secrets(request={"parent": parent}):
            if "cf-token-" in secret.name:
                try:
                    resp = client.access_secret_version(request={"name": f"{secret.name}/versions/latest"})
                    return {"status": "success", "token": resp.payload.data.decode("UTF-8").strip()}
                except Exception:
                    continue
        return {"status": "success", "token": ""}
    except Exception as e:
        return {"status": "error", "message": str(e)}

"""

if "get_common_cf_token" not in c:
    # Inject before app.post("/api/clients/{client_id}/secret/{secret_type}")
    c = c.replace('@app.post("/api/clients/{client_id}/secret/{secret_type}")', new_endpoint + '\n@app.post("/api/clients/{client_id}/secret/{secret_type}")')

with open("backend/main.py", "w") as f:
    f.write(c)
