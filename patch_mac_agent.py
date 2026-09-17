import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

old_mac = r"""                      <p className="text-xs text-gray-400 mb-3 leading-relaxed">Run the following command in a macOS Terminal as root \(or prepend with sudo\)\. This fetches the package, installs it, configures the manager, and loads the daemon\.</p>
                      <div className="relative group">
                        <div className="bg-black/50 p-4 rounded-lg border border-white/5 font-mono text-\[10px\] text-emerald-300 leading-relaxed overflow-x-auto whitespace-pre">
                          \{`curl -o wazuh-agent\.pkg https://packages\.wazuh\.com/4\.x/macos/wazuh-agent-4\.7\.5-1\.pkg && echo "WAZUH_MANAGER='wazuh\.\$\{editClient\.client_id \|\| editClient\.name\}\.infosecfoster\.com'" > /tmp/wazuh_envs && installer -pkg wazuh-agent\.pkg -target / && /Library/Ossec/bin/wazuh-control start`\}
                        </div>
                        <button 
                          onClick=\{\(\) => navigator\.clipboard\.writeText\(`curl -o wazuh-agent\.pkg https://packages\.wazuh\.com/4\.x/macos/wazuh-agent-4\.7\.5-1\.pkg && echo "WAZUH_MANAGER='wazuh\.\$\{editClient\.client_id \|\| editClient\.name\}\.infosecfoster\.com'" > /tmp/wazuh_envs && installer -pkg wazuh-agent\.pkg -target / && /Library/Ossec/bin/wazuh-control start`\)\}"""

new_mac = """                      <p className="text-xs text-gray-400 mb-3 leading-relaxed">Run the following command in a macOS Terminal. It will automatically detect your chip architecture (Intel/Apple Silicon), download the agent, and prompt for your password to install it.</p>
                      <div className="relative group">
                        <div className="bg-black/50 p-4 rounded-lg border border-white/5 font-mono text-[10px] text-emerald-300 leading-relaxed overflow-x-auto whitespace-pre">
                          {`ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/$PKG && echo "WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start`}
                        </div>
                        <button 
                          onClick={() => navigator.clipboard.writeText(`ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/$PKG && echo "WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start`)}"""

c = re.sub(old_mac, new_mac, c, flags=re.DOTALL)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
