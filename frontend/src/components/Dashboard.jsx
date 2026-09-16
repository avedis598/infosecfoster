import { useState, useEffect, useRef } from 'react'
import { signOut } from 'firebase/auth'
import { auth, db } from '../firebase'
import ModuleTree from './ModuleTree'
import { collection, addDoc, serverTimestamp, doc, getDoc, updateDoc, onSnapshot } from 'firebase/firestore'
import { LogOut, Terminal as TerminalIcon, Play, ArrowLeft, CheckCircle2, Activity, X, Server, Shield, Database, LayoutDashboard, Settings2, RefreshCcw, ExternalLink } from 'lucide-react'
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
  if (n.includes('grafana') || n.includes('clickhouse')) return 'Metrics & Visualization'
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
  
  const [selectedSteps, setSelectedSteps] = useState([])
  const [modulesHierarchy, setModulesHierarchy] = useState([])
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
  }

  const [thehiveData, setThehiveData] = useState(null)
  const [shuffleData, setShuffleData] = useState(null)
  const [grafanaData, setGrafanaData] = useState(null)

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
    if (activeTab === 'Shuffle' && !shuffleData) fetchService('shuffle', setShuffleData)
    if (activeTab === 'Grafana' && !grafanaData) fetchService('grafana', setGrafanaData)
  }, [activeTab])



  const tabs = [
    { id: 'Connection', icon: Settings2 },
    { id: 'Setup', icon: Play },
    { id: 'Overview', icon: Server },
    { id: 'Wazuh', icon: Shield },
    { id: 'TheHive', icon: Database },
    { id: 'Grafana', icon: Activity },
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
    setIsConnecting(true)
    
    setTimeout(() => {
      setIsConnected(true)
      setIsConnecting(false)
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
        cloudflare_zone: editClient.cloudflare_zone
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

  // Define env var for ws
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

  if (!client || !editClient) return <div className="min-h-screen flex items-center justify-center bg-obsidian text-white">Loading...</div>

  return (
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
          <div className="max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
            <div className="bg-matte border border-white/5 rounded-3xl p-12 shadow-2xl flex flex-col items-center relative overflow-hidden">
              <div className="absolute top-[-50%] w-[800px] h-[800px] bg-sky-500/10 blur-[120px] rounded-full pointer-events-none"></div>
              
              <button onClick={fetchWazuh} className="absolute top-6 right-6 flex items-center gap-2 bg-obsidian border border-white/10 px-4 py-2 rounded-lg text-xs font-bold text-gray-300 hover:text-white hover:border-white/20 transition-all z-20">
                <RefreshCcw className={`w-3.5 h-3.5 ${!wazuhData && activeTab === 'Wazuh' ? 'animate-spin' : ''}`} /> Refresh
              </button>

              <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-600 mb-4 z-10">
                Wazuh Dashboard
              </h1>
              <p className="text-gray-400 font-mono text-sm mb-8 z-10">https://wazuh.{editClient.client_id}.infosecfoster.com</p>
              
              <button className="bg-sky-500 hover:bg-sky-400 text-white px-8 py-3 rounded-lg font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(14,165,233,0.3)] flex items-center gap-2 transition-all mb-10 z-10">
                <ExternalLink className="w-4 h-4" /> Open in Browser
              </button>
              
              <div className="flex flex-col gap-2 items-center text-sm mb-12 z-10">
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Username:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded italic">pending run</span></div>
                <div className="flex gap-2"><span className="text-gray-500 font-bold">Password:</span><span className="text-gray-400 font-mono bg-white/5 px-2 py-0.5 rounded italic">pending run</span></div>
              </div>

              <div className="w-full max-w-2xl z-10 space-y-8">
                <div>
                  <h3 className="text-lg font-bold text-white mb-4">Agent Status</h3>
                  <div className="grid grid-cols-4 gap-4">
                    {[
                      { label: 'Total', val: wazuhData?.agents?.total ?? '-', color: wazuhData ? 'text-white' : 'text-gray-600' },
                      { label: 'Active', val: wazuhData?.agents?.active ?? '-', color: wazuhData ? 'text-emerald-500' : 'text-gray-600' },
                      { label: 'Disconnected', val: wazuhData?.agents?.disconnected ?? '-', color: wazuhData && wazuhData.agents.disconnected > 0 ? 'text-red-500' : 'text-gray-600' },
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
                      { label: 'Level 12+', val: wazuhData?.alerts?.high ?? '-', color: wazuhData && wazuhData.alerts.high > 0 ? 'text-red-500' : 'text-gray-600' },
                      { label: 'Auth Failure', val: wazuhData?.alerts?.auth ?? '-', color: wazuhData && wazuhData.alerts.auth > 0 ? 'text-amber-500' : 'text-gray-600' }
                    ].map(stat => (
                      <div key={stat.label} className="bg-obsidian border border-white/5 rounded-xl p-4 flex flex-col items-center justify-center shadow-inner">
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-2">{stat.label}</span>
                        <span className={`text-2xl font-black ${stat.color}`}>{stat.val}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== PLACEHOLDERS ==================== */}
        {['TheHive', 'Shuffle'].includes(activeTab) && (
          <div className="h-full flex flex-col items-center justify-center text-gray-500 animate-in fade-in">
            <Settings2 className="w-12 h-12 mb-4 opacity-20" />
            <p className="font-bold tracking-widest uppercase">{activeTab} Dashboard Module</p>
            <p className="text-sm mt-2 opacity-50">Under Construction</p>
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
