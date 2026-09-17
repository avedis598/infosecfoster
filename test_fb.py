import firebase_admin
from firebase_admin import firestore
firebase_admin.initialize_app()
db = firestore.client()
docs = db.collection('clients').get()
for doc in docs:
    data = doc.to_dict()
    print(f"ID: {doc.id}, client_id: {data.get('client_id')}, step_status: {data.get('step_status')}")
