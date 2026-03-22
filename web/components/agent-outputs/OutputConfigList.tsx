'use client'

import { useState } from 'react'
import { 
  Send, 
  Mail,
  MessageSquare,
  Webhook,
  Edit,
  Trash2,
  MoreVertical,
  Loader2,
  AlertCircle,
  Plus,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { useAgentOutputs } from '@/hooks/useAgentOutputs'
import toast from 'react-hot-toast'
import type { OutputConfig } from '@/types/agent-outputs'

export interface OutputConfigListProps {
  agentId: string
  refreshKey?: number
  onCreateClick?: () => void
  onEditClick?: (config: OutputConfig) => void
}

const providerIcons: Record<string, any> = {
  slack: MessageSquare,
  email: Mail,
  webhook: Webhook
}

const providerColors: Record<string, string> = {
  slack: 'bg-pink-100 text-pink-700',
  email: 'bg-blue-100 text-blue-700',
  webhook: 'bg-purple-100 text-purple-700'
}

export function OutputConfigList({ agentId, refreshKey = 0, onCreateClick, onEditClick }: OutputConfigListProps) {
  const { outputs: configs, loading, error, deleteOutput } = useAgentOutputs(agentId)
  const [actionMenuOpen, setActionMenuOpen] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const handleDelete = async (configId: string) => {
    if (!confirm('Are you sure you want to delete this output configuration? This action cannot be undone.')) {
      return
    }

    setDeleting(configId)
    setActionMenuOpen(null)

    try {
      await deleteOutput(configId)
      toast.success('Output configuration deleted successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete output configuration')
    } finally {
      setDeleting(null)
    }
  }

  if (loading && configs.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-red-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-600 text-sm">Loading output configurations...</p>
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
              <p className="font-medium text-red-900">Error Loading Output Configurations</p>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (configs.length === 0) {
    return (
      <div className="p-16 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
          <Send className="w-8 h-8 text-red-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Output Configurations Yet</h3>
        <p className="text-gray-600 mb-6 max-w-md mx-auto text-sm">
          Create your first output configuration to route agent responses to Slack, Email, or external webhooks.
        </p>
        <button
          onClick={onCreateClick}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md"
        >
          <Plus className="w-4 h-4" />
          Create Output Configuration
        </button>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="grid gap-4">
        {configs.map((config) => {
          const Icon = providerIcons[config.provider] || Send
          const colorClass = providerColors[config.provider] || 'bg-gray-100 text-gray-700'

          return (
            <div
              key={config.id}
              className="border border-gray-200 rounded-lg p-5 hover:border-red-300 hover:shadow-sm transition-all bg-white"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div className={`p-2.5 rounded-lg ${colorClass}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-gray-900">{config.name}</h3>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                        config.is_enabled
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          config.is_enabled ? 'bg-green-600' : 'bg-gray-400'
                        }`} />
                        {config.is_enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    
                    {config.description && (
                      <p className="text-sm text-gray-600 mb-3">{config.description}</p>
                    )}

                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                      <span className="capitalize">{config.provider}</span>
                      {config.provider === 'slack' && config.config?.channel && (
                        <>
                          <span className="text-gray-300">•</span>
                          <span className="font-mono text-xs">{config.config.channel}</span>
                        </>
                      )}
                      {config.provider === 'email' && config.config?.to && (
                        <>
                          <span className="text-gray-300">•</span>
                          <span className="text-xs">{config.config.to.join(', ')}</span>
                        </>
                      )}
                      {config.provider === 'webhook' && config.config?.url && (
                        <>
                          <span className="text-gray-300">•</span>
                          <span className="font-mono text-xs truncate max-w-xs">{config.config.url}</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {config.send_on_webhook_trigger && (
                        <div className="flex items-center gap-1.5">
                          <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                          <span>Webhook triggers</span>
                        </div>
                      )}
                      {config.send_on_chat_completion && (
                        <div className="flex items-center gap-1.5">
                          <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                          <span>Chat completions</span>
                        </div>
                      )}
                      {config.retry_on_failure && (
                        <div className="flex items-center gap-1.5">
                          <span className="text-gray-400">•</span>
                          <span>Retries: {config.max_retries}</span>
                        </div>
                      )}
                    </div>

                    {config.output_template && (
                      <div className="mt-3 p-2 bg-gray-50 rounded border border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">Custom Template:</p>
                        <code className="text-xs text-gray-700 font-mono block truncate">
                          {config.output_template}
                        </code>
                      </div>
                    )}
                  </div>
                </div>

                <div className="relative ml-4">
                  <button
                    onClick={() => setActionMenuOpen(actionMenuOpen === config.id ? null : config.id)}
                    disabled={deleting === config.id}
                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {deleting === config.id ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <MoreVertical className="w-5 h-5" />
                    )}
                  </button>

                  {actionMenuOpen === config.id && (
                    <>
                      <div
                        className="fixed inset-0 z-10"
                        onClick={() => setActionMenuOpen(null)}
                      />
                      <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                        <button
                          onClick={() => {
                            setActionMenuOpen(null)
                            onEditClick?.(config)
                          }}
                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          <Edit className="w-4 h-4" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(config.id)}
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
