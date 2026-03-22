/**
 * Agent API Keys Management Hooks
 * Custom hooks for agent API key operations
 */

import { useState, useCallback } from 'react';
import * as apiKeyClient from '@/lib/api/agent-api-keys';
import type {
  AgentApiKey,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  UpdateApiKeyRequest,
  UsageStatsResponse,
  ApiKeyFilters,
} from '@/types/agent-api';

export function useAgentApiKeys() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Get all API keys with optional filters
   */
  const getApiKeys = useCallback(async (filters?: ApiKeyFilters): Promise<AgentApiKey[]> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiKeyClient.getApiKeys(filters);
      return response.keys || [];
    } catch (err: any) {
      setError(err.message || 'Failed to fetch API keys');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Get a specific API key by ID
   */
  const getApiKey = useCallback(async (keyId: string): Promise<AgentApiKey | null> => {
    setLoading(true);
    setError(null);
    try {
      const apiKey = await apiKeyClient.getApiKey(keyId);
      return apiKey;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch API key');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Create a new API key
   * Returns the response with plaintext key (only shown once)
   */
  const createApiKey = useCallback(
    async (data: CreateApiKeyRequest): Promise<CreateApiKeyResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiKeyClient.createApiKey(data);
        return response;
      } catch (err: any) {
        setError(err.message || 'Failed to create API key');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Update an existing API key
   */
  const updateApiKey = useCallback(
    async (keyId: string, data: UpdateApiKeyRequest): Promise<AgentApiKey | null> => {
      setLoading(true);
      setError(null);
      try {
        const apiKey = await apiKeyClient.updateApiKey(keyId, data);
        return apiKey;
      } catch (err: any) {
        setError(err.message || 'Failed to update API key');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Delete an API key
   */
  const deleteApiKey = useCallback(async (keyId: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await apiKeyClient.deleteApiKey(keyId);
      return true;
    } catch (err: any) {
      setError(err.message || 'Failed to delete API key');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Regenerate an API key (creates new key, invalidates old one)
   * Returns the response with new plaintext key
   */
  const regenerateApiKey = useCallback(
    async (keyId: string): Promise<CreateApiKeyResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiKeyClient.regenerateApiKey(keyId);
        return response;
      } catch (err: any) {
        setError(err.message || 'Failed to regenerate API key');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Toggle API key active status
   */
  const toggleApiKeyStatus = useCallback(
    async (keyId: string, isActive: boolean): Promise<AgentApiKey | null> => {
      setLoading(true);
      setError(null);
      try {
        const apiKey = await apiKeyClient.toggleApiKeyStatus(keyId, isActive);
        return apiKey;
      } catch (err: any) {
        setError(err.message || 'Failed to toggle API key status');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Update API key permissions
   */
  const updateApiKeyPermissions = useCallback(
    async (keyId: string, permissions: string[]): Promise<AgentApiKey | null> => {
      setLoading(true);
      setError(null);
      try {
        const apiKey = await apiKeyClient.updateApiKeyPermissions(keyId, permissions);
        return apiKey;
      } catch (err: any) {
        setError(err.message || 'Failed to update API key permissions');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Update API key rate limits
   */
  const updateApiKeyRateLimits = useCallback(
    async (
      keyId: string,
      rateLimits: {
        rate_limit_per_minute?: number;
        rate_limit_per_hour?: number;
        rate_limit_per_day?: number;
      }
    ): Promise<AgentApiKey | null> => {
      setLoading(true);
      setError(null);
      try {
        const apiKey = await apiKeyClient.updateApiKeyRateLimits(keyId, rateLimits);
        return apiKey;
      } catch (err: any) {
        setError(err.message || 'Failed to update API key rate limits');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    loading,
    error,
    getApiKeys,
    getApiKey,
    createApiKey,
    updateApiKey,
    deleteApiKey,
    regenerateApiKey,
    toggleApiKeyStatus,
    updateApiKeyPermissions,
    updateApiKeyRateLimits,
  };
}

/**
 * Hook for API key usage statistics
 */
export function useApiKeyUsage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Get usage statistics for an API key
   */
  const getApiKeyUsage = useCallback(
    async (
      keyId: string,
      periodStart?: string,
      periodEnd?: string
    ): Promise<UsageStatsResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const stats = await apiKeyClient.getApiKeyUsage(keyId, periodStart, periodEnd);
        return stats;
      } catch (err: any) {
        setError(err.message || 'Failed to fetch API key usage');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    loading,
    error,
    getApiKeyUsage,
  };
}
