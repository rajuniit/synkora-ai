import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/client'
import { Webhook, WebhookCreate, WebhookUpdate, WebhookEvent, WebhookStats } from '@/types/webhooks'

export function useWebhooks(agentName: string) {
  const [webhooks, setWebhooks] = useState<Webhook[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchWebhooks = async () => {
    try {
      setIsLoading(true)
      const data = await apiClient.request('GET', `/api/v1/agents/${agentName}/webhooks`)
      setWebhooks(data)
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch webhooks')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const createWebhook = async (webhookData: WebhookCreate): Promise<Webhook> => {
    const data = await apiClient.request('POST', `/api/v1/agents/${agentName}/webhooks`, webhookData)
    await fetchWebhooks()
    return data
  }

  const updateWebhook = async (webhookId: string, webhookData: WebhookUpdate): Promise<Webhook> => {
    const data = await apiClient.request('PATCH', `/api/v1/agents/${agentName}/webhooks/${webhookId}`, webhookData)
    await fetchWebhooks()
    return data
  }

  const deleteWebhook = async (webhookId: string): Promise<void> => {
    await apiClient.request('DELETE', `/api/v1/agents/${agentName}/webhooks/${webhookId}`)
    await fetchWebhooks()
  }

  const getWebhookEvents = async (webhookId: string, limit = 50): Promise<WebhookEvent[]> => {
    const data = await apiClient.request('GET', `/api/v1/agents/${agentName}/webhooks/${webhookId}/events?limit=${limit}`)
    return data
  }

  const deleteWebhookEvent = async (webhookId: string, eventId: string): Promise<void> => {
    await apiClient.request('DELETE', `/api/v1/agents/${agentName}/webhooks/${webhookId}/events/${eventId}`)
  }

  const getWebhookStats = async (webhookId: string): Promise<WebhookStats> => {
    const data = await apiClient.request('GET', `/api/v1/agents/${agentName}/webhooks/${webhookId}/stats`)
    return data
  }

  useEffect(() => {
    if (agentName) {
      fetchWebhooks()
    }
  }, [agentName])

  return {
    webhooks,
    isLoading,
    error,
    createWebhook,
    updateWebhook,
    deleteWebhook,
    getWebhookEvents,
    deleteWebhookEvent,
    getWebhookStats,
    refetch: fetchWebhooks,
  }
}
