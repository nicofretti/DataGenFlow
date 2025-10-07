import { useState, useEffect } from 'react'
import { Box, Text, Spinner } from '@primer/react'

interface JobStatus {
  id: number
  pipeline_id: number
  status: string
  progress: number
}

export default function GlobalJobIndicator() {
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null)

  useEffect(() => {
    // poll every 2 seconds
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/jobs/active')
        if (res.ok) {
          const job = await res.json()
          setActiveJob(job)
        } else {
          setActiveJob(null)
        }
      } catch {
        setActiveJob(null)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  if (!activeJob) return null

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <Spinner size="small" />
      <Text sx={{ fontSize: 1, color: 'fg.muted' }}>
        Generating... {Math.round(activeJob.progress * 100)}%
      </Text>
    </Box>
  )
}
