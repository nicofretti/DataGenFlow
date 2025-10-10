import { Node, Edge } from "reactflow";

interface Block {
  type: string;
  name: string;
  inputs: string[];
  outputs: string[];
}

interface NodeData {
  block: Block;
  config: Record<string, any>;
  accumulatedState: string[];
}

export const DEFAULT_HANDLE_STYLE = {
  width: 10,
  height: 10,
};

/**
 * Calculate accumulated state for each node in the pipeline
 * This shows what data is available at each step
 */
export function calculateAccumulatedState(
  nodes: Node<NodeData>[],
  edges: Edge[]
): Node<NodeData>[] {
  // topological sort to get execution order
  const sorted = topologicalSort(nodes, edges);

  const accumulated = new Set<string>();
  const updatedNodes = [...nodes];

  sorted.forEach((nodeId) => {
    const nodeIndex = updatedNodes.findIndex((n) => n.id === nodeId);
    if (nodeIndex === -1) return;

    const node = updatedNodes[nodeIndex];
    const block = node.data.block;

    // add this block's outputs to accumulated state
    block.outputs.forEach((output) => accumulated.add(output));

    // update node with current accumulated state
    updatedNodes[nodeIndex] = {
      ...node,
      data: {
        ...node.data,
        accumulatedState: Array.from(accumulated),
      },
    };
  });

  return updatedNodes;
}

/**
 * Simple topological sort for sequential pipeline
 * Returns node IDs in execution order
 */
function topologicalSort(nodes: Node[], edges: Edge[]): string[] {
  // build adjacency list
  const graph: Record<string, string[]> = {};
  const inDegree: Record<string, number> = {};

  nodes.forEach((node) => {
    graph[node.id] = [];
    inDegree[node.id] = 0;
  });

  edges.forEach((edge) => {
    graph[edge.source].push(edge.target);
    inDegree[edge.target] = (inDegree[edge.target] || 0) + 1;
  });

  // find starting nodes (no incoming edges)
  const queue: string[] = [];
  nodes.forEach((node) => {
    if (inDegree[node.id] === 0) {
      queue.push(node.id);
    }
  });

  const sorted: string[] = [];

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    sorted.push(nodeId);

    graph[nodeId].forEach((neighbor) => {
      inDegree[neighbor]--;
      if (inDegree[neighbor] === 0) {
        queue.push(neighbor);
      }
    });
  }

  return sorted;
}

/**
 * Convert ReactFlow nodes/edges to our pipeline format
 * Excludes Start and End blocks (UI-only)
 */
export function convertToPipelineFormat(nodes: Node<NodeData>[], edges: Edge[]) {
  // sort nodes by execution order
  const sorted = topologicalSort(nodes, edges);

  const blocks = sorted
    .map((nodeId) => {
      const node = nodes.find((n) => n.id === nodeId);
      if (!node) return null;

      // skip Start and End blocks (UI-only)
      if (node.data.block.type === "StartBlock" || node.data.block.type === "EndBlock") {
        return null;
      }

      return {
        type: node.data.block.type,
        config: node.data.config,
      };
    })
    .filter(Boolean);

  return { blocks };
}

/**
 * Convert pipeline format to ReactFlow nodes/edges
 * Automatically adds Start/End blocks for editing
 */
export function convertFromPipelineFormat(
  pipeline: { blocks: Array<{ type: string; config: Record<string, any> }> },
  allBlocks: Block[]
): { nodes: Node<NodeData>[]; edges: Edge[] } {
  const nodes: Node<NodeData>[] = [];
  const edges: Edge[] = [];

  // define Start and End blocks
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

  // add Start node
  nodes.push({
    id: "start",
    type: "blockNode",
    position: { x: 250, y: 50 },
    data: {
      block: startBlock,
      config: {},
      accumulatedState: [],
    },
  });

  // add pipeline blocks
  pipeline.blocks.forEach((blockDef, index) => {
    const block = allBlocks.find((b) => b.type === blockDef.type);
    if (!block) return;

    // create node
    const nodeId = `${index + 1}`;
    nodes.push({
      id: nodeId,
      type: "blockNode",
      position: { x: 250, y: (index + 1) * 180 + 50 },
      data: {
        block,
        config: blockDef.config || {},
        accumulatedState: [],
      },
    });

    // create edge from previous node (or Start)
    if (index === 0) {
      // connect first block to Start
      edges.push({
        id: `e-start-1`,
        source: "start",
        target: "1",
        type: "smoothstep",
      });
    } else {
      edges.push({
        id: `e${index}-${index + 1}`,
        source: `${index}`,
        target: nodeId,
        type: "smoothstep",
      });
    }
  });

  // add End node
  const endY = (pipeline.blocks.length + 1) * 180 + 50;
  nodes.push({
    id: "end",
    type: "blockNode",
    position: { x: 250, y: endY },
    data: {
      block: endBlock,
      config: {},
      accumulatedState: [],
    },
  });

  // connect last block to End
  if (pipeline.blocks.length > 0) {
    edges.push({
      id: `e${pipeline.blocks.length}-end`,
      source: `${pipeline.blocks.length}`,
      target: "end",
      type: "smoothstep",
    });
  } else {
    // if no blocks, connect Start directly to End
    edges.push({
      id: "e-start-end",
      source: "start",
      target: "end",
      type: "smoothstep",
    });
  }

  return { nodes, edges };
}

/**
 * Auto-layout nodes vertically
 */
export function autoLayout(nodes: Node[]): Node[] {
  return nodes.map((node, index) => ({
    ...node,
    position: { x: 250, y: index * 180 + 50 },
  }));
}
