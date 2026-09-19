from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import json
from google.cloud import firestore

router = APIRouter()
db = firestore.Client()

class ImportTemplateRequest(BaseModel):
    template_id: str

@router.post("/clients/{client_id}/shuffle/import")
async def import_shuffle_workflow(client_id: str, req: ImportTemplateRequest):
    # Fetch template from firestore
    template_ref = db.collection('shuffle_templates').document(req.template_id)
    template_doc = template_ref.get()
    
    if not template_doc.exists:
        raise HTTPException(status_code=404, detail="Template not found in global settings")
        
    template_data = template_doc.to_dict()
    workflow_json = template_data.get('json')
    
    if not workflow_json:
        raise HTTPException(status_code=400, detail="Invalid template data: missing json payload")

    # Fetch client data to get Shuffle API key
    # Wait, the client document ID might be the client_id, let's query the clients collection.
    # Usually the doc id is not client_id, let's search by client_id.
    clients_ref = db.collection('clients').where('client_id', '==', client_id).limit(1).get()
    if not clients_ref:
        # Fallback to document ID
        client_doc = db.collection('clients').document(client_id).get()
        if not client_doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
    else:
        client_doc = clients_ref[0]

    client_data = client_doc.to_dict()
    shuffle_api_key = client_data.get('shuffle_api_key')
    
    if not shuffle_api_key:
        raise HTTPException(status_code=400, detail="Shuffle API key is missing for this client. Please configure it in the client settings.")

    # The shuffle UI runs at this domain
    shuffle_url = f"https://shuffle.{client_id}.infosecfoster.com"
    import_url = f"{shuffle_url}/api/v1/workflows"

    headers = {
        "Authorization": f"Bearer {shuffle_api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(verify=False) as http_client:
        try:
            import_resp = await http_client.post(import_url, headers=headers, json=workflow_json, timeout=15.0)
            
            if import_resp.status_code not in (200, 201):
                print("Shuffle import failed:", import_resp.text)
                raise HTTPException(status_code=import_resp.status_code, detail=f"Shuffle rejected workflow import: {import_resp.text}")
                
            return {"status": "success", "message": "Workflow imported successfully"}

        except httpx.RequestError as e:
            print("HTTP Request Error:", e)
            raise HTTPException(status_code=503, detail="Unable to reach client's Shuffle instance")

@router.get("/clients/{client_id}/shuffle/workflows")
async def list_shuffle_workflows(client_id: str):
    clients_ref = db.collection('clients').where('client_id', '==', client_id).limit(1).get()
    if not clients_ref:
        client_doc = db.collection('clients').document(client_id).get()
        if not client_doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
    else:
        client_doc = clients_ref[0]

    client_data = client_doc.to_dict()
    shuffle_api_key = client_data.get('shuffle_api_key')
    
    if not shuffle_api_key:
        raise HTTPException(status_code=400, detail="Shuffle API key is missing for this client.")

    shuffle_url = f"https://shuffle.{client_id}.infosecfoster.com"
    list_url = f"{shuffle_url}/api/v1/workflows"

    headers = {
        "Authorization": f"Bearer {shuffle_api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(verify=False) as http_client:
        try:
            resp = await http_client.get(list_url, headers=headers, timeout=10.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch workflows: {resp.text}")
                
            workflows = resp.json()
            # Shuffle returns a list of workflow objects
            return {"status": "success", "workflows": workflows}

        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail="Unable to reach client's Shuffle instance")
