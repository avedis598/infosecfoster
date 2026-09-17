with open("backend/orchestrator.py", "r") as f:
    c = f.read()

old_query = """                doc_ref = self.db.collection('clients').where('client_id', '==', self.client_id).limit(1).get()
                if doc_ref:
                    self._client_doc_id = doc_ref[0].id
                else:
                    return"""

new_query = """                doc_ref = self.db.collection('clients').where('client_id', '==', self.client_id).limit(1).get()
                if not doc_ref:
                    doc_ref = self.db.collection('clients').where('name', '==', self.client_id).limit(1).get()
                
                if doc_ref:
                    self._client_doc_id = doc_ref[0].id
                else:
                    # Try to see if client_id is actually the document ID
                    doc_test = self.db.collection('clients').document(self.client_id).get()
                    if doc_test.exists:
                        self._client_doc_id = doc_test.id
                    else:
                        print(f"Warning: Could not find Firestore client document for {self.client_id}")
                        return"""

c = c.replace(old_query, new_query)

with open("backend/orchestrator.py", "w") as f:
    f.write(c)

print("orchestrator fallback patched")
