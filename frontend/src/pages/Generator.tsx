import { useState } from 'react'
import { Box, Heading, FormControl, Button, Flash } from '@primer/react'
import { UploadIcon } from '@primer/octicons-react'

export default function Generator() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleGenerate = async () => {
    if (!file) return

    setLoading(true)
    setMessage('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        body: formData,
      })
      const result = await res.json()
      setMessage(`Generated: ${result.success}/${result.total} records`)
    } catch (error) {
      setMessage(`Error: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      <Heading sx={{ mb: 3 }}>Generate Records</Heading>

      {message && (
        <Flash variant="success" sx={{ mb: 3 }}>
          {message}
        </Flash>
      )}

      <Box sx={{ maxWidth: 480 }}>
        <FormControl>
          <FormControl.Label>Seed File (JSON)</FormControl.Label>
          <input
            type="file"
            accept=".json"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </FormControl>

        <Button
          leadingVisual={UploadIcon}
          onClick={handleGenerate}
          disabled={!file || loading}
          sx={{ mt: 3 }}
        >
          {loading ? 'Generating...' : 'Generate'}
        </Button>
      </Box>
    </Box>
  )
}
