import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import Button from './Button'

export default function Header() {
  const location = useLocation()
  const isDocsPage = location.pathname.startsWith('/docs')
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-gray-800">
      <nav className="container-custom py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <img
              src={`${import.meta.env.BASE_URL}images/logo/logo_name_empty.svg`}
              alt="DataGenFlow Logo"
              className="h-8"
            />
          </Link>

          {/* desktop navigation */}
          <div className="hidden md:flex items-center space-x-6">
            <Link
              to="/docs/overview"
              className={`text-sm hover:text-primary transition-colors ${
                isDocsPage ? 'text-primary' : 'text-gray-300'
              }`}
            >
              Documentation
            </Link>

            <Link
              to="/docs/CHANGELOG"
              className="text-sm text-gray-300 hover:text-primary transition-colors"
            >
              Changelog
            </Link>

            <a
              href="https://github.com/nicofretti/DataGenFlow"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-300 hover:text-primary transition-colors"
            >
              GitHub
            </a>

            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                const element = document.getElementById('quick-start')
                element?.scrollIntoView({ behavior: 'smooth' })
              }}
            >
              Get Started
            </Button>
          </div>

          {/* mobile menu button */}
          <button
            className="md:hidden text-gray-300 hover:text-primary transition-colors"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {isMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* mobile navigation */}
        {isMenuOpen && (
          <div className="md:hidden mt-4 pb-4 space-y-4 border-t border-gray-800 pt-4">
            <Link
              to="/docs/overview"
              className={`block text-sm hover:text-primary transition-colors ${
                isDocsPage ? 'text-primary' : 'text-gray-300'
              }`}
              onClick={() => setIsMenuOpen(false)}
            >
              Documentation
            </Link>

            <Link
              to="/docs/CHANGELOG"
              className="block text-sm text-gray-300 hover:text-primary transition-colors"
              onClick={() => setIsMenuOpen(false)}
            >
              Changelog
            </Link>

            <a
              href="https://github.com/nicofretti/DataGenFlow"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-sm text-gray-300 hover:text-primary transition-colors"
            >
              GitHub
            </a>

            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                const element = document.getElementById('quick-start')
                element?.scrollIntoView({ behavior: 'smooth' })
                setIsMenuOpen(false)
              }}
              className="w-full"
            >
              Get Started
            </Button>
          </div>
        )}
      </nav>
    </header>
  )
}
