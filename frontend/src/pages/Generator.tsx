import { useState, useRef } from 'react'
import {
  Box,
  Heading,
  FormControl,
  Button,
  Flash,
  Text,
  TextInput,
  Select,
  Spinner,
  ProgressBar,
} from '@primer/react'
import { UploadIcon, PlayIcon, XIcon } from '@primer/octicons-react'

export default function Generator() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [temperature, setTemperature] = useState('0.7')
  const [maxTokens, setMaxTokens] = useState('2048')
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    if (!file) return

    setLoading(true)
    setMessage(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      })
      const result = await res.json()
      setMessage({
        type: 'success',
        text: `Generated ${result.success} of ${result.total} records (${result.failed} failed)`,
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

          <FormControl sx={{ mb: 3 }}>
            <FormControl.Label>Temperature</FormControl.Label>
            <TextInput
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
            />
            <FormControl.Caption>Controls randomness (0.0 - 2.0)</FormControl.Caption>
          </FormControl>

          <FormControl sx={{ mb: 4 }}>
            <FormControl.Label>Max Tokens</FormControl.Label>
            <TextInput
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(e.target.value)}
            />
            <FormControl.Caption>Maximum response length</FormControl.Caption>
          </FormControl>

          <Button
            variant="primary"
            size="large"
            block
            leadingVisual={PlayIcon}
            onClick={handleGenerate}
            disabled={!file || loading}
          >
            {loading ? 'Generating...' : 'Generate Records'}
          </Button>
        </Box>
      </Box>
    </Box>
  )
}
