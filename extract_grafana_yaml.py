import sys
from aml_siem.steps.m3_intelligence import M3_STEPS

for step in M3_STEPS:
    if step["id"] == "3.M3.3":
        for cmd_dict in step["cmds"]:
            cmd = cmd_dict["cmd"]
            if "kubectl apply -f - <<'INNER'" in cmd:
                parts = cmd.split("<<'INNER'")
                if len(parts) >= 2:
                    yaml_part = parts[1].split("INNER")[0].strip()
                    print(yaml_part)
                    print("---")
