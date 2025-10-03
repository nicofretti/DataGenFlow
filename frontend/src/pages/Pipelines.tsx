import { useEffect, useState } from 'react'
import {
  Box,
  Heading,
  Text,
  Button,
  Flash,
  Label,
} from '@primer/react'
import { PlayIcon, TrashIcon } from '@primer/octicons-react'

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
  const [executing, setExecuting] = useState<number | null>(null)

  useEffect(() => {
    loadPipelines()
  }, [])

  const loadPipelines = async () => {
    const res = await fetch('/api/pipelines')
    const data = await res.json()
    setPipelines(data)
  }

  const executePipeline = async (id: number) => {
    setExecuting(id)
    setMessage(null)

    try {
      // example execution with sample data
      const res = await fetch(`/api/pipelines/${id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: 'Sample input text',
          system: 'You are a helpful assistant',
          user: 'Say hello',
        }),
      })

      if (!res.ok) throw new Error('Execution failed')

      const result = await res.json()
      setMessage({
        type: 'success',
        text: `Pipeline executed successfully. Result: ${JSON.stringify(result).substring(0, 100)}...`,
      })
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error}` })
    } finally {
      setExecuting(null)
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

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Heading sx={{ mb: 2, color: 'fg.default' }}>Pipelines</Heading>
        <Text sx={{ color: 'fg.default' }}>
          Manage and execute your saved pipelines
        </Text>
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
          <Text sx={{ color: 'fg.default' }}>No pipelines yet. Create one in the Builder!</Text>
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
                    leadingVisual={PlayIcon}
                    onClick={() => executePipeline(pipeline.id)}
                    disabled={executing === pipeline.id}
                  >
                    {executing === pipeline.id ? 'Executing...' : 'Execute'}
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
