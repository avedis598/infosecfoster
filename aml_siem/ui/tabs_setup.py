import tkinter as tk
from tkinter import ttk
import json
import os
import re
from .components import C, FONT_BOLD, FONT_STEP, FONT_MONO, FlatBtn, CollapsibleFrame

class SetupTab(tk.Frame):
    def __init__(self, parent, all_steps, on_run):
        super().__init__(parent, bg=C["bg"])
        self.all_steps = all_steps
        self.on_run = on_run
        
        # Load Titles
        title_file = os.path.join(os.path.dirname(__file__), "roadmap_titles.json")
        try:
            with open(title_file, 'r') as f:
                self.titles = json.load(f)
        except Exception as e:
            self.titles = {"sprints": {}, "steps": {}}
            
        # Step tracking
        self.sel_vars = {}
        self.badge_lbls = {}
        self.sub_lbls = {}
        
        # For auto-scroll
        self.step_frames = {} 
        self.list_canvas = None
        
        self.force_var = tk.BooleanVar(value=False)
        
        self._build_ui()

    def _get_m_key(self, step):
        title = step.get("title", "")
        sid = str(step.get("id", ""))
        
        m = re.search(r'(M\d\.\d)', title)
        if m: return m.group(1)
        m2 = re.search(r'M(\d)(\d)', sid)
        if m2: return f"M{m2.group(1)}.{m2.group(2)}"
        if sid.startswith("0.S") or sid == "0.GATE": return "M0.1"
        if sid.startswith("0.D") or "M0.2" in title: return "M0.2"
        if sid.startswith("0.K") or "M0.3" in title: return "M0.3"
        if sid.startswith("0.N") or "M0.4" in title: return "M0.4"
        if sid.startswith("0.G") or "M0.5" in title: return "M0.5"
        return "Unknown"

    def _build_ui(self):
        self.columnconfigure(0, weight=1, uniform="half")
        self.columnconfigure(1, weight=1, uniform="half")
        self.rowconfigure(0, weight=1)

        # 1. Left pane: Checklist
        left_pane = tk.Frame(self, bg=C["surface"])
        left_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctrl_frame = tk.Frame(left_pane, bg=C["surface"])
        ctrl_frame.pack(fill="x", padx=15, pady=(15,0))
        tk.Label(ctrl_frame, text="Execution Modules", bg=C["surface"], fg=C["text"], 
                 font=FONT_BOLD).pack(side="left")
        
        btn_frame = tk.Frame(ctrl_frame, bg=C["surface"])
        btn_frame.pack(side="right")
        FlatBtn(btn_frame, text="All", bg=C["border"], padx=8, pady=2,
                command=lambda: self._select_all(True)).pack(side="left", padx=2)
        FlatBtn(btn_frame, text="None", bg=C["border"], padx=8, pady=2,
                command=lambda: self._select_all(False)).pack(side="left", padx=2)

        # Bottom Bar: Force Checkbox + Run Button
        bot_frame = tk.Frame(left_pane, bg=C["surface"])
        bot_frame.pack(side="bottom", fill="x", padx=15, pady=15)
        
        chk_force = tk.Checkbutton(bot_frame, text="Force Execute (Skip Pre-checks)", variable=self.force_var, bg=C["surface"], 
                                 fg=C["text"], selectcolor=C["wazuh"], activebackground=C["surface"],
                                 activeforeground=C["text"], font=FONT_STEP)
        chk_force.pack(side="top", anchor="w", pady=(0, 10))
        
        self.run_full_btn = FlatBtn(bot_frame, text="Run Full Deployment (M0-M5)", bg=C["accent"], command=self._on_run_full_click)
        self.run_full_btn.pack(side="top", fill="x", pady=(0, 5))
        
        self.run_btn = FlatBtn(bot_frame, text="Run Selected", bg=C["success"], command=self._on_run_click)
        self.run_btn.pack(side="bottom", fill="x")

        # Container for Scrollable checklist

        list_container = tk.Frame(left_pane, bg=C["surface"])
        list_container.pack(fill="both", expand=True, padx=15, pady=(15, 0))

        self.list_canvas = tk.Canvas(list_container, bg=C["surface"], highlightthickness=0)
        self.list_canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.list_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        
        scroll_frame = tk.Frame(self.list_canvas, bg=C["surface"])
        self.list_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        def _on_configure(e):
            self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))
        scroll_frame.bind("<Configure>", _on_configure)

        self._build_checklist(scroll_frame)
        
        # 2. Right pane: Console
        right_pane = tk.Frame(self, bg=C["card"])
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)
        
        tk.Label(right_pane, text="Console Output", bg=C["card"], fg=C["text"], 
                 font=FONT_BOLD).pack(anchor="w", padx=15, pady=(15,0))
                 
        self.log_text = tk.Text(right_pane, bg=C["card"], fg=C["text"], font=FONT_MONO,
                                selectbackground=C["accent"], relief="flat", wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.log_text.tag_config("head", foreground=C["accent"], font=("Courier New", 10, "bold"))
        self.log_text.tag_config("cmd", foreground=C["text"])
        self.log_text.tag_config("ok", foreground=C["success"])
        self.log_text.tag_config("fail", foreground=C["danger"])
        self.log_text.tag_config("warn", foreground=C["warn"])

        prog_frame = tk.Frame(right_pane, bg=C["card"])
        prog_frame.pack(fill="x", padx=15, pady=(0,15))
        
        self.progress_lbl = tk.Label(prog_frame, text="0%", bg=C["card"], fg=C["muted"], font=FONT_STEP)
        self.progress_lbl.pack(side="right")
        
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", thickness=10, background=C["accent"], troughcolor=C["border"], borderwidth=0)
        self.pbar = ttk.Progressbar(prog_frame, style="TProgressbar", length=100, mode="determinate")
        self.pbar.pack(side="left", fill="x", expand=True, padx=(0,15))

    def _on_run_click(self):
        self.on_run(force=self.force_var.get())

    def _on_run_full_click(self):
        self._select_all(True)
        self.force_var.set(False)
        self.on_run(force=False)

    def _toggle_group(self, var, sids, child_vars=None):
        val = var.get()
        for sid in sids:
            if sid in self.sel_vars:
                self.sel_vars[sid].set(val)
        if child_vars:
            for cv in child_vars:
                cv.set(val)

    def _build_checklist(self, parent):
        grouped = {}
        for step in self.all_steps:
            sid = str(step["id"])
            sprint_idx = sid.split(".")[0]
            m_key = self._get_m_key(step)
            
            if sprint_idx not in grouped:
                grouped[sprint_idx] = {}
            if m_key not in grouped[sprint_idx]:
                grouped[sprint_idx][m_key] = []
                
            grouped[sprint_idx][m_key].append(step)
            
        for sprint_idx, steps_in_sprint in grouped.items():
            sprint_title = self.titles["sprints"].get(sprint_idx, f"Sprint {sprint_idx}")
            sprint_var = tk.BooleanVar(value=True)
            sprint_sids = []
            sprint_m_vars = []
            
            sprint_frame = CollapsibleFrame(
                parent, sprint_title, collapsed=(sprint_idx != "0"),
                show_chk=True, chk_var=sprint_var,
                chk_command=lambda v=sprint_var, sids=sprint_sids, cvs=sprint_m_vars: self._toggle_group(v, sids, cvs)
            )
            sprint_frame.pack(fill="x", pady=(10,2))
            
            for m_key, items in steps_in_sprint.items():
                m_title = self.titles["steps"].get(m_key, m_key)
                # Expand M0.1 and M0.2 by default, collapse others
                collapsed_m = not (sprint_idx == "0" and m_key in ["M0.1", "M0.2"])
                
                m_var = tk.BooleanVar(value=True)
                sprint_m_vars.append(m_var)
                m_sids = []
                
                m_frame = CollapsibleFrame(
                    sprint_frame.sub_frame, m_title, font=FONT_STEP, fg=C["text"], collapsed=collapsed_m,
                    show_chk=True, chk_var=m_var,
                    chk_command=lambda v=m_var, sids=m_sids: self._toggle_group(v, sids)
                )
                m_frame.pack(fill="x", pady=2, padx=(15, 0))
                
                for step in items:
                    sid = step["id"]
                    sprint_sids.append(sid)
                    m_sids.append(sid)
                    
                    item_f = tk.Frame(m_frame.sub_frame, bg=C["surface"])
                    item_f.pack(fill="x", pady=2, padx=(20, 0))
                    
                    self.step_frames[sid] = item_f
                    
                    var = tk.BooleanVar(value=True)
                    self.sel_vars[sid] = var
                    
                    chk = tk.Checkbutton(item_f, text=step["title"], variable=var, bg=C["surface"], 
                                         fg=C["text"], selectcolor=C["wazuh"], activebackground=C["surface"],
                                         activeforeground=C["text"], font=("Segoe UI", 9))
                    chk.pack(side="left")
                    
                    badge = tk.Label(item_f, text="", bg=C["surface"], fg=C["muted"], font=("Helvetica", 9))
                    badge.pack(side="right", padx=10)
                    self.badge_lbls[sid] = badge
                    
                    gates = step.get("cmds", [])
                    if gates:
                        subs = []
                        for g in gates:
                            sub_lbl = tk.Label(m_frame.sub_frame, text=f"○ {g['label']}", bg=C["surface"], 
                                               fg=C["muted"], font=("Segoe UI", 8))
                            sub_lbl.pack(anchor="w", padx=(45,0))
                            subs.append(sub_lbl)
                        self.sub_lbls[sid] = subs

    def _select_all(self, value: bool):
        for var in self.sel_vars.values():
            var.set(value)

    def get_selected_ids(self):
        return [sid for sid, var in self.sel_vars.items() if var.get()]

    def _scroll_to_step(self, sid):
        if not self.list_canvas or sid not in self.step_frames:
            return
        widget = self.step_frames[sid]
        
        # Calculate Y offset of widget relative to canvas window
        canvas_y = self.list_canvas.winfo_rooty()
        widget_y = widget.winfo_rooty()
        
        if widget_y == 0 or canvas_y == 0:
            return
            
        relative_y = widget_y - canvas_y
        
        # Current scroll fraction
        yview = self.list_canvas.yview()
        
        # Convert relative pixels to scroll fraction
        _, _, _, canvas_scroll_h = self.list_canvas.bbox("all") or (0,0,0,1)
        if canvas_scroll_h <= 0: canvas_scroll_h = 1
        
        frac_change = relative_y / float(canvas_scroll_h)
        new_top = max(0.0, min(1.0, yview[0] + frac_change - 0.2)) # 20% margin
        
        self.list_canvas.yview_moveto(new_top)

    def set_badge(self, sid, text, color):
        if sid in self.badge_lbls:
            self.badge_lbls[sid].config(text=text, fg=color)
            if "Running" in text or "Checking" in text:
                self._scroll_to_step(sid)

    def set_sub(self, sid, idx, state):
        icons = {"running": ("●", C["accent"]), "ok": ("✓", C["success"]), "fail": ("✘", C["danger"])}
        icon, color = icons.get(state, ("○", C["muted"]))
        if sid in self.sub_lbls and idx < len(self.sub_lbls[sid]):
            lbl = self.sub_lbls[sid][idx]
            old = lbl.cget("text")
            new_text = icon + old[1:] if old else icon
            lbl.config(text=new_text, fg=color)
            if state == "running":
                self._scroll_to_step(sid)

    def set_progress(self, done, total, label=""):
        pct = int(100 * done / total) if total else 0
        self.pbar["value"] = pct
        self.progress_lbl.config(text=label or f"{pct}%")

    def append_log(self, msg, tag=""):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
    def append_log_output(self, text):
        if not text:
            return
        for line in text.splitlines():
            if "GATE_PASS" in line or "PASS" in line.upper():
                self.append_log("    " + line, "ok")
            elif "GATE_FAIL" in line or "FAIL" in line.upper() or "ERROR" in line.upper():
                self.append_log("    " + line, "fail")
            elif "WARNING" in line.upper() or "WARN" in line.upper():
                self.append_log("    " + line, "warn")
            else:
                self.append_log("    " + line, "cmd")
                
    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
