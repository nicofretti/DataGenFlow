import { Link, useLocation } from 'react-router-dom'
import Button from './Button'

export default function Header() {
  const location = useLocation()
  const isDocsPage = location.pathname.startsWith('/docs')

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-gray-800">
      <nav className="container-custom py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <img
              src={`${import.meta.env.BASE_URL}images/logo/logo_name_empty.svg`}
              alt="DataGenFlow Logo"
              className="w-full h-8"
            />
          </Link>

          <div className="flex items-center space-x-6">
            <Link
              to="/docs/overview"
              className={`text-sm hover:text-primary transition-colors ${
                isDocsPage ? 'text-primary' : 'text-gray-300'
              }`}
            >
              Documentation
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
        </div>
      </nav>
    </header>
  )
}
