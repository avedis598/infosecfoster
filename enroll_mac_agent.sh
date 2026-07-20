#!/bin/bash
# Script to install and enroll local Mac Agent to aml-lab Wazuh Manager

set -e

echo "=== Wazuh Agent Enrollment for macOS (ARM64) ==="
echo "Manager: 34.18.214.72"
echo "------------------------------------------------"

# 1. Download Apple Silicon agent package
if [ ! -f /tmp/wazuh-agent.pkg ]; then
    echo "Downloading Wazuh Agent package..."
    curl -so /tmp/wazuh-agent.pkg https://packages.wazuh.com/4.x/macos/wazuh-agent-4.7.5-1.arm64.pkg
fi

# 2. Write environment variables for enrollment
echo "Configuring environment variables..."
cat << 'EOF' > /tmp/wazuh_envs
WAZUH_MANAGER='34.18.214.72'
WAZUH_AGENT_GROUP='default'
WAZUH_AGENT_NAME='local-mac-agent'
EOF

# 3. Run the installer (requires sudo)
echo "Installing package (sudo password may be required)..."
sudo installer -pkg /tmp/wazuh-agent.pkg -target /

# 4. Patch ossec.conf directly to ensure the correct manager IP is set (resolves upgrade preservation)
echo "Updating manager IP address inside ossec.conf..."
sudo sed -i '' -E 's|<address>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+</address>|<address>34.18.214.72</address>|g' /Library/Ossec/etc/ossec.conf

# 5. Start/Restart the agent
echo "Restarting Wazuh agent service..."
sudo /Library/Ossec/bin/wazuh-control restart

echo "------------------------------------------------"
echo "Done! The agent should connect to the manager shortly."
echo "You can check status using: sudo /Library/Ossec/bin/wazuh-control status"
