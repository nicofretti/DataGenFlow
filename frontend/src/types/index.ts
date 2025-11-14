export interface RecordData {
  id: number;
  output: string;
  status: string;
  metadata: any;
  metrics?: Record<string, number>;
  algorithm?: string;
  trace?: Array<{
    block_type: string;
    input: any;
    output: any;
    accumulated_state?: any;
    error?: string;
  }>;
  error?: string;
}

export interface ValidationConfig {
  field_order: {
    primary: string[];
    secondary: string[];
    hidden: string[];
  };
}

export interface Pipeline {
  id: number;
  name: string;
  definition: {
    name: string;
    blocks: Array<{ type: string; config: Record<string, any> }>;
  };
  created_at?: string;
  validation_config?: ValidationConfig;
}

export interface Job {
  id: number;
  pipeline_id: number;
  status: string;
  progress: number;
  current_seed: number;
  total_seeds: number;
  current_block: string | null;
  current_step: string | null;
  records_generated: number;
  records_failed: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  example_seed?: any;
}

export interface BlockSchema {
  type: string;
  name: string;
  description?: string;
  algorithm?: string;
  paper?: string;
  inputs: string[];
  outputs: string[];
  config_schema?: any;
}

export type LLMProvider = "openai" | "anthropic" | "gemini" | "ollama";

export interface LLMModelConfig {
  name: string;
  provider: LLMProvider;
  endpoint: string;
  api_key: string | null;
  model_name: string;
}

export interface EmbeddingModelConfig {
  name: string;
  provider: LLMProvider;
  endpoint: string;
  api_key: string | null;
  model_name: string;
  dimensions: number | null;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency_ms: number | null;
}
