import { useCallback, useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Node,
  NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";
import { Box, Button, Flash, TextInput, useTheme } from "@primer/react";
import { XIcon } from "@primer/octicons-react";

import BlockPalette from "./BlockPalette";
import BlockNode from "./BlockNode";
import StartEndNode from "./StartEndNode";
import BlockConfigPanel from "./BlockConfigPanel";
import {
  calculateAccumulatedState,
  convertToPipelineFormat,
  convertFromPipelineFormat,
} from "./utils";

// define node types outside component to prevent recreation
const nodeTypes: NodeTypes = {
  blockNode: (props) => {
    const isStartOrEnd =
      props.data.block.type === "StartBlock" || props.data.block.type === "EndBlock";

    if (isStartOrEnd) {
      return <StartEndNode {...props} />;
    }

    return <BlockNode {...props} />;
  },
};

interface Block {
  type: string;
  name: string;
  inputs: string[];
  outputs: string[];
  config_schema: Record<string, any>;
}

interface PipelineEditorProps {
  pipelineId?: number;
  pipelineName?: string;
  initialPipeline?: {
    blocks: Array<{ type: string; config: Record<string, any> }>;
  };
  onSave: (pipeline: any) => Promise<void>;
  onClose: () => void;
}

export default function PipelineEditor({
  pipelineId: _pipelineId,
  pipelineName: initialPipelineName = "New Pipeline",
  initialPipeline,
  onSave,
  onClose,
}: PipelineEditorProps) {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [pipelineName, setPipelineName] = useState(initialPipelineName);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // minimap adjusted for light/dark mode using primer theme colors
  function MinimapWithTheme() {
    const { theme } = useTheme();
    const colors = theme?.colors;

    return (
      <MiniMap
        nodeColor={colors?.neutral.muted || "#f5f5f5"}
        style={{ backgroundColor: colors?.canvas.default || "#ffffff" }}
        nodeStrokeColor={colors?.border.default || "#d0d7de"}
        maskColor={colors?.canvas.subtle || "#f6f8fa"}
      />
    );
  }

  // check if node is configured
  const isNodeConfigured = useCallback((node: Node) => {
    const { block, config } = node.data;
    if (!block.config_schema) return true;

    // check all required fields are filled
    return Object.entries(block.config_schema).every(([key, schema]: [string, any]) => {
      if (schema.required) {
        const value = config[key];
        return value !== undefined && value !== null && value !== "";
      }
      return true;
    });
  }, []);

  // check if node is connected
  const isNodeConnected = useCallback(
    (nodeId: string) => {
      if (nodes.length <= 1) return true;

      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return false;

      const hasIncoming = edges.some((edge) => edge.target === nodeId);
      const hasOutgoing = edges.some((edge) => edge.source === nodeId);

      // Start block should only have outgoing edges
      if (node.data.block.type === "StartBlock") {
        return hasOutgoing;
      }

      // End block should only have incoming edges
      if (node.data.block.type === "EndBlock") {
        return hasIncoming;
      }

      // Regular blocks need either incoming or outgoing
      return hasIncoming || hasOutgoing;
    },
    [edges, nodes]
  );

  // handle node deletion
  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    },
    [setNodes, setEdges]
  );

  // fetch blocks on mount and initialize Start/End nodes
  useEffect(() => {
    async function fetchBlocks() {
      try {
        const res = await fetch("/api/blocks");
        const data = await res.json();

        // define special Start and End blocks (for internal use)
        const startBlock = {
          type: "StartBlock",
          name: "Start",
          description: "Pipeline entry point",
          inputs: [],
          outputs: ["*"],
          config_schema: {},
        };

        const endBlock = {
          type: "EndBlock",
          name: "End",
          description: "Pipeline exit point",
          inputs: ["*"],
          outputs: [],
          config_schema: {},
        };

        // only set regular blocks in palette (exclude Start/End)
        setBlocks(data);

        // load initial pipeline if provided
        if (initialPipeline && data.length > 0) {
          const { nodes, edges } = convertFromPipelineFormat(initialPipeline, data);
          const nodesWithState = calculateAccumulatedState(nodes, edges);
          setNodes(nodesWithState);
          setEdges(edges);
        } else {
          // auto-add Start and End nodes for new pipelines
          const startNode = {
            id: "start",
            type: "blockNode",
            position: { x: 250, y: 50 },
            data: {
              block: startBlock,
              config: {},
              accumulatedState: [],
            },
          };

          const endNode = {
            id: "end",
            type: "blockNode",
            position: { x: 250, y: 400 },
            data: {
              block: endBlock,
              config: {},
              accumulatedState: [],
            },
          };

          setNodes([startNode, endNode]);
        }
      } catch (error) {
        setMessage({ type: "error", text: `Failed to load blocks: ${error}` });
      }
    }
    fetchBlocks();
  }, [initialPipeline, setNodes, setEdges]);

  // update nodes with computed properties
  useEffect(() => {
    if (nodes.length === 0) return;

    // calculate accumulated state
    const nodesWithState = calculateAccumulatedState(nodes, edges);

    // check if accumulated state changed
    const stateChanged = nodesWithState.some((node, i) => {
      const currentState = nodes[i]?.data?.accumulatedState || [];
      const newState = node.data.accumulatedState || [];
      return JSON.stringify(currentState) !== JSON.stringify(newState);
    });

    // add computed properties
    const updatedNodes = nodesWithState.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isConfigured: isNodeConfigured(node),
        isConnected: isNodeConnected(node.id),
        onConfigClick: () => setSelectedNode(node),
        onDelete: () => handleDeleteNode(node.id),
      },
    }));

    // check if callbacks are missing on any node
    const callbacksChanged = updatedNodes.some((node, i) => {
      return !nodes[i]?.data?.onConfigClick || !nodes[i]?.data?.onDelete;
    });

    if (stateChanged || callbacksChanged) {
      setNodes(updatedNodes);
    }
  }, [nodes, edges, setNodes, isNodeConfigured, isNodeConnected, handleDeleteNode]);

  // handle new edge connection
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, type: "smoothstep" }, eds));
    },
    [setEdges]
  );

  // handle drop from palette
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const blockType = event.dataTransfer.getData("application/reactflow");
      const block = blocks.find((b) => b.type === blockType);
      if (!block) return;

      // get position
      const reactFlowBounds = event.currentTarget.getBoundingClientRect();
      const position = {
        x: event.clientX - reactFlowBounds.left - 110,
        y: event.clientY - reactFlowBounds.top,
      };

      // create new node
      const newNode: Node = {
        id: `${nodes.length + 1}`,
        type: "blockNode",
        position,
        data: {
          block,
          config: {},
          accumulatedState: [],
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [blocks, nodes, setNodes]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  // handle config update
  const handleConfigUpdate = useCallback(
    (nodeId: string, config: Record<string, any>) => {
      setNodes((nds) =>
        nds.map((node) => (node.id === nodeId ? { ...node, data: { ...node.data, config } } : node))
      );
      setSelectedNode(null);
    },
    [setNodes]
  );

  // handle save
  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      // validation: check pipeline name
      if (!pipelineName || pipelineName.trim() === "") {
        throw new Error("Pipeline name is required");
      }

      // validation: check at least one block (besides Start/End)
      if (nodes.length === 0) {
        throw new Error("Pipeline must have at least one block");
      }

      // validation: check for Start block
      const startBlocks = nodes.filter((node) => node.data.block.type === "StartBlock");
      if (startBlocks.length === 0) {
        throw new Error("Pipeline must have a Start block");
      }
      if (startBlocks.length > 1) {
        throw new Error("Pipeline can only have one Start block");
      }

      // validation: check for End block
      const endBlocks = nodes.filter((node) => node.data.block.type === "EndBlock");
      if (endBlocks.length === 0) {
        throw new Error("Pipeline must have an End block");
      }
      if (endBlocks.length > 1) {
        throw new Error("Pipeline can only have one End block");
      }

      // validation: check Start block has no incoming edges
      const startBlock = startBlocks[0];
      const startHasIncoming = edges.some((edge) => edge.target === startBlock.id);
      if (startHasIncoming) {
        throw new Error("Start block cannot have incoming connections");
      }

      // validation: check End block has no outgoing edges
      const endBlock = endBlocks[0];
      const endHasOutgoing = edges.some((edge) => edge.source === endBlock.id);
      if (endHasOutgoing) {
        throw new Error("End block cannot have outgoing connections");
      }

      // validation: check all nodes are configured
      const unconfiguredNodes = nodes.filter((node) => !isNodeConfigured(node));
      if (unconfiguredNodes.length > 0) {
        throw new Error(
          `${unconfiguredNodes.length} block(s) are not configured. Please configure all blocks.`
        );
      }

      // validation: check all nodes are connected
      const disconnectedNodes = nodes.filter((node) => !isNodeConnected(node.id));
      if (disconnectedNodes.length > 0) {
        throw new Error(
          `${disconnectedNodes.length} block(s) are not connected. Please connect all blocks.`
        );
      }

      const pipeline = convertToPipelineFormat(nodes, edges);
      await onSave({ name: pipelineName, ...pipeline });
      setMessage({ type: "success", text: "Pipeline saved successfully!" });
    } catch (error) {
      setMessage({ type: "error", text: `Failed to save: ${error}` });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <Box
        sx={{
          p: 3,
          borderBottom: "1px solid",
          borderColor: "border.default",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 3,
        }}
      >
        <Box sx={{ flex: 1, maxWidth: "400px" }}>
          <TextInput
            value={pipelineName}
            onChange={(e) => setPipelineName(e.target.value)}
            placeholder="Pipeline name"
            size="large"
            sx={{ width: "100%", fontSize: 2, fontWeight: "bold" }}
          />
        </Box>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button onClick={handleSave} disabled={saving} variant="primary">
            {saving ? "Saving..." : "Save Pipeline"}
          </Button>
          <Button onClick={onClose}>
            <XIcon /> Close
          </Button>
        </Box>
      </Box>

      {/* Message */}
      {message && (
        <Box sx={{ p: 2 }}>
          <Flash variant={message.type === "error" ? "danger" : "success"}>{message.text}</Flash>
        </Box>
      )}

      {/* Main content */}
      <Box sx={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Block Palette */}
        <BlockPalette blocks={blocks} />

        {/* ReactFlow Canvas */}
        <Box sx={{ flex: 1, position: "relative" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            edgesFocusable={true}
            nodesDraggable={true}
            nodesConnectable={true}
            nodesFocusable={true}
            elementsSelectable={true}
            deleteKeyCode="Delete"
          >
            <Background />
            <Controls />
            <MinimapWithTheme />
          </ReactFlow>
        </Box>

        {/* Config Panel */}
        {selectedNode && (
          <BlockConfigPanel
            node={selectedNode}
            onUpdate={handleConfigUpdate}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </Box>
    </Box>
  );
}
