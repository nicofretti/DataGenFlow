import { useState, useMemo } from "react";
import { Box, Text, TextInput } from "@primer/react";
import { SearchIcon, ChevronDownIcon, ChevronRightIcon } from "@primer/octicons-react";

interface Block {
  type: string;
  name: string;
  description?: string;
  inputs: string[];
  outputs: string[];
  config_schema: Record<string, any>;
}

interface BlockPaletteProps {
  blocks: Block[];
}

type BlockCategory = "generator" | "validator" | "score" | "output";

interface CategorizedBlocks {
  [key: string]: Block[];
}

// categorize blocks based on type
function categorizeBlocks(blocks: Block[]): CategorizedBlocks {
  const categorized: CategorizedBlocks = {
    generator: [],
    validator: [],
    score: [],
    output: [],
  };

  blocks.forEach((block) => {
    const type = block.type.toLowerCase();

    if (type.includes("generator") || type.includes("formatter")) {
      categorized.generator.push(block);
    } else if (type.includes("validator")) {
      categorized.validator.push(block);
    } else if (type.includes("score") || type.includes("metric")) {
      categorized.score.push(block);
    } else if (type.includes("output") || type.includes("pipeline")) {
      categorized.output.push(block);
    } else {
      // default to generator
      categorized.generator.push(block);
    }
  });

  return categorized;
}

// category metadata
const CATEGORY_INFO: Record<BlockCategory, { icon: string; label: string; color: string }> = {
  generator: { icon: "🤖", label: "Generators", color: "#3B82F6" },
  validator: { icon: "✅", label: "Validators", color: "#10B981" },
  score: { icon: "📊", label: "Scores", color: "#8B5CF6" },
  output: { icon: "📤", label: "Output", color: "#F59E0B" },
};

export default function BlockPalette({ blocks }: BlockPaletteProps) {
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({
    generator: false,
    validator: false,
    score: false,
    output: false,
  });

  const onDragStart = (event: React.DragEvent, blockType: string) => {
    event.dataTransfer.setData("application/reactflow", blockType);
    event.dataTransfer.effectAllowed = "move";
  };

  // categorize and filter blocks
  const categorizedBlocks = useMemo(() => {
    const categorized = categorizeBlocks(blocks);

    if (!search) return categorized;

    // filter by search term
    const searchLower = search.toLowerCase();
    const filtered: CategorizedBlocks = {
      generator: [],
      validator: [],
      score: [],
      output: [],
    };

    Object.entries(categorized).forEach(([category, categoryBlocks]) => {
      filtered[category] = categoryBlocks.filter(
        (block) =>
          block.name.toLowerCase().includes(searchLower) ||
          block.type.toLowerCase().includes(searchLower) ||
          (block.description && block.description.toLowerCase().includes(searchLower))
      );
    });

    return filtered;
  }, [blocks, search]);

  const toggleCategory = (category: string) => {
    setCollapsed((prev) => ({ ...prev, [category]: !prev[category] }));
  };

  return (
    <Box
      sx={{
        width: "240px",
        borderRight: "1px solid",
        borderColor: "border.default",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        bg: "canvas.default",
      }}
    >
      {/* Header with search */}
      <Box
        sx={{
          p: 3,
          borderBottom: "1px solid",
          borderColor: "border.default",
          position: "sticky",
          top: 0,
          bg: "canvas.default",
          zIndex: 10,
        }}
      >
        <TextInput
          leadingVisual={SearchIcon}
          placeholder="Search blocks..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ width: "100%" }}
        />
      </Box>

      {/* Block categories */}
      <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
        {(Object.keys(categorizedBlocks) as BlockCategory[]).map((category) => {
          const blocks = categorizedBlocks[category];
          const info = CATEGORY_INFO[category];
          const isCollapsed = collapsed[category];

          // skip empty categories when searching
          if (search && blocks.length === 0) return null;

          return (
            <Box key={category} sx={{ mb: 2 }}>
              {/* Category Header */}
              <Box
                onClick={() => toggleCategory(category)}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  p: 2,
                  cursor: "pointer",
                  borderRadius: 1,
                  "&:hover": {
                    bg: "neutral.subtle",
                  },
                }}
              >
                {isCollapsed ? (
                  <ChevronRightIcon size={12} />
                ) : (
                  <ChevronDownIcon size={12} />
                )}
                <Text sx={{ fontSize: "14px" }}>{info.icon}</Text>
                <Text
                  sx={{
                    fontSize: "13px",
                    fontWeight: "bold",
                    color: "fg.default",
                    flex: 1,
                  }}
                >
                  {info.label}
                </Text>
                <Text
                  sx={{
                    fontSize: "11px",
                    color: "fg.muted",
                    bg: "neutral.subtle",
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                  }}
                >
                  {blocks.length}
                </Text>
              </Box>

              {/* Block Items */}
              {!isCollapsed && (
                <Box sx={{ ml: 3, mt: 1 }}>
                  {blocks.map((block) => (
                    <Box
                      key={block.type}
                      draggable
                      onDragStart={(e: React.DragEvent<HTMLDivElement>) =>
                        onDragStart(e, block.type)
                      }
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        p: 2,
                        mb: 1,
                        borderRadius: 1,
                        bg: "canvas.subtle",
                        cursor: "grab",
                        borderLeft: "2px solid",
                        borderColor: info.color,
                        "&:hover": {
                          bg: "accent.subtle",
                        },
                        "&:active": {
                          cursor: "grabbing",
                        },
                      }}
                    >
                      {/* <Text sx={{ fontSize: "14px" }}>{info.icon}</Text> */}
                      <Text
                        sx={{
                          fontSize: "13px",
                          color: "fg.default",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {block.name}
                      </Text>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          );
        })}

        {/* Empty state */}
        {search &&
          Object.values(categorizedBlocks).every((blocks) => blocks.length === 0) && (
            <Text
              sx={{
                color: "fg.muted",
                fontSize: 1,
                textAlign: "center",
                py: 4,
              }}
            >
              No blocks found
            </Text>
          )}
      </Box>
    </Box>
  );
}
