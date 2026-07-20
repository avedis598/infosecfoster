import tkinter as tk
from tkinter import ttk
from .components import C, FONT_BOLD, FONT_STEP, FONT_MONO, FlatBtn

class SetupTab(tk.Frame):
    def __init__(self, parent, all_steps, on_run):
        super().__init__(parent, bg=C["bg"])
        self.all_steps = all_steps
        self.on_run = on_run
        
        # Step tracking
        self.sel_vars = {}
        self.badge_lbls = {}
        self.sub_lbls = {}
        
        self._build_ui()

    def _build_ui(self):
        # Configure a 50/50 grid
        self.columnconfigure(0, weight=1, uniform="half")
        self.columnconfigure(1, weight=1, uniform="half")
        self.rowconfigure(0, weight=1)

        # 1. Left pane: Checklist
        left_pane = tk.Frame(self, bg=C["surface"])
        left_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Controls
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

        # Run Button (pack at bottom first so it stays visible)
        self.run_btn = FlatBtn(left_pane, text="Run Selected", bg=C["success"], command=self.on_run)
        self.run_btn.pack(side="bottom", fill="x", padx=15, pady=15)

        # Container for Scrollable checklist
        list_container = tk.Frame(left_pane, bg=C["surface"])
        list_container.pack(fill="both", expand=True, padx=15, pady=(15, 0))

        list_canvas = tk.Canvas(list_container, bg=C["surface"], highlightthickness=0)
        list_canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=list_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        list_canvas.configure(yscrollcommand=scrollbar.set)
        
        scroll_frame = tk.Frame(list_canvas, bg=C["surface"])
        list_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        
        def _on_configure(e):
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))
        scroll_frame.bind("<Configure>", _on_configure)

        self._build_checklist(scroll_frame)
        
        # 2. Right pane: Console
        right_pane = tk.Frame(self, bg=C["card"])
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)
        
        # Console Header
        tk.Label(right_pane, text="Console Output", bg=C["card"], fg=C["text"], 
                 font=FONT_BOLD).pack(anchor="w", padx=15, pady=(15,0))
                 
        self.log_text = tk.Text(right_pane, bg=C["card"], fg=C["text"], font=FONT_MONO,
                                selectbackground=C["accent"], relief="flat", wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Setup tags
        self.log_text.tag_config("head", foreground=C["accent"], font=("Courier New", 10, "bold"))
        self.log_text.tag_config("cmd", foreground=C["text"])
        self.log_text.tag_config("ok", foreground=C["success"])
        self.log_text.tag_config("fail", foreground=C["danger"])
        self.log_text.tag_config("warn", foreground=C["warn"])

        # Progress bar
        prog_frame = tk.Frame(right_pane, bg=C["card"])
        prog_frame.pack(fill="x", padx=15, pady=(0,15))
        
        self.progress_lbl = tk.Label(prog_frame, text="0%", bg=C["card"], fg=C["muted"], font=FONT_STEP)
        self.progress_lbl.pack(side="right")
        
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", thickness=10, background=C["accent"], troughcolor=C["border"], borderwidth=0)
        self.pbar = ttk.Progressbar(prog_frame, style="TProgressbar", length=100, mode="determinate")
        self.pbar.pack(side="left", fill="x", expand=True, padx=(0,15))

    def _build_checklist(self, parent):
        last_group = None
        for step in self.all_steps:
            sid = step["id"]
            group = sid.split(".")[0] if "." in sid else ""
            if group != last_group:
                tk.Label(parent, text=f"Sprint {group}", bg=C["surface"], fg=C["accent"], 
                         font=FONT_BOLD).pack(anchor="w", pady=(10,2))
                last_group = group
                
            item_f = tk.Frame(parent, bg=C["surface"])
            item_f.pack(fill="x", pady=2)
            
            var = tk.BooleanVar(value=True)
            self.sel_vars[sid] = var
            
            chk = tk.Checkbutton(item_f, text=step["title"], variable=var, bg=C["surface"], 
                                 fg=C["text"], selectcolor=C["border"], activebackground=C["surface"],
                                 activeforeground=C["text"], font=FONT_STEP)
            chk.pack(side="left")
            
            badge = tk.Label(item_f, text="", bg=C["surface"], fg=C["muted"], font=("Helvetica", 9))
            badge.pack(side="right", padx=10)
            self.badge_lbls[sid] = badge
            
            gates = step.get("gates", [])
            if gates:
                subs = []
                for g in gates:
                    sub_lbl = tk.Label(parent, text=f"○ {g['label']}", bg=C["surface"], 
                                       fg=C["muted"], font=FONT_SMALL)
                    sub_lbl.pack(anchor="w", padx=(25,0))
                    subs.append(sub_lbl)
                self.sub_lbls[sid] = subs

    def _select_all(self, value: bool):
        for var in self.sel_vars.values():
            var.set(value)

    def get_selected_ids(self):
        return [sid for sid, var in self.sel_vars.items() if var.get()]

    # Thread-safe UI update methods (to be called via queue drainer or directly from main thread)
    def set_badge(self, sid, text, color):
        if sid in self.badge_lbls:
            self.badge_lbls[sid].config(text=text, fg=color)

    def set_sub(self, sid, idx, state):
        icons = {"running": ("●", C["accent"]), "ok": ("✓", C["success"]), "fail": ("✘", C["danger"])}
        icon, color = icons.get(state, ("○", C["muted"]))
        if sid in self.sub_lbls and idx < len(self.sub_lbls[sid]):
            lbl = self.sub_lbls[sid][idx]
            old = lbl.cget("text")
            new_text = icon + old[1:] if old else icon
            lbl.config(text=new_text, fg=color)

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
        """Log multi-line output, colouring PASS/FAIL/warn lines."""
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
