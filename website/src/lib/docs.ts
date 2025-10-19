import { DocFile, DocNav, DocMetadata } from './types'

// simple frontmatter parser for browser (gray-matter uses Buffer which doesn't exist in browser)
function parseFrontmatter(text: string): { data: Record<string, any>; content: string } {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/
  const match = text.match(frontmatterRegex)

  if (!match) {
    return { data: {}, content: text }
  }

  const [, frontmatter, content] = match
  const data: Record<string, any> = {}

  // parse simple yaml (key: value pairs)
  frontmatter.split('\n').forEach(line => {
    const colonIndex = line.indexOf(':')
    if (colonIndex > 0) {
      const key = line.slice(0, colonIndex).trim()
      const value = line.slice(colonIndex + 1).trim()
      data[key] = value
    }
  })

  return { data, content: content.trim() }
}

// fetch markdown file from public directory
export async function fetchDoc(slug: string): Promise<DocFile | null> {
  // validate slug against whitelist
  if (!isValidSlug(slug)) {
    console.warn(`Invalid doc slug: ${slug}`)
    return null
  }

  try {
    const url = `/docs/${slug}.md`
    console.log('Fetching doc from:', url)
    const response = await fetch(url)
    console.log('Response status:', response.status, response.statusText)

    if (!response.ok) {
      console.error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`)
      return null
    }

    const text = await response.text()
    console.log('Fetched text length:', text.length)
    const { data, content } = parseFrontmatter(text)

    return {
      slug,
      title: data.title || slugToTitle(slug),
      content,
      metadata: data as DocMetadata
    }
  } catch (error) {
    console.error(`Error fetching doc: ${slug}`, error)
    return null
  }
}

// valid documentation slugs (whitelist)
export const VALID_DOC_SLUGS = [
  'overview',
  'how_to_use',
  'how_to_create_blocks',
  'DEVELOPERS',
  'CONTRIBUTING',
  'MARKDOWN_STYLE_GUIDE',
]

// check if slug is valid
export function isValidSlug(slug: string): boolean {
  return VALID_DOC_SLUGS.includes(slug)
}

// get list of available docs for navigation
export async function getDocsNav(): Promise<DocNav[]> {
  const docs = [
    { slug: 'overview', title: 'Overview', order: 0 },
    { slug: 'how_to_use', title: 'How to Use', order: 1 },
    { slug: 'how_to_create_blocks', title: 'Create Custom Blocks', order: 2 },
    { slug: 'DEVELOPERS', title: 'Developer Guide', order: 3 },
    { slug: 'CONTRIBUTING', title: 'Contributing', order: 4 },
    { slug: 'MARKDOWN_STYLE_GUIDE', title: 'Markdown Style Guide', order: 5 },
  ]

  return docs
}

// convert slug to readable title
export function slugToTitle(slug: string): string {
  return slug
    .replace(/-/g, ' ')
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

// convert title to slug
export function titleToSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}
