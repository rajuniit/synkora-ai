/**
 * React hooks for Agent Output Configuration API
 */

import { useState, useEffect, useCallback } from 'react';
import type {
  OutputConfig,
  OutputDelivery,
  CreateOutputConfigData,
  UpdateOutputConfigData,
  OAuthApp
} from '@/types/agent-outputs';

// Import the apiClient instance
import { apiClient } from '@/lib/api/client';

interface UseAgentOutputsResult {
  outputs: OutputConfig[];
  loading: boolean;
  error: string | null;
  createOutput: (data: CreateOutputConfigData) => Promise<OutputConfig>;
  updateOutput: (id: string, data: UpdateOutputConfigData) => Promise<OutputConfig>;
  deleteOutput: (id: string) => Promise<void>;
  toggleOutput: (id: string, enabled: boolean) => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Hook to manage agent output configurations
 */
export function useAgentOutputs(agentId: string): UseAgentOutputsResult {
  const [outputs, setOutputs] = useState<OutputConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOutputs = useCallback(async () => {
    if (!agentId) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.request('GET', `/api/v1/agents/${agentId}/outputs?include_stats=true`);
      setOutputs(data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load output configurations');
      console.error('Error fetching outputs:', err);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    fetchOutputs();
  }, [fetchOutputs]);

  const createOutput = useCallback(async (data: CreateOutputConfigData): Promise<OutputConfig> => {
    const result = await apiClient.request('POST', `/api/v1/agents/${agentId}/outputs`, data);
    await fetchOutputs(); // Refresh list
    return result;
  }, [agentId, fetchOutputs]);

  const updateOutput = useCallback(async (id: string, data: UpdateOutputConfigData): Promise<OutputConfig> => {
    const result = await apiClient.request('PATCH', `/api/v1/agents/${agentId}/outputs/${id}`, data);
    await fetchOutputs(); // Refresh list
    return result;
  }, [agentId, fetchOutputs]);

  const deleteOutput = useCallback(async (id: string): Promise<void> => {
    await apiClient.request('DELETE', `/api/v1/agents/${agentId}/outputs/${id}`);
    await fetchOutputs(); // Refresh list
  }, [agentId, fetchOutputs]);

  const toggleOutput = useCallback(async (id: string, enabled: boolean): Promise<void> => {
    await updateOutput(id, { is_enabled: enabled });
  }, [updateOutput]);

  return {
    outputs,
    loading,
    error,
    createOutput,
    updateOutput,
    deleteOutput,
    toggleOutput,
    refresh: fetchOutputs
  };
}

interface UseOutputDeliveriesResult {
  deliveries: OutputDelivery[];
  loading: boolean;
  error: string | null;
  retryDelivery: (deliveryId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

/**
 * Hook to manage output delivery history
 */
export function useOutputDeliveries(agentId: string, outputId: string): UseOutputDeliveriesResult {
  const [deliveries, setDeliveries] = useState<OutputDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDeliveries = useCallback(async () => {
    if (!agentId || !outputId) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.request('GET', `/api/v1/agents/${agentId}/outputs/${outputId}/deliveries?limit=50`);
      setDeliveries(data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load deliveries');
      console.error('Error fetching deliveries:', err);
    } finally {
      setLoading(false);
    }
  }, [agentId, outputId]);

  useEffect(() => {
    fetchDeliveries();
  }, [fetchDeliveries]);

  const retryDelivery = useCallback(async (deliveryId: string): Promise<void> => {
    await apiClient.request('POST', `/api/v1/agents/${agentId}/outputs/${outputId}/deliveries/${deliveryId}/retry`);
    await fetchDeliveries(); // Refresh list
  }, [agentId, outputId, fetchDeliveries]);

  return {
    deliveries,
    loading,
    error,
    retryDelivery,
    refresh: fetchDeliveries
  };
}

interface UseOAuthAppsResult {
  oauthApps: OAuthApp[];
  loading: boolean;
  error: string | null;
  getAppsByProvider: (provider: string) => OAuthApp[];
}

/**
 * Hook to fetch OAuth apps for output configuration
 */
export function useOAuthApps(): UseOAuthAppsResult {
  const [oauthApps, setOAuthApps] = useState<OAuthApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOAuthApps = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiClient.getOAuthApps();
        setOAuthApps(data.filter((app: OAuthApp) => app.is_active));
      } catch (err: any) {
        setError(err.response?.data?.message || 'Failed to load OAuth apps');
        console.error('Error fetching OAuth apps:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchOAuthApps();
  }, []);

  const getAppsByProvider = useCallback((provider: string): OAuthApp[] => {
    return oauthApps.filter(app => 
      app.provider.toLowerCase() === provider.toLowerCase()
    );
  }, [oauthApps]);

  return {
    oauthApps,
    loading,
    error,
    getAppsByProvider
  };
}
