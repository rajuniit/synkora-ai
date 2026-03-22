import { apiClient } from './http'

export async function getAppStoreSources(): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/app-store-sources')
  return data
}

export async function getAppStoreSource(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/app-store-sources/${id}`)
  return data
}

export async function createAppStoreSource(sourceData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/app-store-sources', sourceData)
  return data
}

export async function updateAppStoreSource(id: string, sourceData: any): Promise<any> {
  const { data } = await apiClient.axios.patch(`/api/v1/app-store-sources/${id}`, sourceData)
  return data
}

export async function deleteAppStoreSource(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/app-store-sources/${id}`)
}

export async function syncAppStoreReviews(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/app-store-sources/${id}/sync`)
  return data
}

export async function analyzeAppStoreReviews(id: string, analysisData: any): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/app-store-sources/${id}/analyze`, analysisData)
  return data
}

export async function getAppStoreInsights(id: string, params?: any): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/app-store-sources/${id}/insights`, { params })
  return data
}

export async function getAppStoreReviews(id: string, params?: any): Promise<any[]> {
  const { data } = await apiClient.axios.get(`/api/v1/app-store-sources/${id}/reviews`, { params })
  return data
}
