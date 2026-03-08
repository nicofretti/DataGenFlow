import type { BlockInfo, TemplateInfo, ExtensionsStatus } from "../types";

const API_BASE = "/api";

class ExtensionsApi {
  async getStatus(): Promise<ExtensionsStatus> {
    const response = await fetch(`${API_BASE}/extensions/status`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async listBlocks(): Promise<BlockInfo[]> {
    const response = await fetch(`${API_BASE}/extensions/blocks`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async listTemplates(): Promise<TemplateInfo[]> {
    const response = await fetch(`${API_BASE}/extensions/templates`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async reload(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/extensions/reload`, { method: "POST" });
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async validateBlock(name: string): Promise<{ valid: boolean; block: string; error?: string }> {
    const response = await fetch(
      `${API_BASE}/extensions/blocks/${encodeURIComponent(name)}/validate`,
      {
        method: "POST",
      }
    );
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async createPipelineFromTemplate(templateId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/pipelines/from_template/${encodeURIComponent(templateId)}`,
      { method: "POST" }
    );
    if (!response.ok) throw new Error(`http ${response.status}`);
  }

  async installBlockDeps(name: string): Promise<{ status: string; installed: string[] }> {
    const response = await fetch(
      `${API_BASE}/extensions/blocks/${encodeURIComponent(name)}/install-deps`,
      {
        method: "POST",
      }
    );
    if (!response.ok) {
      let detail = `http ${response.status}`;
      try {
        const error = await response.json();
        detail = error.detail || detail;
      } catch {
        // response body not JSON
      }
      throw new Error(detail);
    }
    return response.json();
  }
}

export const extensionsApi = new ExtensionsApi();
