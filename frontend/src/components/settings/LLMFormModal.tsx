import { useState, useEffect } from "react";
import { Box, Button, TextInput, FormControl, Select, Dialog } from "@primer/react";
import type { LLMModelConfig, LLMProvider } from "../../types";
import { isLLMProvider, LLM_PROVIDERS } from "../../types";

const PROVIDER_DEFAULTS: Record<LLMProvider, { endpoint: string; model: string }> = {
  openai: {
    endpoint: "",
    model: "gpt-4",
  },
  anthropic: {
    endpoint: "",
    model: "claude-3-5-sonnet-20241022",
  },
  gemini: {
    endpoint: "",
    model: "gemini-2.0-flash-exp",
  },
  ollama: {
    endpoint: "http://localhost:11434/v1/chat/completions",
    model: "llama3",
  },
};

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: LLMModelConfig) => Promise<void>;
  initialData?: LLMModelConfig;
}

export default function LLMFormModal({ isOpen, onClose, onSave, initialData }: Props) {
  const [name, setName] = useState("");
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [endpoint, setEndpoint] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelName, setModelName] = useState("");
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialData) {
      setName(initialData.name);
      setProvider(initialData.provider);
      setEndpoint(initialData.endpoint);
      setApiKey(initialData.api_key || "");
      setModelName(initialData.model_name);
    } else if (isOpen) {
      // set defaults for new model only when opening
      const defaultProvider: LLMProvider = "openai";
      const defaults = PROVIDER_DEFAULTS[defaultProvider];
      setName("");
      setProvider(defaultProvider);
      setEndpoint(defaults.endpoint);
      setModelName(defaults.model);
      setApiKey("");
    }
  }, [isOpen, initialData]);

  const handleProviderChange = (newProvider: LLMProvider) => {
    setProvider(newProvider);
    if (!initialData) {
      const defaults = PROVIDER_DEFAULTS[newProvider];
      setEndpoint(defaults.endpoint);
      setModelName(defaults.model);
      // ollama doesn't need api key
      if (newProvider === "ollama") {
        setApiKey("");
      }
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) newErrors.name = "name is required";
    if (provider === "ollama" && !endpoint.trim()) {
      newErrors.endpoint = "endpoint is required for ollama";
    }
    if (!modelName.trim()) newErrors.modelName = "model name is required";
    if (provider !== "ollama" && !apiKey.trim()) {
      newErrors.apiKey = "api key is required for this provider";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    const config: LLMModelConfig = {
      name: name.trim(),
      provider,
      endpoint: endpoint.trim(),
      api_key: apiKey.trim() || null,
      model_name: modelName.trim(),
      is_default: initialData?.is_default ?? false,
    };

    setSaving(true);
    try {
      await onSave(config);
      handleClose();
    } catch (error) {
      // error handled by parent
      console.error(error);
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
    setErrors({});
    onClose();
  };

  return (
    <Dialog isOpen={isOpen} onDismiss={handleClose} sx={{ width: "600px" }}>
      <Dialog.Header sx={{ color: "fg.default" }}>
        {initialData ? "Edit LLM Model" : "Add LLM Model"}
      </Dialog.Header>

      <Box sx={{ p: 3, bg: "canvas.default" }}>
        <FormControl required sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>Name</FormControl.Label>
          <TextInput
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., my-gpt4"
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
            onChange={(e) => {
              const val = e.target.value;
              if (isLLMProvider(val)) handleProviderChange(val);
            }}
            block
          >
            {LLM_PROVIDERS.map((p) => (
              <Select.Option key={p.value} value={p.value}>
                {p.label}
              </Select.Option>
            ))}
          </Select>
        </FormControl>

        <FormControl required={provider === "ollama"} sx={{ mb: 3 }}>
          <FormControl.Label sx={{ color: "fg.default" }}>
            Endpoint URL {provider !== "ollama" && "(optional)"}
          </FormControl.Label>
          <TextInput
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            placeholder={
              provider === "ollama"
                ? "http://localhost:11434/v1/chat/completions"
                : "leave empty to use default endpoint"
            }
            block
          />
          {errors.endpoint && (
            <FormControl.Validation variant="error">{errors.endpoint}</FormControl.Validation>
          )}
          {provider !== "ollama" && (
            <FormControl.Caption sx={{ color: "fg.muted" }}>
              leave empty to use the provider&#39;s default endpoint
            </FormControl.Caption>
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
            placeholder="gpt-4"
            block
          />
          {errors.modelName && (
            <FormControl.Validation variant="error">{errors.modelName}</FormControl.Validation>
          )}
          <FormControl.Caption sx={{ color: "fg.muted" }}>
            {provider === "ollama" ? "e.g., llama3, mistral" : "the model identifier"}
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
