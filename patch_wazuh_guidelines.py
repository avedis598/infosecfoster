import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Make sure we add Terminal/Copy icons if needed. But lucide-react already has TerminalIcon. Let's import Copy too.
if "Copy," not in c and "Copy " not in c:
    c = c.replace("import { ", "import { Copy, ", 1)

old_ui = r"""                  <h3 className="text-lg font-bold text-white mb-4">OpenSearch Alerts \(Last 24h\)</h3>
                  <div className="grid grid-cols-3 gap-4">
                    \{\[
                      \{ label: 'Total', val: wazuhData\?\.alerts\?\.total \?\? '-', color: wazuhData \? 'text-white' : 'text-gray-600' \},
                      \{ label: 'Level 12\+', val: wazuhData\?\.alerts\?\.high \?\? '-', color: wazuhData && wazuhData\.alerts\.high > 0 \? 'text-red-500' : 'text-gray-600' \},
                      \{ label: 'Auth Failure', val: wazuhData\?\.alerts\?\.auth \?\? '-', color: wazuhData && wazuhData\.alerts\.auth > 0 \? 'text-amber-500' : 'text-gray-600' \}
                    \]\.map\(stat => \(
                      <div key=\{stat\.label\} className="bg-obsidian border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center shadow-inner">
                        <span className="text-\[10px\] text-gray-400 uppercase tracking-wider font-bold mb-2">\{stat\.label\}</span>
                        <span className=\{`text-2xl font-black \$\{stat\.color\}`\}>\{stat\.val\}</span>
                      </div>
                    \)\)\}
                  </div>
                </div>
              </div>
            </div>
          </div>
        \)\}"""

new_ui = """                  <h3 className="text-lg font-bold text-white mb-4">OpenSearch Alerts (Last 24h)</h3>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { label: 'Total', val: wazuhData?.alerts?.total ?? '-', color: wazuhData ? 'text-white' : 'text-gray-600' },
                      { label: 'Level 12+', val: wazuhData?.alerts?.high ?? '-', color: wazuhData && wazuhData.alerts.high > 0 ? 'text-red-500' : 'text-gray-600' },
                      { label: 'Auth Failure', val: wazuhData?.alerts?.auth ?? '-', color: wazuhData && wazuhData.alerts.auth > 0 ? 'text-amber-500' : 'text-gray-600' }
                    ].map(stat => (
                      <div key={stat.label} className="bg-obsidian border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center shadow-inner">
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2">{stat.label}</span>
                        <span className={`text-2xl font-black ${stat.color}`}>{stat.val}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* AGENT ENROLLMENT GUIDELINES */}
                <div className="mt-8 pt-8 border-t border-white/5">
                  <h3 className="text-lg font-bold text-white mb-6">Agent Enrollment Guidelines</h3>
                  
                  <div className="space-y-6">
                    <div className="bg-obsidian/80 border border-white/5 rounded-xl p-5">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center border border-sky-500/20">
                          <TerminalIcon className="w-4 h-4 text-sky-400" />
                        </div>
                        <h4 className="text-sm font-bold text-gray-200 uppercase tracking-wider">Windows Deployment</h4>
                      </div>
                      <p className="text-xs text-gray-400 mb-3 leading-relaxed">Run the following command in an Administrator PowerShell prompt. This downloads the agent, sets your manager IP, installs the service, and starts it automatically.</p>
                      <div className="relative group">
                        <div className="bg-black/50 p-4 rounded-lg border border-white/5 font-mono text-[10px] text-sky-300 leading-relaxed overflow-x-auto whitespace-pre">
                          {`Invoke-WebRequest -Uri https://packages.wazuh.com/4.x/windows/wazuh-agent-4.7.5-1.msi -OutFile wazuh-agent.msi; msiexec.exe /i wazuh-agent.msi /q WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com' WAZUH_REGISTRATION_SERVER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'; NET START Wazuh`}
                        </div>
                        <button 
                          onClick={() => navigator.clipboard.writeText(`Invoke-WebRequest -Uri https://packages.wazuh.com/4.x/windows/wazuh-agent-4.7.5-1.msi -OutFile wazuh-agent.msi; msiexec.exe /i wazuh-agent.msi /q WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com' WAZUH_REGISTRATION_SERVER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'; NET START Wazuh`)}
                          className="absolute top-2 right-2 p-1.5 bg-white/5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10"
                        >
                          <Copy className="w-3.5 h-3.5 text-gray-400" />
                        </button>
                      </div>
                    </div>

                    <div className="bg-obsidian/80 border border-white/5 rounded-xl p-5">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                          <TerminalIcon className="w-4 h-4 text-emerald-400" />
                        </div>
                        <h4 className="text-sm font-bold text-gray-200 uppercase tracking-wider">macOS Deployment</h4>
                      </div>
                      <p className="text-xs text-gray-400 mb-3 leading-relaxed">Run the following command in a macOS Terminal as root (or prepend with sudo). This fetches the package, installs it, configures the manager, and loads the daemon.</p>
                      <div className="relative group">
                        <div className="bg-black/50 p-4 rounded-lg border border-white/5 font-mono text-[10px] text-emerald-300 leading-relaxed overflow-x-auto whitespace-pre">
                          {`curl -o wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/wazuh-agent-4.7.5-1.pkg && echo "WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'" > /tmp/wazuh_envs && installer -pkg wazuh-agent.pkg -target / && /Library/Ossec/bin/wazuh-control start`}
                        </div>
                        <button 
                          onClick={() => navigator.clipboard.writeText(`curl -o wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/wazuh-agent-4.7.5-1.pkg && echo "WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'" > /tmp/wazuh_envs && installer -pkg wazuh-agent.pkg -target / && /Library/Ossec/bin/wazuh-control start`)}
                          className="absolute top-2 right-2 p-1.5 bg-white/5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10"
                        >
                          <Copy className="w-3.5 h-3.5 text-gray-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}"""

c = re.sub(old_ui, new_ui, c, flags=re.DOTALL)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
