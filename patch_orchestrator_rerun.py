with open("backend/orchestrator.py", "r") as f:
    c = f.read()

old_loop = """            await self.log(f"\\n{'─'*50}\\n[{step_mode.upper()}] {title}", "head")
            self._update_db_status(step["id"], "running")
            step_ok = True"""

new_loop = """            await self.log(f"\\n{'─'*50}\\n[{step_mode.upper()}] {title}", "head")
            self._update_db_status(step["id"], "running")
            
            # Immediately mark ALL subsequent steps in the entire platform as need_rerun
            # because their state may be invalidated by this step running.
            current_global_idx = next((i for i, s in enumerate(all_steps) if s["id"] == step["id"]), -1)
            if current_global_idx != -1:
                for subsequent_step in all_steps[current_global_idx + 1:]:
                    self._update_db_status(subsequent_step["id"], "need_rerun")
                    
            step_ok = True"""

c = c.replace(old_loop, new_loop)

old_post = """            if step_ok:
                self._update_db_status(step["id"], "success")
            else:
                self._update_db_status(step["id"], "failed")
                
                # Mark all subsequent target steps as need_rerun
                current_idx = target_steps.index(step)
                for remaining in target_steps[current_idx + 1:]:
                    self._update_db_status(remaining["id"], "need_rerun")

                await self.log("DEPLOYMENT HALTED DUE TO ERRORS.", "fail")
                return False"""

new_post = """            if step_ok:
                self._update_db_status(step["id"], "success")
            else:
                self._update_db_status(step["id"], "failed")
                await self.log("DEPLOYMENT HALTED DUE TO ERRORS.", "fail")
                return False"""

c = c.replace(old_post, new_post)

with open("backend/orchestrator.py", "w") as f:
    f.write(c)

print("orchestrator patched")
