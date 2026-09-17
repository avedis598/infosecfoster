import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

old_header = r"""          <div className="flex items-center gap-2 bg-obsidian border border-white/10 px-3 py-1\.5 rounded-\[8px\]">
            <Activity className=\{`w-3\.5 h-3\.5 \$\{isConnected \? 'text-lime' : 'text-gray-500'\}`\} />
            <span className="text-\[10px\] font-bold uppercase tracking-wider text-white">
              \{isConnected \? editClient\.ip_address : 'Disconnected'\}
            </span>
          </div>"""

new_header = r"""          <div className="flex items-center gap-2 bg-obsidian border border-white/10 px-3 py-1.5 rounded-[8px]">
            <Activity className={`w-3.5 h-3.5 ${isConnected ? 'text-lime' : 'text-gray-500'}`} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-white">
              {isConnected ? editClient.ip_address : 'Disconnected'}
            </span>
            {isConnected && (
              <button 
                onClick={() => setShowTerminal(true)}
                className="ml-2 text-gray-400 hover:text-white transition-colors"
                title="Open Terminal"
              >
                <TerminalIcon className="w-3.5 h-3.5" />
              </button>
            )}
          </div>"""

c = re.sub(old_header, new_header, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
