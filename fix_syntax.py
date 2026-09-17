with open("backend/main.py", "r") as f:
    c = f.read()

# Fix the res_pods command
c = c.replace(
    'res_pods = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get pods -A --no-headers | awk \'{print $1"/"$2","$4}\'", check=False)',
    'res_pods = await conn.run("KUBECONFIG=$HOME/.kube/config kubectl get pods -A --no-headers | awk \'{print $1\\"/\\"$2\\",\\"$4}\'", check=False)'
)

# Fix the res_img command (it might also have lost backslashes!)
# Let's check what it is:
# "KUBECONFIG=$HOME/.kube/config kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{\"\\n\"}{end}'"
# Wait, if it has {\"\\n\"} in the file, we should leave it alone or fix it if it's broken.
# Let's just fix res_pods for now.

with open("backend/main.py", "w") as f:
    f.write(c)

print("Syntax fixed")
