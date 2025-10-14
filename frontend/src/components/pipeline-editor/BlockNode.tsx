import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Box, Text, IconButton, Label } from "@primer/react";
import { XIcon, GearIcon } from "@primer/octicons-react";
import { DEFAULT_HANDLE_STYLE } from "./utils";

// Constants for maintainability
const BLOCK_NODE_WIDTH = "220px";
const BLOCK_NAME_MAX_WIDTH = "160px";

interface BlockData {
  block: {
    type: string;
    name: string;
    description?: string;
    inputs: string[];
    outputs: string[];
    config_schema?: Record<string, any>;
  };
  config: Record<string, any>;
  accumulatedState: string[];
  isConfigured?: boolean;
  isConnected?: boolean;
  onConfigClick?: () => void;
  onDelete?: () => void;
}

function BlockNode({ data }: NodeProps<BlockData>) {
  const {
    block,
    config,
    accumulatedState,
    isConfigured = true,
    isConnected = true,
    onConfigClick,
    onDelete,
  } = data;

  // Determine connection/configuration status
  const getStatus = () => {
    if (!isConfigured) return { label: "Not Configured", variant: "danger" as const };
    if (!isConnected) return { label: "Not Connected", variant: "attention" as const };
    return null;
  };

  const status = getStatus();

  return (
    <Box
      sx={{
        minWidth: BLOCK_NODE_WIDTH,
        border: "2px solid",
        borderColor: "border.default",
        borderRadius: 2,
        bg: "canvas.default",
        position: "relative",
        "&:hover": {
          borderColor: "accent.emphasis",
          boxShadow: "0 3px 6px rgba(0, 0, 0, 0.1)",
        },
      }}
    >
      {/* Top handle */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ ...DEFAULT_HANDLE_STYLE, background: "#555" }}
      />

      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: "1px solid",
          borderColor: "border.default",
          bg: "canvas.subtle",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, flex: 1 }}>
          <Text
            sx={{
              fontWeight: "bold",
              fontSize: 1,
              color: "fg.default",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: BLOCK_NAME_MAX_WIDTH,
              flexShrink: 1,
            }}
            title={block.name}
          >
            {block.name}
          </Text>

          {status && (
            <Label variant={status.variant} size="small">
              {status.label}
            </Label>
          )}
        </Box>

        <Box sx={{ display: "flex", gap: 1 }}>
          {onConfigClick && (
            <IconButton
              icon={GearIcon}
              aria-label="Configure block"
              size="small"
              variant="invisible"
              onClick={(e) => {
                e.stopPropagation();
                onConfigClick();
              }}
              sx={{
                color: "accent.fg",
                "&:hover": {
                  bg: "accent.subtle",
                },
              }}
            />
          )}
          {onDelete && (
            <IconButton
              icon={XIcon}
              aria-label="Delete block"
              size="small"
              variant="invisible"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              sx={{
                color: "danger.fg",
                "&:hover": {
                  bg: "danger.subtle",
                },
              }}
            />
          )}
        </Box>
      </Box>

      {/* Description */}
      {block.description && (
        <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.default" }}>
          <Text sx={{ fontSize: 0, color: "fg.muted", fontStyle: "italic" }}>
            {block.description}
          </Text>
        </Box>
      )}

      {/* Inputs/Outputs */}
      <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.default" }}>
        <Text sx={{ fontSize: 0, color: "fg.muted", display: "block", mb: 1 }}>
          <strong>IN:</strong> {block.inputs.length > 0 ? block.inputs.join(", ") : "none"}
        </Text>
        <Text sx={{ fontSize: 0, color: "fg.muted", display: "block" }}>
          <strong>OUT:</strong> {block.outputs.length > 0 ? block.outputs.join(", ") : "none"}
        </Text>
      </Box>

      {/* Config */}
      {Object.keys(config).length > 0 && (
        <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "border.default" }}>
          {Object.entries(config)
            .slice(0, 3)
            .map(([key, value]) => (
              <Text key={key} sx={{ fontSize: 0, color: "fg.muted", display: "block" }}>
                {key}: {String(value)}
              </Text>
            ))}
          {Object.keys(config).length > 3 && (
            <Text sx={{ fontSize: 0, color: "fg.muted", fontStyle: "italic" }}>
              +{Object.keys(config).length - 3} more...
            </Text>
          )}
        </Box>
      )}

      {/* Accumulated State */}
      <Box sx={{ p: 2, bg: "accent.subtle" }}>
        <Text
          sx={{ fontSize: 0, fontWeight: "bold", display: "block", mb: 1, color: "fg.default" }}
        >
          Available:
        </Text>
        <Text sx={{ fontSize: 0, color: "fg.default" }}>
          {accumulatedState.length > 0 ? accumulatedState.join(", ") : "none"}
        </Text>
      </Box>

      {/* Bottom handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ ...DEFAULT_HANDLE_STYLE, background: "#555" }}
      />
    </Box>
  );
}

export default memo(BlockNode);
