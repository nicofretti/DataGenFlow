import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Docs from './pages/Docs'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/docs/*" element={<Docs />} />
      </Routes>
    </Router>
  )
}

export default App
