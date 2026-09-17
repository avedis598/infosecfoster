import re

with open("backend/main.py", "r") as f:
    c = f.read()

old_code = r"""                                agents\["total"\] \+\= 1
                                status = agent.get\("status", ""\)\.lower\(\)"""

new_code = """                                if agent.get("id") == "000": continue
                                agents["total"] += 1
                                status = agent.get("status", "").lower()"""

c = re.sub(old_code, new_code, c)

with open("backend/main.py", "w") as f:
    f.write(c)
