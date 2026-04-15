import { apiClient } from './http'

export async function getDataSources(knowledgeBaseId?: string): Promise<any[]> {
  const params = knowledgeBaseId ? { knowledge_base_id: knowledgeBaseId } : {}
  const { data } = await apiClient.axios.get('/api/v1/data-sources', { params })
  return data
}

export async function getDataSource(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/data-sources/${id}`)
  return data
}

export async function createDataSource(sourceData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/data-sources', sourceData)
  return data
}

export async function deleteDataSource(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/data-sources/${id}`)
}

export async function syncDataSource(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/data-sources/${id}/sync`)
  return data
}

export async function getDataSourceSyncHistory(id: string): Promise<any[]> {
  const { data } = await apiClient.axios.get(`/api/v1/data-sources/${id}/sync-history`)
  return data
}

export async function getStreamHealth(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/data-sources/${id}/stream-health`)
  return data
}

export async function updateDataSourceConfig(id: string, config: Record<string, any>): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/data-sources/${id}`, { config })
  return data
}

export async function activateDataSource(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/data-sources/${id}/activate`)
  return data
}

export async function deactivateDataSource(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/data-sources/${id}/deactivate`)
  return data
}
