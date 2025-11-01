import { DocFile, DocNav, DocMetadata } from "./types";

// simple frontmatter parser for browser (gray-matter uses Buffer which doesn't exist in browser)
function parseFrontmatter(text: string): { data: Record<string, any>; content: string } {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/;
  const match = text.match(frontmatterRegex);

  if (!match) {
    return { data: {}, content: text };
  }

  const [, frontmatter, content] = match;
  const data: Record<string, any> = {};

  // parse simple yaml (key: value pairs)
  frontmatter.split("\n").forEach((line) => {
    const colonIndex = line.indexOf(":");
    if (colonIndex > 0) {
      const key = line.slice(0, colonIndex).trim();
      const value = line.slice(colonIndex + 1).trim();
      data[key] = value;
    }
  });

  return { data, content: content.trim() };
}

// fetch markdown file from public directory
export async function fetchDoc(slug: string): Promise<DocFile | null> {
  // validate slug against whitelist
  if (!isValidSlug(slug)) {
    return null;
  }

  try {
    const base = import.meta.env.BASE_URL;
    const url = `${base}docs/${slug}.md`;
    const response = await fetch(url);

    if (!response.ok) {
      return null;
    }

    const text = await response.text();
    const { data, content } = parseFrontmatter(text);

    return {
      slug,
      title: data.title || slugToTitle(slug),
      content,
      metadata: data as DocMetadata,
    };
  } catch {
    return null;
  }
}

// valid documentation slugs (whitelist)
export const VALID_DOC_SLUGS = [
  "overview",
  "how_to_use",
  "templates",
  "how_to_create_blocks",
  "DEVELOPERS",
  "CONTRIBUTING",
  "CHANGELOG",
  "MARKDOWN_STYLE_GUIDE",
];

// check if slug is valid
export function isValidSlug(slug: string): boolean {
  return VALID_DOC_SLUGS.includes(slug);
}

// get list of available docs for navigation
export async function getDocsNav(): Promise<DocNav[]> {
  const docs = [
    { slug: "overview", title: "Overview", order: 0 },
    { slug: "how_to_use", title: "How to Use", order: 1 },
    { slug: "templates", title: "Pipeline Templates", order: 2 },
    { slug: "how_to_create_blocks", title: "Create Custom Blocks", order: 3 },
    { slug: "DEVELOPERS", title: "Developer Guide", order: 4 },
    { slug: "CONTRIBUTING", title: "Contributing", order: 5 },
    { slug: "CHANGELOG", title: "Changelog", order: 6 },
    { slug: "MARKDOWN_STYLE_GUIDE", title: "Markdown Style Guide", order: 7 },
  ];

  return docs;
}

// convert slug to readable title
export function slugToTitle(slug: string): string {
  return slug
    .replace(/-/g, " ")
    .replace(/_/g, " ")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

// convert title to slug
export function titleToSlug(title: string): string {
  return title
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
}
