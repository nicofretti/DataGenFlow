import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Box, Header, Avatar, Text } from '@primer/react'
import Generator from './pages/Generator'
import Review from './pages/Review'

export default function App() {
  return (
    <BrowserRouter>
      <Box sx={{ minHeight: '100vh', bg: 'canvas.default' }}>
        <Header sx={{ px: 3, py: 2 }}>
          <Header.Item>
            <Header.Link as={Link} to="/" sx={{ fontSize: 2, fontWeight: 'bold' }}>
              <Avatar size={24} src="https://github.com/primer.png" sx={{ mr: 2 }} />
              <Text>QADataGen</Text>
            </Header.Link>
          </Header.Item>
          <Header.Item full></Header.Item>
          <Header.Item>
            <Header.Link as={Link} to="/">Generator</Header.Link>
          </Header.Item>
          <Header.Item>
            <Header.Link as={Link} to="/review">Review</Header.Link>
          </Header.Item>
        </Header>

        <Box sx={{ maxWidth: 1280, mx: 'auto', p: 4 }}>
          <Routes>
            <Route path="/" element={<Generator />} />
            <Route path="/review" element={<Review />} />
          </Routes>
        </Box>
      </Box>
    </BrowserRouter>
  )
}
