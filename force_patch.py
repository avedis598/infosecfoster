with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Let's find exactly the Pod Status rendering block and replace it manually.
start_idx = c.find('<h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pod Status</h3>')
end_idx = c.find(') : (', start_idx)

if start_idx != -1 and end_idx != -1:
    new_block = """<div className="flex justify-between items-center mb-6">
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
                <div className="flex flex-col gap-6 mt-4">
                  {Object.entries(
                    overviewData.pods.reduce((acc, pod) => {
                      const cat = getPodCategory(pod.name)
                      if (!acc[cat]) acc[cat] = []
                      acc[cat].push(pod)
                      return acc
                    }, {})
                  ).map(([category, pods]) => (
                    <div key={category} className="bg-obsidian/50 rounded-xl p-4 border border-white/5">
                      <h4 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3 border-b border-white/5 pb-2">{category} <span className="text-gray-600 ml-2">({pods.length})</span></h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 text-sm">
                        {pods.map((p, i) => (
                          <div key={i} className="flex justify-between items-center py-2 border-b border-white/5 hover:bg-white/[0.04] transition-colors rounded px-2 -mx-2">
                            <span className="text-gray-300 truncate pr-4 text-[11px] font-mono" title={p.name}>{p.name.split('/')[1] || p.name}</span>
                            <span className={`text-[9px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-white/5 ${['Running', 'Completed'].includes(p.status) ? 'text-emerald-400' : ['CrashLoopBackOff', 'Error', 'Failed', 'ImagePullBackOff', 'ErrImagePull'].includes(p.status) ? 'text-red-400' : 'text-amber-400'}`}>{p.status}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              """
    
    c = c[:start_idx] + new_block + c[end_idx:]
    
    # We also need to add getPodCategory
    if "getPodCategory" not in c:
        cat_fn = """
const getPodCategory = (name) => {
  const n = name.toLowerCase()
  if (n.includes('wazuh')) return 'Wazuh SIEM'
  if (n.includes('opensearch') && !n.includes('shuffle')) return 'OpenSearch Cluster'
  if (n.includes('shuffle')) return 'Shuffle SOAR'
  if (n.includes('thehive') || n.includes('cassandra')) return 'TheHive Platform'
  if (n.includes('grafana') || n.includes('clickhouse')) return 'Metrics & Visualization'
  if (n.includes('cronjob') || n.includes('report') || n.includes('threat-intel') || n.includes('test-')) return 'CronJobs & Tasks'
  if (n.includes('kube-system') || n.includes('cert-manager') || n.includes('ingress') || n.includes('svclb')) return 'System Infrastructure'
  return 'Other Services'
}

export default function Dashboard"""
        c = c.replace("export default function Dashboard", cat_fn)
    
    with open("frontend/src/components/Dashboard.jsx", "w") as f:
        f.write(c)
    print("SUCCESS")
else:
    print("FAILED TO FIND")
