import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# 1. Update useState for isConnected and activeTab
old_state = r"""  const \[isConnected, setIsConnected\] = useState\(false\)
  const \[isConnecting, setIsConnecting\] = useState\(false\)
  const \[activeTab, setActiveTab\] = useState\('Connection'\)"""

new_state = """  const [isConnected, setIsConnected] = useState(localStorage.getItem('connected_' + id) === 'true')
  const [isConnecting, setIsConnecting] = useState(false)
  const [activeTab, setActiveTab] = useState(localStorage.getItem('tab_' + id) || 'Connection')

  useEffect(() => {
    if (id) {
      localStorage.setItem('tab_' + id, activeTab)
      localStorage.setItem('connected_' + id, isConnected.toString())
    }
  }, [activeTab, isConnected, id])"""

c = re.sub(old_state, new_state, c)

# 2. Update handleConnect
old_handle_connect = r"""    setTimeout\(\(\) => \{
      setIsConnected\(true\)
      setIsConnecting\(false\)
    \}, 1500\)"""

new_handle_connect = """    setTimeout(() => {
      setIsConnected(true)
      setIsConnecting(false)
      setActiveTab('Setup')
    }, 1500)"""

c = re.sub(old_handle_connect, new_handle_connect, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
