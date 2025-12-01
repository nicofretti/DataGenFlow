> **Important**
> The file should reflect the current frontend status for remembering purposes
> to describe the actual ui design, component structure and implementation decisions. It must be technical and include the minimal number of words

# frontend reference

## stack
- react + typescript + vite
- primer react (ui components)
- reactflow (pipeline editor)
- monaco editor (json and template editing)
- shadcn/ui (form components)
- tailwindcss (utility-first styling)

## structure
```
frontend/
  src/
    pages/
      Pipelines.tsx      # template cards + pipeline list + reactflow editor
      Generator.tsx      # seed upload + job progress + error handling
      Review.tsx         # card-based records with collapsible trace, job filter
    components/
      GlobalJobIndicator.tsx  # header job status indicator
      ErrorModal.tsx          # error dialog for validation/network errors
      pipeline-editor/
        PipelineEditor.tsx    # main reactflow canvas
        BlockPalette.tsx      # searchable draggable block list
        BlockNode.tsx         # custom node with accumulated state
        BlockConfigPanel.tsx  # gear icon config form
        StartEndNode.tsx      # circular start/end nodes
        utils.ts              # format conversion, state calculation
```

## pages

### Pipelines.tsx
- template cards at top (one-click create from /api/templates)
- download seed button: detects markdown (.md) vs json (.json) format
  - checks for file_content field to identify markdown seeds
  - downloads with correct content-type and file extension
- pipeline list with expand/collapse
- edit button opens reactflow editor modal
- delete all pipelines button (when pipelines exist)
- no run button (pipelines need seed data)

### Generator.tsx
**features:**
- pipeline selector dropdown
- file input with json validation on select (json and markdown)
- error modal for invalid json, missing fields, network errors
- generate button with loading state
- job progress box (highlighted when running, accent border)
- stats: 3 columns, large numbers (seeds processed, generated, failed)
  - seeds processed: current_seed/total_seeds (live updates)
  - generated: records_generated (increments as seeds complete)
  - failed: records_failed (increments on seed failures)
- current activity with spinner (shows current_block and current_step)
- elapsed time display
- progress bar (updates based on progress field 0.0-1.0)
- 2-second polling for real-time job status updates

**seed validation:**
- manual validation via "Verify the seeds" button (only for JSON files)
- validates against selected pipeline's accumulated state schema
- checks valid json syntax
- checks not empty array
- checks each seed has required metadata fields
- shows minimal error display (first 3 errors + count)
- validation result prevents generation only if file is invalid JSON
- pipeline validation warnings don't block generation
- file upload disabled until pipeline selected

**state management:**
- finally block resets generating flag
- prevents stuck "generating..." state

### Review.tsx
- job selector (required, no "all jobs" option)
- jobs with 0 records hidden from selector
- card-based layout with collapsible trace
- inline status dropdown per record
- accept/reject/edit actions
- navigate to previous when accepting last pending record
- delete all scoped to selected job (deletes records + job)
- export scoped to selected job
- stats update when switching jobs
- real-time record visibility during job execution
  - auto-selects running job when viewing its pipeline
  - polls every 2 seconds for new records
  - simple cache: 'no-store' (no redundant headers or query params)
  - records appear incrementally as backend saves them (~5-7 sec intervals)
  - view stability: tracks current record by ID, not array index
  - when new records arrive, current view stays on same record (single mode)

## components

### GlobalJobIndicator.tsx
- displays in app header sidebar
- polls /api/jobs/active every 2 seconds
- shows current job progress

### ErrorModal.tsx
- primer Dialog component
- props: isOpen, onClose, title, message
- danger variant flash message
- used for: invalid json, network errors, generation failures

### ConfirmModal.tsx
- shadcn radix-ui dialog component
- replaces browser confirm() dialogs
- props: open, onOpenChange, title, description, onConfirm, variant, confirmText, cancelText
- variants: danger (destructive), warning (amber), info (blue)
- features:
  - async support with loading state
  - error handling with toast notifications
  - semantic color tokens (text-destructive, text-amber-600, text-blue-600)
  - icons per variant (AlertCircle, AlertTriangle, Info from lucide)
  - storybook stories for all variants
- used in: Pipelines, Review, Settings for delete operations

### pipeline-editor/

