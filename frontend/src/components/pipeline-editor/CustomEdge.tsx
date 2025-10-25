import { memo } from "react";
import { EdgeProps, getBezierPath, EdgeLabelRenderer, useReactFlow } from "reactflow";
import { Box, IconButton, useTheme } from "@primer/react";
import { XIcon } from "@primer/octicons-react";

interface CustomEdgeData {
  sourceType?: string;
  targetType?: string;
  isValid?: boolean;
  categoryColor?: string;
}

function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
  data,
}: EdgeProps<CustomEdgeData>) {
  const { theme } = useTheme();
  const { setEdges } = useReactFlow();

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isValid = data?.isValid !== false;
  const categoryColor = data?.categoryColor || "#3B82F6";
  const errorColor = theme?.colors?.danger.fg || "#f85149";

  const handleDelete = () => {
    setEdges((edges) => edges.filter((edge) => edge.id !== id));
  };

  return (
    <>
      {/* Main edge path */}
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          stroke: isValid ? categoryColor : errorColor,
          strokeWidth: selected ? 3 : 2,
          opacity: selected ? 1 : 0.7,
          strokeDasharray: isValid ? "none" : "4 4",
          transition: "stroke-width 0.2s ease-out, opacity 0.2s ease-out",
          filter: selected ? `drop-shadow(0 0 4px ${categoryColor})` : "none",
        }}
      />

      {/* Arrow marker */}
      <defs>
        <marker
          id={`arrow-${id}`}
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path
            d="M 0 0 L 10 5 L 0 10 z"
            fill={isValid ? categoryColor : errorColor}
            opacity={selected ? 1 : 0.7}
          />
        </marker>
      </defs>
      <path
        d={edgePath}
        style={{
          stroke: "transparent",
          strokeWidth: 3,
          fill: "none",
          markerEnd: `url(#arrow-${id})`,
        }}
      />

      {/* Delete button when selected */}
      {selected && (
        <EdgeLabelRenderer>
          <Box
            sx={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "all",
            }}
          >
            <IconButton
              icon={XIcon}
              aria-label="Delete connection"
              size="small"
              variant="danger"
              onClick={handleDelete}
              sx={{
                width: 24,
                height: 24,
                minWidth: 24,
                p: 0,
                bg: "danger.emphasis",
                color: "fg.onEmphasis",
                border: "2px solid",
                borderColor: "canvas.default",
                "&:hover": {
                  bg: "danger.fg",
                },
              }}
            />
          </Box>
        </EdgeLabelRenderer>
      )}

      {/* Error icon for invalid connections */}
      {!isValid && (
        <EdgeLabelRenderer>
          <Box
            sx={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "none",
              fontSize: "12px",
            }}
          >
            ❌
          </Box>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export default memo(CustomEdge);
