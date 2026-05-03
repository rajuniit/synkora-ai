import { apiClient } from './http'

export interface WikiArticle {
  id: string
  title: string
  slug: string
  category: string
  summary: string | null
  content?: string
  staleness_score: number
  status: string
  auto_generated: boolean
  source_documents: { doc_id: string; doc_title: string }[]
  backlinks: string[]
  forward_links: string[]
  linked_articles?: { id: string; title: string; slug: string; category: string }[]
  last_compiled_at: string | null
  created_at: string | null
}

export interface AutopilotStatus {
  total_articles: number
  avg_staleness: number
  category_counts: Record<string, number>
  last_compilation: {
    id: string | null
    status: string | null
    started_at: string | null
    completed_at: string | null
    articles_created: number
    articles_updated: number
  } | null
}

export interface WikiGraphData {
  nodes: { id: string; title: string; slug: string; category: string; staleness: number }[]
  links: { source: string; target: string }[]
}

export interface LLMConfigOption {
  id: string
  name: string
  provider: string
  model_name: string
  agent_name: string
}

export async function getLLMConfigsForCompilation(kbId: string): Promise<{ configs: LLMConfigOption[] }> {
  return apiClient.request('GET', `/api/v1/knowledge-bases/${kbId}/autopilot/llm-configs`)
}

export async function triggerCompilation(kbId: string, llmConfigId?: string): Promise<any> {
  return apiClient.request('POST', `/api/v1/knowledge-bases/${kbId}/autopilot/compile`, {
    llm_config_id: llmConfigId ?? null,
  })
}

export async function getWikiArticles(
  kbId: string,
  category?: string,
): Promise<{ articles: WikiArticle[]; categories: Record<string, WikiArticle[]>; total: number }> {
  const url = category
    ? `/api/v1/knowledge-bases/${kbId}/wiki?category=${category}`
    : `/api/v1/knowledge-bases/${kbId}/wiki`
  return apiClient.request('GET', url)
}

export async function getWikiArticle(kbId: string, slug: string): Promise<WikiArticle> {
  return apiClient.request('GET', `/api/v1/knowledge-bases/${kbId}/wiki/article/${slug}`)
}

export async function getWikiGraph(kbId: string): Promise<WikiGraphData> {
  return apiClient.request('GET', `/api/v1/knowledge-bases/${kbId}/wiki/graph`)
}

export async function searchWiki(
  kbId: string,
  query: string,
): Promise<{ results: WikiArticle[]; total: number }> {
  return apiClient.request('POST', `/api/v1/knowledge-bases/${kbId}/wiki/search`, { q: query })
}

export async function getAutopilotStatus(kbId: string): Promise<AutopilotStatus> {
  return apiClient.request('GET', `/api/v1/knowledge-bases/${kbId}/autopilot/status`)
}
