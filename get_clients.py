import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred = credentials.Certificate('backend/serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()
docs = db.collection('clients').get()
for doc in docs:
    d = doc.to_dict()
    print(f"Client {d.get('client_id')}: cf_token = {d.get('cloudflare_token')}")
