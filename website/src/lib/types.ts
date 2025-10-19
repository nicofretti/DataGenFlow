export interface DocMetadata {
  title: string
  description?: string
  order?: number
}

export interface DocFile {
  slug: string
  title: string
  content: string
  metadata: DocMetadata
}

export interface DocNav {
  title: string
  slug: string
  order: number
}
