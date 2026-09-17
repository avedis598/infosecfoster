print("KUBECONFIG=$HOME/.kube/config kubectl get pods -A --no-headers | awk '{print $1\"/\"$2\",\"$4}'")
