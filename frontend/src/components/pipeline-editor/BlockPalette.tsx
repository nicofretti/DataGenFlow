import { useState, useMemo } from "react";
import { Box, Heading, Text, TextInput, Label } from "@primer/react";
import { SearchIcon } from "@primer/octicons-react";

interface Block {
  type: string;
  name: string;
  description?: string;
  algorithm?: string;
  paper?: string;
  inputs: string[];
  outputs: string[];
  config_schema: Record<string, any>;
}

interface BlockPaletteProps {
  blocks: Block[];
}

export default function BlockPalette({ blocks }: BlockPaletteProps) {
  const [search, setSearch] = useState("");

  const onDragStart = (event: React.DragEvent, blockType: string) => {
    event.dataTransfer.setData("application/reactflow", blockType);
    event.dataTransfer.effectAllowed = "move";
  };

  // filter blocks by search term
  const filteredBlocks = useMemo(() => {
    if (!search) return blocks;
    const searchLower = search.toLowerCase();
    return blocks.filter(
      (block) =>
        block.name.toLowerCase().includes(searchLower) ||
        block.type.toLowerCase().includes(searchLower)
    );
  }, [blocks, search]);

  return (
    <Box
      sx={{
        width: "280px",
        borderRight: "1px solid",
        borderColor: "border.default",
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      {/* Header */}
      <Box sx={{ p: 3, borderBottom: "1px solid", borderColor: "border.default" }}>
        <Heading sx={{ fontSize: 2, mb: 2, color: "fg.default" }}>Available Blocks</Heading>
        <TextInput
          leadingVisual={SearchIcon}
          placeholder="Search blocks..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ width: "100%" }}
        />
      </Box>

      {/* Block list */}
      <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
        {filteredBlocks.length === 0 ? (
          <Text sx={{ color: "fg.muted", fontSize: 1, textAlign: "center", py: 4 }}>
            No blocks found
          </Text>
        ) : (
          filteredBlocks.map((block) => (
            <Box
              key={block.type}
              draggable
              onDragStart={(e: React.DragEvent<HTMLDivElement>) => onDragStart(e, block.type)}
              sx={{
                p: 2,
                mb: 1,
                borderRadius: 2,
                bg: "canvas.subtle",
                cursor: "grab",
                borderLeft: "3px solid",
                borderColor: "accent.emphasis",
                "&:hover": {
                  bg: "accent.subtle",
                  borderColor: "accent.fg",
                },
                "&:active": {
                  cursor: "grabbing",
                },
              }}
            >
              <Text
                sx={{
                  fontWeight: "bold",
                  fontSize: 1,
                  display: "block",
                  mb: 1,
                  color: "fg.default",
                }}
              >
                {block.name}
              </Text>
              {block.algorithm && (
                <Box sx={{ mb: 1 }}>
                  <Label variant="accent" size="small">
                    {block.algorithm}
                  </Label>
                </Box>
              )}
              <Text sx={{ fontSize: 0, color: "fg.muted", display: "block" }}>
                IN: {block.inputs.length > 0 ? block.inputs.join(", ") : "none"}
              </Text>
              <Text sx={{ fontSize: 0, color: "fg.muted", display: "block" }}>
                OUT: {block.outputs.length > 0 ? block.outputs.join(", ") : "none"}
              </Text>
            </Box>
          ))
        )}
      </Box>
    </Box>
  );
}
