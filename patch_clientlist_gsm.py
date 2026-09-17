import sys
with open("frontend/src/components/ClientList.jsx", "r") as f:
    c = f.read()

# Replace the handler
old_handler_start = "  const handleAddNewClient = () => {"
old_handler_end = "    setShowModal(true);\n  }"

start_idx = c.find(old_handler_start)
end_idx = c.find(old_handler_end) + len(old_handler_end)

if start_idx != -1 and end_idx != -1:
    new_handler = """  const handleAddNewClient = async () => {
    let cf_token = '';
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
      const res = await fetch(`${backendUrl}/api/secrets/cf/common`);
      const data = await res.json();
      if (data.status === 'success' && data.token) {
        cf_token = data.token;
      }
    } catch (e) {
      console.error("Failed to fetch common CF token from GSM", e);
    }
    
    setNewClient({
      client_name: '', client_id: '', ip_address: '', ssh_username: '', alert_email: '',
      shuffle_api_key: '', cloudflare_token: cf_token, private_key: ''
    });
    setShowModal(true);
  }"""
    c = c[:start_idx] + new_handler + c[end_idx:]

# Remove localStorage sets
c = c.replace("""      if (newClient.cloudflare_token) {
        localStorage.setItem('cf_token_common', newClient.cloudflare_token);
      }
""", "")

with open("frontend/src/components/ClientList.jsx", "w") as f:
    f.write(c)

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    d = f.read()

d = d.replace("""        if (type === 'cf') {
          localStorage.setItem('cf_token_common', input)
        }""", "")

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(d)
