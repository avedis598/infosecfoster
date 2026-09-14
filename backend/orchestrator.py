import asyncio
import json
import urllib.request

class CloudOrchestrator:
    def __init__(self, ws, conn, client_id, domain="infosecfoster.com", alert_email="admin@infosecfoster.com"):
        self.ws = ws
        self.conn = conn
        self.client_id = client_id
        self.domain = domain
        self.alert_email = alert_email

    async def log(self, msg, status="cmd"):
        color = "\x1b[37m" # white
        if status == "head": color = "\x1b[35m" # magenta
        elif status == "ok": color = "\x1b[32m" # green
        elif status == "fail": color = "\x1b[31m" # red
        elif status == "cmd": color = "\x1b[36m" # cyan
        
        # Replace newlines with \r\n for xterm.js
        formatted = msg.replace('\n', '\r\n')
        await self.ws.send_text(f"{color}{formatted}\x1b[0m\r\n")

    async def _run_remote(self, cmd_str):
        if not cmd_str: return True, ""
        
        cmd_str = cmd_str.replace("admin@amlsiem.com", self.alert_email)
        cmd_str = cmd_str.replace("amlsiem.com", self.domain)
        cmd_str = cmd_str.replace("aml-lab", self.client_id)
        
        try:
            result = await self.conn.run(cmd_str, check=False)
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return result.exit_status == 0, output.strip()
        except Exception as e:
            return False, str(e)

    async def run_steps(self, step_ids, is_force=False):
        # Dynamically import all steps to build the full catalog
        all_steps = []
        try:
            from steps.m0_foundation import M0_STEPS
            from steps.m1_detection import M1_STEPS
            from steps.m2_automation import M2_STEPS
            from steps.m3_intelligence import M3_STEPS
            all_steps.extend(M0_STEPS)
            all_steps.extend(M1_STEPS)
            all_steps.extend(M2_STEPS)
            all_steps.extend(M3_STEPS)
        except Exception as e:
            await self.log(f"Failed to load module definitions: {e}", "fail")
            return False

        # Filter steps by step_ids
        # If step_ids is empty, maybe they want to run all? No, if empty it runs none.
        if not step_ids:
            await self.log("No steps selected for deployment.", "fail")
            return False

        target_steps = [s for s in all_steps if s["id"] in step_ids]
        if not target_steps:
            await self.log(f"None of the selected steps {step_ids} were found in the definitions.", "fail")
            return False

        await self.log(f"Starting cloud deployment sequence. Found {len(target_steps)} steps to execute. Force: {is_force}", "head")

        for step in target_steps:
            title = step["title"]
            step_mode = step.get("mode", "remote")
            
            # Pre-check logic
            pre = step.get("pre_check", "")
            if pre and pre != "false" and not is_force:
                ok, out = await self._run_remote(pre)
                if ok:
                    await self.log(f"\n{'─'*50}\n[{step_mode.upper()}] {title}", "head")
                    await self.log(f"  ✓ Already done — {title}", "ok")
                    continue

            await self.log(f"\n{'─'*50}\n[{step_mode.upper()}] {title}", "head")
            
            step_ok = True
            for i, cmd_dict in enumerate(step.get("cmds", [])):
                label = cmd_dict.get("label", f"Step {i+1}")
                await self.log(f"  → {label}", "cmd")
                
                sub_mode = cmd_dict.get("mode", step_mode)
                
                try:
                    if sub_mode == "local" or sub_mode.startswith("local_"):
                        # Cloud optimizations for local tasks
                        if sub_mode == "local_dns":
                            ok, output = True, "[SKIPPED] DNS handled via Google Cloud natively"
                        elif sub_mode == "local_enroll_mac":
                            ok, output = True, "[SKIPPED] Mac enrollment omitted in cloud orchestrator"
                        elif sub_mode == "local_config":
                            ok, output = True, "[SKIPPED] local ssh config not needed in cloud"
                        else:
                            ok, output = True, "[SKIPPED] local task ignored in cloud orchestrator"
                            
                    elif sub_mode == "remote_upload":
                        # In the new system we just execute script inline
                        script = cmd_dict.get("script", "")
                        if script:
                            # Write to temp file and bash it
                            remote_cmd = f"cat << 'INNER_EOF' > /tmp/run.sh\n{script}\nINNER_EOF\nbash /tmp/run.sh && rm /tmp/run.sh"
                            ok, output = await self._run_remote(remote_cmd)
                        else:
                            ok, output = True, ""
                    else:
                        cmd_str = cmd_dict.get("cmd", "")
                        if isinstance(cmd_str, list):
                            # Sometime local cmds are lists like ['bash', '-c', '...']
                            cmd_str = " ".join(cmd_str)
                        ok, output = await self._run_remote(cmd_str)

                    if output:
                        # stream output safely
                        out_lines = output.replace('\n', '\r\n')
                        await self.ws.send_text(f"\x1b[37m{out_lines}\x1b[0m\r\n")

                    if not ok:
                        await self.log(f"  ✘ Failed: {label}", "fail")
                        step_ok = False
                        break
                        
                except Exception as e:
                    await self.log(f"  ✘ Error: {e}", "fail")
                    step_ok = False
                    break
                    
            if not step_ok:
                await self.log("DEPLOYMENT HALTED DUE TO ERRORS.", "fail")
                return False

        await self.log("\n[SUCCESS] All selected steps deployed successfully!", "ok")
        return True

