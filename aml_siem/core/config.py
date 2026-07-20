import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from config.json, preserving extra fields like Cloudflare tokens."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {CONFIG_FILE}: {e}")
        return {}

def save_config(params):
    """Update config.json without overwriting unmanaged fields."""
    current = load_config()
    current.update(params)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(current, f, indent=2)
    except Exception as e:
        print(f"Error saving {CONFIG_FILE}: {e}")
