import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import secretmanager

# We need PROJECT_ID
PROJECT_ID = "infosecfoster-5bb83"

client = secretmanager.SecretManagerServiceClient()
parent = f"projects/{PROJECT_ID}"
for secret in client.list_secrets(request={"parent": parent}):
    if "cf-token-" in secret.name:
        print("Found:", secret.name)
        try:
            resp = client.access_secret_version(request={"name": f"{secret.name}/versions/latest"})
            print("Value:", resp.payload.data.decode("UTF-8"))
            break
        except Exception as e:
            print("Error accessing:", e)
