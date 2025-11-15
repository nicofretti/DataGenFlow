# UI Message Format Standard

## Principles

1. **User-focused**: Tell users what happened and what it means for them
2. **Consistent**: Same format across all messages
3. **Clear**: No jargon, plain language
4. **Actionable**: Explain next steps when needed

## Format Rules

### Success Messages
- **Format**: "Action completed successfully" or "Resource action"
- **Capitalization**: First word capitalized
- **Punctuation**: No ending period
- **Examples**:
  - "Pipeline created successfully"
  - "Records deleted successfully"
  - "Configuration saved successfully"
  - "LLM model deleted successfully"

### Error Messages
- **Format**: "Failed to action: detail" or "Failed to action"
- **Capitalization**: First word capitalized
- **Punctuation**: No ending period
- **Include context**: What failed and why (if known)
- **Examples**:
  - "Failed to load pipelines: Network error"
  - "Failed to delete records: Permission denied"
  - "Failed to save configuration: Invalid field order"

### Warning Messages
- **Format**: "Warning about issue" with emoji optional
- **Capitalization**: First word capitalized
- **Punctuation**: No ending period
- **Examples**:
  - "Pipeline has validation warnings"
  - "File size exceeds recommended limit"

### Info Messages
- **Format**: "Informative statement"
- **Capitalization**: First word capitalized
- **Punctuation**: No ending period
- **Examples**:
  - "All seeds validated successfully"
  - "Connection test successful (45ms)"
  - "Copied to clipboard"

## Anti-Patterns

❌ **Don't**:
- Lowercase start: "failed to load" → "Failed to load"
- Generic errors: "Error: something" → "Failed to something: detail"
- Inconsistent caps: "connection successful" → "Connection successful"
- Periods at end: "Pipeline created." → "Pipeline created successfully"
- Technical jargon without context: "HTTP 500" → "Failed to load: Server error"

✅ **Do**:
- Start with capital letter
- Use active voice
- Be specific about what failed/succeeded
- Include helpful error details when available
- Maintain consistent format across all messages
