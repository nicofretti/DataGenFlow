import { useEffect, useState } from "react";
import { Box, Heading, Text, Button, IconButton, Spinner } from "@primer/react";
import { PlusIcon, TrashIcon, PencilIcon, CheckCircleIcon } from "@primer/octicons-react";
import { toast } from "sonner";
import type { LLMModelConfig, EmbeddingModelConfig } from "../types";
import { llmConfigApi } from "../services/llmConfigApi";
import LLMFormModal from "../components/settings/LLMFormModal";
import EmbeddingFormModal from "../components/settings/EmbeddingFormModal";

export default function Settings() {
  const [llmModels, setLlmModels] = useState<LLMModelConfig[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModelConfig[]>([]);
  const [llmModalOpen, setLlmModalOpen] = useState(false);
  const [embeddingModalOpen, setEmbeddingModalOpen] = useState(false);
  const [editingLlm, setEditingLlm] = useState<LLMModelConfig | null>(null);
  const [editingEmbedding, setEditingEmbedding] = useState<EmbeddingModelConfig | null>(null);
  const [testingLlm, setTestingLlm] = useState<string | null>(null);
  const [testingEmbedding, setTestingEmbedding] = useState<string | null>(null);

  useEffect(() => {
    loadLlmModels();
    loadEmbeddingModels();
  }, []);

  const loadLlmModels = async () => {
    try {
      const models = await llmConfigApi.listLLMModels();
      setLlmModels(models);
    } catch (error) {
      toast.error(`failed to load llm models: ${error}`);
    }
  };

  const loadEmbeddingModels = async () => {
    try {
      const models = await llmConfigApi.listEmbeddingModels();
      setEmbeddingModels(models);
    } catch (error) {
      toast.error(`failed to load embedding models: ${error}`);
    }
  };

  const handleDeleteLlm = async (name: string) => {
    if (!confirm(`delete llm model "${name}"?`)) return;

    try {
      await llmConfigApi.deleteLLMModel(name);
      toast.success("llm model deleted");
      loadLlmModels();
    } catch (error) {
      toast.error(`failed to delete: ${error}`);
    }
  };

  const handleDeleteEmbedding = async (name: string) => {
    if (!confirm(`delete embedding model "${name}"?`)) return;

    try {
      await llmConfigApi.deleteEmbeddingModel(name);
      toast.success("embedding model deleted");
      loadEmbeddingModels();
    } catch (error) {
      toast.error(`failed to delete: ${error}`);
    }
  };

  const handleTestLlm = async (config: LLMModelConfig) => {
    setTestingLlm(config.name);
    try {
      const result = await llmConfigApi.testLLMConnection(config);
      if (result.success) {
        toast.success(`connection successful (${result.latency_ms}ms)`);
      } else {
        toast.error(`connection failed: ${result.message}`);
      }
    } catch (error) {
      toast.error(`test failed: ${error}`);
    } finally {
      setTestingLlm(null);
    }
  };

  const handleTestEmbedding = async (config: EmbeddingModelConfig) => {
    setTestingEmbedding(config.name);
    try {
      const result = await llmConfigApi.testEmbeddingConnection(config);
      if (result.success) {
        toast.success(`connection successful (${result.latency_ms}ms)`);
      } else {
        toast.error(`connection failed: ${result.message}`);
      }
    } catch (error) {
      toast.error(`test failed: ${error}`);
    } finally {
      setTestingEmbedding(null);
    }
  };

  const handleSaveLlm = async (config: LLMModelConfig) => {
    try {
      if (editingLlm) {
        await llmConfigApi.updateLLMModel(editingLlm.name, config);
        toast.success("llm model updated");
      } else {
        await llmConfigApi.saveLLMModel(config);
        toast.success("llm model created");
      }
      setLlmModalOpen(false);
      setEditingLlm(null);
      loadLlmModels();
    } catch (error) {
      toast.error(`failed to save: ${error}`);
      throw error;
    }
  };

  const handleSaveEmbedding = async (config: EmbeddingModelConfig) => {
    try {
      if (editingEmbedding) {
        await llmConfigApi.updateEmbeddingModel(editingEmbedding.name, config);
        toast.success("embedding model updated");
      } else {
        await llmConfigApi.saveEmbeddingModel(config);
        toast.success("embedding model created");
      }
      setEmbeddingModalOpen(false);
      setEditingEmbedding(null);
      loadEmbeddingModels();
    } catch (error) {
      toast.error(`failed to save: ${error}`);
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
              configure language models for text generation
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
              <Box
                key={model.name}
                sx={{
                  p: 3,
                  border: "1px solid",
                  borderColor: "border.default",
                  borderRadius: 2,
                  bg: "canvas.subtle",
                }}
              >
                <Box sx={{ display: "flex", alignItems: "start", justifyContent: "space-between" }}>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
                      <Text sx={{ fontWeight: "bold", fontSize: 2, color: "fg.default" }}>
                        {model.name}
                      </Text>
                      <Box
                        sx={{
                          px: 2,
                          py: 1,
                          borderRadius: 2,
                          bg: "accent.subtle",
                          color: "accent.fg",
                          fontSize: 0,
                          fontWeight: "semibold",
                        }}
                      >
                        {model.provider}
                      </Box>
                      {model.name === "default" && (
                        <Box
                          sx={{
                            px: 2,
                            py: 1,
                            borderRadius: 2,
                            bg: "success.subtle",
                            color: "success.fg",
                            fontSize: 0,
                            fontWeight: "semibold",
                          }}
                        >
                          default
                        </Box>
                      )}
                    </Box>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mb: 1 }}>
                      <Text sx={{ fontSize: 1, color: "fg.muted", mb: 1 }}>
                        model: {model.model_name}
                      </Text>
                      <Text sx={{ fontSize: 1, color: "fg.muted", fontFamily: "mono" }}>
                        {model.endpoint}
                      </Text>
                    </Box>
                  </Box>

                  <Box sx={{ display: "flex", gap: 2 }}>
                    <Button
                      size="small"
                      variant="default"
                      onClick={() => handleTestLlm(model)}
                      disabled={testingLlm === model.name}
                      sx={{
                        color: testingLlm === model.name ? "fg.muted" : "success.fg",
                        borderColor:
                          testingLlm === model.name ? "border.default" : "success.emphasis",
                        "&:hover:not(:disabled)": {
                          bg: "success.subtle",
                          borderColor: "success.emphasis",
                          color: "success.fg",
                        },
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        {testingLlm === model.name ? (
                          <Spinner size="small" />
                        ) : (
                          <CheckCircleIcon size={16} />
                        )}
                        <Text>{testingLlm === model.name ? "testing..." : "test"}</Text>
                      </Box>
                    </Button>
                    <IconButton
                      icon={PencilIcon}
                      aria-label="edit"
                      size="small"
                      onClick={() => {
                        setEditingLlm(model);
                        setLlmModalOpen(true);
                      }}
                    />
                    <IconButton
                      icon={TrashIcon}
                      aria-label="delete"
                      size="small"
                      variant="danger"
                      onClick={() => handleDeleteLlm(model.name)}
                    />
                  </Box>
                </Box>
              </Box>
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
              configure models for text embeddings
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
              <Box
                key={model.name}
                sx={{
                  p: 3,
                  border: "1px solid",
                  borderColor: "border.default",
                  borderRadius: 2,
                  bg: "canvas.subtle",
                }}
              >
                <Box sx={{ display: "flex", alignItems: "start", justifyContent: "space-between" }}>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
                      <Text sx={{ fontWeight: "bold", fontSize: 2, color: "fg.default" }}>
                        {model.name}
                      </Text>
                      <Box
                        sx={{
                          px: 2,
                          py: 1,
                          borderRadius: 2,
                          bg: "accent.subtle",
                          color: "accent.fg",
                          fontSize: 0,
                          fontWeight: "semibold",
                        }}
                      >
                        {model.provider}
                      </Box>
                    </Box>
                    <Text sx={{ fontSize: 1, color: "fg.muted", mb: 1 }}>
                      model: {model.model_name}
                      {model.dimensions && ` (${model.dimensions}d)`}
                    </Text>
                    <Text sx={{ fontSize: 1, color: "fg.muted", fontFamily: "mono" }}>
                      {model.endpoint}
                    </Text>
                  </Box>

                  <Box sx={{ display: "flex", gap: 2 }}>
                    <Button
                      size="small"
                      variant="default"
                      onClick={() => handleTestEmbedding(model)}
                      disabled={testingEmbedding === model.name}
                      sx={{
                        color: testingEmbedding === model.name ? "fg.muted" : "success.fg",
                        borderColor:
                          testingEmbedding === model.name ? "border.default" : "success.emphasis",
                        "&:hover:not(:disabled)": {
                          bg: "success.subtle",
                          borderColor: "success.emphasis",
                          color: "success.fg",
                        },
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        {testingEmbedding === model.name ? (
                          <Spinner size="small" />
                        ) : (
                          <CheckCircleIcon size={16} />
                        )}
                        <Text>{testingEmbedding === model.name ? "testing..." : "test"}</Text>
                      </Box>
                    </Button>
                    <IconButton
                      icon={PencilIcon}
                      aria-label="edit"
                      size="small"
                      onClick={() => {
                        setEditingEmbedding(model);
                        setEmbeddingModalOpen(true);
                      }}
                    />
                    <IconButton
                      icon={TrashIcon}
                      aria-label="delete"
                      size="small"
                      variant="danger"
                      onClick={() => handleDeleteEmbedding(model.name)}
                    />
                  </Box>
                </Box>
              </Box>
            ))}
          </Box>
        )}
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
    </Box>
  );
}
