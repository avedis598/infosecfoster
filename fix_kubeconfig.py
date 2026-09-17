with open("backend/main.py", "r") as f:
    c = f.read()

c = c.replace("KUBECONFIG=~/.kube/config", "KUBECONFIG=$HOME/.kube/config")

with open("backend/main.py", "w") as f:
    f.write(c)
