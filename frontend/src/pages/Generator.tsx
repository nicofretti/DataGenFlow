import { useState, useRef, useEffect } from 'react'
import {
  Box,
  Heading,
  FormControl,
  Button,
  Flash,
  Text,
  Select,
  Spinner,
  ProgressBar,
} from '@primer/react'
import { UploadIcon, PlayIcon, XIcon } from '@primer/octicons-react'

interface Pipeline {
  id: number
  name: string
  definition: {
    name: string
    blocks: any[]
  }
}

export default function Generator() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchPipelines()
  }, [])

  const fetchPipelines = async () => {
    try {
      const res = await fetch('/api/pipelines')
      const data = await res.json()
      setPipelines(data)
    } catch (error) {
      console.error('Failed to fetch pipelines:', error)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type === 'application/json') {
        setFile(droppedFile)
      } else {
        setMessage({ type: 'error', text: 'Please drop a JSON file' })
      }
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setMessage(null)
    }
  }

  const handleGenerate = async () => {
    if (!file || !selectedPipeline) return

    setLoading(true)
    setMessage(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('pipeline_id', selectedPipeline.toString())

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      })
      const result = await res.json()
      const pipelineName = pipelines.find((p) => p.id === selectedPipeline)?.name
      setMessage({
        type: 'success',
        text: `Generated ${result.success} of ${result.total} records using ${pipelineName} (${result.failed} failed)`,
      })
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error}` })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Heading sx={{ mb: 2, color: 'fg.default' }}>Generate Records</Heading>
        <Text sx={{ color: 'fg.default' }}>
          Upload a JSON seed file to generate Q&A records using your LLM
        </Text>
      </Box>

      {message && (
        <Flash variant={message.type === 'error' ? 'danger' : 'success'} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 4 }}>
        {/* Upload Section */}
        <Box>
          <Box
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            sx={{
              border: '2px dashed',
              borderColor: dragActive ? 'accent.emphasis' : 'border.default',
              borderRadius: 2,
              p: 6,
              textAlign: 'center',
              cursor: 'pointer',
              bg: dragActive ? 'accent.subtle' : 'canvas.subtle',
              transition: 'all 0.2s',
              '&:hover': {
                borderColor: 'accent.fg',
                bg: 'accent.subtle',
              },
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            <Box sx={{ color: 'fg.muted' }}>
              <UploadIcon size={48} />
            </Box>
            <Heading as="h3" sx={{ fontSize: 2, mt: 3, mb: 2, color: 'fg.default' }}>
              {file ? file.name : 'Drop JSON file here or click to browse'}
            </Heading>
            <Text sx={{ color: 'fg.default', fontSize: 1 }}>
              {file
                ? `Size: ${(file.size / 1024).toFixed(2)} KB`
                : 'Supported format: .json'}
            </Text>

            {file && (
              <Button
                variant="invisible"
                leadingVisual={XIcon}
                onClick={(e) => {
                  e.stopPropagation()
                  setFile(null)
                }}
                sx={{ mt: 2 }}
              >
                Remove file
              </Button>
            )}
          </Box>

          {loading && (
            <Box sx={{ mt: 3 }}>
              <Text sx={{ mb: 2, fontSize: 1, color: 'fg.muted' }}>Generating records...</Text>
              <ProgressBar progress={null} sx={{ mb: 2 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Spinner size="small" />
                <Text sx={{ fontSize: 1, color: 'fg.muted' }}>This may take a few moments</Text>
              </Box>
            </Box>
          )}
        </Box>

        {/* Configuration Panel */}
        <Box
          sx={{
            border: '1px solid',
            borderColor: 'border.default',
            borderRadius: 2,
            p: 3,
            bg: 'canvas.subtle',
          }}
        >
          <Heading as="h3" sx={{ fontSize: 2, mb: 3, color: 'fg.default' }}>
            Configuration
          </Heading>

          <FormControl sx={{ mb: 4 }} required>
            <FormControl.Label>Pipeline</FormControl.Label>
            <Select
              value={selectedPipeline?.toString() || ''}
              onChange={(e) => setSelectedPipeline(Number(e.target.value) || null)}
            >
              <Select.Option value="">Select a pipeline...</Select.Option>
              {pipelines.map((pipeline) => (
                <Select.Option key={pipeline.id} value={pipeline.id.toString()}>
                  {pipeline.name} ({pipeline.definition.blocks.length} blocks)
                </Select.Option>
              ))}
            </Select>
            <FormControl.Caption>Select pipeline to execute for each seed row</FormControl.Caption>
          </FormControl>

          <Button
            variant="primary"
            size="large"
            block
            leadingVisual={PlayIcon}
            onClick={handleGenerate}
            disabled={!file || !selectedPipeline || loading}
          >
            {loading ? 'Generating...' : 'Generate Records'}
          </Button>
        </Box>
      </Box>
    </Box>
  )
}
