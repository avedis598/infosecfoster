import re
with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

old_ui = """              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pod Status</h3>"""

new_ui = """              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Pod Status</h3>
              {overviewData && overviewData.debug && (
                <div className="bg-blue-500/20 text-blue-400 border border-blue-500/30 p-3 mb-4 rounded-lg text-xs font-mono break-all whitespace-pre-wrap">
                  DEBUG: {JSON.stringify(overviewData.debug, null, 2)}
                </div>
              )}"""

c = c.replace(old_ui, new_ui)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
