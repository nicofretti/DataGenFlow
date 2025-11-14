import { useState, useEffect } from "react";
import { Box, Button, TextInput, FormControl, Select, Dialog } from "@primer/react";
import type { EmbeddingModelConfig, LLMProvider } from "../../types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: EmbeddingModelConfig) => Promise<void>;
  initialData?: EmbeddingModelConfig;
}

const PROVIDERS: { value: LLMProvider; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "gemini", label: "Google Gemini" },
  { value: "ollama", label: "Ollama" },
];

const PROVIDER_DEFAULTS: Record<
  LLMProvider,
  { endpoint: string; model: string; dimensions?: number }
> = {
  openai: {
    endpoint: "https://api.openai.com/v1/embeddings",
    model: "text-embedding-ada-002",
    dimensions: 1536,
  },
  anthropic: {
    endpoint: "https://api.anthropic.com/v1/embeddings",
    model: "claude-embed",
  },
  gemini: {
    endpoint: "https://generativelanguage.googleapis.com/v1/models",
    model: "embedding-001",
  },
  ollama: {
    endpoint: "http://localhost:11434/v1/embeddings",
    model: "nomic-embed-text",
    dimensions: 768,
  },
};

export default function EmbeddingFormModal({ isOpen, onClose, onSave, initialData }: Props) {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [endpoint, setEndpoint] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("");
  const [dimensions, setDimensions] = useState("");
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialData) {
      setName(initialData.name);
      setProvider(initialData.provider);
      setEndpoint(initialData.endpoint);
      setApiKey(initialData.api_key || "");
      setModelName(initialData.model_name);
      setDimensions(initialData.dimensions?.toString() || "");
    } else {
      // set defaults for new model
      const defaults = PROVIDER_DEFAULTS[provider];
      setEndpoint(defaults.endpoint);
      setModelName(defaults.model);
      setDimensions(defaults.dimensions?.toString() || "");
    }
  }, [initialData, provider]);

  const handleProviderChange = (newProvider: LLMProvider) => {
    setProvider(newProvider);
    if (!initialData) {
      const defaults = PROVIDER_DEFAULTS[newProvider];
      setEndpoint(defaults.endpoint);
      setModelName(defaults.model);
      setDimensions(defaults.dimensions?.toString() || "");
      // ollama doesn't need api key
      if (newProvider === "ollama") {
        setApiKey("");
      }
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) newErrors.name = "name is required";
    if (!endpoint.trim()) newErrors.endpoint = "endpoint is required";
    if (!modelName.trim()) newErrors.modelName = "model name is required";
    if (provider !== "ollama" && !apiKey.trim()) {
      newErrors.apiKey = "api key is required for this provider";
    }
    if (dimensions && isNaN(parseInt(dimensions))) {
      newErrors.dimensions = "dimensions must be a number";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    const config: EmbeddingModelConfig = {
      name: name.trim(),
      provider,
      endpoint: endpoint.trim(),
      api_key: apiKey.trim() || null,
      model_name: modelName.trim(),
      dimensions: dimensions ? parseInt(dimensions) : null,
    };

    setSaving(true);
    try {
      await onSave(config);
      handleClose();
    } catch (error) {
      // error handled by parent
      console.error("Failed to save embedding model config:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setName("");
    setProvider("openai");
    setEndpoint("");
    setApiKey("");
    setModelName("");
    setDimensions("");
    setErrors({});
    onClose();
  };

  return (
    <Dialog isOpen={isOpen} onDismiss={handleClose} sx={{ width: "600px" }}>
      <Dialog.Header sx={{ color: "fg.default" }}>
        {initialData ? "Edit Embedding Model" : "Add Embedding Model"}
      </Dialog.Header>

      <Box sx={{ p: 3, bg: "canvas.default" }}>
        <FormControl required sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>Name</FormControl.Label>
          <TextInput
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., my-embeddings"
            disabled={!!initialData}
            block
          />
          {errors.name && (
            <FormControl.Validation variant="error">{errors.name}</FormControl.Validation>
          )}
          <FormControl.Caption sx={{ color: "fg.muted" }}>
            unique identifier for this model
          </FormControl.Caption>
        </FormControl>

        <FormControl required sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>Provider</FormControl.Label>
          <Select
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value as LLMProvider)}
            block
          >
            {PROVIDERS.map((p) => (
              <Select.Option key={p.value} value={p.value}>
                {p.label}
              </Select.Option>
            ))}
          </Select>
        </FormControl>

        <FormControl required sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>Endpoint URL</FormControl.Label>
          <TextInput
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder="https://api.openai.com/v1/embeddings"
            block
          />
          {errors.endpoint && (
            <FormControl.Validation variant="error">{errors.endpoint}</FormControl.Validation>
          )}
        </FormControl>

        <FormControl required={provider !== "ollama"} sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>API Key</FormControl.Label>
          <TextInput
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={provider === "ollama" ? "not required for ollama" : "sk-..."}
            block
          />
          {errors.apiKey && (
            <FormControl.Validation variant="error">{errors.apiKey}</FormControl.Validation>
          )}
          {provider === "ollama" && (
            <FormControl.Caption sx={{ color: "fg.muted" }}>
              ollama doesn&#39;t require an api key
            </FormControl.Caption>
          )}
        </FormControl>

        <FormControl required sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>Model Name</FormControl.Label>
          <TextInput
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="text-embedding-ada-002"
            block
          />
          {errors.modelName && (
            <FormControl.Validation variant="error">{errors.modelName}</FormControl.Validation>
          )}
          <FormControl.Caption sx={{ color: "fg.muted" }}>
            {provider === "ollama" ? "e.g., nomic-embed-text" : "the model identifier"}
          </FormControl.Caption>
        </FormControl>

        <FormControl sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>Dimensions (optional)</FormControl.Label>
          <TextInput
            type="number"
            value={dimensions}
            onChange={(e) => setDimensions(e.target.value)}
            placeholder="e.g., 1536"
            block
          />
          {errors.dimensions && (
            <FormControl.Validation variant="error">{errors.dimensions}</FormControl.Validation>
          )}
          <FormControl.Caption sx={{ color: "fg.muted" }}>
            vector dimensionality
          </FormControl.Caption>
        </FormControl>

        <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end", mt: 4 }}>
          <Button onClick={handleClose} disabled={saving}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </Box>
      </Box>
    </Dialog>
  );
}
