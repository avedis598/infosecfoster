with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Import ErrorBoundary at the top
c = c.replace("import { useState, useEffect, useRef } from 'react'", "import { useState, useEffect, useRef } from 'react'\nimport { ErrorBoundary } from './ErrorBoundary'")

# Wrap the Dashboard component's return statement
c = c.replace("return (\n    <div className=", "return (\n    <ErrorBoundary>\n    <div className=")
c = c.replace("    </div>\n  )\n}", "    </div>\n    </ErrorBoundary>\n  )\n}")

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
