import { useEffect, useState } from "react";
import { Box, Heading, Text, Button, Flash, Label } from "@primer/react";
import { PencilIcon, TrashIcon, PlusIcon, BeakerIcon } from "@primer/octicons-react";
import PipelineEditor from "../components/pipeline-editor/PipelineEditor";

interface Pipeline {
  id: number;
  name: string;
  definition: {
    name: string;
    blocks: Array<{ type: string; config: Record<string, any> }>;
  };
  created_at: string;
}

interface Template {
  id: string;
  name: string;
  description: string;
}

export default function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [editing, setEditing] = useState<{ mode: "new" | "edit"; pipeline?: Pipeline } | null>(
    null
  );

  useEffect(() => {
    loadPipelines();
    loadTemplates();
  }, []);

  const loadPipelines = async () => {
    const res = await fetch("/api/pipelines");
    const data = await res.json();
    setPipelines(data);
  };

  const loadTemplates = async () => {
    try {
      const res = await fetch("/api/templates");
      const data = await res.json();
      setTemplates(data);
    } catch (error) {
      console.error("Failed to load templates:", error);
    }
  };

  const createFromTemplate = async (templateId: string) => {
    try {
      const res = await fetch(`/api/pipelines/from_template/${templateId}`, {
        method: "POST",
      });

      if (!res.ok) throw new Error("Failed to create pipeline from template");

      setMessage({ type: "success", text: "Pipeline created from template" });
      loadPipelines();
    } catch (error) {
      setMessage({ type: "error", text: `Error: ${error}` });
    }
  };

  const savePipeline = async (pipeline: any) => {
    try {
      if (editing?.mode === "new") {
        // create new pipeline
        const res = await fetch("/api/pipelines", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pipeline),
        });

        if (!res.ok) throw new Error("Failed to create pipeline");
        setMessage({ type: "success", text: "Pipeline created successfully" });
      } else if (editing?.mode === "edit" && editing.pipeline) {
        // update existing pipeline
        const res = await fetch(`/api/pipelines/${editing.pipeline.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pipeline),
        });

        if (!res.ok) throw new Error("Failed to update pipeline");
        setMessage({ type: "success", text: "Pipeline updated successfully" });
      }

      setEditing(null);
      loadPipelines();
    } catch (error) {
      throw new Error(`Save failed: ${error}`);
    }
  };

  const deletePipeline = async (id: number) => {
    if (!confirm("Delete this pipeline?")) return;

    try {
      const res = await fetch(`/api/pipelines/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");

      setMessage({ type: "success", text: "Pipeline deleted" });
      loadPipelines();
    } catch (error) {
      setMessage({ type: "error", text: `Error: ${error}` });
    }
  };

  const deleteAllPipelines = async () => {
    if (!confirm(`Delete all ${pipelines.length} pipeline(s)? This cannot be undone!`)) return;

    try {
      // delete each pipeline
      await Promise.all(
        pipelines.map((pipeline) => fetch(`/api/pipelines/${pipeline.id}`, { method: "DELETE" }))
      );

      setMessage({ type: "success", text: "All pipelines deleted" });
      loadPipelines();
    } catch (error) {
      setMessage({ type: "error", text: `Error: ${error}` });
    }
  };

  // show editor if editing
  if (editing) {
    return (
      <PipelineEditor
        pipelineId={editing.pipeline?.id}
        pipelineName={editing.pipeline?.definition.name || "New Pipeline"}
        initialPipeline={editing.pipeline?.definition}
        onSave={savePipeline}
        onClose={() => setEditing(null)}
      />
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 4, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          <Heading sx={{ mb: 2, color: "fg.default" }}>Pipelines</Heading>
          <Text sx={{ color: "fg.default" }}>Create and manage your data generation pipelines</Text>
        </Box>
        <Box sx={{ display: "flex", gap: 2 }}>
          {pipelines.length > 0 && (
            <Button variant="danger" leadingVisual={TrashIcon} onClick={deleteAllPipelines}>
              Delete All
            </Button>
          )}
          <Button
            variant="primary"
            leadingVisual={PlusIcon}
            onClick={() => setEditing({ mode: "new" })}
          >
            New Pipeline
          </Button>
        </Box>
      </Box>

      {message && (
        <Flash variant={message.type === "error" ? "danger" : "success"} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

      {/* Templates Section */}
      {templates.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Heading sx={{ fontSize: 2, mb: 2, color: "fg.default" }}>Templates</Heading>
          <Text sx={{ fontSize: 1, mb: 3, color: "fg.muted" }}>
            Quick-start templates to create pipelines with common configurations
          </Text>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))",
              gap: 3,
            }}
          >
            {templates.map((template) => (
              <Box
                key={template.id}
                sx={{
                  border: "1px solid",
                  borderColor: "border.default",
                  borderRadius: 2,
                  p: 3,
                  bg: "canvas.subtle",
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                  "&:hover": {
                    borderColor: "accent.emphasis",
                  },
                }}
                onClick={() => createFromTemplate(template.id)}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
                  <Box sx={{ color: "accent.fg" }}>
                    <BeakerIcon size={20} />
                  </Box>
                  <Heading as="h4" sx={{ fontSize: 1, color: "fg.default", m: 0 }}>
                    {template.name}
                  </Heading>
                </Box>
                <Text sx={{ fontSize: 1, color: "fg.muted", lineHeight: 1.5 }}>
                  {template.description}
                </Text>
              </Box>
            ))}
          </Box>
        </Box>
      )}

      {/* Pipelines Section */}
      <Heading sx={{ fontSize: 2, mb: 3, color: "fg.default" }}>My Pipelines</Heading>

      {pipelines.length === 0 ? (
        <Box
          sx={{
            textAlign: "center",
            py: 6,
            border: "1px dashed",
            borderColor: "border.default",
            borderRadius: 2,
          }}
        >
          <Text sx={{ color: "fg.default" }}>
            No pipelines yet. Click &ldquo;New Pipeline&rdquo; to create one!
          </Text>
        </Box>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {pipelines.map((pipeline) => (
            <Box
              key={pipeline.id}
              sx={{
                border: "1px solid",
                borderColor: "border.default",
                borderRadius: 2,
                p: 4,
                bg: "canvas.subtle",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "start",
                  mb: 3,
                }}
              >
                <Box>
                  <Heading as="h3" sx={{ fontSize: 2, mb: 1, color: "fg.default" }}>
                    {pipeline.definition.name}
                  </Heading>
                  <Text sx={{ fontSize: 1, color: "fg.default" }}>
                    Created: {new Date(pipeline.created_at).toLocaleString()}
                  </Text>
                </Box>
                <Box sx={{ display: "flex", gap: 2 }}>
                  <Button
                    variant="primary"
                    leadingVisual={PencilIcon}
                    onClick={() => setEditing({ mode: "edit", pipeline })}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="danger"
                    leadingVisual={TrashIcon}
                    onClick={() => deletePipeline(pipeline.id)}
                  >
                    Delete
                  </Button>
                </Box>
              </Box>

              <Box>
                <Text sx={{ fontWeight: "bold", fontSize: 1, mb: 2, color: "fg.default" }}>
                  Blocks ({pipeline.definition.blocks.length}):
                </Text>
                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                  {pipeline.definition.blocks.map((block, idx) => (
                    <Label key={idx} variant="accent">
                      {idx + 1}. {block.type}
                    </Label>
                  ))}
                </Box>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
