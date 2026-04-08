import { apiClient } from './http'
import type { AgentLLMConfig } from '@/types/agent-llm-config'

export interface PlatformAgentLLMConfigUpsert {
  name: string
  provider: string
  model_name: string
  api_key?: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  top_p?: number
  enabled?: boolean
}

export interface PlatformAgentStatus {
  has_access: boolean
  is_configured: boolean
  agent_name: string
  provider: string | null
  model_name: string | null
  plan_tier: string
}

export async function getPlatformAgentStatus(): Promise<PlatformAgentStatus> {
  const response = await apiClient.axios.get<PlatformAgentStatus>('/api/v1/platform-agent/status')
  return response.data
}

export async function getPlatformAgentLLMConfig(): Promise<AgentLLMConfig | null> {
  const response = await apiClient.axios.get<AgentLLMConfig | null>('/api/v1/platform-agent/llm-config')
  return response.data
}

export async function upsertPlatformAgentLLMConfig(data: PlatformAgentLLMConfigUpsert): Promise<AgentLLMConfig> {
  const response = await apiClient.axios.post<AgentLLMConfig>('/api/v1/platform-agent/llm-config', data)
  return response.data
}
