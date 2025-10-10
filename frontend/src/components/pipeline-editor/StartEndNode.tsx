import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Box, Text, Label, useDetails } from "@primer/react";
import { DEFAULT_HANDLE_STYLE } from "./utils";

interface StartEndData {
  block: {
    type: string;
    name: string;
  };
  isConnected?: boolean;
}

function StartEndNode({ data }: NodeProps<StartEndData>) {
  const { block, isConnected = true } = data;
  const isStart = block.type === "StartBlock";

  return (
    <Box
      sx={{
        position: "relative",
      }}
    >
      {/* Only show input handle for End block */}
      {!isStart && (
        <Handle
          type="target"
          position={Position.Top}
          style={{ ...DEFAULT_HANDLE_STYLE, background: "#555" }}
        />
      )}

      {/* Circular node */}
      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
        {!isConnected && block.name == "Start" && (
          <Label variant="attention" size="small">
            Not Connected
          </Label>
        )}
        <Box
          sx={{
            width: "80px",
            height: "80px",
            borderRadius: "50%",
            border: "3px solid",
            borderColor: isStart ? "success.emphasis" : "done.emphasis",
            bg: isStart ? "success.subtle" : "done.subtle",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 1,
            "&:hover": {
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
              transform: "scale(1.05)",
              transition: "all 0.2s",
            },
          }}
        >
          <Text
            sx={{
              fontSize: 2,
              fontWeight: "bold",
              color: "fg.default",
              textAlign: "center",
            }}
          >
            {block.name}
          </Text>
        </Box>
        {!isConnected && block.name == "End" && (
          <Label variant="attention" size="small">
            Not Connected
          </Label>
        )}
      </Box>

      {/* Only show output handle for Start block */}
      {isStart && (
        <Handle
          type="source"
          position={Position.Bottom}
          style={{ ...DEFAULT_HANDLE_STYLE, background: "#555" }}
        />
      )}
    </Box>
  );
}

export default memo(StartEndNode);
