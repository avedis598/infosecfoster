with open("backend/main.py", "r") as f:
    c = f.read()

# Replace sudo k3s kubectl with KUBECONFIG=~/.kube/config kubectl
c = c.replace("sudo k3s kubectl get pods -A --no-headers | awk", "KUBECONFIG=~/.kube/config kubectl get pods -A --no-headers | awk")

with open("backend/main.py", "w") as f:
    f.write(c)
