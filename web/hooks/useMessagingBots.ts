import { useState, useEffect } from 'react'
import { whatsappBotsApi, teamsBotsApi } from '@/lib/api/messaging-bots'
import type {
  WhatsAppBot,
  TeamsBot,
  CreateWhatsAppBotRequest,
  CreateTeamsBotRequest,
  UpdateWhatsAppBotRequest,
  UpdateTeamsBotRequest,
} from '@/types/messaging-bots'

// WhatsApp Bots Hook
export function useWhatsAppBots(agentId?: string) {
  const [bots, setBots] = useState<WhatsAppBot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchBots = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await whatsappBotsApi.getBots(agentId)
      setBots(data)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch WhatsApp bots')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBots()
  }, [agentId])

  const createBot = async (data: CreateWhatsAppBotRequest): Promise<WhatsAppBot> => {
    try {
      const newBot = await whatsappBotsApi.createBot(data)
      setBots([...bots, newBot])
      return newBot
    } catch (err: any) {
      throw new Error(err.message || 'Failed to create WhatsApp bot')
    }
  }

  const updateBot = async (botId: string, data: UpdateWhatsAppBotRequest): Promise<WhatsAppBot> => {
    try {
      const updatedBot = await whatsappBotsApi.updateBot(botId, data)
      setBots(bots.map((b: WhatsAppBot) => b.bot_id === botId ? updatedBot : b))
      return updatedBot
    } catch (err: any) {
      throw new Error(err.message || 'Failed to update WhatsApp bot')
    }
  }

  const deleteBot = async (botId: string): Promise<void> => {
    try {
      await whatsappBotsApi.deleteBot(botId)
      setBots(bots.filter((b: WhatsAppBot) => b.bot_id !== botId))
    } catch (err: any) {
      throw new Error(err.message || 'Failed to delete WhatsApp bot')
    }
  }

  const toggleActive = async (bot: WhatsAppBot): Promise<void> => {
    await updateBot(bot.bot_id, { is_active: !bot.is_active })
  }

  return {
    bots,
    loading,
    error,
    fetchBots,
    createBot,
    updateBot,
    deleteBot,
    toggleActive,
    refetch: fetchBots,
  }
}

// Teams Bots Hook
export function useTeamsBots(agentId?: string) {
  const [bots, setBots] = useState<TeamsBot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchBots = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await teamsBotsApi.getBots(agentId)
      setBots(data)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch Teams bots')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBots()
  }, [agentId])

  const createBot = async (data: CreateTeamsBotRequest): Promise<TeamsBot> => {
    try {
      const newBot = await teamsBotsApi.createBot(data)
      setBots([...bots, newBot])
      return newBot
    } catch (err: any) {
      throw new Error(err.message || 'Failed to create Teams bot')
    }
  }

  const updateBot = async (botId: string, data: UpdateTeamsBotRequest): Promise<TeamsBot> => {
    try {
      const updatedBot = await teamsBotsApi.updateBot(botId, data)
      setBots(bots.map((b: TeamsBot) => b.bot_id === botId ? updatedBot : b))
      return updatedBot
    } catch (err: any) {
      throw new Error(err.message || 'Failed to update Teams bot')
    }
  }

  const deleteBot = async (botId: string): Promise<void> => {
    try {
      await teamsBotsApi.deleteBot(botId)
      setBots(bots.filter((b: TeamsBot) => b.bot_id !== botId))
    } catch (err: any) {
      throw new Error(err.message || 'Failed to delete Teams bot')
    }
  }

  const toggleActive = async (bot: TeamsBot): Promise<void> => {
    await updateBot(bot.bot_id, { is_active: !bot.is_active })
  }

  return {
    bots,
    loading,
    error,
    fetchBots,
    createBot,
    updateBot,
    deleteBot,
    toggleActive,
    refetch: fetchBots,
  }
}