#### PipelineEditor.tsx
- reactflow canvas with controls
- loads blocks from /api/blocks on mount
- drag-and-drop from palette
- manual edge connections
- accumulated state recalculation on changes
- pipeline name editing (editable text input)
- save converts reactflow format to backend format
- validation before save (name required, all configured, all connected)
- start/end blocks auto-added, excluded from save
- computes available fields for each node (from predecessor outputs)
- passes availableFields to BlockConfigPanel for field reference dropdowns

#### BlockPalette.tsx
- left sidebar in editor
- searchable block list (by name or type)
- draggable blocks to canvas
- compact list with left accent border
- shows "no blocks found" when search empty

#### BlockNode.tsx
- custom reactflow node
- displays: block name, inputs, outputs, config params, accumulated state
- status badges: "not configured" (red), "not connected" (yellow)
- gear icon for config (opens BlockConfigPanel)
- delete button (x icon)
- smart config value display:
  - objects: {N fields} or {} for empty
  - arrays: [N items] or [] for empty
  - long strings: truncated to 30 chars with ...
  - simple values: displayed as-is

#### BlockConfigPanel.tsx
- right sidebar config form
- generates form fields from config_schema.properties
- field types:
  - string: TextInput or Monaco editor (for prompts/templates)
  - number: TextInput type="number"
  - boolean: Checkbox
  - object/dict: Monaco JSON editor (300px height, syntax highlighting)
  - enum: Select dropdown with predefined options
  - field_reference: editable TextInput with datalist (suggestions from previous blocks)
- shows field descriptions below inputs (from _config_descriptions)
- shows default values in labels
- computes available fields from previous pipeline blocks
- monaco editor for jinja2 templates (detected by field name or format)
- wordwrap toggle for template fields

#### StartEndNode.tsx
- circular nodes (green start, purple end)
- cannot be deleted
- start: no incoming edges allowed
- end: no outgoing edges allowed
- excluded from backend save (ui-only)

#### utils.ts
**calculateAccumulatedState:**
- processes nodes in pipeline order
- accumulates outputs from each block
- updates node.data.accumulatedState

**convertToBackendFormat:**
- extracts blocks array from reactflow nodes
- filters out start/end nodes
- returns {name, blocks: [{type, config}]}

**convertFromBackendFormat:**
- creates reactflow nodes from blocks array
- positions vertically with 150px spacing
- creates edges connecting sequential blocks
- adds start/end nodes

## ui patterns

### error handling
- client-side validation before api calls
- error modal instead of inline flash messages
- clear error titles and messages
- network error catching with fallback messages

### job progress
- 2-second polling (not websocket)
- highlighted box when running (accent.subtle bg, accent.emphasis border)
- spinner + current activity text
- elapsed time calculation
- large stat numbers (fontSize: 3)

### job filtering
- review page requires job selection
- hide jobs with 0 records
- scoped operations (delete, export) to selected job
- job list refresh after delete

### dark mode support
- all text uses fg.default or fg.muted
- backgrounds use canvas.* colors
- borders use border.default
- accent colors for highlights

## api integration

**endpoints used:**
- GET /api/blocks - fetch available blocks
- GET /api/templates - fetch pipeline templates
- POST /api/pipelines - create pipeline
- GET /api/pipelines - list pipelines
- DELETE /api/pipelines/{id} - delete pipeline
- POST /api/pipelines/from_template/{id} - create from template
- POST /api/generate - start generation (returns job_id)
- GET /api/jobs/active - get running job
- GET /api/jobs/{id} - get job status
- DELETE /api/jobs/{id} - cancel job
- GET /api/records?job_id={id} - list records for job
- PUT /api/records/{id} - update record status
- DELETE /api/records?job_id={id} - delete records + job
- GET /api/export/download?job_id={id} - download jsonl

## branding
- logo: /logo.png (40x40 in sidebar)
- app name: DataGenFlow
- favicon: multiple sizes (16x16, 32x32, 180x180, 192x192, 512x512)
- meta description in index.html

## state management
- react useState (no redux)
- local component state
- polling for job updates
- no websockets

## styling
- primer react components
- sx prop for inline styles
- consistent spacing (p: 3, 4, gap: 2, 3)
- responsive grid layouts

## theme management
- shadcn/ui next-themes as source of truth
- primer ThemeProvider syncs via PrimerThemeWrapper
- theme state: shadcn resolvedTheme → primer colorMode
- cleaned up old colorMode localStorage key
- storybook configured with shadcn theme provider
- theme toggle in navigation syncs both systems
