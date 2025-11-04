import { memo, useState } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Box, Text, IconButton, useTheme } from "@primer/react";
import { KebabHorizontalIcon, GearIcon, CopyIcon, TrashIcon } from "@primer/octicons-react";

interface BlockData {
  block: {
    type: string;
    name: string;
    description?: string;
    inputs: string[];
    outputs: string[];
    config_schema?: Record<string, any>;
    category?: string;
  };
  config: Record<string, any>;
  accumulatedState: string[];
  isConfigured?: boolean;
  isConnected?: boolean;
  onConfigClick?: () => void;
  onDelete?: () => void;
  onDuplicate?: () => void;
}

type BlockCategory = "seeders" | "generators" | "validators" | "metrics";

// category color mapping
const CATEGORY_COLORS: Record<BlockCategory, string> = {
  seeders: "#10B981", // green
  generators: "#3B82F6", // blue
  validators: "#F59E0B", // orange
  metrics: "#8B5CF6", // purple
};

// get category from block data
function getBlockCategory(category?: string): BlockCategory {
  if (category && category in CATEGORY_COLORS) {
    return category as BlockCategory;
  }
  return "generators";
}

// get icon for block type
function getBlockIcon(category: BlockCategory): string {
  switch (category) {
    case "seeders":
      return "🌱";
    case "generators":
      return "🤖";
    case "validators":
      return "✅";
    case "metrics":
      return "📊";
  }
}

// determine which 1-2 config values to show as preview
function getPreviewFields(blockType: string, config: Record<string, any>): Array<[string, string]> {
  const type = blockType.toLowerCase();

  // priority fields based on block type
  let priorityKeys: string[] = [];

  if (type.includes("generator")) {
    priorityKeys = ["model", "temperature", "max_tokens"];
  } else if (type.includes("validator")) {
    priorityKeys = ["min_length", "max_length", "required_fields"];
  } else if (type.includes("score")) {
    priorityKeys = ["generated_field", "reference_field", "metric"];
  }

  // find up to 2 configured values from priority keys
  const preview: Array<[string, string]> = [];

  for (const key of priorityKeys) {
    if (config[key] !== undefined && config[key] !== null && config[key] !== "") {
      let displayValue = String(config[key]);

      // truncate long values
      if (displayValue.length > 20) {
        displayValue = displayValue.slice(0, 20) + "...";
      }

      preview.push([key, displayValue]);

      if (preview.length >= 2) break;
    }
  }

  return preview;
}

