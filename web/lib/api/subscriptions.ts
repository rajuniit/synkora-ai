import { apiClient } from './http'

export async function toggleSubscriptions(agentId: string): Promise<{ agent_id: string; allow_subscriptions: boolean }> {
  const { data } = await apiClient.axios.patch(`/api/v1/agents/${agentId}/subscriptions/toggle`)
  return data
}

export async function getSubscribers(agentId: string): Promise<any[]> {
  const { data } = await apiClient.axios.get(`/api/v1/agents/${agentId}/subscribers`)
  return data
}

export async function deleteSubscriber(agentId: string, subscriptionId: string): Promise<void> {
  await apiClient.axios.delete(`/api/v1/agents/${agentId}/subscribers/${subscriptionId}`)
}

// Public — no auth required, uses a plain axios call
export async function subscribeToAgent(agentId: string, email: string): Promise<{ message: string }> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  const response = await fetch(`${API_URL}/api/v1/agents/${agentId}/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to subscribe')
  }
  return response.json()
}
