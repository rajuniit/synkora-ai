import { useState, useEffect } from 'react';
import { getChatConfig, updateChatConfig, ChatPageConfig, ChatConfigResponse } from '@/lib/api/chat-config';

export function useChatConfig(agentName: string) {
  const [config, setConfig] = useState<ChatConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (agentName) {
      fetchConfig();
    }
  }, [agentName]);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Decode the agent name in case it's URL-encoded
      const decodedAgentName = decodeURIComponent(agentName);
      
      // Fetch the chat config using the agent name (GET endpoint uses agent_name)
      const data = await getChatConfig(decodedAgentName);
      setConfig(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch chat configuration');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async (newConfig: ChatPageConfig) => {
    if (!config) return;
    
    try {
      setSaving(true);
      setError(null);
      // Update uses agent_id
      const updated = await updateChatConfig(config.agent_id, newConfig);
      setConfig(updated);
      return updated;
    } catch (err: any) {
      setError(err.message || 'Failed to save chat configuration');
      throw err;
    } finally {
      setSaving(false);
    }
  };

  return {
    config,
    loading,
    error,
    saving,
    saveConfig,
    refetch: fetchConfig,
  };
}
