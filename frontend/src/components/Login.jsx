import { useState } from 'react'
import { signInWithEmailAndPassword } from 'firebase/auth'
import { auth } from '../firebase'
import { ShieldAlert } from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      await signInWithEmailAndPassword(auth, email, password)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 w-full flex items-center justify-center bg-obsidian text-gray-100 font-sans p-4 relative overflow-hidden">
      
      {/* Ambient background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-violet-glow blur-[120px] rounded-full opacity-40 pointer-events-none"></div>

      <div className="max-w-md w-full p-10 bg-matte rounded-[24px] border border-white/5 shadow-[0_0_60px_rgba(138,43,226,0.15)] relative z-10 backdrop-blur-xl">
        <div className="flex flex-col items-center mb-10">
          <div className="w-16 h-16 rounded-full bg-obsidian border border-white/10 flex items-center justify-center mb-6 shadow-[0_0_20px_rgba(57,255,20,0.1)]">
            <ShieldAlert className="w-8 h-8 text-lime" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2">AML SIEM</h1>
          <p className="text-gray-400 text-sm font-medium">Orchestrator Access</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-950/30 border border-red-500/20 rounded-2xl text-red-400 text-sm font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Email Address</label>
            <input 
              type="email" 
              required
              className="w-full px-5 py-4 bg-obsidian border border-white/10 rounded-[16px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-600"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@infosecfoster.com"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 ml-1">Password</label>
            <input 
              type="password" 
              required
              className="w-full px-5 py-4 bg-obsidian border border-white/10 rounded-[16px] text-white focus:ring-1 focus:ring-violet focus:border-violet outline-none transition-all placeholder:text-gray-600"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full mt-8 py-4 px-6 bg-violet hover:bg-violet-hover text-white font-bold rounded-full transition-all duration-300 shadow-[0_0_20px_var(--color-violet-glow)] hover:shadow-[0_0_30px_var(--color-violet-glow)] disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5"
          >
            {loading ? 'Authenticating...' : 'Secure Login'}
          </button>
        </form>
      </div>
    </div>
  )
}
