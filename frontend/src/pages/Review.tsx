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
} from '@primer/react'
import { CheckIcon, XIcon, PencilIcon, ChevronLeftIcon, ChevronRightIcon, CommentIcon, PersonIcon, GearIcon, ClockIcon, CheckCircleIcon, XCircleIcon } from '@primer/octicons-react'

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
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const [filterStatus, setFilterStatus] = useState<'pending' | 'accepted' | 'rejected'>('pending')
  const [stats, setStats] = useState({ pending: 0, accepted: 0, rejected: 0 })

  const currentRecord = records[currentIndex] || null

  useEffect(() => {
    loadRecords()
    loadStats()
  }, [filterStatus])

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

  const loadRecords = async () => {
    const res = await fetch(`/api/records?status=${filterStatus}&limit=20`)
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

  const startEditing = () => {
    if (!currentRecord) return
    setIsEditing(true)
    setEditValue(currentRecord.assistant)
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
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Heading sx={{ mb: 2, color: 'fg.default' }}>Review Records</Heading>
          <Text sx={{ color: 'fg.default' }}>
            Review and validate generated Q&A pairs • Use keyboard shortcuts
          </Text>
        </Box>

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

            {/* assistant response - main focus */}
            <Box sx={{ mb: 4 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Box sx={{ color: 'fg.default' }}>
                  <CommentIcon size={16} />
                </Box>
                <Text as="div" sx={{ fontSize: 2, fontWeight: 'bold', color: 'fg.default' }}>
                  Assistant Response
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
                    <Text as="div" sx={{ fontSize: 2, whiteSpace: 'pre-wrap', lineHeight: 1.6, color: 'fg.default' }}>
                      {currentRecord.assistant}
                    </Text>
                    {!isExpanded && currentRecord.assistant.length > 500 && (
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
                  </Box>
                  {currentRecord.assistant.length > 500 && (
                    <Button
                      size="small"
                      variant="invisible"
                      onClick={() => setIsExpanded(!isExpanded)}
                      sx={{ mt: 2 }}
                    >
                      {isExpanded ? 'Show less' : 'Show more'}
                    </Button>
                  )}
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
