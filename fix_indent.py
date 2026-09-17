import re

with open("backend/orchestrator.py", "r") as f:
    c = f.read()

c = c.replace("        for step in target_steps:\n                current_running_step = step['id']", "            for step in target_steps:\n                current_running_step = step['id']")
c = c.replace("            title = step[\"title\"]", "                title = step[\"title\"]")
c = c.replace("            step_mode = step.get(\"mode\", \"remote\")", "                step_mode = step.get(\"mode\", \"remote\")")
c = c.replace("            # Pre-check logic", "                # Pre-check logic")
c = c.replace("            pre = step.get(\"pre_check\", \"\")", "                pre = step.get(\"pre_check\", \"\")")

# I need to indent EVERYTHING inside the `try:` block by 4 more spaces.
