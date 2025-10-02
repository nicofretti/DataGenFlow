import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Box, IconButton, ThemeProvider, useTheme, Heading, Text } from '@primer/react'
import { SunIcon, MoonIcon, BeakerIcon, ChecklistIcon } from '@primer/octicons-react'
import Generator from './pages/Generator'
import Review from './pages/Review'

function Navigation() {
  const location = useLocation()
  const { resolvedColorScheme, setColorMode } = useTheme()
  const isDark = resolvedColorScheme === 'dark'

  const navItems = [
    { path: '/', label: 'Generator', icon: BeakerIcon },
    { path: '/review', label: 'Review', icon: ChecklistIcon },
  ]

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* left sidebar */}
      <Box
        sx={{
          width: 240,
          borderRight: '1px solid',
          borderColor: 'border.default',
          bg: 'canvas.subtle',
          display: 'flex',
          flexDirection: 'column',
          position: 'fixed',
          height: '100vh',
          overflowY: 'auto',
        }}
      >
        {/* brand */}
        <Box sx={{ p: 4, borderBottom: '1px solid', borderColor: 'border.default' }}>
          <Heading sx={{ fontSize: 3, mb: 1 }}>QADataGen</Heading>
          <Text sx={{ fontSize: 1, color: 'fg.muted' }}>Dataset Generation</Text>
        </Box>

        {/* navigation links */}
        <Box sx={{ flex: 1, p: 3 }}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <Box
                key={item.path}
                as={Link}
                to={item.path}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                  p: 2,
                  mb: 1,
                  borderRadius: 2,
                  textDecoration: 'none',
                  color: isActive ? 'fg.default' : 'fg.muted',
                  bg: isActive ? 'accent.subtle' : 'transparent',
                  fontWeight: isActive ? 'bold' : 'normal',
                  '&:hover': {
                    bg: isActive ? 'accent.subtle' : 'neutral.subtle',
                  },
                  transition: 'all 0.2s',
                }}
              >
                <item.icon size={20} />
                <Text sx={{ fontSize: 2 }}>{item.label}</Text>
              </Box>
            )
          })}
        </Box>

        {/* theme toggle at bottom */}
        <Box sx={{ p: 3, borderTop: '1px solid', borderColor: 'border.default' }}>
          <IconButton
            icon={isDark ? SunIcon : MoonIcon}
            aria-label="Toggle theme"
            onClick={() => setColorMode(isDark ? 'light' : 'dark')}
            variant="invisible"
            size="large"
            sx={{ width: '100%' }}
          />
        </Box>
      </Box>

      {/* main content */}
      <Box sx={{ flex: 1, ml: '240px', p: 4, bg: 'canvas.default' }}>
        <Box sx={{ maxWidth: 1280, mx: 'auto' }}>
          <Routes>
            <Route path="/" element={<Generator />} />
            <Route path="/review" element={<Review />} />
          </Routes>
        </Box>
      </Box>
    </Box>
  )
}

export default function App() {
  const [colorMode, setColorMode] = useState<'light' | 'dark'>('light')

  return (
    <ThemeProvider colorMode={colorMode}>
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    </ThemeProvider>
  )
}
