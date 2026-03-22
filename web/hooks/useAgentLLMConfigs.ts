/**
 * React hooks for managing Agent LLM Configurations
 * Uses direct API calls with useState/useEffect (no React Query)
 */

import { useState, useEffect, useCallback } from 'react';
import {
  createLLMConfig,
  getLLMConfigs,
  getLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  setDefaultLLMConfig,
} from '@/lib/api/agent-llm-configs';
import type {
  AgentLLMConfig,
  AgentLLMConfigCreate,
  AgentLLMConfigUpdate,
} from '@/types/agent-llm-config';

/**
 * Hook to fetch all LLM configurations for an agent
 */
export function useAgentLLMConfigs(agentName: string, enabledOnly: boolean = false) {
  const [configs, setConfigs] = useState<AgentLLMConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadConfigs = useCallback(async () => {
    if (!agentName) return;
    
    try {
      setIsLoading(true);
      setError(null);
      const data = await getLLMConfigs(agentName, enabledOnly);
      setConfigs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err as Error);
      setConfigs([]);
    } finally {
      setIsLoading(false);
    }
  }, [agentName, enabledOnly]);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  return {
    data: configs,
    isLoading,
    error,
    refetch: loadConfigs,
  };
}

/**
 * Hook to fetch a specific LLM configuration
 */
export function useAgentLLMConfig(agentName: string, configId: string) {
  const [config, setConfig] = useState<AgentLLMConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadConfig = useCallback(async () => {
    if (!agentName || !configId) return;
    
    try {
      setIsLoading(true);
      setError(null);
      const data = await getLLMConfig(agentName, configId);
      setConfig(data);
    } catch (err) {
      setError(err as Error);
      setConfig(null);
    } finally {
      setIsLoading(false);
    }
  }, [agentName, configId]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  return {
    data: config,
    isLoading,
    error,
    refetch: loadConfig,
  };
}

/**
 * Hook to create a new LLM configuration
 */
export function useCreateLLMConfig(agentName: string, onSuccess?: () => void) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (data: AgentLLMConfigCreate) => {
    try {
      setIsPending(true);
      setError(null);
      const result = await createLLMConfig(agentName, data);
      if (onSuccess) onSuccess();
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsPending(false);
    }
  }, [agentName, onSuccess]);

  return {
    mutate,
    mutateAsync: mutate,
    isPending,
    error,
  };
}

/**
 * Hook to update an LLM configuration
 * NOTE: This hook is designed to be called dynamically with different configIds
 */
export function useUpdateLLMConfig(agentName: string, onSuccess?: () => void) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (configId: string, data: AgentLLMConfigUpdate) => {
    try {
      setIsPending(true);
      setError(null);
      const result = await updateLLMConfig(agentName, configId, data);
      if (onSuccess) onSuccess();
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsPending(false);
    }
  }, [agentName, onSuccess]);

  return {
    mutate,
    mutateAsync: mutate,
    isPending,
    error,
  };
}

/**
 * Hook to delete an LLM configuration
 */
export function useDeleteLLMConfig(agentName: string, onSuccess?: () => void) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (configId: string) => {
    try {
      setIsPending(true);
      setError(null);
      await deleteLLMConfig(agentName, configId);
      if (onSuccess) onSuccess();
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsPending(false);
    }
  }, [agentName, onSuccess]);

  return {
    mutate,
    mutateAsync: mutate,
    isPending,
    error,
  };
}

/**
 * Hook to set an LLM configuration as default
 */
export function useSetDefaultLLMConfig(agentName: string, onSuccess?: () => void) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (configId: string) => {
    try {
      setIsPending(true);
      setError(null);
      await setDefaultLLMConfig(agentName, configId);
      if (onSuccess) onSuccess();
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setIsPending(false);
    }
  }, [agentName, onSuccess]);

  return {
    mutate,
    mutateAsync: mutate,
    isPending,
    error,
  };
}

/**
 * Combined hook for managing LLM configurations with all operations
 */
export function useLLMConfigManager(agentName: string) {
  const { data: configs, isLoading, error, refetch } = useAgentLLMConfigs(agentName);

  const createMutation = useCreateLLMConfig(agentName, refetch);
  const updateMutation = useUpdateLLMConfig(agentName, refetch);
  const deleteMutation = useDeleteLLMConfig(agentName, refetch);
  const setDefaultMutation = useSetDefaultLLMConfig(agentName, refetch);

  const handleCreate = useCallback(
    async (data: AgentLLMConfigCreate) => {
      return createMutation.mutateAsync(data);
    },
    [createMutation]
  );

  const handleUpdate = useCallback(
    async (configId: string, data: AgentLLMConfigUpdate) => {
      return updateMutation.mutateAsync(configId, data);
    },
    [updateMutation]
  );

  const handleDelete = useCallback(
    async (configId: string) => {
      return deleteMutation.mutateAsync(configId);
    },
    [deleteMutation]
  );

  const handleSetDefault = useCallback(
    async (configId: string) => {
      return setDefaultMutation.mutateAsync(configId);
    },
    [setDefaultMutation]
  );

  const getDefaultConfig = useCallback(() => {
    return configs?.find((config) => config.is_default);
  }, [configs]);

  const getEnabledConfigs = useCallback(() => {
    return configs?.filter((config) => config.enabled) || [];
  }, [configs]);

  return {
    configs: configs || [],
    isLoading,
    error,
    refetch,
    create: handleCreate,
    update: handleUpdate,
    delete: handleDelete,
    setDefault: handleSetDefault,
    getDefaultConfig,
    getEnabledConfigs,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isSettingDefault: setDefaultMutation.isPending,
  };
}
