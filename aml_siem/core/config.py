import json
import os

CONFIG_FILE = "config.json"

def _migrate_legacy_config(data):
    """Convert flat config to hierarchical client config."""
    if "clients" not in data:
        # It's a legacy flat config, or empty
        legacy_client = {
            "name": "Legacy Client",
            "tier": "Tier A",
        }
        for k, v in list(data.items()):
            if k not in ["active_client", "clients"]:
                legacy_client[k] = v
                del data[k]
        
        data["clients"] = {"legacy": legacy_client}
        data["active_client"] = "legacy"
        _write_config(data)
    return data

def _write_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}")

def load_config():
    """Load and migrate configuration."""
    if not os.path.exists(CONFIG_FILE):
        return {"active_client": None, "clients": {}}
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return _migrate_legacy_config(data)
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}")
        return {"active_client": None, "clients": {}}

def get_active_client_config():
    """Return the configuration dictionary for the active client."""
    data = load_config()
    client_id = data.get("active_client")
    if client_id and client_id in data.get("clients", {}):
        return data["clients"][client_id]
    return {}

def set_active_client(client_id):
    """Set the currently active client."""
    data = load_config()
    if client_id in data.get("clients", {}):
        data["active_client"] = client_id
        _write_config(data)

def save_client_config(client_id, params):
    """Update a specific client's configuration."""
    data = load_config()
    if "clients" not in data:
        data["clients"] = {}
    
    if client_id not in data["clients"]:
        data["clients"][client_id] = {}
        
    data["clients"][client_id].update(params)
    data["active_client"] = client_id
    _write_config(data)

def save_config(params):
    """Backwards compatibility for app.py saving active client config."""
    data = load_config()
    client_id = data.get("active_client")
    if client_id:
        save_client_config(client_id, params)
    else:
        # Default fallback
        save_client_config("default", params)
