import { apiClient } from './http'

// Agent Roles
export async function getAgentRoles(): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/agent-roles')
  return data.data?.roles || data
}

export async function getAgentRole(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/agent-roles/${id}`)
  return data.data || data
}

export async function createAgentRole(roleData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/agent-roles', roleData)
  return data
}

export async function updateAgentRole(id: string, roleData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/agent-roles/${id}`, roleData)
  return data
}

export async function deleteAgentRole(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/agent-roles/${id}`)
}

// Human Contacts
export async function getHumanContacts(): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/human-contacts')
  return data.data?.contacts || data
}

export async function getHumanContact(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/human-contacts/${id}`)
  return data.data || data
}

export async function createHumanContact(contactData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/human-contacts', contactData)
  return data
}

export async function updateHumanContact(id: string, contactData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/human-contacts/${id}`, contactData)
  return data
}

export async function deleteHumanContact(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/human-contacts/${id}`)
}
