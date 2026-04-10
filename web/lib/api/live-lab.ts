import { apiClient } from './http'

export interface ExecutionSummary {
  id: string
  agent_id: string
  agent_name: string
  trigger_source: string
  trigger_detail: string
  message_preview: string
  conversation_id: string
  status: 'running' | 'complete' | 'error' | 'cancelled'
  started_at: string
  completed_at: string
  error: string
  tools_used: string[]
  total_tokens: number
  total_tools: number
  cost: number
}

export interface ExecutionEvent {
  type: string
  _ts?: number
  content?: string
  tool_name?: string
  status?: string
  description?: string
  details?: Record<string, unknown>
  duration_ms?: number
  input_tokens?: number
  output_tokens?: number
  error?: string
  agent?: string
  start_time?: number
  sources?: unknown[]
  metadata?: Record<string, unknown>
}

export interface ExecutionDetail extends ExecutionSummary {
  events: ExecutionEvent[]
}

export async function getExecutions(
  status: 'all' | 'active' | 'recent' = 'all',
  limit = 50,
  offset = 0,
): Promise<{ active?: ExecutionSummary[]; recent?: ExecutionSummary[] }> {
  const response = await apiClient.request(
    'GET',
    `/api/v1/live-lab/executions?status=${status}&limit=${limit}&offset=${offset}`,
  )
  return response?.data || response
}

export async function getExecution(executionId: string): Promise<ExecutionDetail> {
  const response = await apiClient.request('GET', `/api/v1/live-lab/executions/${executionId}`)
  return response?.data || response
}

export function getExecutionStreamUrl(executionId: string): string {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  return `${API_URL}/api/v1/live-lab/executions/${executionId}/stream`
}
