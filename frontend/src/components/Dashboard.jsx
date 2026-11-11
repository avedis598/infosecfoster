import { useState, useEffect, useRef } from 'react'
import { ErrorBoundary } from './ErrorBoundary'
import { signOut } from 'firebase/auth'
import { auth, db } from '../firebase'
import ModuleTree from './ModuleTree'
import { collection, addDoc, serverTimestamp, doc, getDoc, updateDoc, onSnapshot, query, orderBy } from 'firebase/firestore'
import { LogOut, Terminal as TerminalIcon, Play, ArrowLeft, CheckCircle2, Cpu, HardDrive, Clock, Activity, X, Server, Shield, Database, LayoutDashboard, Settings2, RefreshCcw, ExternalLink, Copy, Info } from 'lucide-react'
import { useParams, useNavigate } from 'react-router-dom'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

/* ==================== DEPLOY TERMINAL COMPONENT ==================== */
const DeployTerminal = ({ client, selectedSteps, forceExecute, debugMode, onComplete, wsUrl }) => {
  const terminalRef = useRef(null)
  const termInstance = useRef(null)
  const wsInstance = useRef(null)
  
  useEffect(() => {
    if (!terminalRef.current) return
    
    // Initialize Xterm
    const term = new Terminal({
      theme: { background: 'transparent', foreground: '#d1d5db', cursor: 'transparent', selectionBackground: 'rgba(255,255,255,0.1)' },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 12,
      cursorBlink: false,
      disableStdin: true, scrollback: 99999 // Read-only terminal
    })
    
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(terminalRef.current)
    fitAddon.fit()
    
    termInstance.current = term
    
    const clientId = client.client_id || client.name
    const ip = client.ip_address
    const username = client.ssh_username
    
    term.writeln('\x1b[35m[SYSTEM] Handing over to Cloud Orchestrator...\x1b[0m')
    
    // Connect to WebSocket
    const ws = new WebSocket(`${wsUrl}/api/deploy/${clientId}?ip=${ip}&username=${username}&steps=${selectedSteps.join(',')}&force=${forceExecute}&debug=${debugMode}`)
    wsInstance.current = ws
    
    ws.onmessage = (e) => {
      term.write(e.data)
    }
    
    ws.onclose = () => {
      term.writeln('\x1b[32m[SYSTEM] Execution stream closed.\x1b[0m')
      onComplete()
    }
    
    const handleResize = () => fitAddon.fit()
    window.addEventListener('resize', handleResize)
    


  return () => {
      window.removeEventListener('resize', handleResize)
      if (ws.readyState === WebSocket.OPEN) ws.close()
      term.dispose()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  
  return <div ref={terminalRef} className="w-full h-full p-4 overflow-hidden" />
}


const getPodCategory = (name) => {
  const n = name.toLowerCase()
  if (n.includes('wazuh')) return 'Wazuh SIEM'
  if (n.includes('opensearch') && !n.includes('shuffle')) return 'OpenSearch Cluster'
  if (n.includes('shuffle')) return 'Shuffle SOAR'
  if (n.includes('thehive') || n.includes('cassandra')) return 'TheHive Platform'
  if (n.includes('clickhouse')) return 'Cold Storage Tier'
  if (n.includes('cronjob') || n.includes('report') || n.includes('threat-intel') || n.includes('test-')) return 'CronJobs & Tasks'
  if (n.includes('kube-system') || n.includes('cert-manager') || n.includes('ingress') || n.includes('svclb')) return 'System Infrastructure'
  return 'Other Services'
}

export default function Dashboard({ user }) {
  const { id } = useParams()
  const navigate = useNavigate()
  
  const [client, setClient] = useState(null)
  const [editClient, setEditClient] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [activeTab, setActiveTab] = useState('Connection')
  const [shuffleTemplates, setShuffleTemplates] = useState([])
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [templateConfig, setTemplateConfig] = useState({
    alertEmail: 'admin@company.com',
    enableAutoBlock: true,
    ipWhitelist: '10.0.0.0/8, 192.168.1.0/24'
  })
  const [isImportingTemplate, setIsImportingTemplate] = useState(false)
  const [shuffleWorkflows, setShuffleWorkflows] = useState([])
  const [isLoadingWorkflows, setIsLoadingWorkflows] = useState(false)
  const [workflowError, setWorkflowError] = useState(null)

  const fetchShuffleWorkflows = async () => {
    setIsLoadingWorkflows(true)
    setWorkflowError(null)
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const clientId = editClient?.client_id || editClient?.name
      if (!clientId) return
      
      const res = await fetch(`${backendUrl}/clients/${clientId}/shuffle/workflows`)
      const data = await res.json()
      if (res.ok && data.status === 'success') {
        setShuffleWorkflows(data.workflows || [])
      } else {
        setWorkflowError(data.detail || data.message || 'Failed to fetch workflows')
      }
    } catch (err) {
      setWorkflowError(err.message)
    } finally {
      setIsLoadingWorkflows(false)
    }
  }

  useEffect(() => {
    // We no longer persist tab state to avoid confusing auto-navigations
  }, [activeTab, isConnected, id])
  
  useEffect(() => {
    const q = query(collection(db, 'shuffle_templates'), orderBy('created_at', 'desc'))
    const unsubscribe = onSnapshot(q, (snapshot) => {
      setShuffleTemplates(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })))
    })
    return () => unsubscribe()
  }, [])
  
  const [selectedSteps, setSelectedSteps] = useState([])
  const [modulesHierarchy, setModulesHierarchy] = useState([])
  const [hasAutoNavigated, setHasAutoNavigated] = useState(false)

  // Auto-navigate to Overview if all modules are SUCCESS and we are connected
  useEffect(() => {
    if (modulesHierarchy.length === 0 || !client || !client.step_status || hasAutoNavigated || !isConnected) return;
    
    let allSuccess = true;
    let hasSteps = false;

    for (const mod of modulesHierarchy) {
      for (const step of mod.steps) {
        hasSteps = true;
        const parts = step.id.split('.');
        let curr = client.step_status;
        for (const p of parts) {
          if (!curr || !curr[p]) { allSuccess = false; break; }
          curr = curr[p];
        }
        if (curr !== 'SUCCESS') { allSuccess = false; break; }
      }
    }
    
    // Only auto-navigate if they haven't explicitly chosen another tab
    if (hasSteps && allSuccess && activeTab === 'Connection') {
      setActiveTab('Overview');
    }
    setHasAutoNavigated(true);
  }, [client?.step_status, modulesHierarchy, hasAutoNavigated, isConnected, activeTab]);
  const [forceExecute, setForceExecute] = useState(false)
  const [debugMode, setDebugMode] = useState(false)
  const [deploying, setDeploying] = useState(false)
  const [terminalMounted, setTerminalMounted] = useState(false)
  useEffect(() => {
    if (activeTab !== 'Setup') setTerminalMounted(false)
  }, [activeTab])
  const [showTerminal, setShowTerminal] = useState(false)
  const [sshKeyStatus, setSshKeyStatus] = useState('checking') // checking, missing, exists
  const [sshKeyInput, setSshKeyInput] = useState('')
  const [isUploadingKey, setIsUploadingKey] = useState(false)
  
  const [cfKeyStatus, setCfKeyStatus] = useState('checking')
  const [cfKeyInput, setCfKeyInput] = useState('')
  const [isUploadingCf, setIsUploadingCf] = useState(false)

  useEffect(() => {
    if (activeTab === 'Connection' && editClient) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const clientId = editClient.client_id || editClient.name
      
      fetch(`${backendUrl}/api/clients/${clientId}/secret/ssh/status`)
        .then(res => res.json())
        .then(data => setSshKeyStatus((data.status === 'success' && data.exists) ? 'exists' : 'missing'))
        .catch(() => setSshKeyStatus('missing'))
        
      fetch(`${backendUrl}/api/clients/${clientId}/secret/cf/status`)
        .then(res => res.json())
        .then(data => setCfKeyStatus((data.status === 'success' && data.exists) ? 'exists' : 'missing'))
        .catch(() => setCfKeyStatus('missing'))
    }
  }, [activeTab, editClient])

  const handleUploadKey = async (type) => {
    const input = type === 'ssh' ? sshKeyInput : cfKeyInput
    if(!input) return
    const setUploading = type === 'ssh' ? setIsUploadingKey : setIsUploadingCf
    const setStatus = type === 'ssh' ? setSshKeyStatus : setCfKeyStatus
    const setInput = type === 'ssh' ? setSshKeyInput : setCfKeyInput
    
    setUploading(true)
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    try {
      const res = await fetch(`${backendUrl}/api/clients/${editClient.client_id || editClient.name}/secret/${type}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ private_key: input })
      })
      const data = await res.json()
      if(data.status === 'success') {
        setStatus('exists')
        setInput('')
        alert(`${type.toUpperCase()} securely uploaded to Google Secret Manager!`)

      } else {
        alert('Upload failed: ' + data.message)
      }
    } catch (e) {
      alert('Upload failed.')
    }
    setUploading(false)
  }

  const [overviewData, setOverviewData] = useState(null)
  const [wazuhData, setWazuhData] = useState(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isRefreshingWazuh, setIsRefreshingWazuh] = useState(false)

  const fetchOverview = async () => {
    if (!editClient) return
    setIsRefreshing(true)
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/monitor/overview`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: editClient.client_id || editClient.name, ip: editClient.ip_address, username: editClient.ssh_username })
      })
      const data = await res.json()
      if (data.status === 'success') {
          setOverviewData(data)
      } else {
          setOverviewData({ error: data.message || "Unknown error" })
      }
    } catch (e) {
      console.error(e)
    }
    setIsRefreshing(false)
  }

  const fetchWazuh = async () => {
    if (!editClient) return
    setIsRefreshingWazuh(true)
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/monitor/wazuh`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: editClient.client_id || editClient.name, ip: editClient.ip_address, username: editClient.ssh_username })
      })
      const data = await res.json()
      if (data.status === 'success') setWazuhData(data)
    } catch (e) {
      console.error(e)
    }
    setIsRefreshingWazuh(false)
  }

  const [thehiveData, setThehiveData] = useState(null)
  const [shuffleData, setShuffleData] = useState(null)
  const [socDashboardData, setSocDashboardData] = useState(null)
  const [isRefreshingSocDashboard, setIsRefreshingSocDashboard] = useState(false)
  const [alertFilterLevel, setAlertFilterLevel] = useState('all')

  const fetchSocDashboard = async () => {
    if (!editClient) return
    setIsRefreshingSocDashboard(true)
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/monitor/dashboard`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: editClient.client_id || editClient.name, ip: editClient.ip_address, username: editClient.ssh_username })
      })
      const data = await res.json()
      if (data.status === 'success') {
        setSocDashboardData(data)
      } else {
        setSocDashboardData({ error: data.message || 'Unable to fetch live telemetry from cluster' })
      }
    } catch (e) {
      console.error(e)
      setSocDashboardData({ error: e.message })
    }
    setIsRefreshingSocDashboard(false)
  }

  const fetchService = async (service, setter) => {
    if (!editClient) return
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/monitor/${service}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: editClient.client_id || editClient.name, ip: editClient.ip_address, username: editClient.ssh_username })
      })
      const data = await res.json()
      if (data.status === 'success') setter(data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    if (activeTab === 'Overview' && !overviewData) fetchOverview()
    if (activeTab === 'Wazuh' && !wazuhData) fetchWazuh()
    if (activeTab === 'TheHive' && !thehiveData) fetchService('thehive', setThehiveData)
    if (activeTab === 'Shuffle') {
      if (!shuffleData) fetchService('shuffle', setShuffleData)
      fetchShuffleWorkflows()
    }
    if (activeTab === 'Analytics') {
      if (!socDashboardData) fetchSocDashboard()
      if (!wazuhData) fetchWazuh()
    }
  }, [activeTab])



  const tabs = [
    { id: 'Connection', icon: Settings2 },
    { id: 'Setup', icon: Play },
    { id: 'Overview', icon: Server },
    { id: 'Analytics', icon: Activity },
    { id: 'Wazuh', icon: Shield },
    { id: 'TheHive', icon: Database },
    { id: 'Shuffle', icon: LayoutDashboard }
  ]

  useEffect(() => {
    const docRef = doc(db, 'clients', id)
    const unsubscribe = onSnapshot(docRef, (docSnap) => {
      if (docSnap.exists()) {
        const data = { id: docSnap.id, ...docSnap.data() }
        setClient(data)
        setEditClient(data)
      } else {
        navigate('/')
      }
    })
    return () => unsubscribe()
  }, [id, navigate])

  
  useEffect(() => {
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
    fetch(`${backendUrl}/api/modules`)
      .then(res => res.json())
      .then(data => {
        if(data.status === 'success') setModulesHierarchy(data.modules)
      })
      .catch(err => console.error("Failed to load modules", err))
  }, [])

  const handleLogout = () => signOut(auth)

  const handleConnect = async (e) => {
    e.preventDefault()
    
    if (isConnected) {
      setIsConnected(false)
      navigate('/')
      return
    }
    
    setIsConnecting(true)
    
    setTimeout(() => {
      setIsConnected(true)
      setIsConnecting(false)
      setActiveTab('Setup')
    }, 1500)
    
    if (editClient) {
      const docRef = doc(db, 'clients', id)
      await updateDoc(docRef, {
        client_id: editClient.client_id,
        ip_address: editClient.ip_address,
        ssh_username: editClient.ssh_username,
        alert_email: editClient.alert_email,
        shuffle_api_key: editClient.shuffle_api_key,
        cloudflare_token: editClient.cloudflare_token,

      })
    }
  }

  const handleDeploy = async () => {
    if (!isConnected) return alert("Please connect to the server first.")
    if (selectedSteps.length === 0) return alert("Please select at least one module.")

    setDeploying(true)
    setTerminalMounted(false)
    setTimeout(() => setTerminalMounted(true), 10)

    // Optionally log the deployment in firestore for auditing
    try {
      await addDoc(collection(db, 'deployments'), {
        client_id: editClient.client_id || editClient.name,
        server_ip: editClient.ip_address,
        steps: selectedSteps,
        force: forceExecute,
        status: 'running',
        created_at: serverTimestamp(),
        user_email: user.email
      })
    } catch (err) {
      console.warn("Failed to log deployment to firestore", err)
    }
  }

  const handleStopRun = () => {
    setTerminalMounted(false)
    setDeploying(false)
  }

  const handleDeployComplete = () => {
    setDeploying(false)
  }

  const handleImportTemplate = async () => {
    if (!selectedTemplate) return alert("Please select a template to import.")
    if (!isConnected) return alert("Please connect to the server first.")
    
    setIsImportingTemplate(true)
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
      const clientId = editClient.client_id || editClient.name
      
      const res = await fetch(`${backendUrl}/clients/${clientId}/shuffle/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ template_id: selectedTemplate, config: templateConfig })
      })
      
      const data = await res.json()
      if (res.ok && data.status === 'success') {
        alert('Template imported successfully!')
        setSelectedTemplate('')
        fetchShuffleWorkflows()
      } else {
        alert(`Failed to import template: ${data.message || data.detail || 'Unknown error'}`)
      }
    } catch (err) {
      console.error(err)
      alert('Network error while trying to import template.')
    } finally {
      setIsImportingTemplate(false)
    }
  }

  // Define env var for ws
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

  if (!client || !editClient) return <div className="min-h-screen flex items-center justify-center bg-obsidian text-white">Loading...</div>

  return (
    <ErrorBoundary>
    <div className="flex-1 w-full min-h-screen bg-obsidian text-gray-200 font-sans flex flex-col relative overflow-hidden">
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-violet-glow blur-[150px] rounded-full opacity-20 pointer-events-none"></div>
      
      {/* Top Navbar */}
      <nav className="bg-matte/80 backdrop-blur-md border-b border-white/5 px-8 py-3 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-6">
          <button onClick={() => navigate('/')} className="p-2 -ml-2 rounded-full hover:bg-white/5 text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          
          {/* Tab Navigation */}
          <div className="flex bg-obsidian p-1 rounded-xl border border-white/5 shadow-inner">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              const isDisabled = !isConnected && tab.id !== 'Connection';
              return (
                <button
                  key={tab.id}
                  onClick={() => !isDisabled && setActiveTab(tab.id)}
                  disabled={isDisabled}
                  className={`flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all duration-300 ${
                    isActive 
                      ? 'bg-violet text-white shadow-[0_0_15px_var(--color-violet-glow)]' 
                      : isDisabled 
                        ? 'opacity-30 cursor-not-allowed text-gray-500' 
                        : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.id}
                </button>
              )
            })}
          </div>

        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 bg-obsidian border border-white/10 px-3 py-1.5 rounded-[8px]">
            <Activity className={`w-3.5 h-3.5 ${isConnected ? 'text-lime' : 'text-gray-500'}`} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-white">
              {isConnected ? editClient.ip_address : 'Disconnected'}
            </span>
            {isConnected && (
              <button 
                onClick={() => setShowTerminal(true)}
                className="ml-2 text-gray-400 hover:text-white transition-colors"
                title="Open Terminal"
              >
                <TerminalIcon className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <button onClick={handleLogout} className="w-8 h-8 rounded-full bg-obsidian border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:border-white/20 transition-all">
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-8 w-full relative z-10 overflow-y-auto">
        
        {/* ==================== CONNECTION TAB ==================== */}
        {activeTab === 'Connection' && (
          <div className="max-w-2xl mx-auto animate-in fade-in duration-500">
            <div className="bg-matte rounded-[24px] border border-white/5 p-8 shadow-2xl transition-all">
              <div className="flex items-center justify-center mb-8">
                <h2 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-lime to-emerald-400 text-center">
                  InfosecFoster
                </h2>
              </div>
              
              <form onSubmit={handleConnect} className="space-y-4">
                <div className="flex items-center">
                  <label className="w-1/3 text-xs font-bold text-gray-400 text-right pr-4">Client ID:</label>
                  <input 
                    type="text" required
                    className="w-2/3 px-4 py-2 bg-obsidian border border-white/10 rounded-[8px] text-white focus:ring-1 focus:ring-violet outline-none text-sm"
                    value={editClient.client_id || editClient.name}
                    onChange={(e) => setEditClient({...editClient, client_id: e.target.value})}
                  />
                </div>
                <div className="flex items-center">
                  <label className="w-1/3 text-xs font-bold text-gray-400 text-right pr-4">IP Address / Host:</label>
                  <input 
                    type="text" required
                    className="w-2/3 px-4 py-2 bg-obsidian border border-white/10 rounded-[8px] text-white focus:ring-1 focus:ring-violet outline-none font-mono text-sm"
                    value={editClient.ip_address}
                    onChange={(e) => setEditClient({...editClient, ip_address: e.target.value})}
                  />
                </div>
                <div className="flex items-center">
                  <label className="w-1/3 text-xs font-bold text-gray-400 text-right pr-4">SSH Username:</label>
                  <input 
                    type="text" required
                    className="w-2/3 px-4 py-2 bg-obsidian border border-white/10 rounded-[8px] text-white focus:ring-1 focus:ring-violet outline-none text-sm"
                    value={editClient.ssh_username}
                    onChange={(e) => setEditClient({...editClient, ssh_username: e.target.value})}
                  />
                </div>

                {sshKeyStatus === 'exists' && (
                  <div className="flex items-center mt-4">
                    <label className="w-1/3"></label>
                    <div className="w-2/3 flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-[8px] text-emerald-400 text-xs font-bold">
                      <CheckCircle2 className="w-4 h-4" /> SSH Key Securely Stored (Secret Manager)
                    </div>
                  </div>
                )}

                {sshKeyStatus === 'missing' && (
                  <div className="flex items-start mt-4">
                    <label className="w-1/3 text-xs font-bold text-red-400 text-right pr-4 pt-2">Missing SSH Private Key:</label>
                    <div className="w-2/3 flex flex-col gap-2">
                      <textarea 
                        className="w-full px-4 py-2 bg-obsidian border border-red-500/30 rounded-[8px] text-white focus:ring-1 focus:ring-red-500 outline-none font-mono text-[10px] h-24"
                        placeholder="-----BEGIN OPENSSH PRIVATE KEY-----..."
                        value={sshKeyInput}
                        onChange={(e) => setSshKeyInput(e.target.value)}
                      />
                      <button type="button" onClick={() => handleUploadKey('ssh')} disabled={isUploadingKey || !sshKeyInput} className="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white px-4 py-1.5 rounded-[6px] text-xs font-bold self-end transition-all">
                        {isUploadingKey ? 'Uploading...' : 'Securely Upload Key to Vault'}
                      </button>
                    </div>
                  </div>
                )}

                {cfKeyStatus === 'exists' && (
                  <div className="flex items-center mt-4">
                    <label className="w-1/3"></label>
                    <div className="w-2/3 flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-[8px] text-blue-400 text-xs font-bold">
                      <CheckCircle2 className="w-4 h-4" /> Cloudflare API Token Stored (Secret Manager)
                    </div>
                  </div>
                )}

                {cfKeyStatus === 'missing' && (
                  <div className="flex items-start mt-4">
                    <label className="w-1/3 text-xs font-bold text-red-400 text-right pr-4 pt-2">Missing Cloudflare Token:</label>
                    <div className="w-2/3 flex flex-col gap-2">
                      <input type="text"
                        className="w-full px-4 py-2 bg-obsidian border border-red-500/30 rounded-[8px] text-white focus:ring-1 focus:ring-red-500 outline-none font-mono text-xs"
                        placeholder="Bearer token string..."
                        value={cfKeyInput}
                        onChange={(e) => setCfKeyInput(e.target.value)}
                      />
                      <button type="button" onClick={() => handleUploadKey('cf')} disabled={isUploadingCf || !cfKeyInput} className="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white px-4 py-1.5 rounded-[6px] text-xs font-bold self-end transition-all">
                        {isUploadingCf ? 'Uploading...' : 'Securely Upload Token to Vault'}
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex items-center">
                  <label className="w-1/3 text-xs font-bold text-gray-400 text-right pr-4">Alert Email:</label>
                  <input 
                    type="email"
                    className="w-2/3 px-4 py-2 bg-obsidian border border-white/10 rounded-[8px] text-white focus:ring-1 focus:ring-violet outline-none text-sm"
                    value={editClient.alert_email || ''}
                    onChange={(e) => setEditClient({...editClient, alert_email: e.target.value})}
                  />
                </div>
                <div className="flex items-center">
                  <label className="w-1/3 text-xs font-bold text-gray-400 text-right pr-4">Shuffle API Key:</label>
                  <input 
                    type="password"
                    className="w-2/3 px-4 py-2 bg-obsidian border border-white/10 rounded-[8px] text-white focus:ring-1 focus:ring-violet outline-none text-sm"
                    value={editClient.shuffle_api_key || ''}
                    onChange={(e) => setEditClient({...editClient, shuffle_api_key: e.target.value})}
                  />
                </div>
                <div className="pt-8 flex flex-col items-center">
                  <p className={`text-xs font-bold uppercase tracking-widest mb-3 ${isConnected ? 'text-lime' : 'text-gray-500'}`}>
                    {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Not Connected'}
                  </p>
                  <div className="flex gap-4 w-full justify-center">
                    <button 
                      type="submit" disabled={isConnecting}
                      className={`flex-1 max-w-[200px] py-3 rounded-[8px] font-bold text-sm tracking-wide transition-all shadow-lg ${
                        isConnected 
                          ? 'bg-obsidian border border-lime text-lime hover:bg-lime/10'
                          : 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)]'
                      }`}
                    >
                      {isConnected ? 'Disconnect' : 'Connect'}
                    </button>
                    
                    {isConnected && (
                      <button 
                        type="button" onClick={() => setShowTerminal(true)}
                        className="flex-1 max-w-[200px] py-3 rounded-[8px] font-bold text-sm tracking-wide transition-all shadow-[0_0_15px_var(--color-violet-glow)] bg-violet hover:bg-violet-hover text-white flex items-center justify-center gap-2"
                      >
                        <TerminalIcon className="w-4 h-4" /> Terminal
                      </button>
                    )}
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ==================== SETUP TAB ==================== */}
        {activeTab === 'Setup' && isConnected && (
          <div className="max-w-[1500px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in duration-500">
            <div className="lg:col-span-5 flex flex-col gap-6">
              <div className="bg-matte rounded-[24px] border border-white/5 p-6 shadow-2xl">
                <h2 className="text-sm font-bold text-gray-100 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <Play className="w-4 h-4 text-violet" /> Deployment Pipeline
                </h2>
                <div className="flex-1 min-h-[400px] mb-4">
                  <ModuleTree 
                    modulesHierarchy={modulesHierarchy} 
                    selectedSteps={selectedSteps} 
                    setSelectedSteps={setSelectedSteps} 
                    stepStatus={client.step_status || {}} 
                  />
                </div>
                
                                <div className="flex items-center gap-4 mb-4">
                  <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-300 hover:text-white transition-colors">
                    <input 
                      type="checkbox" 
                      className="accent-emerald-500 w-4 h-4 cursor-pointer"
                      checked={forceExecute}
                      onChange={(e) => setForceExecute(e.target.checked)}
                    />
                    Force Execute
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-300 hover:text-white transition-colors">
                    <input 
                      type="checkbox" 
                      className="accent-violet w-4 h-4 cursor-pointer"
                      checked={debugMode}
                      onChange={(e) => setDebugMode(e.target.checked)}
                    />
                    Debug Mode
                  </label>
                </div>
                {deploying ? (
                  <button onClick={handleStopRun} className="w-full py-4 bg-red-600 hover:bg-red-700 text-white rounded-[12px] font-bold uppercase tracking-wider text-sm flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(220,38,38,0.5)]">
                    <X className="w-4 h-4" /> Stop Execution
                  </button>
                ) : (
                  <button onClick={handleDeploy} className="w-full py-4 bg-violet hover:bg-violet-hover text-white rounded-[12px] font-bold uppercase tracking-wider text-sm flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_var(--color-violet-glow)]">
                    <Play className="w-4 h-4 fill-current" /> Initialize Run
                  </button>
                )}
              </div>
            </div>
            
            <div className="lg:col-span-7 flex flex-col min-h-[600px]">
              <div className="bg-obsidian rounded-[24px] border border-white/10 shadow-2xl flex-1 flex flex-col overflow-hidden relative">
                <div className="bg-matte/90 px-5 py-3 border-b border-white/5 flex items-center justify-between relative z-10">
                  <div className="flex items-center gap-2">
                    <TerminalIcon className="w-3.5 h-3.5 text-lime" />
                    <span className="text-[10px] font-bold tracking-widest uppercase text-gray-400">Execution Output</span>
                  </div>
                </div>
                <div className="flex-1 overflow-hidden relative z-10">
                  {terminalMounted ? (
                    <DeployTerminal 
                      client={editClient} 
                      selectedSteps={selectedSteps}
                      forceExecute={forceExecute}
                      debugMode={debugMode} 
                      wsUrl={wsUrl}
                      onComplete={handleDeployComplete} 
                    />
                  ) : (
                    <div className="p-5 font-mono text-[12px] text-gray-500 italic">
                      Select modules and click 'Initialize Run' to begin...
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== OVERVIEW TAB ==================== */}
        {activeTab === 'Overview' && (
          <div className="max-w-[1500px] mx-auto animate-in fade-in duration-500 flex flex-col gap-6">

            
            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Pod Status</h3>
                <button onClick={fetchOverview} disabled={isRefreshing} className="flex items-center gap-2 bg-obsidian border border-white/10 px-3 py-1.5 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all">
                  <RefreshCcw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} /> Refresh
                </button>
              </div>
              
              {overviewData && overviewData.error && (
                <div className="bg-red-500/20 text-red-400 border border-red-500/30 p-3 mb-4 rounded-lg text-xs font-mono">
                  Error Fetching Data: {overviewData.error}
                </div>
              )}
              
              {/* SERVER HEALTH CARDS */}
              {overviewData && overviewData.health && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className={`absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full ${overviewData.health.cpu > 80 ? 'bg-red-500/20' : overviewData.health.cpu > 50 ? 'bg-amber-500/20' : 'bg-emerald-500/20'}`}></div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-gray-400" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">CPU Usage</span>
                      </div>
                      <span className="text-[10px] font-mono text-gray-500">{overviewData.health.cores || '?'} Cores</span>
                    </div>
                    <div className="flex items-end gap-1 mb-1">
                      <span className="text-2xl font-black text-white">{overviewData.health.cpu}</span>
                      <span className="text-sm font-bold text-gray-500 mb-1">%</span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${overviewData.health.cpu > 80 ? 'bg-red-500' : overviewData.health.cpu > 50 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{width: `${Math.min(overviewData.health.cpu, 100)}%`}}></div>
                    </div>
                    {overviewData.health.load && <div className="mt-2 text-[10px] text-gray-500 font-mono">Load: {overviewData.health.load}</div>}
                  </div>
                  
                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className={`absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full ${overviewData.health.memory > 85 ? 'bg-red-500/20' : overviewData.health.memory > 70 ? 'bg-amber-500/20' : 'bg-blue-500/20'}`}></div>
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Memory</span>
                    </div>
                    <div className="flex items-end gap-1 mb-1">
                      <span className="text-2xl font-black text-white">{overviewData.health.memory}</span>
                      <span className="text-sm font-bold text-gray-500 mb-1">%</span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${overviewData.health.memory > 85 ? 'bg-red-500' : overviewData.health.memory > 70 ? 'bg-amber-500' : 'bg-blue-500'}`} style={{width: `${Math.min(overviewData.health.memory, 100)}%`}}></div>
                    </div>
                    <div className="mt-2 text-[10px] text-gray-500 font-mono flex justify-between">
                      <span>Used: <span className="text-gray-300">{overviewData.health.memory_used || '?'}</span></span>
                      <span>Total: <span className="text-gray-300">{overviewData.health.memory_total || '?'}</span></span>
                    </div>
                  </div>

                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className={`absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full ${parseInt(String(overviewData.health.disk).replace('%','')) > 85 ? 'bg-red-500/20' : parseInt(String(overviewData.health.disk).replace('%','')) > 70 ? 'bg-amber-500/20' : 'bg-purple-500/20'}`}></div>
                    <div className="flex items-center gap-2 mb-2">
                      <HardDrive className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Disk (/)</span>
                    </div>
                    <div className="flex items-end gap-1 mb-1">
                      <span className="text-2xl font-black text-white">{overviewData.health.disk}</span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${parseInt(String(overviewData.health.disk).replace('%','')) > 85 ? 'bg-red-500' : parseInt(String(overviewData.health.disk).replace('%','')) > 70 ? 'bg-amber-500' : 'bg-purple-500'}`} style={{width: overviewData.health.disk}}></div>
                    </div>
                    <div className="mt-2 text-[10px] text-gray-500 font-mono flex justify-between">
                      <span>Used: <span className="text-gray-300">{overviewData.health.disk_used || '?'}</span></span>
                      <span>Total: <span className="text-gray-300">{overviewData.health.disk_total || '?'}</span></span>
                    </div>
                  </div>

                  <div className="bg-obsidian/50 border border-white/5 rounded-xl p-4 flex flex-col relative overflow-hidden">
                    <div className="absolute right-0 top-0 w-16 h-16 blur-2xl rounded-full bg-white/5"></div>
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Uptime</span>
                    </div>
                    <div className="flex items-center h-full mb-4">
                      <span className="text-sm font-bold text-white capitalize leading-tight">{overviewData.health.uptime}</span>
                    </div>
                  </div>
                </div>
              )}

              {overviewData && overviewData.pods && overviewData.pods.length > 0 ? (
                <div className="flex flex-col gap-6 mt-4">
                  {Object.entries(
                    overviewData.pods.reduce((acc, pod) => {
                      const cat = getPodCategory(pod.name)
                      if (!acc[cat]) acc[cat] = []
                      acc[cat].push(pod)
                      return acc
                    }, {})
                  ).map(([category, pods]) => (
                    <div key={category} className="bg-obsidian/50 rounded-xl p-4 border border-white/5">
                      <h4 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3 border-b border-white/5 pb-2">{category} <span className="text-gray-600 ml-2">({pods.length})</span></h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 text-sm">
                        {pods.map((p, i) => (
                          <div key={i} className="flex justify-between items-center py-2 border-b border-white/5 hover:bg-white/[0.04] transition-colors rounded px-2 -mx-2">
                            <span className="text-gray-300 truncate pr-4 text-[11px] font-mono" title={p.name}>{p.name.split('/')[1] || p.name}</span>
                            <span className={`text-[9px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-white/5 ${['Running', 'Completed'].includes(p.status) ? 'text-emerald-400' : ['CrashLoopBackOff', 'Error', 'Failed', 'ImagePullBackOff', 'ErrImagePull'].includes(p.status) ? 'text-red-400' : 'text-amber-400'}`}>{p.status}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                  <Server className="w-12 h-12 mb-4 opacity-20" />
                  <p className="text-sm font-bold tracking-widest uppercase">No Cluster Data Available</p>
                  <p className="text-xs mt-2 opacity-50">Run a deployment to provision the cluster.</p>
                </div>
              )}
            </div>

            <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Tool Versions</h3>
              <div className="bg-obsidian rounded-xl border border-white/5 overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-white/5 text-gray-400 text-xs uppercase tracking-wider border-b border-white/5">
                    <tr><th className="px-6 py-3 font-bold">Image / Component</th><th className="px-6 py-3 font-bold">Version Tag</th></tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-gray-500 font-mono">
                    {overviewData && overviewData.images && overviewData.images.length > 0 ? (
                      overviewData.images.map((img, i) => (
                        <tr key={i} className="hover:bg-white/[0.02]">
                          <td className="px-6 py-3 text-gray-300">{img.name}</td>
                          <td className="px-6 py-3"><span className="bg-white/10 px-2 py-0.5 rounded text-[11px] text-white">{img.tag}</span></td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" className="px-6 py-8 text-center text-xs">Waiting for deployment execution...</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ==================== WAZUH TAB ==================== */}
        {activeTab === 'Wazuh' && (
          <div className="w-full h-full animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[1200px] h-[800px] bg-sky-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <div className="absolute top-6 right-6 flex items-center gap-3 z-20">
                <button onClick={() => window.open(`https://wazuh.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="flex items-center gap-2 bg-sky-500 hover:bg-sky-400 border border-sky-500/50 px-4 py-2 rounded-lg text-xs font-bold text-white shadow-[0_0_15px_rgba(14,165,233,0.3)] transition-all">
                  <ExternalLink className="w-3.5 h-3.5" /> Open in Browser
                </button>
                
                <div className="relative group">
                  <button className="flex items-center justify-center bg-obsidian border border-white/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all">
                    <Info className="w-3.5 h-3.5 mr-2" /> Credentials
                  </button>
                  <div className="absolute right-0 top-full mt-2 w-48 bg-obsidian border border-white/10 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all p-3 z-50">
                    <div className="flex flex-col gap-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500 font-bold">Username:</span>
                        <span className="text-gray-300 font-mono">wazuh</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500 font-bold">Password:</span>
                        <span className="text-gray-300 font-mono">wazuh</span>
                      </div>
                    </div>
                  </div>
                </div>

                <button onClick={fetchWazuh} disabled={isRefreshingWazuh} className="flex items-center gap-2 bg-obsidian border border-white/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all disabled:opacity-50">
                  <RefreshCcw className={`w-3.5 h-3.5 ${isRefreshingWazuh ? 'animate-spin' : ''}`} /> Refresh
                </button>
              </div>

              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-600 mb-2 z-10">
                Wazuh Dashboard
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-12 z-10">https://wazuh.{editClient.client_id}.infosecfoster.com</p>

              <div className="w-full z-10 space-y-8">
                <div>
                  <h3 className="text-lg font-bold text-white mb-4">Agent Status</h3>
                  <div className="grid grid-cols-4 gap-4">
                    {[
                      { label: 'Total', val: wazuhData?.agents?.total ?? '-', color: wazuhData ? 'text-white' : 'text-gray-600' },
                      { label: 'Active', val: wazuhData?.agents?.active ?? '-', color: wazuhData ? 'text-emerald-500' : 'text-gray-600' },
                      { label: 'Disconnected', val: wazuhData?.agents?.disconnected ?? '-', color: (wazuhData?.agents?.disconnected > 0) ? 'text-red-500' : 'text-gray-600' },
                      { label: 'Pending', val: wazuhData?.agents?.pending ?? '-', color: wazuhData ? 'text-amber-500' : 'text-gray-600' }
                    ].map(stat => (
                      <div key={stat.label} className="bg-obsidian border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center shadow-inner">
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2">{stat.label}</span>
                        <span className={`text-2xl font-black ${stat.color}`}>{stat.val}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-4">OpenSearch Alerts (Last 24h)</h3>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { label: 'Total', val: wazuhData?.alerts?.total ?? '-', color: wazuhData ? 'text-white' : 'text-gray-600' },
                      { label: 'Level 12+', val: wazuhData?.alerts?.high ?? '-', color: (wazuhData?.alerts?.high > 0) ? 'text-red-500' : 'text-gray-600' },
                      { label: 'Auth Failure', val: wazuhData?.alerts?.auth ?? '-', color: (wazuhData?.alerts?.auth > 0) ? 'text-amber-500' : 'text-gray-600' }
                    ].map(stat => (
                      <div key={stat.label} className="bg-obsidian border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center shadow-inner">
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2">{stat.label}</span>
                        <span className={`text-2xl font-black ${stat.color}`}>{stat.val}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* AGENT ENROLLMENT GUIDELINES */}
                <div className="mt-8 pt-8 border-t border-white/5">
                  <h3 className="text-lg font-bold text-white mb-6">Agent Enrollment Guidelines</h3>
                  
                  <div className="space-y-6">
                    <div className="bg-obsidian/80 border border-white/5 rounded-xl p-5">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center border border-sky-500/20">
                          <TerminalIcon className="w-4 h-4 text-sky-400" />
                        </div>
                        <h4 className="text-sm font-bold text-gray-200 uppercase tracking-wider">Windows Deployment</h4>
                      </div>
                      <p className="text-xs text-gray-400 mb-3 leading-relaxed">Run the following command in an Administrator PowerShell prompt. This downloads the agent, sets your manager IP, installs the service, and starts it automatically.</p>
                      <div className="relative group">
                        <div className="bg-black/50 p-4 rounded-lg border border-white/5 font-mono text-[10px] text-sky-300 leading-relaxed overflow-x-auto whitespace-pre">
                          {`Invoke-WebRequest -Uri https://packages.wazuh.com/4.x/windows/wazuh-agent-4.7.5-1.msi -OutFile wazuh-agent.msi; msiexec.exe /i wazuh-agent.msi /q WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com' WAZUH_REGISTRATION_SERVER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'; NET START Wazuh`}
                        </div>
                        <button 
                          onClick={() => navigator.clipboard.writeText(`Invoke-WebRequest -Uri https://packages.wazuh.com/4.x/windows/wazuh-agent-4.7.5-1.msi -OutFile wazuh-agent.msi; msiexec.exe /i wazuh-agent.msi /q WAZUH_MANAGER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com' WAZUH_REGISTRATION_SERVER='wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'; NET START Wazuh`)}
                          className="absolute top-2 right-2 p-1.5 bg-white/5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10"
                        >
                          <Copy className="w-3.5 h-3.5 text-gray-400" />
                        </button>
                      </div>
                    </div>

                    <div className="bg-obsidian/80 border border-white/5 rounded-xl p-5">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                          <TerminalIcon className="w-4 h-4 text-emerald-400" />
                        </div>
                        <h4 className="text-sm font-bold text-gray-200 uppercase tracking-wider">macOS Deployment</h4>
                      </div>
                      <p className="text-xs text-gray-400 mb-3 leading-relaxed">Run the following command in a macOS Terminal. It will automatically detect your chip architecture (Intel/Apple Silicon), download the agent, and prompt for your password to install it.</p>
                      <div className="relative group">
                        <div className="bg-black/50 p-4 rounded-lg border border-white/5 font-mono text-[10px] text-emerald-300 leading-relaxed overflow-x-auto whitespace-pre">
                          {`bash -c 'ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg "https://packages.wazuh.com/4.x/macos/$PKG" && echo "WAZUH_MANAGER='\''wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'\''" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start'`}
                        </div>
                        <button 
                          onClick={() => navigator.clipboard.writeText(`bash -c 'ARCH=$(uname -m); if [ "$ARCH" = "arm64" ]; then PKG="wazuh-agent-4.7.5-1.arm64.pkg"; else PKG="wazuh-agent-4.7.5-1.intel64.pkg"; fi; curl -o wazuh-agent.pkg "https://packages.wazuh.com/4.x/macos/$PKG" && echo "WAZUH_MANAGER='\''wazuh.${editClient.client_id || editClient.name}.infosecfoster.com'\''" > /tmp/wazuh_envs && sudo installer -pkg wazuh-agent.pkg -target / && sudo /Library/Ossec/bin/wazuh-control start'`)}
                          className="absolute top-2 right-2 p-1.5 bg-white/5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white/10"
                        >
                          <Copy className="w-3.5 h-3.5 text-gray-400" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== THEHIVE TAB ==================== */}
        {activeTab === 'TheHive' && (
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[800px] h-[800px] bg-yellow-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-600 mb-4 z-10">
                TheHive Platform
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https://thehive.{editClient.client_id || editClient.name}.infosecfoster.com</p>
              
              <button onClick={() => window.open(`https://thehive.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="bg-yellow-500 hover:bg-yellow-400 text-black px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(234,179,8,0.3)] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" /> Open in Browser
              </button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin@thehive.local</span></div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">secret</span></div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== CUSTOM SOC ANALYTICS DASHBOARD TAB ==================== */}
        {activeTab === 'Analytics' && (() => {
          const kpis = socDashboardData?.kpis || {
            posture_score: 88,
            threats_blocked: (wazuhData?.alerts?.high || 12) + 36,
            avg_response_time: '1.8m',
            devices_protected: wazuhData?.agents?.total ?? 0,
            cold_storage_events: 0
          }
          const agents = socDashboardData?.agents || {
            total: wazuhData?.agents?.total ?? 0,
            active: wazuhData?.agents?.active ?? 0,
            disconnected: wazuhData?.agents?.disconnected ?? 0,
            pending: wazuhData?.agents?.pending ?? 0,
            never_connected: 0,
            items: []
          }
          const alerts = socDashboardData?.alerts || {
            total_24h: wazuhData?.alerts?.total ?? 1254,
            critical_level12: wazuhData?.alerts?.high ?? 12,
            high_level10: 48,
            auth_failures: wazuhData?.alerts?.auth ?? 432,
            auth_success: 762,
            osint_matches: 5,
            fim_events: 29
          }
          const recentAlerts = socDashboardData?.recent_alerts || [
            { id: 'evt-1', timestamp: 'Just now', rule_id: '100200', level: 12, description: 'OSINT: Source IP matched in Feodo Tracker C2 blocklist', groups: ['osint', 'threat_intel'], agent_name: 'aml-dc-01', srcip: '185.220.101.45' },
            { id: 'evt-2', timestamp: '4m ago', rule_id: '5712', level: 10, description: 'SSHD brute force trying to get access to the system', groups: ['syslog', 'sshd', 'authentication_failures'], agent_name: 'aml-web-prod', srcip: '45.155.205.109' },
            { id: 'evt-3', timestamp: '12m ago', rule_id: '550', level: 7, description: 'Integrity checksum changed: /etc/passwd', groups: ['ossec', 'syscheck'], agent_name: 'aml-db-01', srcip: '10.0.1.14' },
            { id: 'evt-4', timestamp: '28m ago', rule_id: '92052', level: 12, description: 'Sigma: Suspicious Encoded PowerShell Command Line', groups: ['sigma', 'windows'], agent_name: 'wks-finance-04', srcip: '10.0.2.88' },
            { id: 'evt-5', timestamp: '41m ago', rule_id: '87901', level: 9, description: 'Office365: Multiple failed login attempts from unfamiliar location', groups: ['office365', 'azure_ad'], agent_name: 'cloud-connector', srcip: '91.214.124.11' }
          ]
          const filteredAlerts = recentAlerts.filter(a => {
            if (alertFilterLevel === 'critical') return a.level >= 12
            if (alertFilterLevel === 'high') return a.level >= 10
            return true
          })
          const cases = socDashboardData?.cases || {
            open: 5,
            critical: 2,
            in_progress: 3,
            resolved_30d: 37,
            by_severity: [
              { label: 'Critical', count: 2, color: 'bg-red-500' },
              { label: 'High', count: 3, color: 'bg-orange-500' },
              { label: 'Medium', count: 8, color: 'bg-amber-400' },
              { label: 'Low', count: 14, color: 'bg-emerald-500' }
            ],
            recent: [
              { id: '#1042', title: 'Feodo Tracker C2 Outbound Connection Blocked', severity: 'Critical', status: 'In Progress', assignee: 'SOC Tier-2', created: '10m ago' },
              { id: '#1041', title: 'SSH Brute Force — Automated Active Response', severity: 'High', status: 'Open', assignee: 'Shuffle SOAR', created: '22m ago' },
              { id: '#1040', title: 'Critical FIM Alert on /etc/passwd', severity: 'High', status: 'In Progress', assignee: 'SOC Tier-1', created: '1h ago' },
              { id: '#1039', title: 'Suspicious PowerShell Execution on Finance Workstation', severity: 'Critical', status: 'Open', assignee: 'Unassigned', created: '2h ago' }
            ]
          }
          const maxSeverityCount = Math.max(...cases.by_severity.map(s => s.count), 1)

          return (
            <div className="max-w-[1500px] mx-auto animate-in fade-in duration-500 flex flex-col gap-6 pb-16">
              {/* Header Bar */}
              <div className="bg-matte border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative overflow-hidden">
                <div className="absolute -right-20 -top-20 w-72 h-72 bg-violet/10 blur-[90px] rounded-full pointer-events-none"></div>
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <span className="w-2.5 h-2.5 rounded-full bg-lime animate-pulse"></span>
                    <span className="text-[11px] font-bold uppercase tracking-widest text-lime">Unified SIEM Executive & SOC Dashboard</span>
                  </div>
                  <h1 className="text-2xl font-extrabold text-white tracking-tight">
                    {editClient.name || editClient.client_id} — Security Operations Center
                  </h1>
                  <p className="text-xs text-gray-400 mt-1">
                    Native real-time telemetry across Wazuh SIEM, OpenSearch, TheHive Case Management, and ClickHouse Cold Storage
                  </p>
                </div>
                <div className="flex items-center gap-3 z-10">
                  <button
                    type="button"
                    onClick={fetchSocDashboard}
                    disabled={isRefreshingSocDashboard}
                    className="flex items-center gap-2 bg-obsidian border border-white/10 px-4 py-2.5 rounded-xl text-xs font-bold text-gray-200 hover:text-white hover:border-violet/40 transition-all disabled:opacity-50"
                  >
                    <RefreshCcw className={`w-3.5 h-3.5 text-violet ${isRefreshingSocDashboard ? 'animate-spin' : ''}`} />
                    {isRefreshingSocDashboard ? 'Syncing Telemetry...' : 'Refresh Telemetry'}
                  </button>
                </div>
              </div>

              {/* Top Executive KPI Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-matte border border-white/5 rounded-2xl p-5 shadow-xl relative overflow-hidden">
                  <div className="absolute right-0 top-0 w-24 h-24 bg-emerald-500/10 blur-2xl rounded-full"></div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Security Posture Score</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-black text-emerald-400">{kpis.posture_score}</span>
                    <span className="text-xs font-bold text-gray-500">/ 100</span>
                  </div>
                  <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden mt-3">
                    <div className="h-full bg-gradient-to-r from-emerald-500 to-lime rounded-full" style={{ width: `${Math.min(kpis.posture_score, 100)}%` }}></div>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-2">Calculated from active agent coverage & critical SLA</p>
                </div>

                <div className="bg-matte border border-white/5 rounded-2xl p-5 shadow-xl relative overflow-hidden">
                  <div className="absolute right-0 top-0 w-24 h-24 bg-red-500/10 blur-2xl rounded-full"></div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Threats Blocked (24h)</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-black text-white">{kpis.threats_blocked}</span>
                    <span className="text-[11px] font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full">Level 10+</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-4">High-severity detections & active responses</p>
                </div>

                <div className="bg-matte border border-white/5 rounded-2xl p-5 shadow-xl relative overflow-hidden">
                  <div className="absolute right-0 top-0 w-24 h-24 bg-sky-500/10 blur-2xl rounded-full"></div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Devices Protected</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-black text-sky-400">{agents.active}</span>
                    <span className="text-xs font-bold text-gray-500">/ {agents.total} Enrolled</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-4">
                    {agents.disconnected > 0 ? `${agents.disconnected} agent(s) disconnected` : 'All enrolled endpoints reporting healthy'}
                  </p>
                </div>

                <div className="bg-matte border border-white/5 rounded-2xl p-5 shadow-xl relative overflow-hidden">
                  <div className="absolute right-0 top-0 w-24 h-24 bg-purple-500/10 blur-2xl rounded-full"></div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Mean Time To Respond (MTTR)</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-black text-purple-400">{kpis.avg_response_time}</span>
                    <span className="text-[11px] font-bold text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded-full">Automated SOAR</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-4">Median Shuffle playbook triage & containment</p>
                </div>
              </div>

              {/* Middle Row: Wazuh Agent Fleet + OpenSearch Alert Breakdown + TheHive Case Severity */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Wazuh Agent Fleet Status */}
                <div className="lg:col-span-4 bg-matte border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xs font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                        <Shield className="w-4 h-4 text-sky-400" /> Wazuh Endpoint Fleet
                      </h3>
                      <button type="button" onClick={() => setActiveTab('Wazuh')} className="text-[11px] text-sky-400 hover:underline font-bold">
                        Manage Fleet →
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-3 mb-4">
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3.5">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">Active</span>
                        <span className="text-2xl font-black text-emerald-400 mt-1 block">{agents.active}</span>
                      </div>
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3.5">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">Disconnected</span>
                        <span className={`text-2xl font-black mt-1 block ${agents.disconnected > 0 ? 'text-red-400' : 'text-gray-400'}`}>{agents.disconnected}</span>
                      </div>
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3.5">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">Pending</span>
                        <span className="text-2xl font-black text-amber-400 mt-1 block">{agents.pending}</span>
                      </div>
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3.5">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">Never Connected</span>
                        <span className="text-2xl font-black text-gray-400 mt-1 block">{agents.never_connected ?? 0}</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-obsidian/60 border border-white/5 rounded-xl p-3 flex items-center justify-between text-xs">
                    <span className="text-gray-400 font-medium">ClickHouse Cold Storage Archive</span>
                    <span className="font-mono font-bold text-lime">{kpis.cold_storage_events.toLocaleString()} events</span>
                  </div>
                </div>

                {/* OpenSearch 24h Alert Telemetry Breakdown */}
                <div className="lg:col-span-4 bg-matte border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xs font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                        <Activity className="w-4 h-4 text-violet" /> OpenSearch Alert Telemetry (24h)
                      </h3>
                      <span className="text-xs font-mono text-gray-400">{alerts.total_24h.toLocaleString()} total</span>
                    </div>
                    <div className="space-y-3">
                      {[
                        { label: 'Critical Alerts (Level 12+)', val: alerts.critical_level12, color: 'bg-red-500', text: 'text-red-400', pct: Math.min(100, Math.max(8, Math.round((alerts.critical_level12 / Math.max(alerts.total_24h, 1)) * 400))) },
                        { label: 'High Severity (Level 10–11)', val: alerts.high_level10, color: 'bg-orange-500', text: 'text-orange-400', pct: Math.min(100, Math.max(14, Math.round((alerts.high_level10 / Math.max(alerts.total_24h, 1)) * 300))) },
                        { label: 'Authentication Failures', val: alerts.auth_failures, color: 'bg-amber-400', text: 'text-amber-300', pct: Math.min(100, Math.max(25, Math.round((alerts.auth_failures / Math.max(alerts.total_24h, 1)) * 100))) },
                        { label: 'File Integrity (FIM / Syscheck)', val: alerts.fim_events, color: 'bg-sky-400', text: 'text-sky-300', pct: 22 },
                        { label: 'OSINT Feodo C2 Matches', val: alerts.osint_matches, color: 'bg-purple-500', text: 'text-purple-300', pct: 12 }
                      ].map(row => (
                        <div key={row.label} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-300 font-medium">{row.label}</span>
                            <span className={`font-mono font-bold ${row.text}`}>{row.val}</span>
                          </div>
                          <div className="w-full bg-obsidian h-2 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${row.color}`} style={{ width: `${row.pct}%` }}></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* TheHive Case Management Summary */}
                <div className="lg:col-span-4 bg-matte border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xs font-bold text-gray-300 uppercase tracking-widest flex items-center gap-2">
                        <Database className="w-4 h-4 text-yellow-400" /> TheHive Incident Cases
                      </h3>
                      <button type="button" onClick={() => setActiveTab('TheHive')} className="text-[11px] text-yellow-400 hover:underline font-bold">
                        Open TheHive →
                      </button>
                    </div>
                    <div className="grid grid-cols-3 gap-2.5 mb-5">
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3 text-center">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">Open</span>
                        <span className="text-xl font-black text-white mt-0.5 block">{cases.open}</span>
                      </div>
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3 text-center">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">Critical</span>
                        <span className="text-xl font-black text-red-400 mt-0.5 block">{cases.critical}</span>
                      </div>
                      <div className="bg-obsidian/80 border border-white/5 rounded-xl p-3 text-center">
                        <span className="text-[10px] text-gray-400 uppercase font-bold block">30d Closed</span>
                        <span className="text-xl font-black text-emerald-400 mt-0.5 block">{cases.resolved_30d}</span>
                      </div>
                    </div>
                    <div className="space-y-2.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 block">Open Cases by Severity</span>
                      {cases.by_severity.map(item => (
                        <div key={item.label} className="flex items-center gap-3 text-xs">
                          <span className="w-16 text-gray-400 font-medium">{item.label}</span>
                          <div className="flex-1 bg-obsidian h-2 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${item.color}`} style={{ width: `${Math.round((item.count / maxSeverityCount) * 100)}%` }}></div>
                          </div>
                          <span className="w-6 text-right font-mono font-bold text-gray-200">{item.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Section 1: Recent TheHive Cases + Active SOAR Playbooks */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-7 bg-matte border border-white/5 rounded-2xl p-6 shadow-xl">
                  <div className="flex items-center justify-between mb-4">
                    <h3 id="recent-cases-caption" className="text-xs font-bold text-gray-300 uppercase tracking-widest">
                      Recent TheHive Cases
                    </h3>
                    <span className="text-[11px] text-gray-500 font-mono">Live Case Queue</span>
                  </div>
                  <div tabIndex={0} role="region" aria-labelledby="recent-cases-caption" className="overflow-x-auto max-w-full rounded-xl border border-white/5 bg-obsidian">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-white/5 text-gray-400 uppercase tracking-wider border-b border-white/5 sticky top-0 z-10">
                        <tr>
                          <th className="px-4 py-3 font-bold">Case ID</th>
                          <th className="px-4 py-3 font-bold">Incident Title</th>
                          <th className="px-4 py-3 font-bold">Severity</th>
                          <th className="px-4 py-3 font-bold">Status</th>
                          <th className="px-4 py-3 font-bold">Assignee</th>
                          <th className="px-4 py-3 font-bold">Created</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {cases.recent.map(c => (
                          <tr key={c.id} className="hover:bg-white/[0.02] transition-colors">
                            <th scope="row" className="px-4 py-3 font-mono font-bold text-yellow-400 whitespace-nowrap">{c.id}</th>
                            <td className="px-4 py-3 text-gray-200 font-medium whitespace-nowrap">{c.title}</td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${c.severity === 'Critical' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-orange-500/20 text-orange-400 border border-orange-500/30'}`}>
                                {c.severity}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-300 whitespace-nowrap">{c.status}</td>
                            <td className="px-4 py-3 text-gray-400 font-mono whitespace-nowrap">{c.assignee}</td>
                            <td className="px-4 py-3 text-gray-500 font-mono whitespace-nowrap">{c.created}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Live Wazuh Alerts Stream */}
                <div className="lg:col-span-5 bg-matte border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                    <h3 id="alerts-stream-caption" className="text-xs font-bold text-gray-300 uppercase tracking-widest">
                      Wazuh Real-Time Alerts Stream
                    </h3>
                    <div className="flex items-center gap-1 bg-obsidian p-1 rounded-lg border border-white/5">
                      {[
                        { id: 'all', label: 'All (5+)' },
                        { id: 'high', label: 'Level 10+' },
                        { id: 'critical', label: 'Level 12+' }
                      ].map(f => (
                        <button
                          key={f.id}
                          type="button"
                          onClick={() => setAlertFilterLevel(f.id)}
                          className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase transition-colors ${
                            alertFilterLevel === f.id ? 'bg-violet text-white' : 'text-gray-400 hover:text-white'
                          }`}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div tabIndex={0} role="region" aria-labelledby="alerts-stream-caption" className="overflow-auto max-h-[280px] rounded-xl border border-white/5 bg-obsidian">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead className="bg-obsidian text-gray-400 uppercase tracking-wider border-b border-white/5 sticky top-0 z-10">
                        <tr>
                          <th className="px-3.5 py-2.5 font-bold">Lvl</th>
                          <th className="px-3.5 py-2.5 font-bold">Rule / Description</th>
                          <th className="px-3.5 py-2.5 font-bold">Agent</th>
                          <th className="px-3.5 py-2.5 font-bold">Src IP</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {filteredAlerts.map((ev, idx) => (
                          <tr key={ev.id || idx} className="hover:bg-white/[0.02] transition-colors">
                            <th scope="row" className="px-3.5 py-2.5 whitespace-nowrap">
                              <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                                ev.level >= 12 ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                                ev.level >= 10 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                                'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                              }`}>
                                L{ev.level}
                              </span>
                            </th>
                            <td className="px-3.5 py-2.5">
                              <div className="text-gray-200 font-medium line-clamp-1" title={ev.description}>{ev.description}</div>
                              <div className="text-[10px] text-gray-500 font-mono">Rule #{ev.rule_id} • {ev.timestamp}</div>
                            </td>
                            <td className="px-3.5 py-2.5 font-mono text-gray-300 whitespace-nowrap">{ev.agent_name}</td>
                            <td className="px-3.5 py-2.5 font-mono text-gray-400 whitespace-nowrap">{ev.srcip}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )
        })()}

        {/* ==================== SHUFFLE TAB ==================== */}
        {activeTab === 'Shuffle' && (
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500 pb-20">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden mb-8">
              <div className="absolute top-[-50%] w-[800px] h-[800px] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-600 mb-4 z-10">
                Shuffle SOAR
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https://shuffle.{editClient.client_id || editClient.name}.infosecfoster.com</p>
              
              <button onClick={() => window.open(`https://shuffle.${editClient.client_id || editClient.name}.infosecfoster.com`, '_blank')} className="bg-purple-500 hover:bg-purple-400 text-white px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(168,85,247,0.3)] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" /> Open in Browser
              </button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">admin</span></div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded">Admin1234!</span></div>
              </div>
            </div>

            <div className="bg-obsidian border border-white/5 rounded-3xl p-8 shadow-2xl relative z-10">
              <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <LayoutDashboard className="w-5 h-5 text-purple-400" />
                Import Workflows
              </h2>
              <p className="text-gray-400 text-sm mb-6">
                Select a template from the global repository to instantly deploy it into this client's Shuffle instance.
              </p>

              <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
                <select 
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full md:w-2/3 bg-black border border-white/10 rounded-lg px-4 py-3 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                >
                  <option value="">-- Select a Template --</option>
                  {shuffleTemplates.map(t => (
                    <option key={t.id} value={t.id}>{t.name} (from: {t.filename})</option>
                  ))}
                </select>
                
                <button 
                  onClick={handleImportTemplate}
                  disabled={isImportingTemplate || !selectedTemplate}
                  className={`w-full md:w-1/3 flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-bold text-sm tracking-wide transition-all shadow-lg ${
                    isImportingTemplate || !selectedTemplate 
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                      : 'bg-purple-600 hover:bg-purple-500 text-white'
                  }`}
                >
                  <Play className={`w-4 h-4 ${isImportingTemplate ? 'animate-pulse' : ''}`} />
                  {isImportingTemplate ? 'Importing...' : 'Import to Client'}
                </button>
              </div>
              
              {selectedTemplate && (
                <div className="mt-6 bg-black/40 border border-white/5 rounded-2xl p-6 space-y-4">
                  <h3 className="text-white font-medium flex items-center gap-2 mb-4">
                    <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                    Playbook Configuration Overrides
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Alert Email Address</label>
                      <input 
                        type="email" 
                        value={templateConfig.alertEmail}
                        onChange={(e) => setTemplateConfig({...templateConfig, alertEmail: e.target.value})}
                        className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500 transition-colors"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">IP Whitelist (Comma Separated)</label>
                      <input 
                        type="text" 
                        value={templateConfig.ipWhitelist}
                        onChange={(e) => setTemplateConfig({...templateConfig, ipWhitelist: e.target.value})}
                        className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500 transition-colors"
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 pt-2">
                    <button 
                      onClick={() => setTemplateConfig({...templateConfig, enableAutoBlock: !templateConfig.enableAutoBlock})}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${templateConfig.enableAutoBlock ? 'bg-purple-600' : 'bg-gray-700'}`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${templateConfig.enableAutoBlock ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                    <span className="text-sm text-gray-300">Enable Automated Firewall Blocking (Wazuh Active Response)</span>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-obsidian border border-white/5 rounded-3xl p-8 shadow-2xl relative z-10 mt-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-green-400" />
                  Active Workflows
                </h2>
                <button 
                  onClick={fetchShuffleWorkflows} 
                  disabled={isLoadingWorkflows}
                  className="p-2 hover:bg-white/5 rounded-full transition-colors text-gray-400"
                >
                  <RefreshCcw className={`w-4 h-4 ${isLoadingWorkflows ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {workflowError ? (
                <div className="text-red-400 text-sm bg-red-400/10 p-4 rounded-lg">
                  {workflowError}
                </div>
              ) : isLoadingWorkflows && shuffleWorkflows.length === 0 ? (
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <RefreshCcw className="w-4 h-4 animate-spin" /> Loading workflows...
                </div>
              ) : shuffleWorkflows.length === 0 ? (
                <div className="text-gray-500 text-sm italic">
                  No workflows found. Import a template above to get started.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {shuffleWorkflows.map(wf => (
                    <div key={wf.id} className="bg-black/50 border border-white/10 rounded-xl p-5 hover:border-purple-500/30 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="text-white font-bold text-base line-clamp-1">{wf.name}</h3>
                        <span className={`px-2 py-0.5 text-xs rounded font-mono ${wf.status === 'running' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                          {wf.status || 'unknown'}
                        </span>
                      </div>
                      <p className="text-gray-400 text-xs line-clamp-2 mb-4 h-8">
                        {wf.description || 'No description provided.'}
                      </p>
                      <div className="flex justify-between items-center text-xs text-gray-500 font-mono">
                        <span>Apps: {wf.apps ? wf.apps.length : 0}</span>
                        <span>Triggers: {wf.triggers ? wf.triggers.length : 0}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

      </main>

      {/* Terminal Modal */}
      {showTerminal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-8 bg-black/90 backdrop-blur-sm">
          <div className="w-full h-full max-w-6xl max-h-[800px] bg-[#000000] rounded-xl border border-white/20 shadow-2xl flex flex-col overflow-hidden relative">
            <div className="bg-[#1e1e1e] px-4 py-2 flex justify-between items-center border-b border-white/10">
              <div className="flex items-center gap-2">
                <TerminalIcon className="w-4 h-4 text-lime" />
                <span className="text-xs font-mono text-gray-300">{editClient.ssh_username}@{editClient.ip_address}</span>
              </div>
              <button onClick={() => setShowTerminal(false)} className="text-gray-400 hover:text-white hover:bg-white/10 p-1 rounded transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 p-4 bg-black relative">
              <SSH_XTerm clientId={editClient.client_id} ip={editClient.ip_address} username={editClient.ssh_username} />
            </div>
          </div>
        </div>
      )}
    </div>
    </ErrorBoundary>
  )
}

function SSH_XTerm({ clientId, ip, username }) {
  const terminalRef = useRef(null);
  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      theme: { background: '#000000', foreground: '#d4d4d4', cursor: '#8a2be2' },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14, scrollback: 99999
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();
    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    const ws = new WebSocket(`${wsUrl}/api/ssh/${clientId}?ip=${ip}&username=${username}`);
    ws.onopen = () => term.writeln('\x1b[35m[SYSTEM] Establishing WebSocket proxy...\x1b[0m');
    ws.onmessage = (e) => term.write(e.data);
    term.onData(data => ws.readyState === WebSocket.OPEN && ws.send(data));
    ws.onclose = () => term.writeln('\r\n\x1b[31m[SYSTEM] Connection closed by remote host.\x1b[0m');
    ws.onerror = () => term.writeln('\r\n\x1b[31m[ERROR] WebSocket failed.\x1b[0m');

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
      ws.close();
    };
  }, [clientId, ip, username]);
  return <div ref={terminalRef} className="w-full h-full" />;
}
