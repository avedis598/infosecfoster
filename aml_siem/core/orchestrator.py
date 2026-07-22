import threading
import queue
import time

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
        
        from .config import load_config
        cfg = load_config()
        domain = cfg.get("cf_domain", "amlsiem.com")
        alert_email = cfg.get("alert_email", "admin@amlsiem.com")
        
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
                        pre = pre.replace("admin@amlsiem.com", alert_email).replace("amlsiem.com", domain)
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
                                ok, output = True, "Local execution mock"
                            elif sub_mode == "reconnect":
                                # Simple reconnect mock for now
                                ok, output = True, "Reconnected"
                            elif sub_mode == "remote_upload":
                                script = cmd_dict.get("script", "")
                                if script:
                                    script = script.replace("admin@amlsiem.com", alert_email).replace("amlsiem.com", domain)
                                ok, output = self.ssh.run_script(script)
                            else:
                                cmd_str = cmd_dict.get("cmd", "")
                                if not cmd_str:
                                    ok, output = True, ""
                                else:
                                    cmd_str = cmd_str.replace("admin@amlsiem.com", alert_email).replace("amlsiem.com", domain)
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
