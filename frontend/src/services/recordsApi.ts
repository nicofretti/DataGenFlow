import type { RecordData } from "../types";

const API_BASE = "/api";

class RecordsApi {
  async updateRecord(id: number, updates: Partial<RecordData>): Promise<void> {
    const response = await fetch(`${API_BASE}/records/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `http ${response.status}`);
    }
  }

  async getRecords(params: {
    status: string;
    limit: number;
    pipelineId: number;
    jobId?: number;
  }): Promise<RecordData[]> {
    let url = `${API_BASE}/records?status=${params.status}&limit=${params.limit}&pipeline_id=${params.pipelineId}`;
    if (params.jobId) {
      url += `&job_id=${params.jobId}`;
    }
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`http ${response.status}`);
    }
    return response.json();
  }

  async getRecordsByStatus(
    status: string,
    pipelineId: number,
    jobId?: number
  ): Promise<RecordData[]> {
    let url = `${API_BASE}/records?status=${status}&pipeline_id=${pipelineId}`;
    if (jobId) {
      url += `&job_id=${jobId}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`http ${response.status}`);
    }
    return response.json();
  }

  async deleteAllRecords(jobId?: number): Promise<void> {
    const url = jobId ? `${API_BASE}/records?job_id=${jobId}` : `${API_BASE}/records`;
    const response = await fetch(url, { method: "DELETE" });
    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `http ${response.status}`);
    }
  }
}

export const recordsApi = new RecordsApi();
