# Q&A Generation Template

## Overview

**Complexity:** Advanced (4 blocks with multiplier)
**Use Case:** Generate question-answer pairs from markdown documents

This template converts markdown documentation into question-answer pairs. It automatically chunks long documents and generates 3-5 comprehension questions with answers for each chunk.

**Special Feature:** Supports markdown file upload in the UI. One file can generate multiple Q&A records through automatic chunking.

## Pipeline Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Markdown   │──►│     Text     │──►│  Structured  │──►│     JSON     │
│  Multiplier  │   │  Generator   │   │  Generator   │   │  Validator   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘

Input: file_content
  ↓
+ chunk_text (multiplies: 1 file → N chunks)
  ↓
+ assistant (questions)
  ↓
+ generated (qa_pairs array)
  ↓
+ valid, parsed_json
```

**Blocks:**
1. **MarkdownMultiplierBlock** - Chunks markdown into processable sections (512 tokens, no overlap)
2. **TextGenerator** - Generates 3-5 comprehension questions per chunk
3. **StructuredGenerator** - Answers questions based strictly on chunk content
4. **JSONValidatorBlock** - Validates Q&A structure

**Key Concept:** The multiplier block returns a list, so 1 seed with 2 repetitions and 5 chunks creates **10 records** (1 × 2 × 5).

## Seed Format

⚠️ **Important:** This template uses `file_content` (not `content`).

**Single markdown file:**
```json
{
  "repetitions": 2,
  "metadata": {
    "file_content": "# Python Basics\n\nPython is a high-level programming language...\n\n## Variables\n\nVariables store data values..."
  }
}
```

**Typical workflow:**
1. Upload a `.md` file in the UI (the MarkdownMultiplierBlock handles this)
2. Set repetitions (how many times to process each chunk)
3. Generate - creates multiple records from one file

## Output Format

**Schema:**
```json
{
  "qa_pairs": [
    {
      "question": "string - comprehension question",
      "answer": "string - answer based on content"
    }
  ]
}
```

**Example output (from one chunk):**
```json
{
  "qa_pairs": [
    {
      "question": "What is photosynthesis?",
      "answer": "Photosynthesis is the process by which plants convert sunlight into energy using chlorophyll."
    },
    {
      "question": "What role does chlorophyll play in photosynthesis?",
      "answer": "Chlorophyll in leaves absorbs light, which triggers chemical reactions that produce glucose."
    },
    {
      "question": "What is the end product of photosynthesis?",
      "answer": "The end product of photosynthesis is glucose."
    }
  ]
}
```

## Use Cases

**Perfect for:**
- Converting technical documentation to training datasets
- Creating educational Q&A from tutorials
- Building comprehension tests from long articles
- Processing multi-section markdown documents efficiently

**Not ideal for:**
- Short single-paragraph text (use simpler templates)
- Non-markdown formats (requires preprocessing)
- Open-ended questions (this generates factual Q&A)

## Markdown File Upload Feature

The MarkdownMultiplierBlock is a **seeder block** that enables markdown file upload:

1. Navigate to Generator page
2. Click "Choose File" and select a `.md` file
3. The block automatically:
   - Parses markdown structure (headers, sections)
   - Chunks by size (512 tokens default)
   - Creates one record per chunk

**Result:** 1 uploaded file → Multiple Q&A records (one per chunk)

## Customization

Modify the template in `lib/templates/qa_generation.yaml`:

**Adjust chunk size:**
```yaml
blocks:
  - type: MarkdownMultiplierBlock
    config:
      chunk_size: 1024  # Larger chunks
      chunk_overlap: 50 # Add overlap for context
```

**Change number of questions:**
```yaml
# In StructuredGenerator json_schema:
minItems: 5  # Minimum 5 questions
maxItems: 10 # Maximum 10 questions
```

**Modify question style:**
```yaml
# In TextGenerator system_prompt:
system_prompt: |
  Generate analytical questions that require critical thinking about the text.
```

**Adjust answer detail level:**
```yaml
# In StructuredGenerator user_prompt:
user_prompt: |
  Provide detailed answers with examples from the content.
```

## Example Workflow

**Input:** Technical documentation file (5000 words)

**Processing:**
1. MarkdownMultiplierBlock splits into ~10 chunks
2. Set repetitions = 2
3. Total records created: 10 chunks × 2 reps = **20 Q&A records**

**Output:** 20 records, each with 3-5 question-answer pairs

## Performance Tips

- **Large files:** Increase chunk_size to reduce number of chunks
- **More coverage:** Add chunk_overlap (e.g., 50 tokens)
- **Quality control:** Review first few generated records before processing entire file
- **Repetitions:** Use 1-2 for variety without duplication

## Related Documentation

- [Templates Overview](templates) - All available templates
- [How to Use](how_to_use) - Running pipelines with templates
- [Custom Blocks](how_to_create_blocks) - Understanding multiplier blocks
