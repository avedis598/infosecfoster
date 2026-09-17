import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

old_loading = r'<div className="min-h-screen bg-black flex items-center justify-center text-white"><Activity className="w-6 h-6 animate-spin text-violet" \/><\/div>'
new_loading = r'<div className="min-h-screen bg-[#0D0D0E] flex flex-col items-center justify-center text-white"><Activity className="w-12 h-12 animate-spin text-violet mb-4" /><h2 className="text-xl font-bold">Loading Client Data...</h2></div>'

c = re.sub(old_loading, new_loading, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
