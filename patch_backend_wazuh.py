import re

with open("backend/main.py", "r") as f:
    c = f.read()

old_code = r"""                        if "data" in data and "items" in data\["data"\]:
                            for agent in data\["data"\]\["items"\]:"""

new_code = """                        if "data" in data:
                            items = data["data"]["items"] if isinstance(data["data"], dict) and "items" in data["data"] else data["data"] if isinstance(data["data"], list) else []
                            for agent in items:"""

c = re.sub(old_code, new_code, c)

with open("backend/main.py", "w") as f:
    f.write(c)
