import { apiClient } from './http'

// Projects
export async function getProjects(): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/projects')
  return data.data?.projects || data
}

export async function getProject(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/projects/${id}`)
  return data.data || data
}

export async function createProject(projectData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/projects', projectData)
  return data
}

export async function updateProject(id: string, projectData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/projects/${id}`, projectData)
  return data
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/projects/${id}`)
}

export async function getProjectContext(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/projects/${id}/context`)
  return data.data || data
}

export async function updateProjectContext(id: string, contextData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/projects/${id}/context`, contextData)
  return data
}

export async function addAgentToProject(projectId: string, agentId: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/projects/${projectId}/agents`, { agent_id: agentId })
  return data
}

export async function removeAgentFromProject(projectId: string, agentId: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/projects/${projectId}/agents/${agentId}`)
}

// Escalations
export async function getEscalations(params?: { project_id?: string; status?: string; human_id?: string }): Promise<any[]> {
  const { data } = await apiClient.axios.get('/api/v1/escalations', { params })
  return data.data?.escalations || data
}

export async function getEscalation(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/escalations/${id}`)
  return data.data || data
}

export async function resolveEscalation(id: string, response: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/escalations/${id}/resolve`, { response })
  return data
}
