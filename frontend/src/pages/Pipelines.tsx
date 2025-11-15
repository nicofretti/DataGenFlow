import { useEffect, useState } from "react";
import { Box, Heading, Text, Button, Label } from "@primer/react";
import {
  PencilIcon,
  TrashIcon,
  PlusIcon,
  BeakerIcon,
  DownloadIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CopyIcon,
} from "@primer/octicons-react";
import PipelineEditor from "../components/pipeline-editor/PipelineEditor";
import { useNavigation } from "../App";
import type { Pipeline, Template } from "../types";
import { toast } from "sonner";

export default function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editing, setEditing] = useState<{ mode: "new" | "edit"; pipeline?: Pipeline } | null>(
    null
  );
  const [expandedDebug, setExpandedDebug] = useState<number | null>(null);
  const { setHideNavigation } = useNavigation();

  useEffect(() => {
    loadPipelines();
    loadTemplates();
  }, []);

  // hide navigation for immersive full-screen editing experience
  useEffect(() => {
    setHideNavigation(editing !== null);
  }, [editing, setHideNavigation]);

  const loadPipelines = async () => {
    try {
      const res = await fetch("/api/pipelines");
      if (!res.ok) {
        throw new Error(`http ${res.status}`);
      }
      const data = await res.json();
      setPipelines(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load pipelines:", err);
      toast.error(`Failed to load pipelines: ${message}`);
    }
  };

  const loadTemplates = async () => {
    try {
      const res = await fetch("/api/templates");
      if (!res.ok) {
        throw new Error(`http ${res.status}`);
      }
      const data = await res.json();
      setTemplates(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load templates:", err);
      toast.error(`Failed to load templates: ${message}`);
    }
  };

  const createFromTemplate = async (templateId: string) => {
    try {
      const res = await fetch(`/api/pipelines/from_template/${templateId}`, {
        method: "POST",
      });

      if (!res.ok) throw new Error("Failed to create pipeline from template");

      toast.success("Pipeline created from template successfully");
      loadPipelines();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to create pipeline from template: ${message}`);
    }
  };

  const savePipeline = async (pipeline: Pipeline) => {
    try {
      if (editing?.mode === "new") {
        const res = await fetch("/api/pipelines", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pipeline),
        });

        if (!res.ok) throw new Error("Failed to create pipeline");
        toast.success("Pipeline created successfully");
      } else if (editing?.mode === "edit" && editing.pipeline) {
        const res = await fetch(`/api/pipelines/${editing.pipeline.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(pipeline),
        });

        if (!res.ok) throw new Error("Failed to update pipeline");
        toast.success("Pipeline updated successfully");
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

      toast.success("Pipeline deleted successfully");
      loadPipelines();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to delete pipeline: ${message}`);
    }
  };

  const deleteAllPipelines = async () => {
    if (!confirm(`Delete all ${pipelines.length} pipeline(s)? This cannot be undone!`)) return;

    try {
      await Promise.all(
        pipelines.map((pipeline) => fetch(`/api/pipelines/${pipeline.id}`, { method: "DELETE" }))
      );

      toast.success("All pipelines deleted successfully");
      loadPipelines();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to delete pipelines: ${message}`);
    }
  };

  const downloadExampleSeed = (template: Template) => {
    if (!template.example_seed) return;

    // check if this is a markdown seed (has file_content instead of content)
    const isMarkdownSeed =
      Array.isArray(template.example_seed) &&
      template.example_seed.length > 0 &&
      template.example_seed[0].metadata?.file_content;

    if (isMarkdownSeed) {
      // download markdown content
      const markdownContent = template.example_seed[0].metadata.file_content;
      const blob = new Blob([markdownContent], {
        type: "text/markdown",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `seed_${template.id}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else {
      // download as json
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
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
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
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
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

                <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                  <Button
                    variant="default"
                    size="small"
                    sx={{ flex: "1 1 auto", minWidth: "120px" }}
                    onClick={() => createFromTemplate(template.id)}
                  >
                    Use Template
                  </Button>
                  {template.example_seed && (
                    <Button
                      variant="default"
                      size="small"
                      leadingVisual={DownloadIcon}
                      sx={{ flex: "1 1 auto", minWidth: "140px" }}
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
                  {pipeline.created_at && (
                    <Text sx={{ fontSize: 1, color: "fg.default" }}>
                      Created: {new Date(pipeline.created_at).toLocaleString()}
                    </Text>
                  )}
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

              <Box sx={{ mt: 3, pt: 3 }}>
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
