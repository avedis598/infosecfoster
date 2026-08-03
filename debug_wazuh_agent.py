import json
from aml_siem.core.ssh_runner import SSHRunner
from aml_siem.core.config import get_active_client_config

cfg = get_active_client_config()
ssh = SSHRunner(cfg.get("host"), "22", cfg.get("user"), cfg.get("ssh_key"))
ok, msg = ssh.connect()

cmd = "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}') -c wazuh-manager -- /var/ossec/bin/agent_control -j -s"
ok, out = ssh.run(cmd)
print("OUT:", repr(out))
ssh.close()
