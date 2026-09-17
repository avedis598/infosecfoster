import re

with open("backend/main.py", "r") as f:
    c = f.read()

old_overview = r"""            # Get Server Health
            health = \{"cpu": 0, "memory": 0, "disk": "0%", "uptime": "Unknown"\}
            res_health = await conn\.run\("CPU_IDLE=\$\(vmstat 1 2 \| tail -1 \| awk '\{print \$15\}'\); echo \\"\$\(\(100 - CPU_IDLE\)\)\|\$\(free -m \| awk 'NR==2\{printf \\"%\.1f\\", \$3\*100/\$2\}'\)\|\$\(df -h / \| awk 'NR==2\{print \$5\}'\)\|\$\(uptime -p\)\\"", check=False\)
            if res_health\.exit_status == 0:
                parts = res_health\.stdout\.strip\(\)\.split\('\|'\)
                if len\(parts\) == 4:
                    health = \{
                        "cpu": float\(parts\[0\]\) if parts\[0\]\.replace\('\.','',1\)\.isdigit\(\) else 0,
                        "memory": float\(parts\[1\]\) if parts\[1\]\.replace\('\.','',1\)\.isdigit\(\) else 0,
                        "disk": parts\[2\],
                        "uptime": parts\[3\]\.replace\('up ', ''\)
                    \}"""

new_overview = """            # Get Server Health
            health = {"cpu": 0, "cores": 0, "load": "", "memory": 0, "memory_used": "", "memory_total": "", "disk": "0%", "disk_used": "", "disk_total": "", "uptime": "Unknown"}
            cmd = "CPU_IDLE=$(vmstat 1 2 | tail -1 | awk '{print $15}'); echo \\"$((100 - CPU_IDLE))|$(nproc)|$(cat /proc/loadavg | awk '{print $1\\", \\"$2\\", \\"$3}')|$(free -m | awk 'NR==2{print $3, $2}')|$(df -h / | awk 'NR==2{print $3, $2, $5}')|$(uptime -p)\\""
            res_health = await conn.run(cmd, check=False)
            if res_health.exit_status == 0:
                parts = res_health.stdout.strip().split('|')
                if len(parts) >= 6:
                    cpu_usage = float(parts[0]) if parts[0].replace('.','',1).isdigit() else 0
                    cores = int(parts[1]) if parts[1].isdigit() else 0
                    load = parts[2]
                    
                    mem_parts = parts[3].split()
                    mem_used_mb = float(mem_parts[0]) if len(mem_parts) > 0 else 0
                    mem_total_mb = float(mem_parts[1]) if len(mem_parts) > 1 else 1
                    mem_usage = round((mem_used_mb / mem_total_mb) * 100, 1)
                    
                    disk_parts = parts[4].split()
                    disk_used = disk_parts[0] if len(disk_parts) > 0 else "0G"
                    disk_total = disk_parts[1] if len(disk_parts) > 1 else "0G"
                    disk_pct = disk_parts[2] if len(disk_parts) > 2 else "0%"
                    
                    health = {
                        "cpu": cpu_usage,
                        "cores": cores,
                        "load": load,
                        "memory": mem_usage,
                        "memory_used": f"{round(mem_used_mb/1024, 1)}GB",
                        "memory_total": f"{round(mem_total_mb/1024, 1)}GB",
                        "disk": disk_pct,
                        "disk_used": disk_used,
                        "disk_total": disk_total,
                        "uptime": parts[5].replace('up ', '')
                    }"""

c = re.sub(old_overview, new_overview, c, flags=re.DOTALL)

with open("backend/main.py", "w") as f:
    f.write(c)
