import { apiClient } from './client'
import type {
  WhatsAppBot,
  TeamsBot,
  CreateWhatsAppBotRequest,
  CreateTeamsBotRequest,
  UpdateWhatsAppBotRequest,
  UpdateTeamsBotRequest,
  WhatsAppQRSession,
} from '@/types/messaging-bots'

// WhatsApp Bots API
export const whatsappBotsApi = {
  getBots: async (agentId?: string): Promise<WhatsAppBot[]> => {
    const params = agentId ? { agent_id: agentId } : {}
    const response = await apiClient.request('GET', '/api/v1/whatsapp-bots', undefined, { params })
    return response.data?.bots || response.bots || []
  },

  getBot: async (botId: string): Promise<WhatsAppBot> => {
    const response = await apiClient.request('GET', `/api/v1/whatsapp-bots/${botId}`)
    return response.data || response
  },

  createBot: async (data: CreateWhatsAppBotRequest): Promise<WhatsAppBot> => {
    const response = await apiClient.request('POST', '/api/v1/whatsapp-bots', data)
    return response.data || response
  },

  updateBot: async (botId: string, data: UpdateWhatsAppBotRequest): Promise<WhatsAppBot> => {
    const response = await apiClient.request('PUT', `/api/v1/whatsapp-bots/${botId}`, data)
    return response.data || response
  },

  deleteBot: async (botId: string): Promise<void> => {
    await apiClient.request('DELETE', `/api/v1/whatsapp-bots/${botId}`)
  },

  startQRSession: async (agentId: string, botName: string): Promise<WhatsAppQRSession> => {
    const response = await apiClient.request('POST', '/api/v1/whatsapp-bots/qr/start', {
      agent_id: agentId,
      bot_name: botName,
    })
    return response.data || response
  },

  saveQRBot: async (sessionId: string, agentId: string, botName: string): Promise<WhatsAppBot> => {
    const response = await apiClient.request('POST', `/api/v1/whatsapp-bots/qr/${sessionId}/save`, {
      agent_id: agentId,
      bot_name: botName,
    })
    return response.data || response
  },

  cancelQRSession: async (sessionId: string): Promise<void> => {
    await apiClient.request('DELETE', `/api/v1/whatsapp-bots/qr/${sessionId}`)
  },

  unlinkDevice: async (botId: string): Promise<void> => {
    await apiClient.request('POST', `/api/v1/whatsapp-bots/${botId}/unlink`)
  },
}

// Teams Bots API
export const teamsBotsApi = {
  getBots: async (agentId?: string): Promise<TeamsBot[]> => {
    const params = agentId ? { agent_id: agentId } : {}
    const response = await apiClient.request('GET', '/api/v1/teams-bots', undefined, { params })
    return response.data?.bots || response.bots || []
  },

  getBot: async (botId: string): Promise<TeamsBot> => {
    const response = await apiClient.request('GET', `/api/v1/teams-bots/${botId}`)
    return response.data || response
  },

  createBot: async (data: CreateTeamsBotRequest): Promise<TeamsBot> => {
    const response = await apiClient.request('POST', '/api/v1/teams-bots', data)
    return response.data || response
  },

  updateBot: async (botId: string, data: UpdateTeamsBotRequest): Promise<TeamsBot> => {
    const response = await apiClient.request('PUT', `/api/v1/teams-bots/${botId}`, data)
    return response.data || response
  },

  deleteBot: async (botId: string): Promise<void> => {
    await apiClient.request('DELETE', `/api/v1/teams-bots/${botId}`)
  },
}

// Export individual functions for easier imports
export const getWhatsAppBots = whatsappBotsApi.getBots
export const getWhatsAppBot = whatsappBotsApi.getBot
export const createWhatsAppBot = whatsappBotsApi.createBot
export const updateWhatsAppBot = whatsappBotsApi.updateBot
export const deleteWhatsAppBot = whatsappBotsApi.deleteBot

export const getTeamsBots = teamsBotsApi.getBots
export const getTeamsBot = teamsBotsApi.getBot
export const createTeamsBot = teamsBotsApi.createBot
export const updateTeamsBot = teamsBotsApi.updateBot
export const deleteTeamsBot = teamsBotsApi.deleteBot
