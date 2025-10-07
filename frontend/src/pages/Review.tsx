import { useEffect, useState } from 'react'
import {
  Box,
  Heading,
  Button,
  Label,
  Text,
  Textarea,
  SegmentedControl,
  CounterLabel,
  Flash,
  FormControl,
  Select,
} from '@primer/react'
import { CheckIcon, XIcon, PencilIcon, ChevronLeftIcon, ChevronRightIcon, CommentIcon, PersonIcon, GearIcon, ClockIcon, CheckCircleIcon, XCircleIcon, TrashIcon, DownloadIcon } from '@primer/octicons-react'

interface Record {
  id: number
  system: string
  user: string
  assistant: string
  status: string
  metadata: any
  trace?: Array<{
    block_type: string
    input: any
    output: any
    accumulated_state?: any
    error?: string
  }>
  error?: string
}

interface Pipeline {
  id: number
  name: string
  definition: {
    name: string
    blocks: any[]
  }
}

interface Job {
  id: number
  pipeline_id: number
  status: string
  records_generated: number
  records_failed: number
  started_at: string
}

export default function Review() {
  const [records, setRecords] = useState<Record[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const [filterStatus, setFilterStatus] = useState<'pending' | 'accepted' | 'rejected'>('pending')
  const [stats, setStats] = useState({ pending: 0, accepted: 0, rejected: 0 })
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<number | null>(null)

  const currentRecord = records[currentIndex] || null

  useEffect(() => {
    loadPipelines()
  }, [])

  useEffect(() => {
    loadRecords()
    loadStats()
  }, [filterStatus, selectedJob])

  useEffect(() => {
    if (selectedPipeline) {
      loadJobs(selectedPipeline)
    } else {
      setJobs([])
      setSelectedJob(null)
    }
  }, [selectedPipeline])

  // reset index when changing filter
  useEffect(() => {
    setCurrentIndex(0)
    setIsEditing(false)
    setIsExpanded(false)
  }, [filterStatus])

  // keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (isEditing) return // disable shortcuts while editing

      if (e.key === 'a' && currentRecord) {
        updateStatus(currentRecord.id, 'accepted')
      } else if (e.key === 'r' && currentRecord) {
        updateStatus(currentRecord.id, 'rejected')
      } else if (e.key === 'e' && currentRecord) {
        startEditing()
      } else if (e.key === 'n' && currentIndex < records.length - 1) {
        setCurrentIndex(currentIndex + 1)
        setIsExpanded(false)
      } else if (e.key === 'p' && currentIndex > 0) {
        setCurrentIndex(currentIndex - 1)
        setIsExpanded(false)
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [currentRecord, currentIndex, records.length, isEditing])

  const loadPipelines = async () => {
    try {
      const res = await fetch('/api/pipelines')
      const data = await res.json()
      setPipelines(data)
    } catch (error) {
      console.error('Failed to load pipelines:', error)
    }
  }

  const loadJobs = async (pipelineId: number) => {
    try {
      const res = await fetch(`/api/jobs?pipeline_id=${pipelineId}`)
      const data = await res.json()
      setJobs(data)
    } catch (error) {
      console.error('Failed to load jobs:', error)
      setJobs([])
    }
  }

  const loadRecords = async () => {
    let url = `/api/records?status=${filterStatus}&limit=100`
    if (selectedJob) {
      url += `&job_id=${selectedJob}`
    }
    const res = await fetch(url)
    const data = await res.json()
    setRecords(data)
  }

  const loadStats = async () => {
    // fetch all records to get accurate counts
    const [pending, accepted, rejected] = await Promise.all([
      fetch('/api/records?status=pending').then(r => r.json()),
      fetch('/api/records?status=accepted').then(r => r.json()),
      fetch('/api/records?status=rejected').then(r => r.json()),
    ])
    setStats({
      pending: pending.length,
      accepted: accepted.length,
      rejected: rejected.length,
    })
  }

  const updateStatus = async (id: number, status: string) => {
    await fetch(`/api/records/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    // move to next record after action
    if (currentIndex < records.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
    loadRecords()
    loadStats()
  }

  // get final output from pipeline accumulated state or fallback to assistant
  const getFinalOutput = (record: Record): string => {
    if (record.trace && record.trace.length > 0) {
      const finalState = record.trace[record.trace.length - 1].accumulated_state
      if (finalState?.pipeline_output !== undefined) {
        // if pipeline_output is object, stringify it
        return typeof finalState.pipeline_output === 'string'
          ? finalState.pipeline_output
          : JSON.stringify(finalState.pipeline_output, null, 2)
      }
      // fallback to accumulated state
      return finalState ? JSON.stringify(finalState, null, 2) : record.assistant
    }
    return record.assistant || ''
  }

  const startEditing = () => {
    if (!currentRecord) return
    setIsEditing(true)
    setEditValue(getFinalOutput(currentRecord))
    setIsExpanded(true) // expand when editing
  }

  const saveEdit = async () => {
    if (!currentRecord) return
    await fetch(`/api/records/${currentRecord.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assistant: editValue, status: 'edited' }),
    })
    setIsEditing(false)
    if (currentIndex < records.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
    loadRecords()
  }

  const goToNext = () => {
    if (currentIndex < records.length - 1) {
      setCurrentIndex(currentIndex + 1)
      setIsExpanded(false)
    }
  }

  const goToPrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setIsExpanded(false)
    }
  }

  const deleteAllRecords = async () => {
    if (!confirm('Delete ALL records? This cannot be undone.')) return

    try {
      await fetch('/api/records', { method: 'DELETE' })
      setMessage({ type: 'success', text: 'All records deleted' })
      loadRecords()
      loadStats()
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error}` })
    }
  }

  const exportAccepted = () => {
    window.location.href = '/api/export/download?status=accepted'
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'pending': return 'attention'
      case 'accepted': return 'success'
      case 'rejected': return 'danger'
      case 'edited': return 'accent'
      default: return 'default'
    }
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Heading sx={{ mb: 2, color: 'fg.default' }}>Review Records</Heading>
          <Text sx={{ color: 'fg.default' }}>
            Review and validate generated Q&A pairs • Use keyboard shortcuts
          </Text>
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="primary"
            leadingVisual={DownloadIcon}
            onClick={exportAccepted}
            disabled={stats.accepted === 0}
          >
            Export Accepted
          </Button>
          <Button
            variant="danger"
            leadingVisual={TrashIcon}
            onClick={deleteAllRecords}
          >
            Delete All
          </Button>
        </Box>
      </Box>

      {message && (
        <Flash variant={message.type === 'error' ? 'danger' : 'success'} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

      {/* Filter by Pipeline and Job */}
      <Box sx={{ mb: 3, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
        <FormControl>
          <FormControl.Label>Filter by Pipeline</FormControl.Label>
          <Select
            value={selectedPipeline?.toString() || ''}
            onChange={(e) => {
              const value = e.target.value
              setSelectedPipeline(value ? Number(value) : null)
              setSelectedJob(null)
            }}
          >
            <Select.Option value="">All Pipelines</Select.Option>
            {pipelines.map((pipeline) => (
              <Select.Option key={pipeline.id} value={pipeline.id.toString()}>
                {pipeline.definition.name}
              </Select.Option>
            ))}
          </Select>
          <FormControl.Caption>Filter records by pipeline</FormControl.Caption>
        </FormControl>

        <FormControl>
          <FormControl.Label>Filter by Job</FormControl.Label>
          <Select
            value={selectedJob?.toString() || ''}
            onChange={(e) => {
              const value = e.target.value
              setSelectedJob(value ? Number(value) : null)
            }}
            disabled={!selectedPipeline || jobs.length === 0}
          >
            <Select.Option value="">All Jobs</Select.Option>
            {jobs.map((job) => (
              <Select.Option key={job.id} value={job.id.toString()}>
                Job #{job.id} - {job.status} - {job.records_generated} records ({new Date(job.started_at).toLocaleString()})
              </Select.Option>
            ))}
          </Select>
          <FormControl.Caption>
            {selectedPipeline ? 'Filter records by generation job' : 'Select a pipeline first'}
          </FormControl.Caption>
        </FormControl>
      </Box>

      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
        <SegmentedControl
          aria-label="Filter by status"
          onChange={(index) => {
            const statuses = ['pending', 'accepted', 'rejected'] as const
            setFilterStatus(statuses[index])
          }}
        >
          <SegmentedControl.Button selected={filterStatus === 'pending'}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'fg.default' }}>
              <ClockIcon size={16} style={{ color: '#bf8700' }} />
              <Text>Pending</Text>
              <CounterLabel>{stats.pending}</CounterLabel>
            </Box>
          </SegmentedControl.Button>
          <SegmentedControl.Button selected={filterStatus === 'accepted'}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'fg.default' }}>
              <CheckCircleIcon size={16} style={{ color: '#1a7f37' }} />
              <Text>Accepted</Text>
              <CounterLabel>{stats.accepted}</CounterLabel>
            </Box>
          </SegmentedControl.Button>
          <SegmentedControl.Button selected={filterStatus === 'rejected'}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'fg.default' }}>
              <XCircleIcon size={16} style={{ color: '#cf222e' }} />
              <Text>Rejected</Text>
              <CounterLabel>{stats.rejected}</CounterLabel>
            </Box>
          </SegmentedControl.Button>
        </SegmentedControl>
      </Box>

      {/* keyboard shortcuts hint */}
      <Box sx={{ mb: 3, display: 'flex', gap: 3, fontSize: 1, alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            as="kbd"
            sx={{
              padding: '2px 6px',
              border: '1px solid',
              borderColor: 'border.default',
              borderRadius: '3px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: 'fg.default',
              bg: 'canvas.subtle'
            }}
          >A</Box>
          <Text sx={{ color: 'fg.default' }}>Accept</Text>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            as="kbd"
            sx={{
              padding: '2px 6px',
              border: '1px solid',
              borderColor: 'border.default',
              borderRadius: '3px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: 'fg.default',
              bg: 'canvas.subtle'
            }}
          >R</Box>
          <Text sx={{ color: 'fg.default' }}>Reject</Text>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            as="kbd"
            sx={{
              padding: '2px 6px',
              border: '1px solid',
              borderColor: 'border.default',
              borderRadius: '3px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: 'fg.default',
              bg: 'canvas.subtle'
            }}
          >E</Box>
          <Text sx={{ color: 'fg.default' }}>Edit</Text>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            as="kbd"
            sx={{
              padding: '2px 6px',
              border: '1px solid',
              borderColor: 'border.default',
              borderRadius: '3px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: 'fg.default',
              bg: 'canvas.subtle'
            }}
          >N</Box>
          <Text sx={{ color: 'fg.default' }}>Next</Text>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            as="kbd"
            sx={{
              padding: '2px 6px',
              border: '1px solid',
              borderColor: 'border.default',
              borderRadius: '3px',
              fontSize: '11px',
              fontFamily: 'monospace',
              color: 'fg.default',
              bg: 'canvas.subtle'
            }}
          >P</Box>
          <Text sx={{ color: 'fg.default' }}>Previous</Text>
        </Box>
      </Box>

      {records.length === 0 ? (
        <Box
          sx={{
            textAlign: 'center',
            py: 6,
            border: '1px dashed',
            borderColor: 'border.default',
            borderRadius: 2,
          }}
        >
          <Text sx={{ color: 'fg.default' }}>No {filterStatus} records found</Text>
        </Box>
      ) : currentRecord ? (
        <Box>
          {/* progress indicator */}
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text sx={{ fontSize: 1, color: 'fg.default' }}>
              Record {currentIndex + 1} of {records.length}
            </Text>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                size="small"
                leadingVisual={ChevronLeftIcon}
                onClick={goToPrevious}
                disabled={currentIndex === 0}
              >
                Previous
              </Button>
              <Button
                size="small"
                trailingVisual={ChevronRightIcon}
                onClick={goToNext}
                disabled={currentIndex === records.length - 1}
              >
                Next
              </Button>
            </Box>
          </Box>

          {/* single card view */}
          <Box
            sx={{
              border: '1px solid',
              borderColor: 'border.default',
              borderRadius: 2,
              p: 4,
              bg: 'canvas.subtle',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Text sx={{ fontWeight: 'bold', color: 'fg.default', fontSize: 1 }}>#{currentRecord.id}</Text>
                <Label variant={getStatusVariant(currentRecord.status)}>{currentRecord.status}</Label>
              </Box>
            </Box>

            {/* final output - main focus */}
            <Box sx={{ mb: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Box sx={{ color: 'fg.default' }}>
                  <CommentIcon size={16} />
                </Box>
                <Text as="div" sx={{ fontSize: 2, fontWeight: 'bold', color: 'fg.default' }}>
                  {currentRecord.trace && currentRecord.trace.length > 0 ? 'Pipeline Output' : 'Assistant Response'}
                </Text>
              </Box>
              {isEditing ? (
                <Box>
                  <Textarea
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    rows={12}
                    sx={{
                      width: '100%',
                      fontFamily: 'mono',
                      fontSize: 1,
                      color: 'fg.default',
                      bg: 'canvas.default',
                      borderColor: 'border.default'
                    }}
                  />
                  <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                    <Button size="small" variant="primary" onClick={saveEdit}>
                      Save
                    </Button>
                    <Button size="small" onClick={() => setIsEditing(false)}>
                      Cancel
                    </Button>
                  </Box>
                </Box>
              ) : (
                <Box
                  sx={{
                    border: '1px solid',
                    borderColor: 'border.default',
                    borderRadius: 2,
                    p: 3,
                    bg: 'canvas.default',
                  }}
                >
                  <Box
                    sx={{
                      maxHeight: isExpanded ? 'none' : '200px',
                      overflow: isExpanded ? 'visible' : 'hidden',
                      position: 'relative',
                    }}
                  >
                    {(() => {
                      const output = getFinalOutput(currentRecord)
                      const outputStr = typeof output === 'string' ? output : JSON.stringify(output)
                      return (
                        <>
                          <Text as="div" sx={{ fontSize: 2, whiteSpace: 'pre-wrap', lineHeight: 1.6, color: 'fg.default' }}>
                            {outputStr}
                          </Text>
                          {!isExpanded && outputStr.length > 500 && (
                            <Box
                              sx={{
                                position: 'absolute',
                                bottom: 0,
                                left: 0,
                                right: 0,
                                height: '60px',
                                background: 'linear-gradient(transparent, var(--bgColor-default))',
                              }}
                            />
                          )}
                        </>
                      )
                    })()}
                  </Box>
                  {(() => {
                    const output = getFinalOutput(currentRecord)
                    const outputStr = typeof output === 'string' ? output : JSON.stringify(output)
                    return outputStr.length > 500 && (
                      <Button
                        size="small"
                        variant="invisible"
                        onClick={() => setIsExpanded(!isExpanded)}
                        sx={{ mt: 2 }}
                      >
                        {isExpanded ? 'Show less' : 'Show more'}
                      </Button>
                    )
                  })()}
                </Box>
              )}
            </Box>

            {/* context section - collapsible */}
            <Box
              sx={{
                border: '1px solid',
                borderColor: 'border.muted',
                borderRadius: 2,
                p: 3,
                bg: 'canvas.inset',
                mb: 3,
              }}
            >
              <details>
                <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: '12px', color: 'inherit' }}>
                  <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, color: 'fg.default' }}>
                    <Box sx={{ color: 'fg.default' }}>
                      <GearIcon size={16} />
                    </Box>
                    <Text sx={{ fontSize: 1, fontWeight: 'semibold', color: 'fg.default' }}>System & User Context</Text>
                  </Box>
                </summary>

                <Box sx={{ mt: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Box sx={{ color: 'fg.default' }}>
                      <GearIcon size={14} />
                    </Box>
                    <Text as="div" sx={{ fontSize: 1, fontWeight: 'semibold', color: 'fg.default' }}>
                      System Prompt
                    </Text>
                  </Box>
                  <Text as="div" sx={{ fontSize: 1, mb: 3, color: 'fg.default' }}>
                    {currentRecord.system}
                  </Text>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Box sx={{ color: 'fg.default' }}>
                      <PersonIcon size={14} />
                    </Box>
                    <Text as="div" sx={{ fontSize: 1, fontWeight: 'semibold', color: 'fg.default' }}>
                      User Message
                    </Text>
                  </Box>
                  <Text as="div" sx={{ fontSize: 1, color: 'fg.default' }}>
                    {currentRecord.user}
                  </Text>
                </Box>
              </details>
            </Box>

            {/* execution trace - collapsible */}
            {currentRecord.trace && currentRecord.trace.length > 0 && (
              <Box
                sx={{
                  border: '1px solid',
                  borderColor: 'border.muted',
                  borderRadius: 2,
                  p: 3,
                  bg: 'canvas.inset',
                }}
              >
                <details>
                  <summary style={{ cursor: 'pointer', fontWeight: 600, marginBottom: '12px', color: 'inherit' }}>
                    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 1, color: 'fg.default' }}>
                      <Text sx={{ fontSize: 1, fontWeight: 'semibold', color: 'fg.default' }}>
                        Execution Trace ({currentRecord.trace.length} blocks)
                      </Text>
                    </Box>
                  </summary>

                  <Box sx={{ mt: 2 }}>
                    {currentRecord.trace.map((step, index) => (
                      <Box
                        key={index}
                        sx={{
                          mb: 3,
                          pb: 3,
                          borderBottom: index < currentRecord.trace!.length - 1 ? '1px solid' : 'none',
                          borderColor: step.error ? 'danger.emphasis' : 'border.muted',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                          <Text as="div" sx={{ fontSize: 1, fontWeight: 'semibold', color: step.error ? 'danger.fg' : 'fg.default' }}>
                            {index + 1}. {step.block_type}
                          </Text>
                          {step.error && (
                            <Label variant="danger" sx={{ fontSize: 0 }}>
                              Failed
                            </Label>
                          )}
                        </Box>
                        {step.error && (
                          <Flash variant="danger" sx={{ mb: 2, fontSize: 0 }}>
                            {step.error}
                          </Flash>
                        )}
                        <Box
                          sx={{
                            fontFamily: 'mono',
                            fontSize: 0,
                            p: 2,
                            bg: 'canvas.default',
                            borderRadius: 1,
                            overflow: 'auto',
                            maxHeight: '200px',
                            color: 'fg.default',
                          }}
                        >
                          <pre style={{ margin: 0 }}>
                            {JSON.stringify({ input: step.input, output: step.output }, null, 2)}
                          </pre>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </details>
              </Box>
            )}

            {filterStatus === 'pending' && !isEditing && (
              <Box sx={{ display: 'flex', gap: 2, mt: 4 }}>
                <Button
                  variant="primary"
                  size="medium"
                  onClick={() => updateStatus(currentRecord.id, 'accepted')}
                >
                  Accept <kbd style={{ marginLeft: '8px', opacity: 0.6 }}>A</kbd>
                </Button>
                <Button
                  variant="danger"
                  size="medium"
                  onClick={() => updateStatus(currentRecord.id, 'rejected')}
                >
                  Reject <kbd style={{ marginLeft: '8px', opacity: 0.6 }}>R</kbd>
                </Button>
                <Button
                  size="medium"
                  onClick={startEditing}
                >
                  Edit <kbd style={{ marginLeft: '8px', opacity: 0.6 }}>E</kbd>
                </Button>
              </Box>
            )}
          </Box>
        </Box>
      ) : null}
    </Box>
  )
}
