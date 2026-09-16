import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { onAuthStateChanged } from 'firebase/auth'
import { auth } from './firebase'
import { ErrorBoundary } from './components/ErrorBoundary'

import Login from './components/Login'
import Dashboard from './components/Dashboard'
import ClientList from './components/ClientList'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser)
      setLoading(false)
    })
    return () => unsubscribe()
  }, [])

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-[#0D0D0E] text-white">Loading...</div>
  }

  return (
    <ErrorBoundary>
    <BrowserRouter>
      <Routes>
        <Route 
          path="/login" 
          element={!user ? <Login /> : <Navigate to="/" />} 
        />
        <Route 
          path="/" 
          element={user ? <ClientList user={user} /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/client/:id" 
          element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} 
        />
      </Routes>
    </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
