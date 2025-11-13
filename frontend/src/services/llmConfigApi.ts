import type { ConnectionTestResult, EmbeddingModelConfig, LLMModelConfig } from "../types";

const API_BASE = "/api";

class LLMConfigApi {
  // llm models
  async listLLMModels(): Promise<LLMModelConfig[]> {
    const response = await fetch(`${API_BASE}/llm-models`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async getLLMModel(name: string): Promise<LLMModelConfig> {
    const response = await fetch(`${API_BASE}/llm-models/${encodeURIComponent(name)}`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async saveLLMModel(config: LLMModelConfig): Promise<void> {
    const response = await fetch(`${API_BASE}/llm-models`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
  }

  async updateLLMModel(name: string, config: LLMModelConfig): Promise<void> {
    const response = await fetch(`${API_BASE}/llm-models/${encodeURIComponent(name)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
  }

  async deleteLLMModel(name: string): Promise<void> {
    const response = await fetch(`${API_BASE}/llm-models/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
  }

  async testLLMConnection(config: LLMModelConfig): Promise<ConnectionTestResult> {
    const response = await fetch(`${API_BASE}/llm-models/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  // embedding models
  async listEmbeddingModels(): Promise<EmbeddingModelConfig[]> {
    const response = await fetch(`${API_BASE}/embedding-models`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async getEmbeddingModel(name: string): Promise<EmbeddingModelConfig> {
    const response = await fetch(`${API_BASE}/embedding-models/${encodeURIComponent(name)}`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async saveEmbeddingModel(config: EmbeddingModelConfig): Promise<void> {
    const response = await fetch(`${API_BASE}/embedding-models`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
  }

  async updateEmbeddingModel(name: string, config: EmbeddingModelConfig): Promise<void> {
    const response = await fetch(`${API_BASE}/embedding-models/${encodeURIComponent(name)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
  }

  async deleteEmbeddingModel(name: string): Promise<void> {
    const response = await fetch(`${API_BASE}/embedding-models/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
  }

  async testEmbeddingConnection(config: EmbeddingModelConfig): Promise<ConnectionTestResult> {
    const response = await fetch(`${API_BASE}/embedding-models/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }
}

export const llmConfigApi = new LLMConfigApi();
