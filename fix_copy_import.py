with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Remove Copy from 'react' import
c = c.replace("import { Copy, useState", "import { useState")

# Add Copy to 'lucide-react' import
if "Copy," not in c.split("lucide-react")[0]:
    c = c.replace("from 'lucide-react'", ", Copy } from 'lucide-react'")
    c = c.replace("} , Copy }", ", Copy }") # clean up

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
