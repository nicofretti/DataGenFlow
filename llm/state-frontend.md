> **Important**
> The file should reflect the current frontend status for remembering purposes
> to describe the actual ui design, component structure and implementation decisions. It must be technical and include the minimal number of words

# frontend state

## stack
react + typescript + vite + primer react + reactflow + monaco + shadcn/ui + tailwindcss

## structure
```
frontend/src/
  pages/
    Pipelines.tsx      # templates + list + reactflow editor
    Generator.tsx      # upload + job progress + validation
    Review.tsx         # cards + collapsible trace + job filter
    Settings.tsx       # LLM/embedding config management
  components/
    GlobalJobIndicator.tsx     # header job status
    ConfigureFieldsModal.tsx   # field configuration
    SingleRecordView.tsx       # card view with trace
    TableRecordView.tsx        # table view
    RecordDetailsModal.tsx     # detail popup
    KeyboardShortcut.tsx       # keyboard hints
    pipeline-editor/
      PipelineEditor.tsx       # reactflow canvas
      BlockPalette.tsx         # searchable block list
      BlockNode.tsx            # custom node
      BlockConfigPanel.tsx     # config sidebar
      StartEndNode.tsx         # circular start/end
      utils.ts                 # format conversion
    settings/
      LLMFormModal.tsx         # llm config form
      EmbeddingFormModal.tsx   # embedding config form
    ui/                        # shadcn components
      button, confirm-modal, sonner, etc
```

## pages

### Pipelines.tsx
- template cards: one-click create from templates
- seed download: auto-detects .md vs .json by file_content field
- pipeline list: expand/collapse, edit (reactflow modal), delete
- delete all pipelines button
- no run button (requires seed data)

### Generator.tsx
- pipeline selector dropdown
- file upload: json/markdown with validation
- seed validation: "Verify the seeds" button (json only)
  - validates against accumulated_state_schema
  - checks: syntax, array not empty, metadata fields present
  - warnings don't block generation
- job progress: highlighted box when running, 2s polling
  - stats: seeds processed (current/total), generated, failed
  - current activity: spinner + current_block + current_step
  - elapsed time, progress bar (0.0-1.0)
- error modal for validation/network errors

### Review.tsx
- job selector (required, hides jobs with 0 records)
- card layout with collapsible trace
- inline status dropdown per record
- accept/reject/edit actions
- delete all scoped to job (deletes records + job)
- export scoped to job
- real-time updates: 2s polling, incremental record visibility
- view stability: tracks by ID, single mode preserves current record

### Settings.tsx
- LLM/embedding model management
- provider/model selection (OpenAI, Anthropic, Ollama, etc)
- API key configuration
- connection testing
- default model selection

## components

### GlobalJobIndicator.tsx
polls /api/jobs/active every 2s, shows current job progress in header

### ConfirmModal.tsx
shadcn radix-ui dialog, replaces browser confirm()
- variants: danger (destructive), warning (amber), info (blue)
- async support with loading state, error handling with toasts
- icons: AlertCircle, AlertTriangle, Info
- used for: delete operations in Pipelines, Review, Settings

### pipeline-editor/

**PipelineEditor.tsx**
- reactflow canvas with controls, drag-drop from palette
- loads blocks from /api/blocks
- manual edge connections, accumulated state auto-calculated
- editable pipeline name
- validation before save: name required, all configured, all connected
- start/end nodes auto-added, excluded from save
- computes availableFields for each node from predecessors

**BlockPalette.tsx**
- left sidebar, searchable (name/type)
- draggable blocks, compact list with accent border
- "no blocks found" on empty search

**BlockNode.tsx**
- displays: name, inputs, outputs, config, accumulated state
- badges: "not configured" (red), "not connected" (yellow)
- gear icon (config), delete (x)
- smart config display: {N fields}, [N items], truncate 30 chars

**BlockConfigPanel.tsx**
- right sidebar form from config_schema.properties
- fields: string (TextInput/Monaco), number, boolean (Checkbox), object (Monaco JSON), enum (Select), field_reference (TextInput + datalist)
- shows descriptions, default values
- monaco for jinja2 templates with wordwrap toggle
- json-or-template fields: checkbox toggle between JSON mode (validated) and Jinja2 template mode
- json mode state resets when switching between nodes
- model dropdowns (LLM/embedding): preserve custom model names not in API response

**StartEndNode.tsx**
- circular green start, purple end
- cannot delete, start no incoming, end no outgoing
- ui-only, excluded from backend save

**utils.ts**
- calculateAccumulatedState: processes nodes in order, accumulates outputs
- convertToBackendFormat: extracts blocks, filters start/end
- convertFromBackendFormat: creates reactflow nodes, 150px vertical spacing

## patterns

### error handling
- client validation before api calls
- error modals with clear titles/messages
- network error catching with fallbacks

### job progress
- 2s polling (no websockets)
- highlighted box when running (accent.subtle bg, accent.emphasis border)
- spinner + current activity
- elapsed time, large stat numbers (fontSize: 3)

### job filtering
- Review requires job selection
- hide jobs with 0 records
- scoped delete/export to job

### dark mode
- text: fg.default, fg.muted
- backgrounds: canvas.*
- borders: border.default
- accents for highlights

## api integration

**endpoints:**
- GET /api/blocks, /api/templates, /api/pipelines, /api/jobs/active, /api/jobs/{id}, /api/records
- POST /api/pipelines, /api/pipelines/from_template/{id}, /api/generate, /api/seeds/validate
- PUT /api/records/{id}, /api/llm-models/{name}, /api/embedding-models/{name}
- DELETE /api/pipelines/{id}, /api/jobs/{id}, /api/records
- GET /api/export/download, /api/llm-models, /api/embedding-models

## branding
logo: /logo.png (40x40), name: DataGenFlow, favicon: multiple sizes

## state management
react useState (no redux), local component state, polling for jobs

## styling
primer react sx prop, consistent spacing (p: 3, 4, gap: 2, 3), responsive grids

## theme
- shadcn next-themes as source
- primer ThemeProvider syncs via PrimerThemeWrapper
- shadcn resolvedTheme → primer colorMode
- theme toggle syncs both systems
