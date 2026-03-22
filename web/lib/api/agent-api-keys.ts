import { apiClient } from './client';
import type {
  AgentApiKey,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  UpdateApiKeyRequest,
  ApiKeyListResponse,
  UsageStatsResponse,
  ApiKeyFilters,
} from '@/types/agent-api';

const BASE_PATH = '/api/v1/agent-api-keys';

/**
 * Create a new API key for an agent
 */
export async function createApiKey(
  data: CreateApiKeyRequest
): Promise<CreateApiKeyResponse> {
  return await apiClient.request('POST', BASE_PATH, data);
}

/**
 * Get all API keys with optional filters
 */
export async function getApiKeys(
  filters?: ApiKeyFilters
): Promise<ApiKeyListResponse> {
  const params: any = {};
  
  if (filters?.agent_id) {
    params.agent_id = filters.agent_id;
  }
  if (filters?.is_active !== undefined) {
    params.is_active = filters.is_active;
  }
  if (filters?.search) {
    params.search = filters.search;
  }

  return await apiClient.request('GET', BASE_PATH, null, { params });
}

/**
 * Get a specific API key by ID
 */
export async function getApiKey(keyId: string): Promise<AgentApiKey> {
  return await apiClient.request('GET', `${BASE_PATH}/${keyId}`);
}

/**
 * Update an existing API key
 */
export async function updateApiKey(
  keyId: string,
  data: UpdateApiKeyRequest
): Promise<AgentApiKey> {
  return await apiClient.request('PUT', `${BASE_PATH}/${keyId}`, data);
}

/**
 * Delete an API key
 */
export async function deleteApiKey(keyId: string): Promise<void> {
  await apiClient.request('DELETE', `${BASE_PATH}/${keyId}`);
}

/**
 * Regenerate an API key (creates new key, invalidates old one)
 */
export async function regenerateApiKey(
  keyId: string
): Promise<CreateApiKeyResponse> {
  return await apiClient.request('POST', `${BASE_PATH}/${keyId}/regenerate`);
}

/**
 * Get usage statistics for an API key
 */
export async function getApiKeyUsage(
  keyId: string,
  periodStart?: string,
  periodEnd?: string
): Promise<UsageStatsResponse> {
  const params: any = {};
  
  if (periodStart) {
    params.period_start = periodStart;
  }
  if (periodEnd) {
    params.period_end = periodEnd;
  }

  return await apiClient.request('GET', `${BASE_PATH}/${keyId}/usage`, null, { params });
}

/**
 * Toggle API key active status
 */
export async function toggleApiKeyStatus(
  keyId: string,
  isActive: boolean
): Promise<AgentApiKey> {
  return updateApiKey(keyId, { is_active: isActive });
}

/**
 * Update API key permissions
 */
export async function updateApiKeyPermissions(
  keyId: string,
  permissions: string[]
): Promise<AgentApiKey> {
  return updateApiKey(keyId, { permissions });
}

/**
 * Update API key rate limits
 */
export async function updateApiKeyRateLimits(
  keyId: string,
  rateLimits: {
    rate_limit_per_minute?: number;
    rate_limit_per_hour?: number;
    rate_limit_per_day?: number;
  }
): Promise<AgentApiKey> {
  return updateApiKey(keyId, rateLimits);
}
