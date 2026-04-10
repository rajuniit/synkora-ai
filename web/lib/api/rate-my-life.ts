import { apiClient } from './http'
import type { DebateSession, DebateEvent } from './war-room'

export interface DimensionAnswer {
  dimension: string
  score: number
  context: string
}

export interface LifeAuditScores {
  career: number
  financial: number
  physical: number
  mental: number
  relationships: number
  growth: number
  overall: number
}

export interface AgentHighlight {
  agent_name: string
  dimension: string
  quote: string
  score: number
}

export interface LifeAuditResult {
  id: string
  status: string
  scores: LifeAuditScores
  agent_highlights: AgentHighlight[]
  verdict: string | null
  share_token: string | null
  created_at: string
  answers: DimensionAnswer[]
}

export interface CreateLifeAuditResponse {
  id: string
  share_token: string
  status: string
}

export async function createLifeAudit(answers: DimensionAnswer[]): Promise<CreateLifeAuditResponse> {
  const response = await apiClient.request('POST', '/api/v1/rate-my-life', { answers })
  return response?.data || response
}

export async function getLifeAudit(id: string): Promise<LifeAuditResult> {
  const response = await apiClient.request('GET', `/api/v1/rate-my-life/${id}`)
  return response?.data || response
}

export async function listLifeAudits(): Promise<{ audits: LifeAuditResult[] }> {
  const response = await apiClient.request('GET', '/api/v1/rate-my-life/history/list')
  return response?.data || response
}

export function getLifeAuditStreamUrl(id: string): string {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  return `${API_URL}/api/v1/rate-my-life/${id}/stream`
}

export async function getPublicLifeAudit(shareToken: string): Promise<LifeAuditResult> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  const response = await fetch(`${API_URL}/api/v1/rate-my-life/public/${shareToken}`)
  if (!response.ok) throw new Error('Life audit not found')
  return response.json()
}

// Re-export for convenience -- the debate stream uses the same event types
export type { DebateSession, DebateEvent }
