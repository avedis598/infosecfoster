with open("backend/main.py", "r") as f:
    c = f.read()

# Replace `sudo k3s kubectl` with `KUBECONFIG=~/.kube/config kubectl`
old_pods_cmd = 'await conn.run("sudo k3s kubectl get pods -A --no-headers | awk \'{print $1\\"/\\"$2\\",\\"$4}\'", check=False)'
new_pods_cmd = 'await conn.run("KUBECONFIG=~/.kube/config kubectl get pods -A --no-headers | awk \'{print $1\\"/\\"$2\\",\\"$4}\'", check=False)'
c = c.replace(old_pods_cmd, new_pods_cmd)

old_img_cmd = 'await conn.run("sudo k3s kubectl get pods -A -o jsonpath=\'{range .items[*]}{.spec.containers[*].image}{\\\"\\\\n\\\"}{end}\'", check=False)'
new_img_cmd = 'await conn.run("KUBECONFIG=~/.kube/config kubectl get pods -A -o jsonpath=\'{range .items[*]}{.spec.containers[*].image}{\\\"\\\\n\\\"}{end}\'", check=False)'
c = c.replace(old_img_cmd, new_img_cmd)

with open("backend/main.py", "w") as f:
    f.write(c)

print("Overview API patched in main.py")
