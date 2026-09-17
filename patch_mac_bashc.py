with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

old = r"""{`ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/$PKG && echo "WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start`}"""

new = r"""{`bash -c 'ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg "https://packages.wazuh.com/4.x/macos/$PKG" && echo "WAZUH_MANAGER='\''wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'\''" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start'`}"""

old_btn = r"""onClick={() => navigator.clipboard.writeText(`ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/$PKG && echo "WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start`)}"""

new_btn = r"""onClick={() => navigator.clipboard.writeText(`bash -c 'ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg "https://packages.wazuh.com/4.x/macos/$PKG" && echo "WAZUH_MANAGER='\''wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'\''" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start'`)}"""

c = c.replace(old, new)
c = c.replace(old_btn, new_btn)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
