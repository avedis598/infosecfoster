import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# I need to insert the `getPodCategory` function before the Dashboard component or inside it.
# Let's put it right above the `export default function Dashboard`

category_fn = """
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

export default function Dashboard({ user }) {"""

c = c.replace("export default function Dashboard({ user }) {", category_fn)

# Now, replace the rendering block.
old_rendering = r"""              \{overviewData && overviewData\.pods && overviewData\.pods\.length > 0 \? \(
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 text-sm border-t border-white/5">
                  \{overviewData\.pods\.map\(\(p, i\) => \(
                    <div key=\{i\} className="flex justify-between items-center py-2\.5 border-b border-white/5 hover:bg-white/\[0\.02\]">
                      <span className="text-gray-300 truncate pr-4 text-xs font-mono" title=\{p\.name\}>\{p\.name\.split\('/'\)\[1\] \|\| p\.name\}</span>
                      <span className=\{`text-\[10px\] uppercase font-bold tracking-widest px-2 py-0\.5 rounded bg-white/5 \$\{.*?\}`\}>\{p\.status\}</span>
                    </div>
                  \)\)\}
                </div>
              \) : \("""

new_rendering = """              {overviewData && overviewData.pods && overviewData.pods.length > 0 ? (
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
              ) : ("""

c = re.sub(old_rendering, new_rendering, c, flags=re.DOTALL)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)

