import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { collection, query, orderBy, onSnapshot, addDoc, serverTimestamp, deleteDoc, doc } from 'firebase/firestore'
import { db } from '../firebase'
import { ArrowLeft, Key, LayoutDashboard, Upload, Trash2, FileJson } from 'lucide-react'

export default function Settings({ user }) {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('Secret Keys')
  const [templates, setTemplates] = useState([])
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    const q = query(collection(db, 'shuffle_templates'), orderBy('created_at', 'desc'))
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const data = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }))
      setTemplates(data)
    })
    return () => unsubscribe()
  }, [])

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setIsUploading(true)
    try {
      const text = await file.text()
      const json = JSON.parse(text)
      
      // Shuffle exports usually have a "name" and "description" at the root level, but it depends on the export format.
      // We will just use the filename if missing, and store the raw object.
      let templateName = json.name || file.name.replace('.json', '')
      let description = json.description || 'Uploaded Shuffle Playbook'

      await addDoc(collection(db, 'shuffle_templates'), {
        name: templateName,
        description: description,
        filename: file.name,
        json: json,
        created_at: serverTimestamp(),
        uploaded_by: user.email
      })
      
      e.target.value = '' // Reset input
    } catch (err) {
      console.error(err)
      alert('Failed to parse JSON or upload template. Ensure it is a valid JSON file.')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDeleteTemplate = async (id) => {
    if (confirm('Are you sure you want to delete this template?')) {
      await deleteDoc(doc(db, 'shuffle_templates', id))
    }
  }

  return (
    <div className="min-h-screen bg-[#0D0D0E] text-white font-sans selection:bg-sky-500/30">
      <nav className="border-b border-white/5 bg-black/50 backdrop-blur-xl px-8 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/')} 
            className="w-10 h-10 rounded-full bg-obsidian border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:border-white/20 transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 border border-violet-500/30 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(139,92,246,0.2)]">
              <Key className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-fuchsia-600">
                Global Settings
              </h1>
              <p className="text-[10px] text-gray-500 font-bold tracking-widest uppercase">Configuration & Assets</p>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-8 py-12">
        <div className="flex gap-4 mb-8 border-b border-white/10 pb-4">
          <button
            onClick={() => setActiveTab('Secret Keys')}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-bold uppercase tracking-widest transition-all ${
              activeTab === 'Secret Keys'
                ? 'bg-white/10 text-white border border-white/20'
                : 'text-gray-500 hover:text-white hover:bg-white/5'
            }`}
          >
            <Key className="w-4 h-4" /> Secret Keys
          </button>
          <button
            onClick={() => setActiveTab('Shuffle Templates')}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-bold uppercase tracking-widest transition-all ${
              activeTab === 'Shuffle Templates'
                ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30 shadow-[0_0_20px_rgba(139,92,246,0.15)]'
                : 'text-gray-500 hover:text-white hover:bg-white/5'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" /> Shuffle Templates
          </button>
        </div>

        {activeTab === 'Secret Keys' && (
          <div className="bg-obsidian border border-white/10 p-8 rounded-2xl">
            <h2 className="text-xl font-bold mb-4">Secret Keys Management</h2>
            <p className="text-gray-400 text-sm">
              Global secrets and API keys can be managed here. (Placeholder for future development)
            </p>
          </div>
        )}

        {activeTab === 'Shuffle Templates' && (
          <div className="space-y-6">
            <div className="bg-obsidian border border-white/10 p-8 rounded-2xl flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold mb-2">Upload Workflow Template</h2>
                <p className="text-gray-400 text-sm max-w-xl">
                  Upload exported Shuffle JSON workflow templates here. These templates will be available globally to import into any connected client's Shuffle instance.
                </p>
              </div>
              <div className="relative">
                <input 
                  type="file" 
                  accept=".json" 
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed" 
                />
                <button className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold text-sm tracking-wide transition-all ${isUploading ? 'bg-gray-600' : 'bg-violet-600 hover:bg-violet-500'} text-white shadow-lg`}>
                  <Upload className={`w-4 h-4 ${isUploading ? 'animate-bounce' : ''}`} />
                  {isUploading ? 'Uploading...' : 'Select JSON File'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {templates.length === 0 && (
                <div className="col-span-full py-12 text-center text-gray-500 border border-dashed border-white/10 rounded-2xl bg-black/20">
                  <FileJson className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  <p>No templates uploaded yet.</p>
                </div>
              )}
              {templates.map(template => (
                <div key={template.id} className="bg-obsidian border border-white/5 rounded-2xl p-6 relative group hover:border-violet-500/30 transition-all">
                  <button 
                    onClick={() => handleDeleteTemplate(template.id)}
                    className="absolute top-4 right-4 p-2 bg-red-500/10 text-red-400 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-red-500 hover:text-white"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <div className="w-10 h-10 bg-violet-500/20 rounded-lg flex items-center justify-center mb-4 border border-violet-500/30">
                    <FileJson className="w-5 h-5 text-violet-400" />
                  </div>
                  <h3 className="font-bold text-white mb-2 truncate" title={template.name}>{template.name}</h3>
                  <p className="text-xs text-gray-400 line-clamp-2 mb-4 h-8" title={template.description}>{template.description}</p>
                  
                  <div className="text-[10px] text-gray-500 font-mono bg-black/50 px-2 py-1 rounded border border-white/5 inline-block max-w-full truncate">
                    {template.filename}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
