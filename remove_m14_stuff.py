import re

with open("backend/steps/m1_detection.py", "r") as f:
    c = f.read()

# 1. Remove the local tasks from M1.4
# They look like: 
# {'label': 'Install Wazuh sudoers rule (enables password-free agent control)', 'mode': 'local_install_wazuh_sudo', 'cmd': ''}, 
# {'label': 'Reset and re-enroll local macOS agent (if keys exist)', 'mode': 'local_enroll_mac', 'cmd': ''}
c = re.sub(r",\s*\{'label':\s*'Install Wazuh sudoers rule.*?\}", "", c, flags=re.DOTALL)
c = re.sub(r",\s*\{'label':\s*'Reset and re-enroll local macOS agent.*?\}", "", c, flags=re.DOTALL)

# 2. Remove the entire GATE_M14 step dict
pattern_gate = r"\{\s*\"id\":\s*'1\.GATE_M14',.*?\},"
c = re.sub(pattern_gate, "", c, flags=re.DOTALL)

with open("backend/steps/m1_detection.py", "w") as f:
    f.write(c)

print("Removed M1.4 local tasks and GATE_M14")
