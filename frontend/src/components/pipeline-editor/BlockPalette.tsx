import { useState, useMemo } from "react";
import { Box, Text, TextInput, Tooltip } from "@primer/react";
import { SearchIcon, ChevronDownIcon, ChevronRightIcon } from "@primer/octicons-react";

interface Block {
  type: string;
  name: string;
  description?: string;
  inputs: string[];
  outputs: string[];
  config_schema: Record<string, any>;
  category: string;
  source?: string;
  available?: boolean;
  error?: string | null;
}

interface BlockPaletteProps {
  blocks: Block[];
}

type BlockCategory = "seeders" | "generators" | "validators" | "metrics";

interface CategorizedBlocks {
  [key: string]: Block[];
}

// categorize blocks using backend category field
function categorizeBlocks(blocks: Block[]): CategorizedBlocks {
  const categorized: CategorizedBlocks = {
    seeders: [],
    generators: [],
    validators: [],
    metrics: [],
  };

  blocks.forEach((block) => {
    const category = block.category || "generators";
    if (category in categorized) {
      categorized[category].push(block);
    } else {
      categorized.generators.push(block);
    }
  });

  return categorized;
}

// category metadata
const CATEGORY_INFO: Record<BlockCategory, { icon: string; label: string; color: string }> = {
  seeders: { icon: "🌱", label: "Seeders", color: "#10B981" },
  generators: { icon: "🤖", label: "Generators", color: "#3B82F6" },
  validators: { icon: "✅", label: "Validators", color: "#F59E0B" },
  metrics: { icon: "📊", label: "Metrics", color: "#8B5CF6" },
};

export default function BlockPalette({ blocks }: BlockPaletteProps) {
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({
    seeders: false,
    generators: false,
    validators: false,
    metrics: false,
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
      seeders: [],
      generators: [],
      validators: [],
      metrics: [],
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
                {isCollapsed ? <ChevronRightIcon size={12} /> : <ChevronDownIcon size={12} />}
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
                  {blocks.map((block) => {
                    const isAvailable = block.available !== false;
                    const blockItem = (
                      <Box
                        key={block.type}
                        draggable={isAvailable}
                        onDragStart={
                          isAvailable
                            ? (e: React.DragEvent<HTMLDivElement>) => onDragStart(e, block.type)
                            : undefined
                        }
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          p: 2,
                          mb: 1,
                          borderRadius: 1,
                          bg: isAvailable ? "canvas.subtle" : "neutral.subtle",
                          cursor: isAvailable ? "grab" : "not-allowed",
                          borderLeft: "2px solid",
                          borderColor: isAvailable ? info.color : "border.muted",
                          opacity: isAvailable ? 1 : 0.5,
                          "&:hover": isAvailable
                            ? { bg: "accent.subtle" }
                            : {},
                          "&:active": isAvailable
                            ? { cursor: "grabbing" }
                            : {},
                        }}
                      >
                        <Text
                          sx={{
                            fontSize: "13px",
                            color: isAvailable ? "fg.default" : "fg.muted",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            flex: 1,
                          }}
                        >
                          {block.name}
                        </Text>
                        {block.source && block.source !== "builtin" && (
                          <Text
                            sx={{
                              fontSize: "10px",
                              color: "fg.muted",
                              bg: "neutral.subtle",
                              px: 1,
                              borderRadius: 1,
                            }}
                          >
                            {block.source}
                          </Text>
                        )}
                      </Box>
                    );

                    if (!isAvailable && block.error) {
                      return (
                        <Tooltip key={block.type} aria-label={block.error} direction="e">
                          {blockItem}
                        </Tooltip>
                      );
                    }

                    return blockItem;
                  })}
                </Box>
              )}
            </Box>
          );
        })}

        {/* Empty state */}
        {search && Object.values(categorizedBlocks).every((blocks) => blocks.length === 0) && (
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
