import re

with open("frontend/src/components/Dashboard.jsx", "r") as f:
    c = f.read()

old_import = r"import \{ LogOut, Terminal as TerminalIcon, Play, ArrowLeft, CheckCircle2, Cpu, HardDrive, Clock, Activity, X, Server, Shield, Database, LayoutDashboard, Settings2, RefreshCcw, ExternalLink , Copy \} from 'lucide-react'"
new_import = "import { LogOut, Terminal as TerminalIcon, Play, ArrowLeft, CheckCircle2, Cpu, HardDrive, Clock, Activity, X, Server, Shield, Database, LayoutDashboard, Settings2, RefreshCcw, ExternalLink, Copy, Info } from 'lucide-react'"

c = re.sub(old_import, new_import, c)

with open("frontend/src/components/Dashboard.jsx", "w") as f:
    f.write(c)
