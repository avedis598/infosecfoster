import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# 1. Remove "Cluster Overview" card completely.
old_cluster_overview_card = """            <div className="flex items-center justify-between bg-matte border border-white/5 rounded-xl px-6 py-4 shadow-xl">
              <h2 className="text-xl font-bold text-white tracking-wide">Cluster Overview</h2>
              <button onClick={fetchOverview} disabled={isRefreshing} className="flex items-center gap-2 bg-obsidian border border-white/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all">
                <RefreshCcw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} /> Refresh
              </button>
            </div>"""
c = c.replace(old_cluster_overview_card, "")

# 2 & 3. Add refresh button to Pod Status card and change to 2-column table style
old_pod_status_section = r"""            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pod Status</h3>
              \{overviewData && overviewData\.error && \(.*?Error Fetching Data: \{overviewData\.error\}.*?</div>\n              \)\}
              \{overviewData && overviewData\.pods && overviewData\.pods\.length > 0 \? \(
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  \{overviewData\.pods\.map\(\(p, i\) => \(
                    <div key=\{i\} className="bg-obsidian border border-white/5 rounded-lg p-3 flex flex-col gap-1">
                      <span className="text-xs font-bold text-gray-300 truncate" title=\{p\.name\}>\{p\.name\.split\('/'\)\[1\] \|\| p\.name\}</span>
                      <span className=\{`text-\[10px\] uppercase font-bold tracking-widest \$\{.*?\}`\}>\{p\.status\}</span>
                    </div>
                  \)\)\}
                </div>"""

new_pod_status_section = """            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Pod Status</h3>
                <button onClick={fetchOverview} disabled={isRefreshing} className="flex items-center gap-2 bg-obsidian border border-white/10 px-3 py-1.5 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all">
                  <RefreshCcw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} /> Refresh
                </button>
              </div>
              {overviewData && overviewData.error && (
                <div className="bg-red-500/20 text-red-400 border border-red-500/30 p-3 mb-4 rounded-lg text-xs font-mono">
                  Error Fetching Data: {overviewData.error}
                </div>
              )}
              {overviewData && overviewData.pods && overviewData.pods.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 text-sm border-t border-white/5">
                  {overviewData.pods.map((p, i) => (
                    <div key={i} className="flex justify-between items-center py-2.5 border-b border-white/5 hover:bg-white/[0.02]">
                      <span className="text-gray-300 truncate pr-4 text-xs font-mono" title={p.name}>{p.name.split('/')[1] || p.name}</span>
                      <span className={`text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-white/5 ${['Running', 'Completed'].includes(p.status) ? 'text-emerald-400' : ['CrashLoopBackOff', 'Error', 'Failed', 'ImagePullBackOff', 'ErrImagePull'].includes(p.status) ? 'text-red-400' : 'text-amber-400'}`}>{p.status}</span>
                    </div>
                  ))}
                </div>"""

c = re.sub(old_pod_status_section, new_pod_status_section, c, flags=re.DOTALL)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
