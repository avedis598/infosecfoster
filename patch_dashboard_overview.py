import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Replace the pods rendering section
old_pods = """                      <span className={`text-[10px] uppercase font-bold tracking-widest ${p.status === 'Running' || p.status === 'Completed' ? 'text-emerald-500' : 'text-amber-500'}`}>{p.status}</span>"""

new_pods = """                      <span className={`text-[10px] uppercase font-bold tracking-widest ${['Running', 'Completed'].includes(p.status) ? 'text-emerald-500' : ['CrashLoopBackOff', 'Error', 'Failed', 'ImagePullBackOff', 'ErrImagePull'].includes(p.status) ? 'text-red-500' : 'text-amber-500'}`}>{p.status}</span>"""

c = c.replace(old_pods, new_pods)

# Add Tool Versions section
old_tool_section = """            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Service Health</h3>"""

new_tool_section = """            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Tool Versions</h3>
              {overviewData && overviewData.images && overviewData.images.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {overviewData.images.map((img, i) => (
                    <div key={i} className="bg-obsidian border border-white/5 px-3 py-1.5 rounded flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-300">{img.name}</span>
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono">{img.tag}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500">No version data available.</div>
              )}
            </div>

            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Service Health</h3>"""

c = c.replace(old_tool_section, new_tool_section)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)

print("Overview section patched in Dashboard.jsx")
