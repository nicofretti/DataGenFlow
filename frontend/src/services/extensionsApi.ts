import type { BlockInfo, TemplateInfo, ExtensionsStatus, DependencyInfo } from "../types";

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
    const response = await fetch(`${API_BASE}/extensions/blocks/${encodeURIComponent(name)}/validate`, {
      method: "POST",
    });
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async getBlockDependencies(name: string): Promise<DependencyInfo[]> {
    const response = await fetch(`${API_BASE}/extensions/blocks/${encodeURIComponent(name)}/dependencies`);
    if (!response.ok) throw new Error(`http ${response.status}`);
    return response.json();
  }

  async installBlockDeps(name: string): Promise<{ status: string; installed: string[] }> {
    const response = await fetch(`${API_BASE}/extensions/blocks/${encodeURIComponent(name)}/install-deps`, {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `http ${response.status}`);
    }
    return response.json();
  }
}

export const extensionsApi = new ExtensionsApi();
