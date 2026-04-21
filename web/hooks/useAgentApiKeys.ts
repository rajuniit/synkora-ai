/**
 * Agent API Keys Management Hooks
 * Custom hooks for agent API key operations
 */

import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import * as apiKeyClient from '@/lib/api/agent-api-keys';
import type {
  AgentApiKey,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  UpdateApiKeyRequest,
  UsageStatsResponse,
  ApiKeyFilters,
} from '@/types/agent-api';

/** Extract the most useful error message from an API error. */
function extractErrorMessage(err: any, fallback: string): string {
  // FastAPI returns { detail: string } or { detail: [{msg, ...}] }
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return err?.message || fallback;
}

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
      const msg = extractErrorMessage(err, 'Failed to fetch API keys');
      setError(msg);
      toast.error(msg);
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
      const msg = extractErrorMessage(err, 'Failed to fetch API key');
      setError(msg);
      toast.error(msg);
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
        const msg = extractErrorMessage(err, 'Failed to create API key');
        setError(msg);
        toast.error(msg);
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
        const msg = extractErrorMessage(err, 'Failed to update API key');
        setError(msg);
        toast.error(msg);
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
      toast.success('API key deleted');
      return true;
    } catch (err: any) {
      const msg = extractErrorMessage(err, 'Failed to delete API key');
      setError(msg);
      toast.error(msg);
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
        const msg = extractErrorMessage(err, 'Failed to regenerate API key');
        setError(msg);
        toast.error(msg);
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
        const msg = extractErrorMessage(err, 'Failed to toggle API key status');
        setError(msg);
        toast.error(msg);
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
        const msg = extractErrorMessage(err, 'Failed to update API key permissions');
        setError(msg);
        toast.error(msg);
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
        const msg = extractErrorMessage(err, 'Failed to update API key rate limits');
        setError(msg);
        toast.error(msg);
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
    async (keyId: string, days: number = 30): Promise<UsageStatsResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const stats = await apiKeyClient.getApiKeyUsage(keyId, days);
        return stats;
      } catch (err: any) {
        const msg = extractErrorMessage(err, 'Failed to fetch API key usage');
        setError(msg);
        toast.error(msg);
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
