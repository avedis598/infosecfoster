with open("backend/main.py", "r") as f:
    c = f.read()

import re

old = """            if res_pods.exit_status == 0 and res_pods.stdout:
                for line in res_pods.stdout.strip().split('\\n'):
                    parts = line.split(',')
                    if len(parts) == 2:
                        pods.append({"name": parts[0], "status": parts[1]})

            # Get Images
            res_img = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{\\\"\\\\n\\\"}{end}'", check=False)
            images = []
            if res_img.exit_status == 0 and res_img.stdout:
                img_set = set()
                for line in res_img.stdout.strip().split('\\n'):
                    for img in line.split():
                        img_set.add(img)
                for img in img_set:
                    parts = img.split(':')
                    name = parts[0].split('/')[-1]
                    tag = parts[1] if len(parts) > 1 else 'latest'
                    images.append({"name": name, "tag": tag})
                    
            return {"status": "success", "pods": pods, "images": images}"""

new = """            debug_info = {
                "pods_exit": res_pods.exit_status,
                "pods_out": res_pods.stdout,
                "pods_err": res_pods.stderr
            }
            if res_pods.exit_status == 0 and res_pods.stdout:
                for line in res_pods.stdout.strip().split('\\n'):
                    parts = line.split(',')
                    if len(parts) == 2:
                        pods.append({"name": parts[0], "status": parts[1]})

            # Get Images
            res_img = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{\\\"\\\\n\\\"}{end}'", check=False)
            images = []
            debug_info["img_exit"] = res_img.exit_status
            debug_info["img_out"] = res_img.stdout
            debug_info["img_err"] = res_img.stderr
            if res_img.exit_status == 0 and res_img.stdout:
                img_set = set()
                for line in res_img.stdout.strip().split('\\n'):
                    for img in line.split():
                        img_set.add(img)
                for img in img_set:
                    parts = img.split(':')
                    name = parts[0].split('/')[-1]
                    tag = parts[1] if len(parts) > 1 else 'latest'
                    images.append({"name": name, "tag": tag})
            
            if res_pods.exit_status != 0 or res_img.exit_status != 0:
                return {"status": "error", "message": f"Command failed. Debug: {debug_info}"}
                    
            return {"status": "success", "pods": pods, "images": images, "debug": debug_info}"""

c = c.replace(old, new)

with open("backend/main.py", "w") as f:
    f.write(c)