function BlockNode({ data, selected }: NodeProps<BlockData>) {
  const {
    block,
    config,
    isConfigured = true,
    isConnected = true,
    onConfigClick,
    onDelete,
    onDuplicate,
  } = data;

  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const { theme } = useTheme();

  const category = getBlockCategory(block.category);
  const categoryColor = CATEGORY_COLORS[category];
  const icon = getBlockIcon(category);
  const previewFields = getPreviewFields(block.type, config);

  // get theme colors for handles
  const handleBorderColor = theme?.colors?.canvas.default || "#ffffff";

  // determine status to show (prioritize connection over configuration)
  const getStatus = () => {
    // skip status checks for Start/End blocks
    if (block.type === "StartBlock" || block.type === "EndBlock") {
      return null;
    }

    if (!isConnected) {
      return { icon: "🔌", text: "Not connected", color: "attention.fg" };
    }
    if (!isConfigured) {
      return { icon: "⚠", text: "Needs setup", color: "attention.fg" };
    }
    return { icon: "✓", text: "Configured", color: "success.fg" };
  };

  const status = getStatus();

  return (
    <Box
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => {
        setShowTooltip(false);
        setShowQuickActions(false);
      }}
      sx={{
        width: "200px",
        minHeight: "110px",
        border: selected ? "3px solid" : "2px solid",
        borderColor: categoryColor,
        borderRadius: 2,
        bg: "canvas.default",
        position: "relative",
        transition: "transform 0.2s ease-out, box-shadow 0.2s ease-out",
        transform: showTooltip ? "scale(1.03)" : "scale(1)",
        boxShadow: selected ? `0 0 0 3px ${categoryColor}40` : "none",
        "&:hover": {
          cursor: "pointer",
        },
      }}
    >
      {/* Input Handle (left side, centered) */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          width: 12,
          height: 12,
          background: categoryColor,
          border: `2px solid ${handleBorderColor}`,
          left: -6,
        }}
      />

      {/* Top Bar */}
      <Box
        onMouseEnter={() => setShowQuickActions(true)}
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          borderBottom: "1px solid",
          borderColor: "border.default",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1, minWidth: 0 }}>
          <Text sx={{ fontSize: "16px" }}>{icon}</Text>
          <Text
            sx={{
              fontSize: "13px",
              fontWeight: "bold",
              color: "fg.default",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {block.name}
          </Text>
        </Box>

        {/* Quick Actions Menu */}
        {showQuickActions && (
          <Box
            sx={{
              display: "flex",
              gap: 0,
              bg: "canvas.subtle",
              borderRadius: 1,
              border: "1px solid",
              borderColor: "border.default",
            }}
          >
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
                  "&:hover": { bg: "accent.subtle" },
                  p: 1,
                }}
              />
            )}
            {onDuplicate && (
              <IconButton
                icon={CopyIcon}
                aria-label="Duplicate block"
                size="small"
                variant="invisible"
                onClick={(e) => {
                  e.stopPropagation();
                  onDuplicate();
                }}
                sx={{
                  color: "fg.muted",
                  "&:hover": { bg: "neutral.subtle" },
                  p: 1,
                }}
              />
            )}
            {onDelete && (
              <IconButton
                icon={TrashIcon}
                aria-label="Delete block"
                size="small"
                variant="invisible"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
                sx={{
                  color: "danger.fg",
                  "&:hover": { bg: "danger.subtle" },
                  p: 1,
                }}
              />
            )}
          </Box>
        )}

        {/* Three-dot icon when not hovering */}
        {!showQuickActions && (
          <Box sx={{ color: "fg.muted" }}>
            <KebabHorizontalIcon size={16} />
          </Box>
        )}
      </Box>

      {/* Middle Section - Preview */}
      <Box
        sx={{
          p: 2,
          minHeight: "40px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        {previewFields.length > 0 ? (
          previewFields.map(([key, value]) => (
            <Text
              key={key}
              sx={{
                fontSize: "11px",
                color: "fg.muted",
                mb: 0.5,
              }}
            >
              {key}: {value}
            </Text>
          ))
        ) : (
          <Text
            sx={{
              fontSize: "11px",
              color: "fg.muted",
              fontStyle: "italic",
            }}
          >
            {isConfigured ? "No preview" : "Not configured yet"}
          </Text>
        )}
      </Box>

      {/* Bottom Status Bar */}
      {status && (
        <Box
          sx={{
            p: 2,
            borderTop: "1px solid",
            borderColor: "border.default",
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <Text sx={{ fontSize: "10px", color: status.color }}>{status.icon}</Text>
          <Text sx={{ fontSize: "10px", color: status.color }}>{status.text}</Text>
        </Box>
      )}

      {/* Output Handle (right side, centered) */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          width: 12,
          height: 12,
          background: categoryColor,
          border: `2px solid ${handleBorderColor}`,
          right: -6,
        }}
      />

      {/* Tooltip */}
      {showTooltip && (
        <Box
          sx={{
            position: "absolute",
            bottom: "100%",
            left: "50%",
            transform: "translateX(-50%)",
            mb: 2,
            p: 2,
            bg: "canvas.overlay",
            border: "1px solid",
            borderColor: "border.default",
            borderRadius: 2,
            boxShadow: "shadow.large",
            minWidth: "250px",
            maxWidth: "300px",
            zIndex: 1000,
            pointerEvents: "none",
          }}
        >
          <Text sx={{ fontWeight: "bold", fontSize: 1, mb: 1, color: "fg.default" }}>
            {block.name}
          </Text>
          {block.description && (
            <Text sx={{ fontSize: 0, color: "fg.muted", mb: 1, display: "block" }}>
              {block.description}
            </Text>
          )}
          <Text sx={{ fontSize: "11px", color: "fg.muted", display: "block" }}>
            IN: {block.inputs.length > 0 ? block.inputs.slice(0, 3).join(", ") : "none"}
            {block.inputs.length > 3 && "..."}
          </Text>
          <Text sx={{ fontSize: "11px", color: "fg.muted", display: "block" }}>
            OUT: {block.outputs.length > 0 ? block.outputs.slice(0, 3).join(", ") : "none"}
            {block.outputs.length > 3 && "..."}
          </Text>
        </Box>
      )}
    </Box>
  );
}

export default memo(BlockNode);
