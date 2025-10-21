# Conversational AI Vertical

DataGenFlow includes a complete vertical for generating synthetic conversational data using research-backed algorithms.

## Quick Start

Generate customer service conversations in 5 steps:

### 1. Create Pipeline from Template

1. Open DataGenFlow
2. Navigate to "Create Pipeline" → "From Template"
3. Select "Customer Service Conversations"

### 2. Prepare Seed Data

Create a JSON file with your generation parameters:

```json
{
  "repetitions": 5,
  "metadata": {
    "topic": "billing_issue",
    "persona_style": "frustrated_customer",
    "num_turns": 5
  }
}
```

**Fields:**
- `repetitions`: How many conversations to generate
- `metadata.topic`: Conversation topic or domain
- `metadata.persona_style`: Customer personality type
- `metadata.num_turns`: Number of dialogue turns

### 3. Execute Pipeline

1. Upload your seed file
2. Click "Execute"
3. Wait for generation to complete

### 4. Review Results

Review each generated conversation:
- View quality metrics (diversity, coherence, engagement)
- See full execution trace
- Use keyboard shortcuts (A: Accept, R: Reject, E: Edit)

### 5. Export Data

Export accepted conversations as JSONL for training your models.

---

## Customer Service Template

The "Customer Service Conversations" template includes:

### Pipeline Blocks

1. **PersonaGeneratorBlock** - Creates customer and agent personas
2. **DialogueGeneratorBlock** - Generates multi-turn conversation
3. **BackTranslationBlock** - Creates diverse variations
4. **ValidatorBlock** - Ensures quality standards
5. **MetricsCalculatorBlock** - Computes quality metrics

### Pre-configured Settings

- **Personas:** 2 (customer + agent)
- **Personality traits:** Helpful, professional
- **Dialogue turns:** 5
- **Diversity variations:** 1
- **Temperature:** 0.7

### Quality Metrics

Every generated conversation includes:
- Diversity score (variation from similar conversations)
- Coherence score (sentence structure quality)
- Engagement score (interactive elements)

### Research Algorithms Used

- **Persona-Driven Generation** (Li et al., 2016)
- **Back-Translation Diversity** (Sennrich et al., 2016)

See [Research Algorithms](research-algorithms.md) for details.

---

## Use Cases

### Training Conversational AI

Generate diverse training data for:
- Customer support chatbots
- Voice assistants
- Dialogue systems
- Intent classification models

### Testing and Evaluation

Create test cases with:
- Different difficulty levels
- Various persona types
- Edge cases and adversarial examples
- Specific domain coverage

### Data Augmentation

Expand existing datasets:
- Generate variations of seed conversations
- Increase diversity while maintaining quality
- Balance dataset across topics and styles

---

## Customization

### Modify Existing Template

1. Load the template
2. Adjust block configurations:
   - Change number of personas
   - Modify personality traits
   - Adjust temperature for more/less variation
   - Add custom validation rules
3. Save as new template

### Create Custom Template

Combine blocks to build domain-specific templates:

```
PersonaGenerator → DialogueGenerator → DomainValidator → MetricsCalculator
```

Example for medical support:
```json
{
  "name": "Medical Support Conversations",
  "blocks": [
    {
      "type": "PersonaGeneratorBlock",
      "config": {
        "num_personas": 2,
        "personality_traits": ["concerned", "professional"]
      }
    },
    {
      "type": "DialogueGeneratorBlock",
      "config": {
        "turns": 7,
        "algo": "persona_driven"
      }
    },
    {
      "type": "MedicalValidatorBlock",
      "config": {
        "check_medical_accuracy": true
      }
    },
    {
      "type": "MetricsCalculatorBlock",
      "config": {
        "compute": ["diversity", "coherence", "empathy"]
      }
    }
  ]
}
```

---

## Advanced Features

### Seedless Generation

The template works without seed data. Blocks can generate initial state:

```json
{
  "repetitions": 10
}
```

This generates 10 random conversations without specific constraints.

### Metadata Control

Fine-tune generation with metadata:

```json
{
  "repetitions": 3,
  "metadata": {
    "topic": "technical_support",
    "difficulty": "advanced",
    "sentiment": "neutral",
    "resolution": "successful"
  }
}
```

Blocks use metadata to guide generation and maintain consistency.

### Metrics Filtering

Filter results by quality thresholds:
- Only accept conversations with diversity > 0.5
- Reject low coherence (< 0.3)
- Keep only highly engaging conversations

*(Note: UI filtering is coming in future updates. Currently done manually during review.)*

---

## Example Output

### Input Seed
```json
{
  "repetitions": 1,
  "metadata": {
    "topic": "billing_issue",
    "persona_style": "frustrated_customer",
    "num_turns": 3
  }
}
```

### Generated Conversation
```
Customer: I was charged twice for my subscription this month. This is unacceptable.

Agent: I sincerely apologize for the inconvenience. Let me look into your account right away to resolve this issue.

Customer: Please do. I've been a loyal customer for three years and this is disappointing.

Agent: I completely understand your frustration. I can see the duplicate charge here. I'm processing a refund immediately, and it should appear in your account within 2-3 business days.

Customer: Thank you. I appreciate the quick response.

Agent: You're very welcome. Is there anything else I can help you with today?
```

### Quality Metrics
```json
{
  "diversity": 0.72,
  "coherence": 0.85,
  "engagement": 0.68
}
```

---

## Best Practices

### Seed Data Design

- **Be specific:** More detailed metadata produces better results
- **Use repetitions:** Generate multiple variations to increase diversity
- **Test incrementally:** Start with 1-2 repetitions, then scale up

### Pipeline Configuration

- **Temperature tuning:**
  - Low (0.3-0.5): More consistent, less creative
  - Medium (0.6-0.8): Balanced variety
  - High (0.9-1.0): Maximum creativity, less predictable

- **Persona traits:** Use 2-3 traits for best results
- **Dialogue turns:** 3-7 turns work well for most use cases

### Quality Review

- Review trace logs to understand how conversations were generated
- Use metrics as guidelines, not absolute thresholds
- Edit promising conversations that need minor adjustments
- Build a feedback loop: rejected examples inform future seeds

---

## Troubleshooting

### Low Diversity Scores

**Problem:** Generated conversations are too similar.

**Solutions:**
- Increase temperature in DialogueGeneratorBlock
- Add more BackTranslation variations
- Use more varied personality traits
- Increase repetitions with different metadata

### Poor Coherence

**Problem:** Conversations don't make sense.

**Solutions:**
- Lower temperature for more consistent generation
- Reduce number of dialogue turns
- Add more specific context in metadata
- Check LLM endpoint configuration

### Generic Personas

**Problem:** Personas feel flat or uninteresting.

**Solutions:**
- Add more specific personality traits
- Include background context in metadata
- Use PersonaGenerator with more detailed prompts
- Review and edit persona outputs before dialogue generation

---

## Next Steps

- Explore [Research Algorithms](research-algorithms.md) documentation
- Create custom blocks for your domain
- Build your own conversation templates
- Share templates with your team

For technical details on implementing custom blocks, see [Custom Block Development](how_to_create_blocks.md).
