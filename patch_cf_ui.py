import sys
with open("frontend/src/components/ClientList.jsx", "r") as f:
    c = f.read()

# 1. Add state variable
state_inject = "  const navigate = useNavigate()"
new_state = "  const navigate = useNavigate()\n  const [isCfTokenDerived, setIsCfTokenDerived] = useState(false)"
c = c.replace(state_inject, new_state)

# 2. Update fetch logic
fetch_old = """      if (data.status === 'success' && data.token) {
        cf_token = data.token;
      }"""
fetch_new = """      if (data.status === 'success' && data.token) {
        cf_token = data.token;
        setIsCfTokenDerived(true);
      } else {
        setIsCfTokenDerived(false);
      }"""
c = c.replace(fetch_old, fetch_new)

# 3. Update the UI
ui_old = """                  <div>
                    <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">API Token</label>
                    <input 
                      type="password"
                      className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                      value={newClient.cloudflare_token}
                      onChange={(e) => setNewClient({ ...newClient, cloudflare_token: e.target.value })}
                      placeholder="cfut_C7vOHs..."
                    />
                  </div>"""

ui_new = """                  <div>
                    <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1 flex justify-between items-center">
                      <span>API Token</span>
                      {isCfTokenDerived && (
                         <span className="text-[9px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/30 flex items-center gap-1">
                           <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
                           Secured by GSM
                         </span>
                      )}
                    </label>
                    <input 
                      type="password"
                      className={`w-full px-4 py-3 rounded-[12px] text-white outline-none transition-all placeholder:text-gray-700 ${
                        isCfTokenDerived 
                          ? 'bg-blue-900/20 border-2 border-blue-500/40 focus:ring-1 focus:ring-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.1)] text-blue-200' 
                          : 'bg-obsidian border border-white/10 focus:ring-1 focus:ring-violet focus:border-violet'
                      }`}
                      value={newClient.cloudflare_token}
                      onChange={(e) => {
                        setNewClient({ ...newClient, cloudflare_token: e.target.value });
                        setIsCfTokenDerived(false);
                      }}
                      placeholder="cfut_C7vOHs..."
                    />
                  </div>"""

c = c.replace(ui_old, ui_new)

with open("frontend/src/components/ClientList.jsx", "w") as f:
    f.write(c)
