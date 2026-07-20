import sys
import os

# Ensure the package can be imported if run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aml_siem.ui.app import AMLSiemApp
from aml_siem.steps import ALL_STEPS

def main():
    app = AMLSiemApp(steps_def=ALL_STEPS)
    app.mainloop()

if __name__ == "__main__":
    main()
