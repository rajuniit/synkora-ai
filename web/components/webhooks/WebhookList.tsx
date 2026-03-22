'use client'

import { useEffect, useState } from 'react'
import {
  Webhook,
  Github,
  MessageSquare,
  CheckSquare,
  Activity,
  Copy,
  Edit,
  Trash2,
  MoreVertical,
  Loader2,
  AlertCircle,
  Plus
} from 'lucide-react'
import { useWebhooks } from '@/hooks/useWebhooks'
import toast from 'react-hot-toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

export interface WebhookListProps {
  agentName: string
  refreshKey?: number
  onCreateClick?: () => void
}

const providerIcons: Record<string, any> = {
  github: Github,
  clickup: CheckSquare,
  jira: Activity,
  slack: MessageSquare,
  custom: Webhook
}

const providerColors: Record<string, string> = {
  github: 'bg-gray-100 text-gray-700',
  clickup: 'bg-purple-100 text-purple-700',
  jira: 'bg-blue-100 text-blue-700',
  slack: 'bg-pink-100 text-pink-700',
  custom: 'bg-amber-100 text-amber-700'
}

export function WebhookList({ agentName, refreshKey = 0, onCreateClick }: WebhookListProps) {
  const { webhooks, isLoading: loading, error, deleteWebhook } = useWebhooks(agentName)
  const [actionMenuOpen, setActionMenuOpen] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const handleCopyUrl = (url: string) => {
    const fullUrl = `${API_URL}${url}`
    navigator.clipboard.writeText(fullUrl)
    toast.success('Webhook URL copied to clipboard')
  }

  const handleDelete = async (webhookId: string) => {
    if (!confirm('Are you sure you want to delete this webhook? This action cannot be undone.')) {
      return
    }

    setDeleting(webhookId)
    setActionMenuOpen(null)

    try {
      await deleteWebhook(webhookId)
      toast.success('Webhook deleted successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete webhook')
    } finally {
      setDeleting(null)
    }
  }

  if (loading && webhooks.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-red-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-600 text-sm">Loading webhooks...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-900">Error Loading Webhooks</p>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (webhooks.length === 0) {
    return (
      <div className="p-16 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
          <Webhook className="w-8 h-8 text-red-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Webhooks Yet</h3>
        <p className="text-gray-600 mb-6 max-w-md mx-auto text-sm">
          Create your first webhook to receive real-time events from GitHub, ClickUp, Jira, or Slack.
        </p>
        <button
          onClick={onCreateClick}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md"
        >
          <Plus className="w-4 h-4" />
          Create Webhook
        </button>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="grid gap-4">
        {webhooks.map((webhook) => {
          const Icon = providerIcons[webhook.provider.toLowerCase()] || Webhook
          const colorClass = providerColors[webhook.provider.toLowerCase()] || providerColors.custom

          return (
            <div
              key={webhook.id}
              className="border border-gray-200 rounded-lg p-5 hover:border-red-300 hover:shadow-sm transition-all bg-white"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div className={`p-2.5 rounded-lg ${colorClass}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-gray-900">{webhook.name}</h3>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                        webhook.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          webhook.is_active ? 'bg-green-600' : 'bg-gray-400'
                        }`} />
                        {webhook.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                      <span className="capitalize">{webhook.provider}</span>
                      {webhook.event_types && webhook.event_types.length > 0 && (
                        <>
                          <span className="text-gray-300">•</span>
                          <span>{webhook.event_types.join(', ')}</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg p-3 border border-gray-200">
                      <code className="text-xs text-gray-700 flex-1 truncate font-mono">
                        {`${API_URL}${webhook.webhook_url}`}
                      </code>
                      <button
                        onClick={() => handleCopyUrl(webhook.webhook_url)}
                        className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                        title="Copy URL"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="flex items-center gap-6 mt-3 text-xs text-gray-500">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-green-600">{webhook.success_count || 0}</span>
                        <span>successful</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-red-600">{webhook.failure_count || 0}</span>
                        <span>failed</span>
                      </div>
                      {webhook.last_triggered_at && (
                        <>
                          <span className="text-gray-300">•</span>
                          <span>
                            Last triggered {new Date(webhook.last_triggered_at).toLocaleDateString()}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="relative ml-4">
                  <button
                    onClick={() => setActionMenuOpen(actionMenuOpen === webhook.id ? null : webhook.id)}
                    disabled={deleting === webhook.id}
                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {deleting === webhook.id ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <MoreVertical className="w-5 h-5" />
                    )}
                  </button>

                  {actionMenuOpen === webhook.id && (
                    <>
                      <div
                        className="fixed inset-0 z-10"
                        onClick={() => setActionMenuOpen(null)}
                      />
                      <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                        <button
                          onClick={() => {
                            setActionMenuOpen(null)
                            // TODO: Implement edit functionality
                            toast.error('Edit functionality coming soon')
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(webhook.id)}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
