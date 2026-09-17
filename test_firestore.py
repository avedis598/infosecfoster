import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase (assuming default credentials work here, or we use the backend's method)
try:
    firebase_admin.initialize_app()
except ValueError:
    pass

db = firestore.client()
doc = db.collection('clients').document('EiQ5QCpfs6dZUSuYy9Cr').get()

if doc.exists:
    data = doc.to_dict()
    print("Client ID:", data.get('client_id'))
    print("Step Status:", data.get('step_status'))
else:
    print("Document does not exist.")
