import { useEffect, useState, useRef } from "react";
import { Box, Heading, Text, Button, Spinner, Tooltip } from "@primer/react";
import { PlusIcon, CircleIcon, CheckCircleFillIcon } from "@primer/octicons-react";
import { toast } from "sonner";
import type { LLMModelConfig, EmbeddingModelConfig } from "../types";
import { llmConfigApi } from "../services/llmConfigApi";
import LLMFormModal from "../components/settings/LLMFormModal";
import EmbeddingFormModal from "../components/settings/EmbeddingFormModal";
import { ConfirmModal } from "../components/ui/confirm-modal";
import { ModelCard } from "../components/settings/ModelCard";

export default function Settings() {
  const [llmModels, setLlmModels] = useState<LLMModelConfig[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModelConfig[]>([]);
  const [llmModalOpen, setLlmModalOpen] = useState(false);
  const [embeddingModalOpen, setEmbeddingModalOpen] = useState(false);
  const [editingLlm, setEditingLlm] = useState<LLMModelConfig | null>(null);
  const [editingEmbedding, setEditingEmbedding] = useState<EmbeddingModelConfig | null>(null);
  const [testingLlm, setTestingLlm] = useState<string | null>(null);
  const [testingEmbedding, setTestingEmbedding] = useState<string | null>(null);
  const [deletingLlm, setDeletingLlm] = useState<string | null>(null);
  const [deletingEmbedding, setDeletingEmbedding] = useState<string | null>(null);
  const [settingDefaultLlm, setSettingDefaultLlm] = useState<string | null>(null);
  const [settingDefaultEmbedding, setSettingDefaultEmbedding] = useState<string | null>(null);
  const [langfuseEnabled, setLangfuseEnabled] = useState<boolean>(false);
  const [langfuseHost, setLangfuseHost] = useState<string | null>(null);
  const [loadingLangfuse, setLoadingLangfuse] = useState(true);

  const isMountedRef = useRef(true);

  useEffect(() => {
    // Reset to true on each mount (important for React StrictMode double-mount)
    isMountedRef.current = true;

    loadLlmModels();
    loadEmbeddingModels();
    loadLangfuseStatus();

    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadLlmModels = async () => {
    try {
      const models = await llmConfigApi.listLLMModels();
      if (isMountedRef.current) {
        setLlmModels(models);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to load LLM models: ${message}`);
    }
  };

  const loadEmbeddingModels = async () => {
    try {
      const models = await llmConfigApi.listEmbeddingModels();
      if (isMountedRef.current) {
        setEmbeddingModels(models);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to load embedding models: ${message}`);
    }
  };

  const loadLangfuseStatus = async () => {
    try {
      const data = await llmConfigApi.getLangfuseStatus();
      if (isMountedRef.current) {
        setLangfuseEnabled(data.enabled);
        setLangfuseHost(data.host ?? null);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.error("Failed to load Langfuse status:", message);
    } finally {
      if (isMountedRef.current) {
        setLoadingLangfuse(false);
      }
    }
  };

  const handleDeleteLlm = async (name: string) => {
    try {
      await llmConfigApi.deleteLLMModel(name);
      toast.success("LLM model deleted successfully");
      loadLlmModels();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to delete LLM model: ${message}`);
    }
  };

  const handleDeleteEmbedding = async (name: string) => {
    try {
      await llmConfigApi.deleteEmbeddingModel(name);
      toast.success("Embedding model deleted successfully");
      loadEmbeddingModels();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to delete embedding model: ${message}`);
    }
  };

  const handleTestLlm = async (config: LLMModelConfig) => {
    setTestingLlm(config.name);
    try {
      const result = await llmConfigApi.testLLMConnection(config);
      if (result.success) {
        toast.success(`Connection test successful (${result.latency_ms}ms)`);
      } else {
        toast.error(`Connection test failed: ${result.message}`);
      }
    } catch (error) {
      console.error(error);
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Connection test failed: ${message}`);
    } finally {
      if (isMountedRef.current) {
        setTestingLlm(null);
      }
    }
  };

  const handleTestEmbedding = async (config: EmbeddingModelConfig) => {
    setTestingEmbedding(config.name);
    try {
      const result = await llmConfigApi.testEmbeddingConnection(config);
      if (result.success) {
        toast.success(`Connection test successful (${result.latency_ms}ms)`);
      } else {
        toast.error(`Connection test failed: ${result.message}`);
      }
    } catch (error) {
      console.error(error);
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Connection test failed: ${message}`);
    } finally {
      if (isMountedRef.current) {
        setTestingEmbedding(null);
      }
    }
  };

  const handleSetDefaultLlm = async (name: string) => {
    if (settingDefaultLlm === name) return;
    setSettingDefaultLlm(name);
    try {
      await llmConfigApi.setDefaultLLMModel(name);
      toast.success("Default LLM model updated");
      loadLlmModels();
    } catch (error) {
      console.error(error);
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to set default LLM model: ${message}`);
    } finally {
      if (isMountedRef.current) {
        setSettingDefaultLlm(null);
      }
    }
  };

  const handleSetDefaultEmbedding = async (name: string) => {
    if (settingDefaultEmbedding === name) return;
    setSettingDefaultEmbedding(name);
    try {
      await llmConfigApi.setDefaultEmbeddingModel(name);
      toast.success("Default embedding model updated");
      loadEmbeddingModels();
    } catch (error) {
      console.error(error);
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to set default embedding model: ${message}`);
    } finally {
      if (isMountedRef.current) {
        setSettingDefaultEmbedding(null);
      }
    }
  };

  const handleSaveLlm = async (config: LLMModelConfig) => {
    try {
      if (editingLlm) {
        await llmConfigApi.updateLLMModel(editingLlm.name, config);
        toast.success("LLM model updated successfully");
      } else {
        await llmConfigApi.saveLLMModel(config);
        toast.success("LLM model created successfully");
      }
      setLlmModalOpen(false);
      setEditingLlm(null);
      loadLlmModels();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to save LLM model: ${message}`);
      throw error;
    }
  };

  const handleSaveEmbedding = async (config: EmbeddingModelConfig) => {
    try {
      if (editingEmbedding) {
        await llmConfigApi.updateEmbeddingModel(editingEmbedding.name, config);
        toast.success("Embedding model updated successfully");
      } else {
        await llmConfigApi.saveEmbeddingModel(config);
        toast.success("Embedding model created successfully");
      }
      setEmbeddingModalOpen(false);
      setEditingEmbedding(null);
      loadEmbeddingModels();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error(`Failed to save embedding model: ${message}`);
      throw error;
    }
  };

  return (
    <Box>
      <Heading sx={{ mb: 4, color: "fg.default" }}>Settings</Heading>

      {/* llm models section */}
      <Box sx={{ mb: 6 }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
          <Box>
            <Heading as="h2" sx={{ fontSize: 3, color: "fg.default" }}>
              LLM Models
            </Heading>
            <Text sx={{ color: "fg.muted", fontSize: 1 }}>
              Configure language models for text generation
            </Text>
          </Box>
          <Button
            leadingVisual={PlusIcon}
            onClick={() => {
              setEditingLlm(null);
              setLlmModalOpen(true);
            }}
          >
            Add Model
          </Button>
        </Box>

        {llmModels.length === 0 ? (
          <Box
            sx={{
              p: 4,
              textAlign: "center",
              border: "1px solid",
              borderColor: "border.default",
              borderRadius: 2,
              bg: "canvas.subtle",
            }}
          >
            <Text sx={{ color: "fg.muted" }}>no llm models configured</Text>
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {llmModels.map((model) => (
              <ModelCard
                key={model.name}
                model={model}
                status={{
                  isDefault: model.is_default ?? false,
                  isTesting: testingLlm === model.name,
                  isSettingDefault: settingDefaultLlm === model.name,
                }}
                actions={{
                  onSetDefault: () => handleSetDefaultLlm(model.name),
                  onTest: () => handleTestLlm(model),
                  onEdit: () => {
                    setEditingLlm(model);
                    setLlmModalOpen(true);
                  },
                  onDelete: () => setDeletingLlm(model.name),
                }}
              />
            ))}
          </Box>
        )}
      </Box>

      {/* embedding models section */}
      <Box>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
          <Box>
            <Heading as="h2" sx={{ fontSize: 3, color: "fg.default" }}>
              Embedding Models
            </Heading>
            <Text sx={{ color: "fg.muted", fontSize: 1 }}>
              Configure models for text embeddings
            </Text>
          </Box>
          <Button
            leadingVisual={PlusIcon}
            onClick={() => {
              setEditingEmbedding(null);
              setEmbeddingModalOpen(true);
            }}
          >
            Add Model
          </Button>
        </Box>

        {embeddingModels.length === 0 ? (
          <Box
            sx={{
              p: 4,
              textAlign: "center",
              border: "1px solid",
              borderColor: "border.default",
              borderRadius: 2,
              bg: "canvas.subtle",
            }}
          >
            <Text sx={{ color: "fg.muted" }}>no embedding models configured</Text>
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {embeddingModels.map((model) => (
              <ModelCard
                key={model.name}
                model={model}
                status={{
                  isDefault: model.is_default ?? false,
                  isTesting: testingEmbedding === model.name,
                  isSettingDefault: settingDefaultEmbedding === model.name,
                }}
                actions={{
                  onSetDefault: () => handleSetDefaultEmbedding(model.name),
                  onTest: () => handleTestEmbedding(model),
                  onEdit: () => {
                    setEditingEmbedding(model);
                    setEmbeddingModalOpen(true);
                  },
                  onDelete: () => setDeletingEmbedding(model.name),
                }}
                extraDetails={model.dimensions ? ` (${model.dimensions}d)` : undefined}
              />
            ))}
          </Box>
        )}
      </Box>

      {/* langfuse integration section */}
      <Box sx={{ mt: 6 }}>
        <Box sx={{ mb: 3, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box>
            <Heading as="h2" sx={{ fontSize: 3, color: "fg.default" }}>
              Langfuse Integration
            </Heading>
            <Text sx={{ color: "fg.muted", fontSize: 1 }}>
              Enable LLM tracing and dataset uploads for observability
            </Text>
          </Box>
          {loadingLangfuse ? (
            <Spinner size="small" />
          ) : (
            <Tooltip aria-label={langfuseEnabled ? "Enabled" : "Disabled"} direction="w">
              <Box sx={{ color: langfuseEnabled ? "success.fg" : "fg.muted" }}>
                {langfuseEnabled ? <CheckCircleFillIcon size={16} /> : <CircleIcon size={16} />}
              </Box>
            </Tooltip>
          )}
        </Box>

        <Box
          sx={{
            p: 4,
            border: "1px solid",
            borderColor: "border.default",
            borderRadius: 2,
            bg: "canvas.subtle",
          }}
        >
          {langfuseEnabled && langfuseHost && (
            <Box
              sx={{
                mb: 3,
                p: 3,
                bg: "canvas.default",
                borderRadius: 2,
                border: "1px solid",
                borderColor: "border.default",
              }}
            >
              <Text sx={{ fontSize: 1, color: "fg.muted", mb: 1, display: "block" }}>
                Connected to:
              </Text>
              <Text
                sx={{
                  fontSize: 2,
                  fontFamily: "mono",
                  color: "fg.default",
                  fontWeight: "semibold",
                }}
              >
                {langfuseHost}
              </Text>
            </Box>
          )}

          <Box
            as="pre"
            sx={{
              p: 3,
              bg: "canvas.default",
              border: "1px solid",
              borderColor: "border.default",
              borderRadius: 2,
              fontSize: 1,
              fontFamily: "mono",
              color: "fg.default",
              overflow: "auto",
              mb: 3,
            }}
          >
            {`LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PROJECT_ID=your-project-id`}
          </Box>

          <Text sx={{ color: "fg.muted", fontSize: 1 }}>
            {langfuseEnabled
              ? "Langfuse is configured and ready to use. Dataset uploads and tracing are enabled."
              : "Add the environment variables above to your .env file and restart the application."}{" "}
            <a
              href="https://langfuse.com/docs/get-started"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "inherit" }}
            >
              View Documentation
            </a>
          </Text>
        </Box>
      </Box>

      {/* modals */}
      {llmModalOpen && (
        <LLMFormModal
          isOpen={llmModalOpen}
          onClose={() => {
            setLlmModalOpen(false);
            setEditingLlm(null);
          }}
          onSave={handleSaveLlm}
          initialData={editingLlm || undefined}
        />
      )}

      {embeddingModalOpen && (
        <EmbeddingFormModal
          isOpen={embeddingModalOpen}
          onClose={() => {
            setEmbeddingModalOpen(false);
            setEditingEmbedding(null);
          }}
          onSave={handleSaveEmbedding}
          initialData={editingEmbedding || undefined}
        />
      )}

      {/* confirm modals */}
      <ConfirmModal
        open={deletingLlm !== null}
        onOpenChange={(open) => !open && setDeletingLlm(null)}
        title="Delete LLM Model"
        description={`Are you sure you want to delete "${deletingLlm}"? This action cannot be undone.`}
        onConfirm={async () => {
          if (deletingLlm) {
            await handleDeleteLlm(deletingLlm);
            setDeletingLlm(null);
          }
        }}
        variant="danger"
        confirmText="Delete"
      />

      <ConfirmModal
        open={deletingEmbedding !== null}
        onOpenChange={(open) => !open && setDeletingEmbedding(null)}
        title="Delete Embedding Model"
        description={`Are you sure you want to delete "${deletingEmbedding}"? This action cannot be undone.`}
        onConfirm={async () => {
          if (deletingEmbedding) {
            await handleDeleteEmbedding(deletingEmbedding);
            setDeletingEmbedding(null);
          }
        }}
        variant="danger"
        confirmText="Delete"
      />
    </Box>
  );
}
