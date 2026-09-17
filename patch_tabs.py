import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Fix Wazuh "Open in Browser" and add basic content to other tabs
def replacer_wazuh(match):
    return match.group(0).replace('<button className="bg-sky-500', '<button onClick={() => window.open(`https://wazuh.${editClient.client_id || editClient.name}.infosecfoster.com`, \'_blank\')} className="bg-sky-500')

c = re.sub(r'<button className="bg-sky-500 hover:bg-sky-400 text-white px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-\[0_0_20px_rgba\(14,165,233,0\.3\)\] flex items-center gap-2 transition-all mb-10 z-10">.*?Open in Browser\s*</button>', replacer_wazuh, c, flags=re.DOTALL)

# Also fix the pending run passwords
c = c.replace('<span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded italic">pending run</span>', '<span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">wazuh</span>')

# Replace the placeholders for TheHive and Shuffle, and ADD Grafana (it wasn't even in the placeholder list!)
old_placeholders = r"""        \{\/\* ==================== PLACEHOLDERS ==================== \*\/\}
        \{\['TheHive', 'Shuffle'\]\.includes\(activeTab\) && \(
          <div className="h-full flex flex-col items-center justify-center text-gray-500 animate-in fade-in">
            <Settings2 className="w-12 h-12 mb-4 opacity-20" />
            <p className="font-bold tracking-widest uppercase">\{activeTab\} Dashboard Module</p>
            <p className="text-sm mt-2 opacity-50">Under Construction</p>
          </div>
        \)\}"""

new_tabs = """        {/* ==================== THEHIVE TAB ==================== */}
        {activeTab === 'TheHive' && (
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[800px] h-[800px] bg-yellow-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-600 mb-4 z-10">
                TheHive Platform
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https://thehive.{editClient.client_id || editClient.name}.infosecfoster.com</p>
              
              <button onClick={() => window.open(`https://thehive.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="bg-yellow-500 hover:bg-yellow-400 text-black px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(234,179,8,0.3)] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" /> Open in Browser
              </button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin@thehive.local</span></div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">secret</span></div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== GRAFANA TAB ==================== */}
        {activeTab === 'Grafana' && (
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[800px] h-[800px] bg-orange-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-red-600 mb-4 z-10">
                Grafana Metrics
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https://grafana.{editClient.client_id || editClient.name}.infosecfoster.com</p>
              
              <button onClick={() => window.open(`https://grafana.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="bg-orange-500 hover:bg-orange-400 text-white px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(249,115,22,0.3)] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" /> Open in Browser
              </button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin</span></div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin</span></div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== SHUFFLE TAB ==================== */}
        {activeTab === 'Shuffle' && (
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[800px] h-[800px] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-600 mb-4 z-10">
                Shuffle SOAR
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https://shuffle.{editClient.client_id || editClient.name}.infosecfoster.com</p>
              
              <button onClick={() => window.open(`https://shuffle.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="bg-purple-500 hover:bg-purple-400 text-white px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(168,85,247,0.3)] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" /> Open in Browser
              </button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin@shuffle.com</span></div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin</span></div>
              </div>
            </div>
          </div>
        )}"""

c = re.sub(old_placeholders, new_tabs, c, flags=re.DOTALL)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)

