import { useEffect, useState } from 'react'
import {
  Box,
  Heading,
  Text,
  Button,
  Flash,
  Label,
} from '@primer/react'
import { PencilIcon, TrashIcon, PlusIcon } from '@primer/octicons-react'
import PipelineEditor from '../components/pipeline-editor/PipelineEditor'

interface Pipeline {
  id: number
  name: string
  definition: {
    name: string
    blocks: Array<{ type: string; config: Record<string, any> }>
  }
  created_at: string
}

export default function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [editing, setEditing] = useState<{ mode: 'new' | 'edit'; pipeline?: Pipeline } | null>(null)

  useEffect(() => {
    loadPipelines()
  }, [])

  const loadPipelines = async () => {
    const res = await fetch('/api/pipelines')
    const data = await res.json()
    setPipelines(data)
  }

  const savePipeline = async (pipeline: any) => {
    try {
      if (editing?.mode === 'new') {
        // create new pipeline
        const res = await fetch('/api/pipelines', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pipeline),
        })

        if (!res.ok) throw new Error('Failed to create pipeline')
        setMessage({ type: 'success', text: 'Pipeline created successfully' })
      } else if (editing?.mode === 'edit' && editing.pipeline) {
        // update existing pipeline
        const res = await fetch(`/api/pipelines/${editing.pipeline.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pipeline),
        })

        if (!res.ok) throw new Error('Failed to update pipeline')
        setMessage({ type: 'success', text: 'Pipeline updated successfully' })
      }

      setEditing(null)
      loadPipelines()
    } catch (error) {
      throw new Error(`Save failed: ${error}`)
    }
  }

  const deletePipeline = async (id: number) => {
    if (!confirm('Delete this pipeline?')) return

    try {
      const res = await fetch(`/api/pipelines/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')

      setMessage({ type: 'success', text: 'Pipeline deleted' })
      loadPipelines()
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error}` })
    }
  }

  const deleteAllPipelines = async () => {
    if (!confirm(`Delete all ${pipelines.length} pipeline(s)? This cannot be undone!`)) return

    try {
      // delete each pipeline
      await Promise.all(
        pipelines.map((pipeline) =>
          fetch(`/api/pipelines/${pipeline.id}`, { method: 'DELETE' })
        )
      )

      setMessage({ type: 'success', text: 'All pipelines deleted' })
      loadPipelines()
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error}` })
    }
  }

  // show editor if editing
  if (editing) {
    return (
      <PipelineEditor
        pipelineId={editing.pipeline?.id}
        pipelineName={editing.pipeline?.definition.name || 'New Pipeline'}
        initialPipeline={editing.pipeline?.definition}
        onSave={savePipeline}
        onClose={() => setEditing(null)}
      />
    )
  }

  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Heading sx={{ mb: 2, color: 'fg.default' }}>Pipelines</Heading>
          <Text sx={{ color: 'fg.default' }}>
            Create and manage your data generation pipelines
          </Text>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {pipelines.length > 0 && (
            <Button
              variant="danger"
              leadingVisual={TrashIcon}
              onClick={deleteAllPipelines}
            >
              Delete All
            </Button>
          )}
          <Button
            variant="primary"
            leadingVisual={PlusIcon}
            onClick={() => setEditing({ mode: 'new' })}
          >
            New Pipeline
          </Button>
        </Box>
      </Box>

      {message && (
        <Flash variant={message.type === 'error' ? 'danger' : 'success'} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

      {pipelines.length === 0 ? (
        <Box
          sx={{
            textAlign: 'center',
            py: 6,
            border: '1px dashed',
            borderColor: 'border.default',
            borderRadius: 2,
          }}
        >
          <Text sx={{ color: 'fg.default' }}>No pipelines yet. Click "New Pipeline" to create one!</Text>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {pipelines.map((pipeline) => (
            <Box
              key={pipeline.id}
              sx={{
                border: '1px solid',
                borderColor: 'border.default',
                borderRadius: 2,
                p: 4,
                bg: 'canvas.subtle',
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 3 }}>
                <Box>
                  <Heading as="h3" sx={{ fontSize: 2, mb: 1, color: 'fg.default' }}>
                    {pipeline.definition.name}
                  </Heading>
                  <Text sx={{ fontSize: 1, color: 'fg.default' }}>
                    Created: {new Date(pipeline.created_at).toLocaleString()}
                  </Text>
                </Box>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button
                    variant="primary"
                    leadingVisual={PencilIcon}
                    onClick={() => setEditing({ mode: 'edit', pipeline })}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="danger"
                    leadingVisual={TrashIcon}
                    onClick={() => deletePipeline(pipeline.id)}
                  >
                    Delete
                  </Button>
                </Box>
              </Box>

              <Box>
                <Text sx={{ fontWeight: 'bold', fontSize: 1, mb: 2, color: 'fg.default' }}>
                  Blocks ({pipeline.definition.blocks.length}):
                </Text>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                  {pipeline.definition.blocks.map((block, idx) => (
                    <Label key={idx} variant="accent">
                      {idx + 1}. {block.type}
                    </Label>
                  ))}
                </Box>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}
