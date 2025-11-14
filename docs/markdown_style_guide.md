---
title: Markdown Style Guide
description: Guidelines for writing markdown documentation for DataGenFlow
---

# Markdown Style Guide

This guide defines the markdown formatting standards for DataGenFlow documentation to ensure consistent rendering.

## Table of Contents
- [Document Structure](#document-structure)
- [Code Blocks](#code-blocks)
- [Headings and Anchor Links](#headings-and-anchor-links)
- [Admonitions](#admonitions)
- [Links](#links)
- [Lists](#lists)
- [Tables](#tables)
- [Images](#images)
- [Formatting](#formatting)
- [Code Copy Feature](#code-copy-feature)

## Document Structure

### Frontmatter

Add YAML frontmatter at the top of the document for metadata, followed by an H1 title:

```markdown
---
title: Your Page Title
description: Brief description of the page
---

# Your Page Title

Your introduction paragraph here...

## Table of Contents
...
```

**Important:** Both frontmatter AND H1 title are required. The H1 should match the frontmatter title exactly.

### Page Organization

1. **H1 Title**: One per document (must match frontmatter title)
2. **Table of Contents**: For all docs except README.md (place after H1 and intro paragraph)
3. **H2 Sections**: Major topics
4. **H3 Subsections**: Subtopics within sections
5. **H4 and below**: Use sparingly for deep nesting

### Table of Contents Format

```markdown
## Table of Contents
- [Section Name](#section-name)
- [Another Section](#another-section)
  - [Subsection](#subsection)
```

## Code Blocks

### Required Format

**ALWAYS** specify the language and close code blocks properly:
````markdown
```language
code here
```
````

### Supported Languages

Use these language identifiers:
- `python` - Python code
- `bash` - Shell commands
- `javascript` or `typescript` - JS/TS code
- `json` - JSON data
- `yaml` - YAML configuration
- `text` - Plain text, ASCII art, or diagrams
- `sql` - SQL queries

### Examples

**Good:**

````markdown
```python
def hello():
    print("Hello, world!")
```
````

**Bad (missing language):**

````markdown
```
def hello():
    print("Hello, world!")
```
````

**Bad (not closed):**

````markdown
```python
def hello():
    print("Hello, world!")
````

### Inline Code

Use single backticks for inline code: `` `variable_name` ``

## Headings and Anchor Links

### Heading Levels

```markdown
## H2 Section
### H3 Subsection
#### H4 Minor heading
```

### Automatic Anchor IDs

Headings automatically generate anchor IDs:

- `## My Section` → `#my-section`
- `## API Reference` → `#api-reference`
- `## Block System Overview` → `#block-system-overview`

**Rules:**
- Lowercase only
- Spaces become hyphens
- Remove special characters (keep alphanumeric and hyphens)
- Examples:
  - `Development Setup` → `development-setup`
  - `Custom Blocks (Advanced)` → `custom-blocks-advanced`

### Linking to Sections

```markdown
[Jump to section](#section-name)
```

## Admonitions

Use styled blockquotes for callouts:

### Note (Informational)

```markdown
> **Note:** This is informational content that provides additional context.
```

### Warning (Caution)

```markdown
> **Warning:** This warns about potential issues or gotchas.
```

### Tip (Helpful Hint)

```markdown
> **Tip:** This provides a helpful suggestion or best practice.
```

### Multi-line Admonitions

```markdown
> **Note:** This is a longer note that spans multiple lines.
> You can continue on the next line by starting with `>`.
>
> Even add paragraphs within the admonition.
```

## Links

### External Links

```markdown
[Link text](https://example.com)
```

### Internal Documentation Links

```markdown
[Developer Guide](DEVELOPERS)
[How to Use](docs/how_to_use)
```

**Note:** No `.md` extension needed for doc links.

### Anchor Links (within page)

```markdown
[Go to section](#section-name)
```

## Lists

### Unordered Lists

```markdown
- Item one
- Item two
  - Nested item
  - Another nested item
- Item three
```

### Ordered Lists

```markdown
1. First step
2. Second step
3. Third step
```

### Task Lists (GitHub-flavored)

```markdown
- [x] Completed task
- [ ] Pending task
- [ ] Another pending task
```

## Tables

Use GitHub-flavored markdown tables:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |
```

**Alignment:**

```markdown
| Left | Center | Right |
|:-----|:------:|------:|
| A    | B      | C     |
```

## Images

### Basic Image

```markdown
![Alt text](path/to/image.png)
```

### Images from Repository

Images in `/images/` directory:

```markdown
![Logo](/images/logo/banner.png)
```

## Formatting

### Emphasis

```markdown
*italic* or _italic_
**bold** or __bold__
***bold italic*** or ___bold italic___
```

### Horizontal Rule

```markdown
---
```

### Blockquotes (non-admonition)

```markdown
> This is a regular blockquote
> without **Note:**/**Warning:**/**Tip:** prefix
```

### Strikethrough

```markdown
~~strikethrough text~~
```

## Code Copy Feature

All code blocks in the documentation automatically include a "Copy" button in the top-right corner. Users can click this button to copy the entire code block to their clipboard.

**This happens automatically** - you don't need to add anything special to your markdown. Just use proper code blocks with language specification:

```python
def example():
    print("This code block will have a copy button")
```

The copy button:
- Appears on hover in the top-right corner
- Shows "✓ Copied!" confirmation when clicked
- Resets after 2 seconds
- Only copies the code (not line numbers or syntax highlighting)

## Checklist for New Documentation

Before publishing documentation:

- [ ] Code blocks have language specified (python, bash, json, yaml, text, etc.)
- [ ] All code blocks are properly closed with ```
- [ ] Table of contents included (except README.md)
- [ ] Anchor links match heading IDs (lowercase, hyphens)
- [ ] Admonitions use **Note:**/**Warning:**/**Tip:** prefix
- [ ] External links open in new tab (automatic)
- [ ] Images use correct paths (/images/... for repo images)
- [ ] H1 title matches frontmatter title (both required)
- [ ] Headings follow logical hierarchy (H2 → H3 → H4, no skipping)

## Testing Your Markdown

1. Review your markdown file locally
2. Verify:
   - Table of contents links use correct anchor format
   - Code blocks have language identifiers
   - Admonitions use proper format (`> **Note:**`)
   - Internal links omit `.md` extension
   - Headings follow logical hierarchy

---

**Questions or Issues?**

If you encounter rendering issues not covered in this guide, please open an issue with:
- The markdown that's not rendering correctly
- Expected vs actual behavior
- Screenshot if applicable
