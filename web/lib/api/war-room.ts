import { apiClient } from './http'

export interface DebateParticipant {
  id: string
  agent_id: string | null
  agent_name: string
  role: string | null
  is_external: boolean
  color: string
}

export interface DebateMessage {
  id: string
  participant_id: string
  agent_name: string
  round: number
  content: string
  is_verdict: boolean
  is_external: boolean
  created_at: string
  color: string
}

export interface DebateSession {
  id: string
  topic: string
  debate_type: string
  rounds: number
  current_round: number
  status: 'pending' | 'active' | 'synthesizing' | 'completed' | 'error'
  is_public: boolean
  allow_external: boolean
  share_token: string | null
  debate_metadata?: { context?: DebateContext } | null
  participants: DebateParticipant[]
  messages: DebateMessage[]
  verdict: string | null
  created_at: string
  completed_at: string | null
}

export interface DebateListItem {
  id: string
  topic: string
  debate_type: string
  rounds: number
  current_round: number
  status: string
  participant_count: number
  is_public: boolean
  created_at: string
}

export interface DebateTemplate {
  id: string
  name: string
  description: string
  topic_template: string
  suggested_roles: string[]
  context_type?: string
}

export interface PRInfo {
  repo_full_name: string
  pr_number: number
  pr_title: string
  pr_description: string
  pr_author: string
  pr_base_branch: string
  pr_head_branch: string
  pr_diff: string
  pr_files_changed: string[]
  additions: number
  deletions: number
  changed_files: number
  state: string
  mergeable: boolean | null
  html_url: string
}

export interface DebateContext {
  type: 'github_pr' | 'text'
  github_url?: string
  repo_full_name?: string
  pr_number?: number
  pr_title?: string
  pr_description?: string
  pr_diff?: string
  pr_files_changed?: string[]
  pr_author?: string
  pr_base_branch?: string
  pr_head_branch?: string
  text?: string
}

export interface DebateEvent {
  type: string
  topic?: string
  participants?: DebateParticipant[]
  rounds?: number
  round?: number
  participant_id?: string
  agent_name?: string
  content?: string
  color?: string
  status?: string
  is_verdict?: boolean
}

export async function fetchPRInfo(url: string): Promise<PRInfo> {
  const response = await apiClient.request('POST', '/api/v1/war-room/fetch-pr', { url })
  return response?.data || response
}

export async function getDebateTemplates(): Promise<{ templates: DebateTemplate[] }> {
  const response = await apiClient.request('GET', '/api/v1/war-room/templates')
  return response?.data || response
}

export async function createDebate(data: {
  topic: string
  debate_type: string
  rounds: number
  participants: { agent_id: string; role?: string }[]
  synthesizer_agent_id?: string
  is_public?: boolean
  allow_external?: boolean
  context?: DebateContext
}): Promise<DebateSession> {
  const response = await apiClient.request('POST', '/api/v1/war-room/debates', data)
  return response?.data || response
}

export async function listDebates(status?: string): Promise<{ debates: DebateListItem[] }> {
  const url = status ? `/api/v1/war-room/debates?status=${status}` : '/api/v1/war-room/debates'
  const response = await apiClient.request('GET', url)
  return response?.data || response
}

export async function getDebate(id: string): Promise<DebateSession> {
  const response = await apiClient.request('GET', `/api/v1/war-room/debates/${id}`)
  return response?.data || response
}

export async function updateDebate(
  id: string,
  data: {
    topic?: string
    debate_type?: string
    rounds?: number
    participants?: { agent_id: string; role?: string }[]
    synthesizer_agent_id?: string
    is_public?: boolean
    allow_external?: boolean
    context?: DebateContext
  },
): Promise<DebateSession> {
  const response = await apiClient.request('PUT', `/api/v1/war-room/debates/${id}`, data)
  return response?.data || response
}

export async function stopDebate(id: string): Promise<DebateSession> {
  const response = await apiClient.request('POST', `/api/v1/war-room/debates/${id}/stop`)
  return response?.data || response
}

export async function deleteDebate(id: string): Promise<void> {
  await apiClient.request('DELETE', `/api/v1/war-room/debates/${id}`)
}

export function getDebateStartStreamUrl(id: string): string {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  return `${API_URL}/api/v1/war-room/debates/${id}/start`
}

export function getPublicDebateStreamUrl(shareToken: string): string {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  return `${API_URL}/api/v1/war-room/${shareToken}/live`
}

export async function getPublicDebate(shareToken: string): Promise<DebateSession> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  const response = await fetch(`${API_URL}/api/v1/war-room/${shareToken}/public`)
  if (!response.ok) throw new Error('Debate not found')
  return response.json()
}
