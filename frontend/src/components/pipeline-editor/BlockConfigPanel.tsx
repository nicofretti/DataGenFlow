import { useState } from 'react'
import { Box, Heading, Button, TextInput, Checkbox, Text } from '@primer/react'
import { XIcon } from '@primer/octicons-react'
import { Node } from 'reactflow'

interface BlockConfigPanelProps {
  node: Node
  onUpdate: (nodeId: string, config: Record<string, any>) => void
  onClose: () => void
}

export default function BlockConfigPanel({
  node,
  onUpdate,
  onClose,
}: BlockConfigPanelProps) {
  const { block, config } = node.data
  const [formData, setFormData] = useState<Record<string, any>>(config || {})

  const handleChange = (key: string, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = () => {
    onUpdate(node.id, formData)
  }

  const renderField = (key: string, schema: any) => {
    const value = formData[key] ?? schema.default ?? ''

    // boolean field
    if (schema.type === 'boolean') {
      return (
        <Checkbox
          checked={value}
          onChange={(e) => handleChange(key, e.target.checked)}
        />
      )
    }

    // number field
    if (schema.type === 'number' || schema.type === 'integer') {
      return (
        <TextInput
          type="number"
          value={value}
          onChange={(e) => handleChange(key, parseFloat(e.target.value))}
          sx={{ width: '100%' }}
        />
      )
    }

    // string field (default)
    return (
      <TextInput
        value={value}
        onChange={(e) => handleChange(key, e.target.value)}
        sx={{ width: '100%' }}
      />
    )
  }

  return (
    <Box
      sx={{
        width: '300px',
        borderLeft: '1px solid',
        borderColor: 'border.default',
        p: 3,
        overflowY: 'auto',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Heading sx={{ fontSize: 2, color: 'fg.default' }}>Configure</Heading>
        <Button
          onClick={onClose}
          variant="invisible"
          sx={{ p: 1, minWidth: 'auto' }}
        >
          <XIcon />
        </Button>
      </Box>

      {/* Block name */}
      <Box sx={{ mb: 3 }}>
        <Text sx={{ fontWeight: 'bold', display: 'block', mb: 2, color: 'fg.default' }}>
          {block.name}
        </Text>
        <Text sx={{ fontSize: 0, color: 'fg.muted' }}>
          {block.type}
        </Text>
      </Box>

      {/* Config fields */}
      <Box sx={{ flex: 1, mb: 3 }}>
        {Object.entries(block.config_schema || {}).map(([key, schema]: [string, any]) => (
          <Box key={key} sx={{ mb: 3 }}>
            <Text
              sx={{
                fontSize: 1,
                fontWeight: 'bold',
                display: 'block',
                mb: 1,
                color: 'fg.default',
              }}
            >
              {key}
              {schema.required && (
                <Text as="span" sx={{ color: 'danger.fg', ml: 1 }}>
                  *
                </Text>
              )}
            </Text>
            {schema.description && (
              <Text
                sx={{
                  fontSize: 0,
                  color: 'fg.muted',
                  display: 'block',
                  mb: 1,
                }}
              >
                {schema.description}
              </Text>
            )}
            {renderField(key, schema)}
          </Box>
        ))}
      </Box>

      {/* Actions */}
      <Box sx={{ display: 'flex', gap: 2 }}>
        <Button onClick={handleSave} variant="primary" sx={{ flex: 1 }}>
          Save
        </Button>
        <Button onClick={onClose} sx={{ flex: 1 }}>
          Cancel
        </Button>
      </Box>
    </Box>
  )
}
