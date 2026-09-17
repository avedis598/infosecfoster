import re

with open("backend/orchestrator.py", "r") as f:
    c = f.read()

pattern = r"(        for step in target_steps:.*?)(        await self\.log\(\"\\n\[SUCCESS\] All selected steps deployed successfully!\", \"ok\"\)\n        return True)"

def do_replace(match):
    body = match.group(1)
    footer = match.group(2)
    
    # Indent every line in body by 4 spaces
    indented_body = "\n".join("    " + line if line.strip() else line for line in body.split("\n"))
    indented_body = indented_body.replace("            for step in target_steps:", "            for step in target_steps:\n                current_running_step = step['id']")
    
    out = """        current_running_step = None
        try:
""" + indented_body + """        except Exception as e:
            if current_running_step:
                try:
                    self._update_db_status({current_running_step: "failed"})
                except:
                    pass
            raise e

""" + footer
    return out

new_c = re.sub(pattern, do_replace, c, flags=re.DOTALL)

with open("backend/orchestrator.py", "w") as f:
    f.write(new_c)

print("Orchestrator try-except patched cleanly")
