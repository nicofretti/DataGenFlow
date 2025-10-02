import { useEffect, useState } from 'react'
import { Box, Heading, DataTable, Button, Label, Text } from '@primer/react'
import { CheckIcon, XIcon } from '@primer/octicons-react'

interface Record {
  id: number
  system: string
  user: string
  assistant: string
  status: string
  metadata: any
}

export default function Review() {
  const [records, setRecords] = useState<Record[]>([])

  useEffect(() => {
    loadRecords()
  }, [])

  const loadRecords = async () => {
    const res = await fetch('/api/records?status=pending&limit=10')
    const data = await res.json()
    setRecords(data)
  }

  const updateStatus = async (id: number, status: string) => {
    await fetch(`/api/records/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    setRecords(records.filter((r) => r.id !== id))
  }

  return (
    <Box>
      <Heading sx={{ mb: 3 }}>Review Records</Heading>

      {records.length === 0 ? (
        <Text>No pending records</Text>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {records.map((record) => (
            <Box key={record.id} sx={{ border: '1px solid', borderColor: 'border.default', borderRadius: 2, p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Text sx={{ fontWeight: 'bold' }}>ID: {record.id}</Text>
                <Label variant="attention">{record.status}</Label>
              </Box>
              <Text as="p" sx={{ mb: 1 }}><strong>System:</strong> {record.system}</Text>
              <Text as="p" sx={{ mb: 1 }}><strong>User:</strong> {record.user}</Text>
              <Text as="p" sx={{ mb: 2 }}><strong>Assistant:</strong> {record.assistant}</Text>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="primary"
                  leadingVisual={CheckIcon}
                  onClick={() => updateStatus(record.id, 'accepted')}
                >
                  Accept
                </Button>
                <Button
                  variant="danger"
                  leadingVisual={XIcon}
                  onClick={() => updateStatus(record.id, 'rejected')}
                >
                  Reject
                </Button>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}
