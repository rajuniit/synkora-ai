/**
 * Types for Agent LLM Configuration
 */

export interface AgentLLMConfig {
  id: string;
  agent_id: string;
  tenant_id: string;
  name: string;
  provider: string;
  model_name: string;
  api_base?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  additional_params?: Record<string, any>;
  is_default: boolean;
  display_order: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentLLMConfigCreate {
  name: string;
  provider: string;
  model_name: string;
  api_key: string;
  api_base?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  additional_params?: Record<string, any>;
  is_default?: boolean;
  display_order?: number;
  enabled?: boolean;
}

export interface AgentLLMConfigUpdate {
  name?: string;
  provider?: string;
  model_name?: string;
  api_key?: string;
  api_base?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  additional_params?: Record<string, any>;
  is_default?: boolean;
  display_order?: number;
  enabled?: boolean;
}

export interface AgentLLMConfigReorder {
  config_orders: Array<{
    config_id: string;
    display_order: number;
  }>;
}

// Note: Provider and model lists are now fetched dynamically from the API
// See web/lib/api/llm-providers.ts for API client functions

/**
 * Helper function to get a readable model label
 * @param provider - The LLM provider name
 * @param modelName - The model identifier
 * @returns A formatted model label
 */
export function getModelLabel(provider: string, modelName: string): string {
  // Return the model name as-is, or format it if needed
  return modelName || 'Unknown Model'
}
