import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import Landing from './pages/Landing'
import Docs from './pages/Docs'

function RedirectHandler() {
  const navigate = useNavigate()
  
  useEffect(() => {
    // handle redirect from 404.html
    const params = new URLSearchParams(window.location.search)
    const redirect = params.get('redirect')
    
    if (redirect) {
      // remove the redirect parameter and navigate to the intended path
      window.history.replaceState({}, '', window.location.pathname)
      navigate(redirect, { replace: true })
    }
  }, [navigate])
  
  return null
}

function App() {
  const basename = import.meta.env.BASE_URL
  
  return (
    <Router basename={basename}>
      <RedirectHandler />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/docs/*" element={<Docs />} />
      </Routes>
    </Router>
  )
}

export default App
