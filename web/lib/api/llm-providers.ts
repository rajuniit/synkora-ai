/**
 * API client for LLM Provider Presets
 */

import { apiClient } from './client';

export interface ModelPreset {
  name: string;
  model_name: string;
  description: string;
  default_temperature: number;
  default_max_tokens: number | null;
  default_top_p: number | null;
  additional_params: Record<string, any> | null;
  max_input_tokens: number | null;
  max_output_tokens: number | null;
}

export interface ProviderPreset {
  provider_id: string;
  provider_name: string;
  description: string;
  requires_api_key: boolean;
  requires_api_base: boolean;
  default_api_base: string | null;
  setup_instructions: string | null;
  documentation_url: string | null;
  model_count?: number;
  models?: ModelPreset[];
}

/**
 * Get all available LLM provider presets
 */
export async function getLLMProviders(): Promise<ProviderPreset[]> {
  return await apiClient.request('GET', '/api/v1/llm-providers');
}

/**
 * Get details for a specific provider including models
 */
export async function getLLMProvider(providerId: string): Promise<ProviderPreset> {
  return await apiClient.request('GET', `/api/v1/llm-providers/${providerId}`);
}

/**
 * Get models for a specific provider
 */
export async function getProviderModels(providerId: string): Promise<ModelPreset[]> {
  return await apiClient.request('GET', `/api/v1/llm-providers/${providerId}/models`);
}
