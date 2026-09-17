import sys
with open("frontend/src/components/ClientList.jsx", "r") as f:
    c = f.read()

# Replace the state initialization
c = c.replace("cloudflare_token: '',\n    cloudflare_zone: ''", "cloudflare_token: ''")
c = c.replace("cloudflare_token: '', cloudflare_zone: ''", "cloudflare_token: ''")
c = c.replace("cloudflare_zone: newClient.cloudflare_zone,", "")

# Replace the handler
old_handler_start = "  const handleAddNewClient = () => {"
old_handler_end = "    setShowModal(true);\n  }"

start_idx = c.find(old_handler_start)
end_idx = c.find(old_handler_end) + len(old_handler_end)

if start_idx != -1 and end_idx != -1:
    new_handler = """  const handleAddNewClient = () => {
    let cf_token = localStorage.getItem('cf_token_common') || '';
    for (const c of clients) {
      if (c.cloudflare_token) {
        cf_token = c.cloudflare_token;
        break;
      }
    }
    setNewClient({
      client_name: '', client_id: '', ip_address: '', ssh_username: '', alert_email: '',
      shuffle_api_key: '', cloudflare_token: cf_token, private_key: ''
    });
    setShowModal(true);
  }"""
    c = c[:start_idx] + new_handler + c[end_idx:]

# Save to localStorage on submit
save_point = "      await addDoc(collection(db, 'clients'), {"
new_save = """      if (newClient.cloudflare_token) {
        localStorage.setItem('cf_token_common', newClient.cloudflare_token);
      }
      await addDoc(collection(db, 'clients'), {"""
c = c.replace(save_point, new_save)

# Remove the Zone ID HTML
zone_html_start = "                  <div>\n                    <label className=\"block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1\">Zone ID</label>"
zone_html_end = "placeholder=\"717dadb849...\"\n                    />\n                  </div>"

start_html = c.find(zone_html_start)
end_html = c.find(zone_html_end) + len(zone_html_end)

if start_html != -1 and end_html != -1:
    c = c[:start_html] + c[end_html:]

# Fix grid col
c = c.replace('className="grid grid-cols-1 md:grid-cols-2 gap-5"', 'className="grid grid-cols-1 gap-5"')

with open("frontend/src/components/ClientList.jsx", "w") as f:
    f.write(c)

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    d = f.read()

# In Dashboard, there's a reference to cloudflare_zone during the save operation.
# We just need to remove it.
d = d.replace("        cloudflare_zone: editClient.cloudflare_zone", "")

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(d)
