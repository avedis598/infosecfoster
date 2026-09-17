import re

with open("backend/main.py", "r") as f:
    c = f.read()

# We insert the health check command into monitor_overview
old_overview = r"""            # Get Pods
            res_pods = await conn.run\("KUBECONFIG=\$HOME/\.kube/config kubectl get pods -A --no-headers \| awk '\{print \$1\\"/\\"\$2\\",\\"\$4\}'", check=False\)
            pods = \[\]"""

new_overview = """            # Get Server Health
            health = {"cpu": 0, "memory": 0, "disk": "0%", "uptime": "Unknown"}
            res_health = await conn.run("CPU_IDLE=$(vmstat 1 2 | tail -1 | awk '{print $15}'); echo \\"$((100 - CPU_IDLE))|$(free -m | awk 'NR==2{printf \\"%.1f\\", $3*100/$2}')|$(df -h / | awk 'NR==2{print $5}')|$(uptime -p)\\"", check=False)
            if res_health.exit_status == 0:
                parts = res_health.stdout.strip().split('|')
                if len(parts) == 4:
                    health = {
                        "cpu": float(parts[0]) if parts[0].replace('.','',1).isdigit() else 0,
                        "memory": float(parts[1]) if parts[1].replace('.','',1).isdigit() else 0,
                        "disk": parts[2],
                        "uptime": parts[3].replace('up ', '')
                    }

            # Get Pods
            res_pods = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get pods -A --no-headers | awk '{print $1\\"/\\"$2\\",\\"$4}'", check=False)
            pods = []"""

c = re.sub(old_overview, new_overview, c, flags=re.DOTALL)

# And update the return payload
c = c.replace('return {"status": "success", "pods": pods, "images": images, "debug": debug_info}', 'return {"status": "success", "pods": pods, "images": images, "health": health, "debug": debug_info}')

with open("backend/main.py", "w") as f:
    f.write(c)
