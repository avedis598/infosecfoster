import re

with open("frontend/src/App.jsx", "r") as f:
    c = f.read()

import_boundary = "import { ErrorBoundary } from './components/ErrorBoundary'\n"
if "import { ErrorBoundary }" not in c:
    c = c.replace("import { auth } from './firebase'", "import { auth } from './firebase'\n" + import_boundary)

return_old = r"  return \(\n    <BrowserRouter>"
return_new = r"""  return (
    <ErrorBoundary>
    <BrowserRouter>"""
c = re.sub(return_old, return_new, c)

c = c.replace("</BrowserRouter>\n  )", "</BrowserRouter>\n    </ErrorBoundary>\n  )")

with open("frontend/src/App.jsx", "w") as f:
    f.write(c)
