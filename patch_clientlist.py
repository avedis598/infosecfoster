import re

with open("frontend/src/components/ClientList.jsx", "r") as f:
    c = f.read()

inject_handler = r"""  const handleLogout = async \(\) => \{
    await signOut\(auth\)
  \}"""

new_handler = """  const handleLogout = async () => {
    await signOut(auth)
  }

  const handleAddNewClient = () => {
    let cf_token = '';
    let cf_zone = '';
    for (const c of clients) {
      if (c.cloudflare_token) {
        cf_token = c.cloudflare_token;
        cf_zone = c.cloudflare_zone || '';
        break;
      }
    }
    setNewClient({
      client_name: '', client_id: '', ip_address: '', ssh_username: '', alert_email: '',
      shuffle_api_key: '', cloudflare_token: cf_token, cloudflare_zone: cf_zone, private_key: ''
    });
    setShowModal(true);
  }"""

c = re.sub(inject_handler, new_handler, c)

c = c.replace("onClick={() => setShowModal(true)}", "onClick={handleAddNewClient}")

with open("frontend/src/components/ClientList.jsx", "w") as f:
    f.write(c)
