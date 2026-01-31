import { useEffect, useState } from "react";
import { Box, Heading, Text, Button, Spinner, Label } from "@primer/react";
import { SyncIcon, CheckCircleFillIcon, XCircleFillIcon, PackageIcon } from "@primer/octicons-react";
import { toast } from "sonner";
import type { BlockInfo, TemplateInfo, ExtensionsStatus } from "../types";
import { extensionsApi } from "../services/extensionsApi";

export default function Extensions() {
  const [status, setStatus] = useState<ExtensionsStatus | null>(null);
  const [blocks, setBlocks] = useState<BlockInfo[]>([]);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [s, b, t] = await Promise.all([
        extensionsApi.getStatus(),
        extensionsApi.listBlocks(),
        extensionsApi.listTemplates(),
      ]);
      setStatus(s);
      setBlocks(b);
      setTemplates(t);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to load extensions: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReload = async () => {
    setReloading(true);
    try {
      await extensionsApi.reload();
      await loadAll();
      toast.success("Extensions reloaded");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to reload: ${message}`);
    } finally {
      setReloading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <Spinner size="large" />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 4 }}>
        <Heading sx={{ color: "fg.default" }}>Extensions</Heading>
        <Button
          leadingVisual={SyncIcon}
          onClick={handleReload}
          disabled={reloading}
        >
          {reloading ? "Reloading..." : "Reload"}
        </Button>
      </Box>

      {/* status overview */}
      {status && (
        <Box sx={{ display: "flex", gap: 3, mb: 5 }}>
          <StatusCard
            title="Blocks"
            items={[
              { label: "Builtin", value: status.blocks.builtin_blocks },
              { label: "Custom", value: status.blocks.custom_blocks },
              { label: "User", value: status.blocks.user_blocks },
            ]}
            available={status.blocks.available}
            unavailable={status.blocks.unavailable}
          />
          <StatusCard
            title="Templates"
            items={[
              { label: "Builtin", value: status.templates.builtin_templates },
              { label: "User", value: status.templates.user_templates },
            ]}
            available={status.templates.total}
            unavailable={0}
          />
        </Box>
      )}

      {/* blocks section */}
      <Box sx={{ mb: 5 }}>
        <Heading as="h2" sx={{ fontSize: 3, color: "fg.default", mb: 3 }}>
          Blocks
        </Heading>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {blocks.map((block) => (
            <BlockCard key={block.type} block={block} />
          ))}
        </Box>
      </Box>

      {/* templates section */}
      <Box>
        <Heading as="h2" sx={{ fontSize: 3, color: "fg.default", mb: 3 }}>
          Templates
        </Heading>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {templates.map((tmpl) => (
            <TemplateCard key={tmpl.id} template={tmpl} />
          ))}
        </Box>
      </Box>
    </Box>
  );
}

function StatusCard({
  title,
  items,
  available,
  unavailable,
}: {
  title: string;
  items: { label: string; value: number }[];
  available: number;
  unavailable: number;
}) {
  return (
    <Box
      sx={{
        flex: 1,
        p: 3,
        border: "1px solid",
        borderColor: "border.default",
        borderRadius: 2,
        bg: "canvas.subtle",
      }}
    >
      <Text sx={{ fontWeight: "bold", fontSize: 2, color: "fg.default", display: "block", mb: 2 }}>
        {title}
      </Text>
      <Box sx={{ display: "flex", gap: 3, mb: 2 }}>
        {items.map((item) => (
          <Box key={item.label}>
            <Text sx={{ fontSize: 3, fontWeight: "bold", color: "fg.default", display: "block" }}>
              {item.value}
            </Text>
            <Text sx={{ fontSize: 0, color: "fg.muted" }}>{item.label}</Text>
          </Box>
        ))}
      </Box>
      <Box sx={{ display: "flex", gap: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CheckCircleFillIcon size={12} />
          <Text sx={{ fontSize: 0, color: "success.fg" }}>{available} available</Text>
        </Box>
        {unavailable > 0 && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <XCircleFillIcon size={12} />
            <Text sx={{ fontSize: 0, color: "danger.fg" }}>{unavailable} unavailable</Text>
          </Box>
        )}
      </Box>
    </Box>
  );
}

function BlockCard({ block }: { block: BlockInfo }) {
  return (
    <Box
      sx={{
        p: 3,
        border: "1px solid",
        borderColor: block.available ? "border.default" : "danger.muted",
        borderRadius: 2,
        bg: block.available ? "canvas.subtle" : "danger.subtle",
        opacity: block.available ? 1 : 0.8,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Text sx={{ fontWeight: "bold", fontSize: 2, color: "fg.default" }}>{block.name}</Text>
          <SourceBadge source={block.source} />
          <Label variant={block.available ? "success" : "danger"} size="small">
            {block.available ? "available" : "unavailable"}
          </Label>
        </Box>
        <Text sx={{ fontSize: 0, color: "fg.muted", fontFamily: "mono" }}>{block.type}</Text>
      </Box>
      <Text sx={{ fontSize: 1, color: "fg.muted", mt: 1, display: "block" }}>
        {block.description}
      </Text>
      {!block.available && block.error && (
        <Box
          sx={{
            mt: 2,
            p: 2,
            bg: "danger.subtle",
            borderRadius: 1,
            border: "1px solid",
            borderColor: "danger.muted",
          }}
        >
          <Text sx={{ fontSize: 0, color: "danger.fg" }}>{block.error}</Text>
        </Box>
      )}
      {block.dependencies.length > 0 && (
        <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 1 }}>
          <PackageIcon size={12} />
          <Text sx={{ fontSize: 0, color: "fg.muted" }}>
            {block.dependencies.join(", ")}
          </Text>
        </Box>
      )}
    </Box>
  );
}

function TemplateCard({ template }: { template: TemplateInfo }) {
  return (
    <Box
      sx={{
        p: 3,
        border: "1px solid",
        borderColor: "border.default",
        borderRadius: 2,
        bg: "canvas.subtle",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Text sx={{ fontWeight: "bold", fontSize: 2, color: "fg.default" }}>{template.name}</Text>
        <SourceBadge source={template.source} />
      </Box>
      <Text sx={{ fontSize: 1, color: "fg.muted", mt: 1, display: "block" }}>
        {template.description}
      </Text>
    </Box>
  );
}

function SourceBadge({ source }: { source: string }) {
  const variants: Record<string, { bg: string; color: string }> = {
    builtin: { bg: "accent.subtle", color: "accent.fg" },
    custom: { bg: "attention.subtle", color: "attention.fg" },
    user: { bg: "done.subtle", color: "done.fg" },
  };
  const style = variants[source] || variants.builtin;

  return (
    <Box
      sx={{
        px: 2,
        py: "2px",
        borderRadius: 2,
        bg: style.bg,
        color: style.color,
        fontSize: 0,
        fontWeight: "semibold",
      }}
    >
      {source}
    </Box>
  );
}
