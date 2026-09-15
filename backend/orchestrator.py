import asyncio
import json
import urllib.request

class CloudOrchestrator:
    def __init__(self, ws, conn, client_id, domain="infosecfoster.com", alert_email="admin@infosecfoster.com", db=None):
        self.ws = ws
        self.conn = conn
        self.client_id = client_id
        self.domain = domain
        self.alert_email = alert_email
        self.db = db

    def _update_db_status(self, updates):
        if not self.db: return
        try:
            if not hasattr(self, '_client_doc_id'):
                doc_ref = self.db.collection('clients').where('client_id', '==', self.client_id).limit(1).get()
                if not doc_ref:
                    doc_ref = self.db.collection('clients').where('name', '==', self.client_id).limit(1).get()
                
                if doc_ref:
                    self._client_doc_id = doc_ref[0].id
                else:
                    # Try to see if client_id is actually the document ID
                    doc_test = self.db.collection('clients').document(self.client_id).get()
                    if doc_test.exists:
                        self._client_doc_id = doc_test.id
                    else:
                        print(f"Warning: Could not find Firestore client document for {self.client_id}")
                        return
            
            update_dict = {}
            for step_id, status in updates.items():
                update_dict[f'step_status.{step_id}'] = status
                
            if update_dict:
                self.db.collection('clients').document(self._client_doc_id).update(update_dict)
        except Exception as e:
            pass

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
        
        cmd_str = cmd_str.replace("admin@infosecfoster.com", self.alert_email)
        cmd_str = cmd_str.replace("infosecfoster.com", self.domain)
        cmd_str = cmd_str.replace("aml-lab", self.client_id)
        
        if getattr(self, "debug_mode", False):
            cmd_str = cmd_str.replace("2>/dev/null", "").replace(">/dev/null 2>&1", "").replace(">/dev/null", "")
            await self.ws.send_text(f"\x1b[36m[DEBUG CMD] {cmd_str}\x1b[0m\r\n")
            
        try:
            result = await self.conn.run(cmd_str, check=False)
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return result.exit_status == 0, output.strip()
        except Exception as e:
            return False, str(e)

    async def run_steps(self, step_ids, is_force=False, debug=False):
        self.debug_mode = debug
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
                    self._update_db_status({step["id"]: "success"})
                    continue

            await self.log(f"\n{'─'*50}\n[{step_mode.upper()}] {title}", "head")
            
            updates = {step["id"]: "running"}
            current_global_idx = next((i for i, s in enumerate(all_steps) if s["id"] == step["id"]), -1)
            if current_global_idx != -1:
                for subsequent_step in all_steps[current_global_idx + 1:]:
                    updates[subsequent_step["id"]] = "need_rerun"
                    
            self._update_db_status(updates)
            step_ok = True
            for i, cmd_dict in enumerate(step.get("cmds", [])):
                label = cmd_dict.get("label", f"Step {i+1}")
                await self.log(f"  → {label}", "cmd")
                
                sub_mode = cmd_dict.get("mode", step_mode)
                
                try:
                    if sub_mode == "local" or sub_mode.startswith("local_"):
                        # Cloud optimizations for local tasks
                        if sub_mode == "local_dns":
                            record_name = cmd_dict.get("record_name", "test")
                            try:
                                import json, os
                                import urllib.request
                                from google.cloud import secretmanager
                                secret_id = f"cf-token-{self.client_id.lower().replace(' ', '-')}"
                                parent = f"projects/{os.environ.get('PROJECT_ID', 'infosecfoster-5bb83')}"
                                sm_client = secretmanager.SecretManagerServiceClient()
                                resp = sm_client.access_secret_version(request={"name": f"{parent}/secrets/{secret_id}/versions/latest"})
                                cf_token = resp.payload.data.decode('utf-8').strip()
                                
                                req = urllib.request.Request(
                                    'https://api.cloudflare.com/client/v4/zones?name=infosecfoster.com',
                                    headers={'Authorization': f'Bearer {cf_token}', 'Content-Type': 'application/json'}
                                )
                                with urllib.request.urlopen(req) as response:
                                    zone_data = json.loads(response.read().decode('utf-8'))
                                    
                                if not zone_data.get('success') or not zone_data.get('result'):
                                    ok, output = False, f"[FAIL] Failed to fetch Cloudflare Zone ID for infosecfoster.com. API Response: {zone_data}"
                                else:
                                    zone_id = zone_data['result'][0]['id']
                                    payload = json.dumps({"type":"A","name":record_name,"content":self.conn.get_extra_info('peername')[0],"ttl":1,"proxied":False}).encode('utf-8')
                                    req2 = urllib.request.Request(
                                        f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
                                        data=payload,
                                        headers={'Authorization': f'Bearer {cf_token}', 'Content-Type': 'application/json'}
                                    )
                                    try:
                                        with urllib.request.urlopen(req2) as response2:
                                            dns_data = json.loads(response2.read().decode('utf-8'))
                                            if dns_data.get('success'):
                                                ok, output = True, f"[SUCCESS] DNS A Record '{record_name}.infosecfoster.com' -> {self.conn.get_extra_info('peername')[0]} active in Cloudflare"
                                            else:
                                                ok, output = False, f"[FAIL] Cloudflare API Error: {dns_data.get('errors')}"
                                    except urllib.error.HTTPError as e:
                                        err_res = json.loads(e.read().decode('utf-8'))
                                        if err_res.get('errors') and 'already exists' in str(err_res.get('errors')):
                                            ok, output = True, f"[SUCCESS] DNS A Record '{record_name}.infosecfoster.com' -> {self.conn.get_extra_info('peername')[0]} active in Cloudflare (Already Existed)"
                                        else:
                                            ok, output = False, f"[FAIL] HTTP {e.code}: {err_res}"
                            except Exception as e:
                                ok, output = False, f"[FAIL] Cloudflare API error. Did you upload the CF token to Secret Manager? Error: {e}"
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
                            remote_cmd = f"cat << 'INNER_EOF' > /tmp/run.sh\n{script}\nINNER_EOF\nbash /tmp/run.sh && rm -f /tmp/run.sh"
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
                    
            if step_ok:
                self._update_db_status({step["id"]: "success"})
            else:
                self._update_db_status({step["id"]: "failed"})
                await self.log("DEPLOYMENT HALTED DUE TO ERRORS.", "fail")
                return False

        await self.log("\n[SUCCESS] All selected steps deployed successfully!", "ok")
        return True

