import { apiClient } from './http'

export async function getTelegramBots(agentId?: string): Promise<any[]> {
  const params = agentId ? { agent_id: agentId } : {}
  const { data } = await apiClient.axios.get('/api/v1/telegram-bots', { params })
  return data
}

export async function getTelegramBot(botId: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/telegram-bots/${botId}`)
  return data
}

export async function createTelegramBot(botData: any): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/telegram-bots', botData)
  return data
}

export async function updateTelegramBot(botId: string, botData: any): Promise<any> {
  const { data } = await apiClient.axios.put(`/api/v1/telegram-bots/${botId}`, botData)
  return data
}

export async function deleteTelegramBot(botId: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/telegram-bots/${botId}`)
}

export async function startTelegramBot(botId: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/telegram-bots/${botId}/start`)
  return data
}

export async function stopTelegramBot(botId: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/telegram-bots/${botId}/stop`)
  return data
}

export async function restartTelegramBot(botId: string): Promise<any> {
  const { data } = await apiClient.axios.post(`/api/v1/telegram-bots/${botId}/restart`)
  return data
}

export async function getTelegramBotStatus(botId: string): Promise<any> {
  const { data } = await apiClient.axios.get(`/api/v1/telegram-bots/${botId}/status`)
  return data
}

export async function validateTelegramToken(token: string): Promise<any> {
  const { data } = await apiClient.axios.post('/api/v1/telegram-bots/validate-token', { bot_token: token })
  return data
}
