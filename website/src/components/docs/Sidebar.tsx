import { Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getDocsNav } from '@/lib/docs'
import { DocNav } from '@/lib/types'

export default function Sidebar() {
  const [docs, setDocs] = useState<DocNav[]>([])
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    getDocsNav().then(setDocs)
  }, [])

  useEffect(() => {
    setIsMenuOpen(false)
  }, [location.pathname])

  const currentSlug = location.pathname.replace('/docs/', '')
  const currentDoc = docs.find(doc => doc.slug === currentSlug)

  return (
    <>
      {/* mobile menu button */}
      <div className="lg:hidden fixed left-0 right-0 z-40 bg-background border-b border-gray-800">
        <div className="flex items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center">
            <img
              src={`${import.meta.env.BASE_URL}images/logo/logo_name_empty.svg`}
              alt="DataGenFlow"
              className="h-8"
            />
          </Link>
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="flex items-center gap-2 text-gray-300 hover:text-primary transition-colors"
          >
            <span className="text-sm font-medium">
              {currentDoc?.title || 'Documentation'}
            </span>
            <svg
              className={`w-5 h-5 transition-transform ${isMenuOpen ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {isMenuOpen && (
          <div className="border-t border-gray-800 bg-background-dark max-h-96 overflow-y-auto">
            <nav className="p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
                Documentation
              </h3>
              <ul className="space-y-1">
                {docs.map((doc) => {
                  const isActive = currentSlug === doc.slug

                  return (
                    <li key={doc.slug}>
                      <Link
                        to={`/docs/${doc.slug}`}
                        className={`block px-3 py-2.5 rounded-lg text-sm transition-all ${
                          isActive
                            ? 'bg-primary/20 text-primary font-semibold border-l-2 border-primary pl-3'
                            : 'text-gray-400 hover:text-white hover:bg-gray-800/50 border-l-2 border-transparent hover:border-gray-700 pl-3'
                        }`}
                      >
                        {doc.title}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </nav>
          </div>
        )}
      </div>

      {/* desktop sidebar */}
      <aside className="w-64 border-r border-gray-800 h-screen sticky top-0 overflow-y-auto bg-background-dark hidden lg:block">
        <div className="p-6">
          <Link to="/" className="flex items-center mb-10 group">
            <img
              src={`${import.meta.env.BASE_URL}images/logo/logo_name_empty.svg`}
              alt="DataGenFlow"
              className="h-8 w-full transition-opacity group-hover:opacity-80"
            />
          </Link>

          <nav>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4 px-3">
              Documentation
            </h3>

            <ul className="space-y-1">
              {docs.map((doc) => {
                const isActive = currentSlug === doc.slug

                return (
                  <li key={doc.slug}>
                    <Link
                      to={`/docs/${doc.slug}`}
                      className={`block px-3 py-2.5 rounded-lg text-sm transition-all ${
                        isActive
                          ? 'bg-primary/20 text-primary font-semibold border-l-2 border-primary pl-3'
                          : 'text-gray-400 hover:text-white hover:bg-gray-800/50 border-l-2 border-transparent hover:border-gray-700 pl-3'
                      }`}
                    >
                      {doc.title}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </nav>

          <div className="mt-8 pt-6 border-t border-gray-800">
            <a
              href="https://github.com/nicofretti/DataGenFlow"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-primary transition-colors"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              <span>View on GitHub</span>
            </a>
          </div>
        </div>
      </aside>
    </>
  )
}
