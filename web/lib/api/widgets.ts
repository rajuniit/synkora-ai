import { apiClient } from './http'

export async function getWidgets(agentId?: string): Promise<any[]> {
  const params = agentId ? { agent_id: agentId } : {}
  const { data } = await apiClient.axios.get('/api/v1/widgets', { params })
  return data.data?.widgets || data
}

export async function getWidget(widgetId: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/widgets/${widgetId}`)
  return data.data || data
}

export async function createWidget(widgetData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/widgets', widgetData)
  return data
}

export async function updateWidget(widgetId: string, widgetData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/widgets/${widgetId}`, widgetData)
  return data
}

export async function deleteWidget(widgetId: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/widgets/${widgetId}`)
}

export async function regenerateWidgetKey(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/widgets/${id}/regenerate-key`)
  return data
}

export async function getWidgetEmbedCode(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/widgets/${id}/embed-code`)
  return data
}

export async function regenerateIdentitySecret(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/widgets/${id}/regenerate-identity-secret`)
  return data
}

export async function getWidgetRoutes(id: string): Promise<any[]> {
  const { data } = await apiClient.axios.get(`/api/v1/widgets/${id}/routes`)
  return data.data?.routes || []
}

export async function setWidgetRoutes(id: string, routes: { external_org_id: string; agent_id: string }[]): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/widgets/${id}/routes`, routes)
  return data
}

export async function deleteWidgetRoute(id: string, externalOrgId: string): Promise<any> {
  const { data } = await apiClient.axios.delete(`/api/v1/widgets/${id}/routes/${encodeURIComponent(externalOrgId)}`)
  return data
}
