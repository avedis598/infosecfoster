print("KUBECONFIG=$HOME/.kube/config kubectl get pods -A -o jsonpath='{range .items[*]}{.spec.containers[*].image}{\"\\n\"}{end}'")
