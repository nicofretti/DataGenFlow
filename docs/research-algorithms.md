# Research Algorithms

DataGenFlow includes peer-reviewed algorithms for synthetic data generation, implemented as reusable blocks.

## Available Algorithms

### 1. Back-Translation Diversity (Sennrich et al., 2016)

**Purpose:** Generate diverse conversation variations from the same intent.

**Algorithm:**
1. Take original conversation
2. Paraphrase to intermediate representation
3. Regenerate from paraphrase to create variation
4. Measure lexical and semantic diversity

**Use Cases:**
- Training data augmentation
- Robustness testing
- Increasing dataset diversity

**Block:** `BackTranslationBlock`

**Configuration:**
- `num_variations` (int): Number of variations to generate
- `temperature` (float): Sampling temperature for generation
- `paraphrase_model` (str): Model to use for paraphrasing

**Outputs:**
- `diverse_conversations`: List of conversation variations
- `diversity_score`: Lexical diversity metric (0-1)
- `algorithm`: Algorithm identifier
- `paper`: Citation reference

**Citation:** Sennrich et al., 2016 - Improving Neural Machine Translation Models with Monolingual Data

---

### 2. Persona-Driven Generation (Li et al., 2016)

**Purpose:** Generate consistent character voices in conversations.

**Algorithm:**
1. Define personas with personality traits
2. Inject personality constraints into generation
3. Generate dialogue maintaining persona consistency

**Use Cases:**
- Character consistency in dialogues
- Dialogue quality improvement
- Domain-specific conversation generation

**Blocks:** `PersonaGeneratorBlock`, `DialogueGeneratorBlock`

**PersonaGeneratorBlock Configuration:**
- `num_personas` (int): Number of personas to generate
- `personality_traits` (list): Desired personality traits
- `generate_from_metadata` (bool): Use metadata for context

**DialogueGeneratorBlock Configuration:**
- `turns` (int): Number of conversation turns
- `algo` (str): Algorithm to use (default: "persona_driven")
- `max_tokens` (int): Maximum tokens for generation

**Outputs:**
- `personas`: Generated persona definitions
- `dialogue`: Multi-turn conversation
- `turn_count`: Number of turns in dialogue
- `algorithm`: Algorithm identifier

**Citation:** Li et al., 2016 - A Persona-Based Neural Conversation Model

---

### 3. Adversarial Perturbation (Belinkov & Bisk, 2018)

**Purpose:** Generate edge cases for robustness testing.

**Algorithm:**
1. Start with valid conversation
2. Apply controlled perturbations (typos, context shifts, contradictions)
3. Measure difficulty increase

**Use Cases:**
- Adversarial testing
- Robustness evaluation
- Edge case coverage

**Block:** `AdversarialPerturbationBlock`

**Configuration:**
- `perturbation_type` (str): Type of perturbation to apply
  - `realistic_noise`: Add typos and word order changes
  - `context_shift`: Change topic midway
  - `contradiction`: Add contradictory statements
- `intensity` (float): Perturbation intensity (0-1)

**Outputs:**
- `perturbed_conversation`: Modified conversation
- `difficulty_score`: Difficulty metric (0-1)
- `perturbations_applied`: List of applied perturbations
- `paper`: Citation reference

**Citation:** Belinkov & Bisk, 2018 - Synthetic and Natural Noise Both Break Neural Machine Translation

---

## Quality Metrics

All research algorithm pipelines automatically compute quality metrics using the `MetricsCalculatorBlock`.

### Available Metrics

**Diversity Score (0-1)**
- Measures lexical and semantic variation between texts
- Higher scores indicate more diverse outputs
- Computed using sequence matching algorithms

**Coherence Score (0-1)**
- Evaluates sentence structure quality
- Based on word count and sentence patterns
- Higher scores indicate better-formed text

**Engagement Score (0-1)**
- Measures interactive elements in text
- Counts questions, exclamations, and conversational markers
- Higher scores indicate more engaging content

**Difficulty Score (0-1)**
- Evaluates challenge level for models
- Based on perturbations, errors, and complexity
- Higher scores indicate harder test cases

### MetricsCalculatorBlock

**Configuration:**
- `compute` (list): List of metrics to calculate
  - Options: `["diversity", "coherence", "engagement", "difficulty"]`

**Outputs:**
- `metrics`: Dictionary of computed metric values
- `metrics_summary`: Human-readable summary string

**Usage Example:**
```python
MetricsCalculatorBlock(
    compute=["diversity", "coherence", "engagement"]
)
```

---

## Using Research Algorithms

### In Pipeline Editor

1. Drag algorithm blocks from the block palette
2. Configure parameters in block settings
3. Connect blocks in desired order
4. Execute pipeline to see results with metrics

### In Templates

Research algorithms are pre-configured in templates like "Customer Service Conversations". Simply select the template and run with your seed data.

### Custom Pipelines

Combine research algorithms with custom blocks for domain-specific workflows:

```
PersonaGenerator → DialogueGenerator → YourCustomBlock → MetricsCalculator
```

Each algorithm block adds its outputs to the accumulated state, making them available to subsequent blocks automatically.
