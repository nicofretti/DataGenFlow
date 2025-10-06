import { useEffect, useState } from 'react'
import {
  Box,
  Heading,
  Text,
  Button,
  TextInput,
  FormControl,
  Flash,
} from '@primer/react'
import { PlusIcon, TrashIcon, PlayIcon } from '@primer/octicons-react'

interface BlockSchema {
  type: string
  name: string
  description: string
  inputs: string[]
  outputs: string[]
  config_schema: Record<string, any>
}

interface PipelineBlock {
  type: string
  config: Record<string, any>
}

export default function Builder() {
  const [availableBlocks, setAvailableBlocks] = useState<BlockSchema[]>([])
  const [pipelineBlocks, setPipelineBlocks] = useState<PipelineBlock[]>([])
  const [pipelineName, setPipelineName] = useState('')
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    loadBlocks()
  }, [])

  const loadBlocks = async () => {
    const res = await fetch('/api/blocks')
    const data = await res.json()
    setAvailableBlocks(data)
  }

  const addBlock = (blockType: string) => {
    const schema = availableBlocks.find((b) => b.type === blockType)
    if (!schema) return

    // initialize config with defaults
    const config: Record<string, any> = {}
    Object.entries(schema.config_schema).forEach(([key, schemaInfo]: [string, any]) => {
      config[key] = schemaInfo.default ?? ''
    })

    setPipelineBlocks([...pipelineBlocks, { type: blockType, config }])
  }

  const removeBlock = (index: number) => {
    setPipelineBlocks(pipelineBlocks.filter((_, i) => i !== index))
    if (selectedIndex === index) setSelectedIndex(null)
  }

  const updateBlockConfig = (index: number, key: string, value: any) => {
    const updated = [...pipelineBlocks]
    updated[index].config[key] = value
    setPipelineBlocks(updated)
  }

  const savePipeline = async () => {
    if (!pipelineName.trim()) {
      setMessage({ type: 'error', text: 'Pipeline name is required' })
      return
    }

    if (pipelineBlocks.length === 0) {
      setMessage({ type: 'error', text: 'Add at least one block' })
      return
    }

    try {
      const res = await fetch('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: pipelineName,
          blocks: pipelineBlocks,
        }),
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || 'Failed to save pipeline')
      }

      setMessage({ type: 'success', text: 'Pipeline saved successfully' })
      setPipelineName('')
      setPipelineBlocks([])
      setSelectedIndex(null)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Unknown error' })
    }
  }

  const selectedBlock = selectedIndex !== null ? pipelineBlocks[selectedIndex] : null
  const selectedSchema = selectedBlock
    ? availableBlocks.find((b) => b.type === selectedBlock.type)
    : null

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Heading sx={{ mb: 2, color: 'fg.default' }}>Pipeline Builder</Heading>
        <Text sx={{ color: 'fg.default' }}>
          Build custom workflows by chaining blocks together
        </Text>
      </Box>

      {message && (
        <Flash variant={message.type === 'error' ? 'danger' : 'success'} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr', gap: 4 }}>
        {/* block library */}
        <Box>
          <Heading as="h3" sx={{ fontSize: 2, mb: 3, color: 'fg.default' }}>
            Available Blocks
          </Heading>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {availableBlocks.map((block) => (
              <Box
                key={block.type}
                sx={{
                  border: '1px solid',
                  borderColor: 'border.default',
                  borderRadius: 2,
                  p: 2,
                  cursor: 'pointer',
                  '&:hover': { bg: 'accent.subtle' },
                }}
                onClick={() => addBlock(block.type)}
              >
                <Text sx={{ fontWeight: 'bold', fontSize: 1, color: 'fg.default' }}>
                  {block.name}
                </Text>
                <Text sx={{ fontSize: 0, color: 'fg.default' }}>{block.description}</Text>
              </Box>
            ))}
          </Box>
        </Box>

        {/* pipeline blocks */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Heading as="h3" sx={{ fontSize: 2, color: 'fg.default' }}>
              Pipeline
            </Heading>
            <Button leadingVisual={PlayIcon} variant="primary" onClick={savePipeline}>
              Save Pipeline
            </Button>
          </Box>

          <FormControl sx={{ mb: 3 }}>
            <FormControl.Label>Pipeline Name</FormControl.Label>
            <TextInput
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
              placeholder="My Pipeline"
            />
          </FormControl>

          {pipelineBlocks.length === 0 ? (
            <Box
              sx={{
                border: '1px dashed',
                borderColor: 'border.default',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
              }}
            >
              <Text sx={{ color: 'fg.default' }}>Click blocks on the left to add them</Text>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {pipelineBlocks.map((block, index) => (
                <Box
                  key={index}
                  sx={{
                    border: '1px solid',
                    borderColor: selectedIndex === index ? 'accent.emphasis' : 'border.default',
                    borderRadius: 2,
                    p: 2,
                    cursor: 'pointer',
                    bg: selectedIndex === index ? 'accent.subtle' : 'transparent',
                  }}
                  onClick={() => setSelectedIndex(index)}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text sx={{ fontWeight: 'bold', color: 'fg.default' }}>
                      {index + 1}. {block.type}
                    </Text>
                    <Button
                      size="small"
                      variant="danger"
                      leadingVisual={TrashIcon}
                      onClick={(e) => {
                        e.stopPropagation()
                        removeBlock(index)
                      }}
                    >
                      Remove
                    </Button>
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </Box>

        {/* config panel */}
        <Box>
          <Heading as="h3" sx={{ fontSize: 2, mb: 3, color: 'fg.default' }}>
            Configuration
          </Heading>

          {selectedBlock && selectedSchema ? (
            <Box
              sx={{
                border: '1px solid',
                borderColor: 'border.default',
                borderRadius: 2,
                p: 3,
                bg: 'canvas.subtle',
              }}
            >
              <Text sx={{ fontWeight: 'bold', mb: 2, color: 'fg.default' }}>
                {selectedSchema.name}
              </Text>
              <Text sx={{ fontSize: 1, mb: 3, color: 'fg.default' }}>
                {selectedSchema.description}
              </Text>

              {Object.entries(selectedSchema.config_schema).map(([key, schemaInfo]: [string, any]) => (
                <FormControl key={key} sx={{ mb: 2 }}>
                  <FormControl.Label>{key}</FormControl.Label>
                  <TextInput
                    value={selectedBlock.config[key] ?? ''}
                    onChange={(e) => updateBlockConfig(selectedIndex!, key, e.target.value)}
                    placeholder={schemaInfo.default?.toString() ?? ''}
                  />
                  {!schemaInfo.required && (
                    <FormControl.Caption>Optional (default: {schemaInfo.default})</FormControl.Caption>
                  )}
                </FormControl>
              ))}
            </Box>
          ) : (
            <Box
              sx={{
                border: '1px dashed',
                borderColor: 'border.default',
                borderRadius: 2,
                p: 4,
                textAlign: 'center',
              }}
            >
              <Text sx={{ color: 'fg.default' }}>Select a block to configure</Text>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}
