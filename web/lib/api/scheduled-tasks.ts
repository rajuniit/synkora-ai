import { apiClient } from './http'

export async function getScheduledTasks(skip?: number, limit?: number): Promise<any[]> {
  const params: any = {}
  if (skip !== undefined) params.skip = skip
  if (limit !== undefined) params.limit = limit
  const { data } = await apiClient.axios.get('/api/v1/scheduled-tasks', { params })
  return data
}

export async function getScheduledTask(id: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/scheduled-tasks/${id}`)
  return data
}

export async function createScheduledTask(taskData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/scheduled-tasks', taskData)
  return data
}

export async function updateScheduledTask(id: string, taskData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/scheduled-tasks/${id}`, taskData)
  return data
}

export async function deleteScheduledTask(id: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/scheduled-tasks/${id}`)
}

export async function executeScheduledTask(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/scheduled-tasks/${id}/execute`)
  return data
}

export async function toggleScheduledTask(id: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/scheduled-tasks/${id}/toggle`)
  return data
}

export async function getTaskExecutions(taskId: string, skip?: number, limit?: number): Promise<any[]> {
  const params: any = {}
  if (skip !== undefined) params.skip = skip
  if (limit !== undefined) params.limit = limit
  const { data } = await apiClient.axios.get(`/api/v1/scheduled-tasks/${taskId}/executions`, { params })
  return data
}

export async function validateCronExpression(cronExpression: string): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/scheduled-tasks/validate-cron', {
    cron_expression: cronExpression
  })
  return data
}
