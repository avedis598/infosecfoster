import json, uuid

def get_uuid():
    return str(uuid.uuid4())

with open('PB01_Shuffle_Workflow.json', 'r') as f:
    data = json.load(f)

# ID mapping
id_map = {}

# Fix triggers
for t in data.get('triggers', []):
    new_id = get_uuid()
    id_map[t['id']] = new_id
    t['id'] = new_id

# Fix actions
for a in data.get('actions', []):
    new_id = get_uuid()
    id_map[a['id']] = new_id
    a['id'] = new_id
    
# Fix branches
for b in data.get('branches', []):
    b['id'] = get_uuid()
    b['source_id'] = id_map.get(b['source_id'], b['source_id'])
    b['destination_id'] = id_map.get(b['destination_id'], b['destination_id'])

# Additional required top-level fields for Shuffle V1
data['id'] = get_uuid()
data['org_id'] = ""

# Shuffle JSON usually includes these fields at root level as well
data['execution_argument'] = ""
data['is_valid'] = True

with open('PB01_Shuffle_Workflow.json', 'w') as f:
    json.dump(data, f, indent=2)

print("Fixed PB01_Shuffle_Workflow.json")
