import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

# Fix agents.disconnected
old_disc = r"color: wazuhData && wazuhData\.agents\.disconnected > 0 \? 'text-red-500' : 'text-gray-600'"
new_disc = "color: (wazuhData?.agents?.disconnected > 0) ? 'text-red-500' : 'text-gray-600'"
c = re.sub(old_disc, new_disc, c)

# Fix alerts.high
old_high = r"color: wazuhData && wazuhData\.alerts\.high > 0 \? 'text-red-500' : 'text-gray-600'"
new_high = "color: (wazuhData?.alerts?.high > 0) ? 'text-red-500' : 'text-gray-600'"
c = re.sub(old_high, new_high, c)

# Fix alerts.auth
old_auth = r"color: wazuhData && wazuhData\.alerts\.auth > 0 \? 'text-amber-500' : 'text-gray-600'"
new_auth = "color: (wazuhData?.alerts?.auth > 0) ? 'text-amber-500' : 'text-gray-600'"
c = re.sub(old_auth, new_auth, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
