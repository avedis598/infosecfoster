import sys
import os

import aml_siem_setup_old as old

def write_module(name, data, var_name):
    with open(name, "w") as out:
        out.write(f"{var_name} = [\n")
        for item in data:
            out.write("    {\n")
            for k, v in item.items():
                if isinstance(v, str) and '\n' in v:
                    out.write(f'        "{k}": """{v}""",\n')
                else:
                    out.write(f'        "{k}": {repr(v)},\n')
            out.write("    },\n")
        out.write("]\n")

if __name__ == "__main__":
    m0_steps = old.LOCAL_STEPS + old.REMOTE_STEPS + old.DOCKER_STEPS + old.K3S_STEPS + old.NGINX_STEPS + old.GIT_STEPS
    m1_steps = old.OPENSEARCH_STEPS + old.WAZUH_STEPS + old.DASHBOARD_STEPS + old.AGENT_STEPS + old.SYSLOG_STEPS
    m2_steps = old.PLAYBOOK_STEPS + old.PLAYBOOK_OTHER_STEPS
    
    # Prepend Sprint identifiers to step IDs for UI grouping if they don't already have one
    for step in m0_steps:
        if not str(step["id"]).startswith("0."):
            step["id"] = "0." + str(step["id"])
            
    for step in m1_steps:
        if not str(step["id"]).startswith("1."):
            step["id"] = "1." + str(step["id"])
            
    for step in m2_steps:
        if not str(step["id"]).startswith("2."):
            step["id"] = "2." + str(step["id"])
            
    write_module("aml_siem/steps/m0_foundation.py", m0_steps, "M0_STEPS")
    write_module("aml_siem/steps/m1_detection.py", m1_steps, "M1_STEPS")
    write_module("aml_siem/steps/m2_automation.py", m2_steps, "M2_STEPS")
    print("Done extracting steps.")
