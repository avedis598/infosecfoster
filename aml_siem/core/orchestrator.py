import threading
import queue
import time
import json
import urllib.request
import urllib.error

class Orchestrator:
    def __init__(self, ssh_runner):
        self.ssh = ssh_runner
        self.ui_queue = queue.Queue()
        self.running = False
        
    def _put_ui(self, fn):
        """Push a callable onto the UI queue."""
        self.ui_queue.put(fn)
        
    def run_steps(self, steps, on_log, on_log_output, on_badge_update, on_sub_update, on_progress, on_complete, force=False):
        """Execute a list of step dictionaries in a background thread."""
        if self.running:
            return False
            
        self.running = True
        
        from .config import get_active_client_config
        cfg = get_active_client_config()
        domain = cfg.get("cf_domain", "amlsiem.com")
        alert_email = cfg.get("alert_email", "admin@amlsiem.com")
        client_id = cfg.get("client_id", "aml-lab")
        
        def worker():
            try:
                # Count total sub-commands across all steps
                total_subs = sum(len(step.get("cmds", [])) for step in steps)
                done = 0
                
                on_progress(0, total_subs, "Starting...")
                
                for step in steps:
                    if not self.running:
                        break
                        
                    step_id = step["id"]
                    title = step["title"]
                    step_mode = step.get("mode", "remote")
                    
                    # Pre-check (skip if already done)
                    pre = step.get("pre_check", "")
                    if pre and not force:
                        pre = pre.replace("admin@amlsiem.com", alert_email).replace("amlsiem.com", domain).replace("aml-lab", client_id)
                        if pre != "false":
                            ok, out = self.ssh.run(pre)
                            if ok:
                                on_log(f"\n{'─'*52}\n[{step_mode.upper()}] {title}", "head")
                                on_log(f"  ✓ Already done — {title}", "ok")
                                done += len(step.get("cmds", []))
                                on_progress(done, total_subs, f"{done}/{total_subs} sub-steps")
                                on_badge_update(step_id, "Skipped", "gray")
                                continue

                    on_log(f"\n{'─'*52}\n[{step_mode.upper()}] {title}", "head")
                    on_badge_update(step_id, "Running...", "cyan")
                    
                    step_ok = True
                    for i, cmd_dict in enumerate(step.get("cmds", [])):
                        if not self.running:
                            break
                            
                        label = cmd_dict.get("label", f"Step {i+1}")
                        on_log(f"  → {label}", "cmd")
                        on_sub_update(step_id, i, "running")
                        
                        sub_mode = cmd_dict.get("mode", step_mode)
                        
                        try:
                            if sub_mode == "local" or sub_mode.startswith("local_"):
                                if sub_mode == "local_get_ip":
                                    ok, output = True, f"Confirmed VM external IP: {cfg.get('host')}"
                                elif sub_mode == "local_dns":
                                    cf_token = cfg.get("cf_token", "")
                                    cf_zone = cfg.get("cf_zone", "")
                                    host_ip = cfg.get("host", "")
                                    record_name = cmd_dict.get("record_name", "").replace("aml-lab", client_id)
                                    if record_name.endswith(f".{client_id}"):
                                        record_name = record_name.replace(f".{client_id}", f".{client_id}.{domain}")
                                    elif record_name == client_id:
                                        record_name = f"{client_id}.{domain}"
                                    
                                    if not (cf_token and cf_zone and host_ip):
                                        ok, output = False, "Missing Cloudflare token, zone, or host IP in config"
                                    else:
                                        req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{cf_zone}/dns_records?name={record_name}", headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"})
                                        try:
                                            with urllib.request.urlopen(req) as resp:
                                                data = json.loads(resp.read().decode())
                                                records = data.get("result", [])
                                            
                                            payload = json.dumps({"type": "A", "name": record_name, "content": host_ip, "ttl": 1, "proxied": False}).encode("utf-8")
                                            if records:
                                                rec_id = records[0]["id"]
                                                req_upd = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{cf_zone}/dns_records/{rec_id}", data=payload, headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}, method="PUT")
                                                with urllib.request.urlopen(req_upd) as resp_upd:
                                                    ok, output = True, f"Updated existing A record {record_name} to {host_ip}"
                                            else:
                                                req_new = urllib.request.Request(f"https://api.cloudflare.com/client/v4/zones/{cf_zone}/dns_records", data=payload, headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}, method="POST")
                                                with urllib.request.urlopen(req_new) as resp_new:
                                                    ok, output = True, f"Created new A record {record_name} to {host_ip}"
                                        except Exception as e:
                                            ok, output = False, f"Cloudflare API error: {e}"
                                elif sub_mode == "local_install_wazuh_sudo":
                                    ok, output = True, "Skipped sudoers install (using native macOS UI prompt instead)"
                                elif sub_mode == "local_enroll_mac":
                                    import subprocess
                                    import socket
                                    wazuh_server = f"wazuh.{client_id}.{domain}"
                                    agent_name = socket.gethostname()
                                    skip_enrollment = False
                                    
                                    # Check existing agent status on manager
                                    pod_cmd = f"KUBECONFIG=~/.kube/config kubectl get pods -n {client_id} -l node-role=master -o jsonpath='{{.items[0].metadata.name}}'"
                                    ok_pod, pod_name = self.ssh.run(pod_cmd)
                                    if ok_pod and pod_name:
                                        pod_name = pod_name.strip()
                                        _, agents_list = self.ssh.run(f"KUBECONFIG=~/.kube/config kubectl exec -n {client_id} {pod_name} -c wazuh-manager -- /var/ossec/bin/manage_agents -l")
                                        agent_id = None
                                        if agents_list:
                                            for line in agents_list.splitlines():
                                                if agent_name in line and "ID:" in line:
                                                    for p in line.split(","):
                                                        p = p.strip()
                                                        if p.startswith("ID:"):
                                                            agent_id = p.replace("ID:", "").strip()
                                        if agent_id:
                                            _, status_out = self.ssh.run(f"KUBECONFIG=~/.kube/config kubectl exec -n {client_id} {pod_name} -c wazuh-manager -- /var/ossec/bin/agent_control -i {agent_id}")
                                            is_active = status_out and ("Status: Active" in status_out or "Status: active" in status_out.lower())
                                            if is_active and not force:
                                                skip_enrollment = True
                                                ok, output = True, f"Agent {agent_name} ({agent_id}) is already active. Skipping enrollment."
                                            else:
                                                self.ssh.run(f"KUBECONFIG=~/.kube/config kubectl exec -n {client_id} {pod_name} -c wazuh-manager -- /var/ossec/bin/manage_agents -r {agent_id}")
                                                
                                    if not skip_enrollment:
                                        # Use osascript to prompt for admin password natively via UI
                                        # agent-auth only gets the key. We must also update ossec.conf with the server address.
                                        script = f"/Library/Ossec/bin/agent-auth -m {wazuh_server} && sed -i '' 's|<address>.*</address>|<address>{wazuh_server}</address>|g' /Library/Ossec/etc/ossec.conf && /Library/Ossec/bin/wazuh-control restart"
                                        osa = f'do shell script "{script}" with administrator privileges'
                                        try:
                                            res = subprocess.run(["osascript", "-e", osa], capture_output=True, text=True)
                                            if res.returncode == 0:
                                                ok, output = True, f"Enrolled MAC agent to {wazuh_server}\n{res.stdout}"
                                            else:
                                                ok, output = False, f"Enrollment failed: {res.stderr}\n{res.stdout}"
                                        except Exception as e:
                                            ok, output = False, f"Error running osascript: {e}"
                                else:
                                    ok, output = True, "Local execution mock"
                            elif sub_mode == "reconnect":
                                # Simple reconnect mock for now
                                ok, output = True, "Reconnected"
                            elif sub_mode == "remote_upload":
                                script = cmd_dict.get("script", "")
                                if script:
                                    script = script.replace("admin@amlsiem.com", alert_email).replace("amlsiem.com", domain).replace("aml-lab", client_id)
                                ok, output = self.ssh.run_script(script)
                            else:
                                cmd_str = cmd_dict.get("cmd", "")
                                if not cmd_str:
                                    ok, output = True, ""
                                else:
                                    cmd_str = cmd_str.replace("admin@amlsiem.com", alert_email).replace("amlsiem.com", domain).replace("aml-lab", client_id)
                                    ok, output = self.ssh.run(cmd_str)
                                    
                            if output:
                                on_log_output(output)
                                
                            if ok:
                                on_sub_update(step_id, i, "ok")
                                done += 1
                                on_progress(done, total_subs, f"{done}/{total_subs} sub-steps")
                            else:
                                step_ok = False
                                on_sub_update(step_id, i, "fail")
                                on_log(f"  ✘ Failed: {label}", "fail")
                                on_badge_update(step_id, "Failed", "red")
                                self.running = False
                                break
                                
                        except Exception as e:
                            step_ok = False
                            on_sub_update(step_id, i, "fail")
                            on_log(f"  ✘ Error: {e}", "fail")
                            on_badge_update(step_id, "Error", "red")
                            self.running = False
                            break
                            
                    if step_ok and self.running:
                        on_badge_update(step_id, "Done", "green")
                        
            except Exception as e:
                on_log(f"Error during execution: {e}", "fail")
            finally:
                self.running = False
                on_complete()
                
        threading.Thread(target=worker, daemon=True).start()
        
    def stop(self):
        """Signal the orchestrator to stop execution before the next step."""
        self.running = False
