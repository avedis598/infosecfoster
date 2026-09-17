with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

import re
# Remove the debug box from the UI
c = re.sub(r'\{overviewData && overviewData\.debug && \(\s*<div className="bg-blue-500/20 text-blue-400 border border-blue-500/30 p-3 mb-4 rounded-lg text-xs font-mono break-all whitespace-pre-wrap">\s*DEBUG: \{JSON\.stringify\(overviewData\.debug, null, 2\)\}\s*</div>\s*\)\}', '', c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)

