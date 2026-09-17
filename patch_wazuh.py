import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# 1. Add isRefreshingWazuh state
state_match = r"const \[isRefreshing, setIsRefreshing\] = useState\(false\)"
c = re.sub(state_match, "const [isRefreshing, setIsRefreshing] = useState(false)\n  const [isRefreshingWazuh, setIsRefreshingWazuh] = useState(false)", c)

# 2. Update fetchWazuh to use the state
fetch_old = r"""  const fetchWazuh = async \(\) => \{
    if \(\!editClient\) return
    try \{"""

fetch_new = """  const fetchWazuh = async () => {
    if (!editClient) return
    setIsRefreshingWazuh(true)
    try {"""
c = re.sub(fetch_old, fetch_new, c)

fetch_end_old = r"""      if \(data\.status === 'success'\) setWazuhData\(data\)
    \} catch \(e\) \{
      console\.error\(e\)
    \}
  \}"""

fetch_end_new = """      if (data.status === 'success') setWazuhData(data)
    } catch (e) {
      console.error(e)
    }
    setIsRefreshingWazuh(false)
  }"""
c = re.sub(fetch_end_old, fetch_end_new, c)


# 3. Replace the Wazuh Tab Layout
layout_old = r"""        \{\/\* ==================== WAZUH TAB ==================== \*\/\}
        \{activeTab === 'Wazuh' && \(
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white\/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-\[-50%\] w-\[800px\] h-\[800px\] bg-sky-500\/10 blur-\[120px\] rounded-full pointer-events-none"><\/div>
              
              <button onClick=\{fetchWazuh\} className="absolute top-6 right-6 flex items-center gap-2 bg-obsidian border border-white\/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white\/20 transition-all z-20">
                <RefreshCcw className=\{`w-3\.5 h-3\.5 \$\{\!wazuhData && activeTab === 'Wazuh' \? 'animate-spin' : ''\}`\} \/> Refresh
              <\/button>

              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-600 mb-4 z-10">
                Wazuh Dashboard
              <\/h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https:\/\/wazuh\.\{editClient\.client_id\}\.infosecfoster\.com<\/p>
              
              <button onClick=\{\(\) => window\.open\(`https:\/\/wazuh\.\$\{editClient\.client_id \|\| editClient\.name\}\.infosecfoster\.com`, '_blank'\)\} className="bg-sky-500 hover:bg-sky-400 text-white px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-\[0_0_20px_rgba\(14,165,233,0\.3\)\] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" \/> Open in Browser
              <\/button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:<\/span><span className="text-gray-400 font-mono bg-white\/5 px-2 py-0\.5 rounded">wazuh<\/span><\/div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:<\/span><span className="text-gray-400 font-mono bg-white\/5 px-2 py-0\.5 rounded">wazuh<\/span><\/div>
              <\/div>

              <div className="w-full max-w-2xl z-10 space-y-8">"""

layout_new = """        {/* ==================== WAZUH TAB ==================== */}
        {activeTab === 'Wazuh' && (
          <div className="w-full h-full animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[1200px] h-[800px] bg-sky-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <div className="absolute top-6 right-6 flex items-center gap-3 z-20">
                <button onClick={() => window.open(`https://wazuh.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="flex items-center gap-2 bg-sky-500 hover:bg-sky-400 border border-sky-500/50 px-4 py-2 rounded-lg text-xs font-bold text-white shadow-[0_0_15px_rgba(14,165,233,0.3)] transition-all">
                  <ExternalLink className="w-3.5 h-3.5" /> Open in Browser
                </button>
                
                <div className="relative group">
                  <button className="flex items-center justify-center bg-obsidian border border-white/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all">
                    <Info className="w-3.5 h-3.5 mr-2" /> Credentials
                  </button>
                  <div className="absolute right-0 top-full mt-2 w-48 bg-obsidian border border-white/10 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all p-3 z-50">
                    <div className="flex flex-col gap-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500 font-bold">Username:</span>
                        <span className="text-gray-300 font-mono">wazuh</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500 font-bold">Password:</span>
                        <span className="text-gray-300 font-mono">wazuh</span>
                      </div>
                    </div>
                  </div>
                </div>

                <button onClick={fetchWazuh} disabled={isRefreshingWazuh} className="flex items-center gap-2 bg-obsidian border border-white/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all disabled:opacity-50">
                  <RefreshCcw className={`w-3.5 h-3.5 ${isRefreshingWazuh ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>

              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-600 mb-2 z-10">
                Wazuh Dashboard
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-12 z-10">https://wazuh.{editClient.client_id}.infosecfoster.com</p>

              <div className="w-full z-10 space-y-8">"""

c = re.sub(layout_old, layout_new, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
