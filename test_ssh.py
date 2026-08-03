import sys
sys.path.append('.')
from aml_siem.core.ssh_runner import run_ssh_command

cmd = "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}') -c wazuh-manager -- cat /var/ossec/etc/ossec.conf | tail -n 40"
code, stdout, stderr = run_ssh_command(cmd)
print("STDOUT:\n", stdout)
print("STDERR:\n", stderr)
