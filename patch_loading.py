import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Add a loading return before the main return
inject_point = r"  return \("
loading_guard = """  if (!client || !editClient) {
    return <div className="min-h-screen bg-black flex items-center justify-center text-white"><Activity className="w-6 h-6 animate-spin text-violet" /></div>
  }

  return ("""

c = re.sub(inject_point, loading_guard, c, count=1)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
