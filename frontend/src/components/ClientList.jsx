import { useState, useEffect } from 'react'
import { collection, query, orderBy, onSnapshot, addDoc, deleteDoc, doc, serverTimestamp } from 'firebase/firestore'
import { db, auth } from '../firebase'
import { useNavigate } from 'react-router-dom'
import { Server, Plus, Trash2, ArrowRight, ShieldAlert, LogOut, Key } from 'lucide-react'
import { signOut } from 'firebase/auth'

export default function ClientList({ user }) {
  const [clients, setClients] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [newClient, setNewClient] = useState({ 
    client_name: '',
    client_id: '', 
    ip_address: '',
    ssh_username: '',
    private_key: '',
    alert_email: '',
    shuffle_api_key: '',
    cloudflare_token: '',
    cloudflare_zone: ''
  })
  const navigate = useNavigate()

  const handleAddNewClient = () => {
    let cf_token = '';
    let cf_zone = '';
    for (const c of clients) {
      if (c.cloudflare_token) {
        cf_token = c.cloudflare_token;
        cf_zone = c.cloudflare_zone || '';
        break;
      }
    }
    setNewClient({
      client_name: '', client_id: '', ip_address: '', ssh_username: '', alert_email: '',
      shuffle_api_key: '', cloudflare_token: cf_token, cloudflare_zone: cf_zone, private_key: ''
    });
    setShowModal(true);
  }

  useEffect(() => {
    const q = query(collection(db, 'clients'), orderBy('created_at', 'desc'))
    const unsubscribe = onSnapshot(q, (snapshot) => {
      setClients(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })))
    })
    return () => unsubscribe()
  }, [])

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => setNewClient({ ...newClient, private_key: e.target.result })
      reader.readAsText(file)
    }
  }

  const handleAddClient = async (e) => {
    e.preventDefault()
    if (!newClient.client_name || !newClient.client_id || !newClient.ip_address || !newClient.ssh_username) {
      alert("Please fill in the required fields (Client Name, Client ID, IP, Username).")
      return
    }

    setIsSaving(true)

    try {
      let secretReference = null;
      
      // If a private key was uploaded, securely transfer it to the FastAPI backend -> Secret Manager
      if (newClient.private_key) {
        const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
        const res = await fetch(`${backendUrl}/api/secrets`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            client_id: newClient.client_id,
            private_key: newClient.private_key
          })
        });
        
        if (!res.ok) throw new Error("Failed to store SSH Key in Secret Manager");
        
        const data = await res.json();
        secretReference = data.secret_version; // e.g. projects/123/secrets/ssh-key-amllab/versions/1
      }

      // Save everything else to Firestore, referencing only the Secret Name, NEVER the raw key
      await addDoc(collection(db, 'clients'), {
        name: newClient.client_name,
        client_id: newClient.client_id,
        ip_address: newClient.ip_address,
        ssh_username: newClient.ssh_username,
        ssh_secret_ref: secretReference, // <--- The secure GSM reference!
        alert_email: newClient.alert_email,
        shuffle_api_key: newClient.shuffle_api_key,
        cloudflare_token: newClient.cloudflare_token,
        cloudflare_zone: newClient.cloudflare_zone,
        created_at: serverTimestamp(),
        owner_email: user.email
      })
      
      setNewClient({ 
        client_name: '', client_id: '', ip_address: '', ssh_username: '', private_key: '', 
        alert_email: '', shuffle_api_key: '', cloudflare_token: '', cloudflare_zone: '' 
      })
      setShowModal(false)
    } catch (error) {
      alert("Error saving client: " + error.message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this client?')) {
      await deleteDoc(doc(db, 'clients', id))
    }
  }

  return (
    <div className="min-h-screen bg-obsidian text-gray-200 font-sans flex flex-col relative overflow-hidden">
      
      {/* Background Glows */}
      <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-violet-glow blur-[150px] rounded-full opacity-20 pointer-events-none"></div>

      {/* Navbar */}
      <nav className="bg-matte/80 backdrop-blur-md border-b border-white/5 px-8 py-5 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-obsidian border border-white/10 flex items-center justify-center shadow-[0_0_15px_rgba(138,43,226,0.3)]">
            <ShieldAlert className="text-violet w-5 h-5" />
          </div>
          <div>
            <h1 className="font-extrabold text-xl text-white tracking-tight leading-tight">AML SIEM</h1>
            <p className="text-xs text-gray-500 font-semibold tracking-wider uppercase">Client Management</p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <span className="text-xs font-semibold text-gray-400">{user.email}</span>
          <button onClick={() => signOut(auth)} className="w-10 h-10 rounded-full bg-obsidian border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:border-white/20 transition-all">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 p-8 max-w-[1400px] mx-auto w-full relative z-10">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-white tracking-tight">Active Deployments</h2>
          <button 
            onClick={handleAddNewClient}
            className="px-5 py-2.5 bg-violet hover:bg-violet-hover text-white rounded-full font-bold text-sm tracking-wide flex items-center gap-2 transition-all shadow-[0_0_20px_var(--color-violet-glow)] hover:shadow-[0_0_30px_var(--color-violet-glow)] transform hover:-translate-y-0.5"
          >
            <Plus className="w-4 h-4" /> Add Client
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {clients.map(client => (
            <div 
              key={client.id}
              onClick={() => navigate(`/client/${client.id}`)}
              className="bg-matte rounded-[24px] border border-white/5 p-6 shadow-xl hover:border-violet/50 hover:shadow-[0_0_30px_var(--color-violet-glow)] transition-all cursor-pointer group flex flex-col relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-violet/5 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none transition-all group-hover:bg-violet/20"></div>
              
              <div className="flex justify-between items-start mb-6 relative z-10">
                <div className="w-12 h-12 rounded-full bg-obsidian border border-white/10 flex items-center justify-center">
                  <Server className="w-6 h-6 text-lime" />
                </div>
                <button 
                  onClick={(e) => handleDelete(e, client.id)}
                  className="p-2 text-gray-600 hover:text-red-500 hover:bg-red-500/10 rounded-full transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              
              <div className="relative z-10">
                <h3 className="text-lg font-bold text-white mb-1 truncate">{client.client_id || client.name}</h3>
                <p className="text-sm font-medium text-gray-500 mb-6 font-mono">{client.ip_address}</p>
              </div>
              
              <div className="mt-auto flex items-center justify-between pt-4 border-t border-white/5 relative z-10">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Manage SIEM</span>
                <ArrowRight className="w-4 h-4 text-violet group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          ))}
        </div>

        {clients.length === 0 && (
          <div className="text-center py-20 bg-matte/50 rounded-[24px] border border-white/5 border-dashed">
            <Server className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-400 font-medium">No clients configured yet.</p>
          </div>
        )}
      </main>

      {/* Add Client Modal */}
      {showModal && (
        <div className="fixed inset-0 z-[100] overflow-y-auto">
          <div className="min-h-screen px-4 flex items-center justify-center py-12">
            <div 
              className="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity" 
              onClick={() => setShowModal(false)}
            ></div>
            <div className="relative bg-matte rounded-[24px] border border-white/10 p-8 w-full max-w-2xl shadow-2xl z-10">
              <h2 className="text-xl font-bold text-white mb-6">Register New Client</h2>
            
            <form onSubmit={handleAddClient} className="space-y-6">
              
              {/* Primary Config */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Client Name</label>
                  <input 
                    type="text" required autoFocus
                    className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                    value={newClient.client_name}
                    onChange={(e) => setNewClient({ ...newClient, client_name: e.target.value })}
                    placeholder="InfosecFoster Lab"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Client ID</label>
                  <input 
                    type="text" required
                    className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                    value={newClient.client_id}
                    onChange={(e) => setNewClient({ ...newClient, client_id: e.target.value })}
                    placeholder="aml-lab"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">IP Address / Host</label>
                  <input 
                    type="text" required
                    className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white font-mono focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                    value={newClient.ip_address}
                    onChange={(e) => setNewClient({ ...newClient, ip_address: e.target.value })}
                    placeholder="104.198.8.20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">SSH Username</label>
                  <input 
                    type="text" required
                    className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                    value={newClient.ssh_username}
                    onChange={(e) => setNewClient({ ...newClient, ssh_username: e.target.value })}
                    placeholder="amlak-siem-admin"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Alert Email</label>
                  <input 
                    type="email"
                    className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                    value={newClient.alert_email}
                    onChange={(e) => setNewClient({ ...newClient, alert_email: e.target.value })}
                    placeholder="sheikhsanath12@gmail.com"
                  />
                </div>
              </div>

              {/* SSH Key Upload */}
              <div className="bg-obsidian/50 p-4 rounded-[16px] border border-white/5">
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1 flex items-center gap-2">
                  <Key className="w-3.5 h-3.5" /> SSH Private Key
                </label>
                <div className="flex items-center gap-4">
                  <input 
                    type="file"
                    onChange={handleFileUpload}
                    className="flex-1 text-sm text-gray-500 file:mr-4 file:py-2.5 file:px-5 file:rounded-full file:border-0 file:text-xs file:font-bold file:uppercase file:tracking-wider file:bg-matte file:text-gray-300 hover:file:bg-white/5 hover:file:text-white transition-all cursor-pointer bg-obsidian border border-white/5 rounded-[12px] py-1.5 px-2"
                  />
                  {newClient.private_key && (
                    <span className="text-xs text-lime font-medium px-3 py-1 bg-lime/10 rounded-full border border-lime/20 whitespace-nowrap">
                      Ready to Encrypt
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-gray-500 mt-2 ml-1">
                  Your raw private key will be sent securely to Google Secret Manager and wiped from browser memory. It will never be stored in the database.
                </p>
              </div>

              {/* API Keys */}
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Shuffle API Key (Optional)</label>
                <input 
                  type="password"
                  className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all"
                  value={newClient.shuffle_api_key}
                  onChange={(e) => setNewClient({ ...newClient, shuffle_api_key: e.target.value })}
                />
              </div>

              {/* Cloudflare Section */}
              <div className="border-t border-white/5 pt-5">
                <h3 className="text-sm font-bold text-white mb-4">Cloudflare API (Optional)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">API Token</label>
                    <input 
                      type="password"
                      className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                      value={newClient.cloudflare_token}
                      onChange={(e) => setNewClient({ ...newClient, cloudflare_token: e.target.value })}
                      placeholder="cfut_C7vOHs..."
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Zone ID</label>
                    <input 
                      type="text"
                      className="w-full px-4 py-3 bg-obsidian border border-white/10 rounded-[12px] text-white font-mono focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-700"
                      value={newClient.cloudflare_zone}
                      onChange={(e) => setNewClient({ ...newClient, cloudflare_zone: e.target.value })}
                      placeholder="717dadb849..."
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-4 pt-4">
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={isSaving}
                  className="flex-1 py-4 bg-obsidian hover:bg-white/5 border border-white/5 text-gray-300 font-bold rounded-full transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isSaving}
                  className="flex-1 py-4 bg-violet hover:bg-violet-hover text-white font-bold rounded-full transition-colors shadow-[0_0_20px_var(--color-violet-glow)] disabled:opacity-50 flex items-center justify-center"
                >
                  {isSaving ? 'Encrypting & Saving...' : 'Save Configuration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
      )}
    </div>
  )
}
