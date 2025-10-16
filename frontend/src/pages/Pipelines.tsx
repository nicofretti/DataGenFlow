import { useEffect, useState } from "react";
import { Box, Heading, Text, Button, Flash, Label, IconButton } from "@primer/react";
import {
  PencilIcon,
  TrashIcon,
  PlusIcon,
  BeakerIcon,
  DownloadIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CopyIcon,
  ToolsIcon,
} from "@primer/octicons-react";
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
  example_seed?: any;
}

export default function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [editing, setEditing] = useState<{ mode: "new" | "edit"; pipeline?: Pipeline } | null>(
    null
  );
  const [expandedDebug, setExpandedDebug] = useState<number | null>(null);

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
    } catch {
      // silent fail - templates are optional
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

  const downloadExampleSeed = (template: Template) => {
    if (!template.example_seed) return;

    const blob = new Blob([JSON.stringify(template.example_seed, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `seed_${template.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setMessage({ type: "success", text: "Copied to clipboard" });
    setTimeout(() => setMessage(null), 2000);
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
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
                  <Box sx={{ color: "accent.fg" }}>
                    <BeakerIcon size={20} />
                  </Box>
                  <Heading as="h4" sx={{ fontSize: 1, color: "fg.default", m: 0 }}>
                    {template.name}
                  </Heading>
                </Box>
                <Text sx={{ fontSize: 1, color: "fg.muted", lineHeight: 1.5, mb: 3, flexGrow: 1 }}>
                  {template.description}
                </Text>

                <Box sx={{ display: "flex", gap: 2 }}>
                  <Button
                    variant="default"
                    sx={{ flex: 1 }}
                    onClick={() => createFromTemplate(template.id)}
                  >
                    Use Template
                  </Button>
                  {template.example_seed && (
                    <Button
                      variant="default"
                      leadingVisual={DownloadIcon}
                      onClick={(e) => {
                        e.stopPropagation();
                        downloadExampleSeed(template);
                      }}
                    >
                      Download Seed
                    </Button>
                  )}
                </Box>
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

              <Box sx={{ mt: 3, pt: 3}}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    cursor: "pointer",
                    py: 1,
                  }}
                  onClick={() =>
                    setExpandedDebug(expandedDebug === pipeline.id ? null : pipeline.id)
                  }
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <Box sx={{ color: "fg.muted" }}>
                      {expandedDebug === pipeline.id ? (
                        <ChevronDownIcon size={16} />
                      ) : (
                        <ChevronRightIcon size={16} />
                      )}
                    </Box>
                    <Text sx={{ fontSize: 1, color: "fg.muted" }}>Developer Tools</Text>
                  </Box>

                  {!expandedDebug && (
                    <Text sx={{ fontSize: 0, color: "fg.muted", fontFamily: "mono" }}>
                      ID: {pipeline.id}
                    </Text>
                  )}
                </Box>

                {expandedDebug === pipeline.id && (
                  <Box sx={{ pl: 4 }}>
                    <Box sx={{ fontSize: 1, color: "fg.muted", lineHeight: 2 }}>
                      <Text sx={{ display: "block" }}>1. Open debug_pipeline.py</Text>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                        <Text sx={{ display: "block", color: "fg.muted" }}>
                          {" "}
                          2. Set PIPELINE_ID =
                        </Text>

                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 2,
                          }}
                        >
                          <Box>
                            <Text
                              sx={{
                                fontFamily: "mono",
                                fontSize: 2,
                                fontWeight: "bold",
                                color: "accent.fg",
                              }}
                            >
                              {pipeline.id}
                            </Text>
                          </Box>
                          <Button
                            size="small"
                            leadingVisual={CopyIcon}
                            onClick={(e) => {
                              e.stopPropagation();
                              copyToClipboard(pipeline.id.toString());
                            }}
                          >
                            Copy ID
                          </Button>
                        </Box>
                      </Box>
                      <Text sx={{ display: "block" }}>3. Configure your test seed data</Text>
                      <Text sx={{ display: "block" }}>
                        4. Set breakpoints in your custom blocks
                      </Text>
                      <Text sx={{ display: "block" }}>
                        5. Press F5 in VS Code to start debugging
                      </Text>
                    </Box>
                  </Box>
                )}
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
