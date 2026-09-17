with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Add handleStopRun
c = c.replace("const handleDeployComplete = () => {", "const handleStopRun = () => {\n    setTerminalMounted(false)\n    setDeploying(false)\n  }\n\n  const handleDeployComplete = () => {")

# Replace button
old_button = """                <button onClick={handleDeploy} disabled={deploying} className="w-full py-4 bg-violet hover:bg-violet-hover disabled:opacity-50 text-white rounded-[12px] font-bold uppercase tracking-wider text-sm flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_var(--color-violet-glow)]">
                  <Play className="w-4 h-4 fill-current" /> {deploying ? 'Deploying...' : 'Initialize Run'}
                </button>"""

new_button = """                {deploying ? (
                  <button onClick={handleStopRun} className="w-full py-4 bg-red-600 hover:bg-red-700 text-white rounded-[12px] font-bold uppercase tracking-wider text-sm flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(220,38,38,0.5)]">
                    <X className="w-4 h-4" /> Stop Execution
                  </button>
                ) : (
                  <button onClick={handleDeploy} className="w-full py-4 bg-violet hover:bg-violet-hover text-white rounded-[12px] font-bold uppercase tracking-wider text-sm flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_var(--color-violet-glow)]">
                    <Play className="w-4 h-4 fill-current" /> Initialize Run
                  </button>
                )}"""

c = c.replace(old_button, new_button)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)

print("Dashboard stop button patched")
