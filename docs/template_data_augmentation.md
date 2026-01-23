---
title: Data Augmentation Template
description: Generate synthetic records preserving statistical distributions from sample data
---

# Data Augmentation Template

## Table of Contents
- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Seed Format](#seed-format)
- [Output Format](#output-format)
- [How It Works](#how-it-works)
- [Use Cases](#use-cases)
- [Customization](#customization)
- [Filtering Duplicates](#filtering-duplicates)
- [Tuning Parameters](#tuning-parameters)
- [Common Issues](#common-issues)
- [Example Workflow](#example-workflow)
- [Related Documentation](#related-documentation)

## Overview

**Complexity:** Advanced (3 blocks with multiplier)
**Use Case:** Generate synthetic data that preserves statistical patterns from samples

This template creates realistic synthetic records from sample data while maintaining:
- Statistical distributions (e.g., "electronics" appears 50% of the time)
- Numeric range constraints (e.g., electronics prices $299-$899, furniture prices $199-$349)
- Semantic coherence (LLM-generated fields match context)
- Output diversity (duplicate detection via embeddings)

**Special Features:**
- Statistical sampling preserves distributions
- LLM-powered semantic field generation
- Embedding-based duplicate detection
- Supports field dependencies

## Pipeline Architecture

```text
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Structure  │──►│  Semantic   │──►│  Duplicate  │
│   Sampler   │   │  Infiller   │   │   Remover   │
└─────────────┘   └─────────────┘   └─────────────┘

Input: samples array
  ↓
+ category, _hints (multiplies: 1 seed → N skeletons)
  ↓
+ description, price (LLM-generated fields)
  ↓
+ is_duplicate, similarity_to_seeds, similarity_to_generated
```

**Blocks:**
1. **StructureSampler** - Learns distributions from samples, generates statistical skeletons
2. **SemanticInfiller** - Completes skeletons with LLM-generated semantic fields
3. **DuplicateRemover** - Filters similar records using embedding similarity

**Key Concept:** The StructureSampler is a multiplier block that generates N skeletons from one seed. Each skeleton flows through the remaining blocks to create one record.

## Seed Format

**Required fields:**
- `samples` - Array of example records (minimum 3 recommended)
- `target_count` - Number of synthetic records to generate
- `categorical_fields` - Fields to preserve distribution
- `fields_to_generate` - Fields for LLM to generate

**Optional fields:**
- `numeric_fields` - Numeric distributions to preserve
- `dependencies` - Field relationships (e.g., role depends on plan)
- `comparison_fields` - Fields for duplicate detection

**Example seed (Product Catalog):**
```json
[
  {
    "repetitions": 1,
    "metadata": {
      "samples": [
        {"category": "electronics", "price": 299, "description": "Wireless noise-canceling headphones with premium sound quality"},
        {"category": "electronics", "price": 899, "description": "13-inch laptop with high-resolution display"},
        {"category": "furniture", "price": 199, "description": "Ergonomic office chair with lumbar support"},
        {"category": "furniture", "price": 349, "description": "Adjustable standing desk with memory presets"}
      ],
      "target_count": 10,
      "categorical_fields": ["category"],
      "numeric_fields": ["price"],
      "fields_to_generate": ["description", "price"],
      "comparison_fields": ["description"]
    }
  }
]
```

**Field Explanations:**
- **`samples`** - Example products showing the data structure (4 samples provided)
- **`target_count`** - How many new products to generate (10 in this example)
- **`categorical_fields`** - Fields with discrete values that preserve distribution (50% electronics, 50% furniture)
- **`numeric_fields`** - Fields with numeric ranges that provide hints to the LLM (electronics: $299-$899, furniture: $199-$349)
- **`fields_to_generate`** - Fields for the LLM to create NEW content for (description and price)
- **`comparison_fields`** - Fields to check for duplicates using embedding similarity (description)

> **Note:** `price` appears in both `numeric_fields` and `fields_to_generate`. This provides range hints to guide the LLM while letting it generate contextually appropriate prices.
>
> **Tip:** Use 4-10 diverse samples for best results. More samples = better distribution learning.

## Output Format

The pipeline outputs a `generated_samples` array containing the final records.

Each generated record contains:
- Sampled categorical fields (preserving distribution)
- LLM-generated semantic fields
- Duplicate detection metadata

**Example output:**
```json
{
  "generated_samples": [
    {
      "category": "electronics",
      "price": 449,
      "description": "Bluetooth speaker with 360-degree sound and waterproof design",
      "is_duplicate": false,
      "similarity_to_seeds": 0.45,
      "similarity_to_generated": 0.42
    }
  ]
}
```

**Each record contains:**
- Sampled categorical fields (`category`)
- LLM-generated fields (`price`, `description`)
- Duplicate detection metadata:
  - `similarity_to_seeds`: highest similarity to original seed samples
  - `similarity_to_generated`: highest similarity to other generated records
  - `is_duplicate`: true if either similarity exceeds threshold

**Note:** Input configuration fields like `samples`, `target_count`, `categorical_fields`, etc. are NOT included in the output.

## How It Works

### Stage 1: StructureSampler (Statistical Skeleton Generation)

**What it does:**
- Analyzes sample data to learn categorical frequencies
- Computes numeric statistics (min, max, mean) for range hints
- Respects field dependencies (e.g., role depends on plan)
- Generates N skeletons respecting learned distributions

**Example:** If samples show "Free" plan 40% and "Pro" 30%, generated skeletons maintain these ratios.

**Output per skeleton:**
```json
{
  "category": "electronics",
  "_hints": {
    "price_range": [199.0, 899.0],
    "exemplars": [
      {"category": "electronics", "price": 299, "description": "Wireless headphones"},
      {"category": "electronics", "price": 899, "description": "13-inch laptop"}
    ]
  }
}
```

### Stage 2: SemanticInfiller (LLM-Powered Field Completion)

**What it does:**
- Receives skeleton with locked statistical fields
- Builds contextual prompt with numeric hints and exemplar examples
- Calls LLM to generate semantic fields (bio, description, etc.)
- Restores locked fields if LLM overwrites them

**Prompt structure:**
```text
You are a data generator. Complete the following record skeleton.

Skeleton: {category: "electronics"}

Numeric hints:
- price should be between 199-899

Matching examples:
- {category: "electronics", price: 299, description: "Wireless headphones"}

Generate: ["description", "price"]
Return JSON: {"description": "...", "price": ...}
```

**Locked fields behavior:** Categorical fields sampled by StructureSampler (e.g., `category`) are preserved even if the LLM tries to modify them.

### Stage 3: DuplicateRemover (Similarity Filtering)

**What it does:**
- Extracts text from comparison fields
- Generates embeddings via embedding model
- Computes cosine similarity with cached embeddings
- Marks records as duplicates if similarity > threshold

**Output:**
```json
{
  "category": "electronics",
  "price": 549,
  "description": "Portable bluetooth speaker with waterproof design",
  "is_duplicate": false,
  "similarity_to_seeds": 0.72,
  "similarity_to_generated": 0.45
}
```

**Output fields:**
- `similarity_to_seeds`: highest similarity to any original sample
- `similarity_to_generated`: highest similarity to previously generated records
- `is_duplicate`: true if either similarity exceeds threshold

> **Note:** DuplicateRemover gracefully degrades if embedding model is unavailable - marks all records as `is_duplicate: false` with similarity scores of 0.0.

## Use Cases

**Perfect for:**
- Expanding training datasets while maintaining patterns
- Creating realistic test data for applications
- Generating synthetic user profiles with distributions
- Data augmentation for ML training sets
- Privacy-preserving data generation (learn from real, generate synthetic)

**Not ideal for:**
- Time-series data (no temporal modeling)
- Graph/network data (no relationship modeling)
- Highly correlated numeric fields (limited correlation preservation)

## Customization

Modify the template in `lib/templates/data_augmentation.yaml`:

**Adjust generation count:**
```yaml
blocks:
  - type: StructureSampler
    config:
      target_count: 100  # Generate 100 records
```

**Change LLM creativity:**
```yaml
  - type: SemanticInfiller
    config:
      temperature: 0.9  # Higher = more creative (0.7-0.9 recommended)
      max_tokens: 300   # Longer outputs
```

**Adjust duplicate threshold:**
```yaml
  - type: DuplicateRemover
    config:
      similarity_threshold: 0.9  # Stricter (0.8-0.9 recommended)
```

**Add more dependencies:**
```json
{
  "dependencies": {
    "role": ["plan"],
    "storage": ["plan"]
  }
}
```

## Filtering Duplicates

Records marked as `is_duplicate: true` should be filtered post-generation:

**Via API:**
```python
result = await pipeline.execute(seed_data)
generated = result.result.get("generated_samples", [])
unique_records = [r for r in generated if not r.get("is_duplicate")]
```

**Via export (manual filter):**
```bash
# Export all records
curl http://localhost:8000/api/export?job_id=1 > output.jsonl

# Filter duplicates from generated_samples
jq '.generated_samples[] | select(.is_duplicate == false)' output.jsonl > unique.jsonl
```

> **Note:** Keeping duplicates in the trace allows adjusting the threshold post-generation and analyzing similarity score distributions (`similarity_to_seeds` and `similarity_to_generated`).

## Tuning Parameters

### Quality vs Speed

**High quality (slower):**
```yaml
target_count: 100
temperature: 0.9
max_tokens: 300
similarity_threshold: 0.9
```

**Fast iteration (lower quality):**
```yaml
target_count: 20
temperature: 0.7
max_tokens: 150
similarity_threshold: 0.75
```

### Diversity vs Fidelity

**Preserve distributions (higher fidelity):**
- Include all important `categorical_fields`
- Specify `dependencies` accurately
- Include `numeric_fields` with tight ranges

**Increase diversity (creative generation):**
- Omit some `categorical_fields` (LLM generates freely)
- Higher temperature (0.8-0.9)
- Lower `similarity_threshold` (0.75-0.8)

## Common Issues

### Low diversity (many duplicates)

**Causes:**
- Too few samples (<5)
- Temperature too low (<0.5)
- Fields too restrictive

**Fixes:**
- Add more diverse samples
- Increase temperature to 0.8-0.9
- Generate more semantic fields
- Increase similarity_threshold to 0.85-0.9

### Unrealistic outputs

**Causes:**
- Dependencies not specified
- Numeric hints too broad
- Temperature too high (>0.95)

**Fixes:**
- Add dependencies config
- Provide numeric_fields for constraints
- Reduce temperature to 0.7-0.8
- Include exemplar samples matching target patterns

### LLM errors (invalid JSON)

**Causes:**
- max_tokens too low (truncated JSON)
- Complex nested structures

**Fixes:**
- Increase max_tokens to 200-300
- Simplify fields (fewer nested objects)
- SemanticInfiller handles markdown wrappers automatically

### Missing embeddings

**Cause:** Embedding model not configured

**Behavior:** DuplicateRemover marks all as `is_duplicate: false`

**Fix:** Configure default embedding model in Settings page

## Example Workflow

**Goal:** Generate 100 synthetic user profiles

### Step 1: Prepare samples (6 examples)
```json
[
  {"plan": "Free", "role": "Viewer", "storage": 1, "bio": "Student learning"},
  {"plan": "Free", "role": "Viewer", "storage": 2, "bio": "Just exploring"},
  {"plan": "Pro", "role": "Editor", "storage": 50, "bio": "Freelance designer"},
  {"plan": "Pro", "role": "Editor", "storage": 75, "bio": "Agency owner"},
  {"plan": "Pro", "role": "Admin", "storage": 100, "bio": "Team lead"},
  {"plan": "Enterprise", "role": "Admin", "storage": 500, "bio": "CTO"}
]
```

### Step 2: Create pipeline from template
```bash
curl -X POST http://localhost:8000/api/pipelines/from_template/data_augmentation \
  -H "Content-Type: application/json" \
  -d '{"name": "User Profile Augmentation"}'
```

### Step 3: Start generation
```bash
curl -X POST http://localhost:8000/api/generate \
  -F "file=@seed_data_augmentation.json" \
  -F "pipeline_id=1"
```

### Step 4: Monitor progress
```bash
# Poll job status
curl http://localhost:8000/api/jobs/1
```

### Step 5: Review and export
```bash
# Export unique records only
curl http://localhost:8000/api/export?job_id=1 | jq 'select(.is_duplicate == false)' > unique_users.jsonl
```

**Result:** 100 synthetic user profiles preserving original distributions

> **Tip:** For large datasets, start with 20 records to verify quality before scaling up.

## Related Documentation

- [Templates Overview](templates) - All available templates
- [How to Use](how_to_use) - Running pipelines with templates
- [Custom Blocks](how_to_create_blocks) - Creating custom blocks and understanding multipliers
