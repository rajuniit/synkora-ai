import { apiClient } from './http'

export async function getCustomTools(): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/custom-tools')
  return data.data?.tools || data
}

export async function getCustomTool(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/custom-tools/${id}`)
  return data.data || data
}

export async function createCustomTool(toolData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/custom-tools', toolData)
  return data
}

export async function updateCustomTool(id: string, toolData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/custom-tools/${id}`, toolData)
  return data
}

export async function deleteCustomTool(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/custom-tools/${id}`)
}

export async function importCustomToolFromUrl(url: string): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/custom-tools/import-url', { url })
  return data
}

export async function getCustomToolOperations(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/custom-tools/${id}/operations`)
  return data.data || data
}

export async function testCustomTool(id: string, params?: any): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/custom-tools/${id}/test`, params || {})
  return data
}

export async function executeCustomTool(id: string, operationId: string, params: any): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/custom-tools/${id}/execute`, {
    operation_id: operationId,
    parameters: params
  })
  return data
}
