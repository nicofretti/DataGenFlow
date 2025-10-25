import { useCallback, useEffect, useState, useRef, useMemo } from "react";
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
  EdgeTypes,
  ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import "../../styles/pipeline-editor.css";
import { Box, Button, Flash, Text, TextInput, useTheme } from "@primer/react";
import { XIcon, ZapIcon } from "@primer/octicons-react";

import BlockPalette from "./BlockPalette";
import BlockNode from "./BlockNode";
import StartEndNode from "./StartEndNode";
import BlockConfigPanel from "./BlockConfigPanel";
import CustomEdge from "./CustomEdge";
import { getLayoutedElements } from "./layoutUtils";
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

// define edge types
const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
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
  const { theme } = useTheme();
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

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
    if (!block.config_schema?.properties) return true;

    // check all required fields are filled
    const required = block.config_schema.required || [];
    return required.every((key: string) => {
      const value = config[key];
      return value !== undefined && value !== null && value !== "";
    });
  }, []);

  // check if node is connected
  const isNodeConnected = useCallback(
    (nodeId: string) => {
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

  // handle node duplication
  const handleDuplicateNode = useCallback(
    (nodeId: string) => {
      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return;

      // create new node with same data but new ID and offset position
      const newNode: Node = {
        ...node,
        id: `${Date.now()}`,
        position: {
          x: node.position.x + 50,
          y: node.position.y + 50,
        },
      };

      setNodes((nds) => [...nds, newNode]);
    },
    [nodes, setNodes]
  );

  // handle auto-layout
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodes, edges, "TB");

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    // fit view after layout with a small delay to ensure nodes are positioned
    setTimeout(() => {
      reactFlowInstance.current?.fitView({ padding: 0.2, duration: 300 });
    }, 50);
  }, [nodes, edges, setNodes, setEdges]);

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

          // apply auto-layout on initial load
          const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
            nodesWithState,
            edges,
            "TB"
          );

          setNodes(layoutedNodes);
          setEdges(layoutedEdges);

          // fit view after initial layout
          setTimeout(() => {
            reactFlowInstance.current?.fitView({ padding: 0.2, duration: 300 });
          }, 100);
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
        onDuplicate: () => handleDuplicateNode(node.id),
      },
    }));

    // check if callbacks are missing on any node
    const callbacksChanged = updatedNodes.some((node, i) => {
      return (
        !nodes[i]?.data?.onConfigClick || !nodes[i]?.data?.onDelete || !nodes[i]?.data?.onDuplicate
      );
    });

    // check if configuration status changed
    const configStatusChanged = updatedNodes.some((node, i) => {
      return nodes[i]?.data?.isConfigured !== node.data.isConfigured;
    });

    // check if connection status changed
    const connectionStatusChanged = updatedNodes.some((node, i) => {
      return nodes[i]?.data?.isConnected !== node.data.isConnected;
    });

    if (stateChanged || callbacksChanged || configStatusChanged || connectionStatusChanged) {
      setNodes(updatedNodes);
    }
  }, [
    nodes,
    edges,
    setNodes,
    isNodeConfigured,
    isNodeConnected,
    handleDeleteNode,
    handleDuplicateNode,
  ]);

  // handle new edge connection
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, type: "custom" }, eds));
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

  // compute available fields from previous blocks
  const getAvailableFields = useCallback(
    (currentNode: Node | null): string[] => {
      if (!currentNode) return [];

      // find all nodes that come before this node in the pipeline
      const predecessors = new Set<string>();
      const visited = new Set<string>();

      const findPredecessors = (nodeId: string) => {
        if (visited.has(nodeId)) return;
        visited.add(nodeId);

        edges.forEach((edge) => {
          if (edge.target === nodeId) {
            predecessors.add(edge.source);
            findPredecessors(edge.source);
          }
        });
      };

      findPredecessors(currentNode.id);

      // collect all outputs from predecessor nodes
      const availableFields = new Set<string>();

      nodes.forEach((node) => {
        if (predecessors.has(node.id)) {
          const outputs = node.data.block.outputs || [];
          outputs.forEach((output: string) => {
            if (output !== "*") {
              availableFields.add(output);
            }
          });
        }
      });

      return Array.from(availableFields).sort();
    },
    [nodes, edges]
  );

  // handle config update
  const handleConfigUpdate = useCallback(
    (nodeId: string, config: Record<string, any>) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === nodeId) {
            return { ...node, data: { ...node.data, config } };
          }
          return node;
        })
      );
      // close the panel after updating
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

  // calculate pipeline validity
  const isPipelineValid = useMemo(() => {
    if (nodes.length === 0) return false;

    // check all nodes are configured and connected
    return nodes.every((node) => {
      const isConfigured = isNodeConfigured(node);
      const isConnected = isNodeConnected(node.id);
      return isConfigured && isConnected;
    });
  }, [nodes, isNodeConfigured, isNodeConnected]);

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
          height: "60px",
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

        {/* Status indicator */}
        {nodes.length > 0 && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 2,
              py: 1,
              borderRadius: 2,
              border: "1px solid",
              borderColor: isPipelineValid ? "success.emphasis" : "danger.emphasis",
              bg: isPipelineValid ? "success.subtle" : "danger.subtle",
            }}
          >
            <Box
              sx={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                bg: isPipelineValid ? "success.fg" : "danger.fg",
              }}
            />
            <Text
              sx={{
                fontSize: 1,
                fontWeight: "bold",
                color: isPipelineValid ? "success.fg" : "danger.fg",
              }}
            >
              {isPipelineValid ? "Valid" : "Invalid"}
            </Text>
          </Box>
        )}

        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          {/* Auto-layout button */}
          <Button
            onClick={handleAutoLayout}
            disabled={nodes.length < 2}
            variant="invisible"
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <ZapIcon size={16} />
            Auto-layout
          </Button>
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
        <Box sx={{ flex: 1, position: "relative", bg: "canvas.inset" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onInit={(instance) => {
              reactFlowInstance.current = instance;
            }}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            edgesFocusable={true}
            nodesDraggable={true}
            nodesConnectable={true}
            nodesFocusable={true}
            elementsSelectable={true}
            deleteKeyCode="Delete"
            fitView
          >
            <Background color={theme?.colors?.border.muted || "#e1e4e8"} gap={20} size={2} />
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
            availableFields={getAvailableFields(selectedNode)}
          />
        )}
      </Box>
    </Box>
  );
}
