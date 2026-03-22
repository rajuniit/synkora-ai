import { apiClient } from './http'

export async function getDatabaseConnections(): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/database-connections')
  return data
}

export async function getDatabaseConnection(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/database-connections/${id}`)
  return data
}

export async function createDatabaseConnection(connectionData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/database-connections', connectionData)
  return data
}

export async function updateDatabaseConnection(id: string, connectionData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/database-connections/${id}`, connectionData)
  return data
}

export async function deleteDatabaseConnection(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/database-connections/${id}`)
}

export async function testDatabaseConnection(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/database-connections/${id}/test`)
  return data
}

export async function testDatabaseConnectionDetails(connectionData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/database-connections/test', connectionData)
  return data
}
