/**
 * API client for Agent LLM Configurations
 */

import { apiClient } from './client';
import type {
  AgentLLMConfig,
  AgentLLMConfigCreate,
  AgentLLMConfigUpdate,
  AgentLLMConfigReorder,
} from '@/types/agent-llm-config';

/**
 * Create a new LLM configuration for an agent
 */
export async function createLLMConfig(
  agentId: string,
  data: AgentLLMConfigCreate
): Promise<AgentLLMConfig> {
  return await apiClient.request(
    'POST',
    `/api/v1/agents/${agentId}/llm-configs`,
    data
  );
}

/**
 * Get all LLM configurations for an agent
 */
export async function getLLMConfigs(
  agentId: string,
  enabledOnly: boolean = false
): Promise<AgentLLMConfig[]> {
  const params = enabledOnly ? { enabled_only: true } : {};
  return await apiClient.request(
    'GET',
    `/api/v1/agents/${agentId}/llm-configs`,
    undefined,
    { params }
  );
}

/**
 * Get a specific LLM configuration
 */
export async function getLLMConfig(
  agentId: string,
  configId: string
): Promise<AgentLLMConfig> {
  return await apiClient.request(
    'GET',
    `/api/v1/agents/${agentId}/llm-configs/${configId}`
  );
}

/**
 * Update an LLM configuration
 */
export async function updateLLMConfig(
  agentId: string,
  configId: string,
  data: AgentLLMConfigUpdate
): Promise<AgentLLMConfig> {
  return await apiClient.request(
    'PATCH',
    `/api/v1/agents/${agentId}/llm-configs/${configId}`,
    data
  );
}

/**
 * Delete an LLM configuration
 */
export async function deleteLLMConfig(
  agentId: string,
  configId: string
): Promise<void> {
  await apiClient.request(
    'DELETE',
    `/api/v1/agents/${agentId}/llm-configs/${configId}`
  );
}

/**
 * Set an LLM configuration as default
 */
export async function setDefaultLLMConfig(
  agentId: string,
  configId: string
): Promise<AgentLLMConfig> {
  return await apiClient.request(
    'POST',
    `/api/v1/agents/${agentId}/llm-configs/${configId}/set-default`
  );
}

/**
 * Reorder LLM configurations
 */
export async function reorderLLMConfigs(
  agentId: string,
  data: AgentLLMConfigReorder
): Promise<AgentLLMConfig[]> {
  return await apiClient.request(
    'POST',
    `/api/v1/agents/${agentId}/llm-configs/reorder`,
    data
  );
}