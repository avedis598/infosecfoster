import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# We need to add the Lucide icons if not imported
if "Activity," not in c and "Activity " not in c:
    c = c.replace("import { ", "import { Activity, Cpu, HardDrive, Clock, ", 1)

old_ui = r"""              \{overviewData && overviewData\.error && \(
                <div className="bg-red-500/20 text-red-400 border border-red-500/30 p-3 mb-4 rounded-lg text-xs font-mono">
                  Error Fetching Data: \{overviewData\.error\}
                </div>
              \)\}
              \{overviewData && overviewData\.pods && overviewData\.pods\.length > 0 \? \("""

new_ui = """              {overviewData && overviewData.error && (
                <div className="bg-red-500/20 text-red-400 border border-red-500/30 p-3 mb-4 rounded-lg text-xs font-mono">
                  Error Fetching Data: {overviewData.error}
                </div>
              )}
              
              {/* SERVER HEALTH CARDS */}
              {overviewData && overviewData.health && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className={`absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full ${overviewData.health.cpu > 80 ? 'bg-red-500/20' : overviewData.health.cpu > 50 ? 'bg-amber-500/20' : 'bg-emerald-500/20'}`}></div>
                    <div className="flex items-center gap-2 mb-2">
                      <Cpu className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">CPU Usage</span>
                    </div>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-black text-white">{overviewData.health.cpu}</span>
                      <span className="text-sm font-bold text-gray-500 mb-1">%</span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full mt-3 overflow-hidden">
                      <div className={`h-full rounded-full ${overviewData.health.cpu > 80 ? 'bg-red-500' : overviewData.health.cpu > 50 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{width: `${Math.min(overviewData.health.cpu, 100)}%`}}></div>
                    </div>
                  </div>
                  
                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className={`absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full ${overviewData.health.memory > 85 ? 'bg-red-500/20' : overviewData.health.memory > 70 ? 'bg-amber-500/20' : 'bg-blue-500/20'}`}></div>
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Memory</span>
                    </div>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-black text-white">{overviewData.health.memory}</span>
                      <span className="text-sm font-bold text-gray-500 mb-1">%</span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full mt-3 overflow-hidden">
                      <div className={`h-full rounded-full ${overviewData.health.memory > 85 ? 'bg-red-500' : overviewData.health.memory > 70 ? 'bg-amber-500' : 'bg-blue-500'}`} style={{width: `${Math.min(overviewData.health.memory, 100)}%`}}></div>
                    </div>
                  </div>

                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className={`absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full ${parseInt(overviewData.health.disk.replace('%','')) > 85 ? 'bg-red-500/20' : parseInt(overviewData.health.disk.replace('%','')) > 70 ? 'bg-amber-500/20' : 'bg-purple-500/20'}`}></div>
                    <div className="flex items-center gap-2 mb-2">
                      <HardDrive className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Disk (/)</span>
                    </div>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-black text-white">{overviewData.health.disk}</span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full mt-3 overflow-hidden">
                      <div className={`h-full rounded-full ${parseInt(overviewData.health.disk.replace('%','')) > 85 ? 'bg-red-500' : parseInt(overviewData.health.disk.replace('%','')) > 70 ? 'bg-amber-500' : 'bg-purple-500'}`} style={{width: overviewData.health.disk}}></div>
                    </div>
                  </div>

                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className="absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full bg-white/5"></div>
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Uptime</span>
                    </div>
                    <div className="flex items-center h-full">
                      <span className="text-sm font-bold text-white capitalize leading-tight">{overviewData.health.uptime}</span>
                    </div>
                  </div>
                </div>
              )}

              {overviewData && overviewData.pods && overviewData.pods.length > 0 ? ("""

c = re.sub(old_ui, new_ui, c, flags=re.DOTALL)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
