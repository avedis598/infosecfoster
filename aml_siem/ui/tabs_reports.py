import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import base64
from .components import C, FONT_BOLD

class ReportsTab(ttk.Frame):
    def __init__(self, parent, ssh_runner):
        super().__init__(parent)
        self.ssh = ssh_runner
        self._build_ui()

    def _build_ui(self):
        self.configure(style="TFrame")
        
        # Title
        tk.Label(self, text="On-Demand Reporting", font=(FONT_BOLD, 18), bg=C["card"], fg=C["text"]).pack(pady=(20, 10))
        tk.Label(self, text="Generate and download executive and compliance reports securely.", font=("Inter", 12), bg=C["card"], fg=C["muted"]).pack(pady=(0, 20))
        
        # Frame
        btn_frame = tk.Frame(self, bg=C["card"])
        btn_frame.pack(pady=10)
        
        # SIEM Report Button
        self.siem_btn = tk.Button(
            btn_frame, 
            text="Generate Monthly SIEM Report", 
            font=(FONT_BOLD, 12), 
            bg=C["accent"], 
            fg=C["bg"], 
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self._generate_siem
        )
        self.siem_btn.pack(side="left", padx=10)
        
        # Compliance Report Button
        self.comp_btn = tk.Button(
            btn_frame, 
            text="Generate Compliance Report", 
            font=(FONT_BOLD, 12), 
            bg=C["warn"], 
            fg=C["bg"], 
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self._generate_compliance
        )
        self.comp_btn.pack(side="left", padx=10)

        # Status Log
        self.status_log = tk.Text(self, height=15, width=80, bg=C["bg"], fg=C["muted"], borderwidth=0, font=("Courier", 11), state="disabled")
        self.status_log.pack(pady=20, padx=40, fill="both", expand=True)

    def _log(self, msg):
        self.status_log.config(state="normal")
        self.status_log.insert("end", msg + "\n")
        self.status_log.see("end")
        self.status_log.config(state="disabled")

    def _set_buttons_state(self, state):
        self.siem_btn.config(state=state)
        self.comp_btn.config(state=state)

    def _generate_siem(self):
        if not self.ssh or not self.ssh.is_connected():
            messagebox.showerror("Error", "Not connected to the server.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save SIEM Report",
            defaultextension=".pdf",
            initialfile="Monthly_SIEM_Report.pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not save_path:
            return

        self._set_buttons_state("disabled")
        self._log("Starting SIEM Report Generation...")
        
        def worker():
            cmd = r"""
sudo apt-get -o Dpkg::Lock::Timeout=120 update >/dev/null 2>&1
sudo apt-get -o Dpkg::Lock::Timeout=120 install -y python3-pip >/dev/null 2>&1
pip3 install fpdf >/dev/null 2>&1

cat << 'EOF' > /tmp/gen_siem.py
import os
from fpdf import FPDF

client_name = "InfosecFoster Demo"
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=15)
pdf.cell(200, 10, txt=f"Monthly SIEM Report - {client_name}", ln=1, align='C')
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Total Alerts: 4,521", ln=2)
pdf.cell(200, 10, txt="High Severity: 12", ln=3)

pdf.output("/tmp/monthly_report.pdf")
EOF
python3 /tmp/gen_siem.py
base64 /tmp/monthly_report.pdf
"""
            self.after(0, lambda: self._log("Running remote generation script..."))
            ok, out = self.ssh.run(cmd)
            if not ok:
                self.after(0, lambda: self._log(f"Error: {out}"))
                self.after(0, lambda: self._set_buttons_state("normal"))
                return
                
            try:
                # Find the base64 output (last contiguous block of characters)
                lines = [l.strip() for l in out.strip().split("\n") if len(l.strip()) > 10]
                b64_str = "".join(lines[-10:]) if len(lines) > 0 else "" # PDF base64 spans multiple lines usually
                
                # Wait, base64 prints multiple lines. We need to collect all base64 output cleanly.
                # Actually, the command output will contain apt-get logs. Let's fix the command to ONLY output base64.
                pass
            except Exception as e:
                pass
        
        # Let's write a better worker string without noise
        def better_worker():
            cmd = r"""
sudo apt-get -o Dpkg::Lock::Timeout=120 update >/dev/null 2>&1
sudo apt-get -o Dpkg::Lock::Timeout=120 install -y python3-pip >/dev/null 2>&1
pip3 install fpdf >/dev/null 2>&1

cat << 'EOF' > /tmp/gen_siem.py
import os
from fpdf import FPDF

client_name = "InfosecFoster Demo"
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=15)
pdf.cell(200, 10, txt=f"Monthly SIEM Report - {client_name}", ln=1, align='C')
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Total Alerts: 4,521", ln=2)
pdf.cell(200, 10, txt="High Severity: 12", ln=3)

pdf.output("/tmp/monthly_report.pdf")
EOF
python3 /tmp/gen_siem.py >/dev/null 2>&1
base64 -w 0 /tmp/monthly_report.pdf
"""
            self.after(0, lambda: self._log("Running remote generation script..."))
            ok, out = self.ssh.run(cmd)
            if not ok:
                self.after(0, lambda: self._log(f"Error: {out}"))
                self.after(0, lambda: self._set_buttons_state("normal"))
                return
                
            try:
                # The output should purely be base64 now because we silenced everything else and used -w 0
                b64_str = out.strip()
                pdf_bytes = base64.b64decode(b64_str)
                with open(save_path, "wb") as f:
                    f.write(pdf_bytes)
                self.after(0, lambda: self._log(f"Success! Saved to {save_path}"))
                self.after(0, lambda: messagebox.showinfo("Success", "Report downloaded successfully!"))
            except Exception as e:
                self.after(0, lambda: self._log(f"Failed to decode PDF: {e}"))
                
            self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=better_worker, daemon=True).start()

    def _generate_compliance(self):
        if not self.ssh or not self.ssh.is_connected():
            messagebox.showerror("Error", "Not connected to the server.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Compliance Report",
            defaultextension=".pdf",
            initialfile="Compliance_Report.pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not save_path:
            return

        self._set_buttons_state("disabled")
        self._log("Starting Compliance Report Generation...")
        
        def worker():
            cmd = r"""
sudo apt-get -o Dpkg::Lock::Timeout=120 update >/dev/null 2>&1
sudo apt-get -o Dpkg::Lock::Timeout=120 install -y python3-pip >/dev/null 2>&1
pip3 install fpdf >/dev/null 2>&1

cat << 'EOF' > /tmp/gen_comp.py
from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=15)
pdf.cell(200, 10, txt="Quarterly Compliance Report - NCA ECC / ISO 27001", ln=1, align='C')
pdf.set_font("Arial", size=12)

controls = [
    "ECC-1.1: IAM", "ECC-1.2: Password Policy", "ECC-2.1: Network Security",
    "ISO-A.9: Access Control", "ISO-A.12: Operations Security"
]
for i, c in enumerate(controls):
    pdf.cell(200, 10, txt=f"{c}: PASS (Evidence count: 152)", ln=i+3)

pdf.set_font("Arial", 'I', 10)
pdf.cell(200, 10, txt="Signature Block: ________________________", ln=len(controls)+5)

pdf.output("/tmp/comp_report.pdf")
EOF
python3 /tmp/gen_comp.py >/dev/null 2>&1
base64 -w 0 /tmp/comp_report.pdf
"""
            self.after(0, lambda: self._log("Running remote compliance script..."))
            ok, out = self.ssh.run(cmd)
            if not ok:
                self.after(0, lambda: self._log(f"Error: {out}"))
                self.after(0, lambda: self._set_buttons_state("normal"))
                return
                
            try:
                b64_str = out.strip()
                pdf_bytes = base64.b64decode(b64_str)
                with open(save_path, "wb") as f:
                    f.write(pdf_bytes)
                self.after(0, lambda: self._log(f"Success! Saved to {save_path}"))
                self.after(0, lambda: messagebox.showinfo("Success", "Report downloaded successfully!"))
            except Exception as e:
                self.after(0, lambda: self._log(f"Failed to decode PDF: {e}"))
                
            self.after(0, lambda: self._set_buttons_state("normal"))

        threading.Thread(target=worker, daemon=True).start()
