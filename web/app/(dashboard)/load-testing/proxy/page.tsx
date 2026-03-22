'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  ArrowLeft,
  Plus,
  Server,
  Key,
  Activity,
  Trash2,
  Eye,
  EyeOff,
  RefreshCw,
  Copy,
  CheckCircle,
  XCircle,
  Settings,
  Zap,
} from 'lucide-react'
import {
  getProxyConfigs,
  deleteProxyConfig,
  regenerateProxyApiKey,
  type ProxyConfig,
} from '@/lib/api/load-testing'

export default function ProxyConfigsPage() {
  const [proxyConfigs, setProxyConfigs] = useState<ProxyConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [regenerating, setRegenerating] = useState<string | null>(null)
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; config: ProxyConfig | null }>({
    show: false,
    config: null,
  })
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())
  const [newApiKey, setNewApiKey] = useState<{ id: string; key: string } | null>(null)

  useEffect(() => {
    fetchProxyConfigs()
  }, [])

  const fetchProxyConfigs = async () => {
    try {
      setLoading(true)
      const response = await getProxyConfigs()
      setProxyConfigs(response.items || [])
    } catch (err) {
      toast.error('Failed to load proxy configurations')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteModal.config) return

    setDeleting(deleteModal.config.id)
    try {
      await deleteProxyConfig(deleteModal.config.id)
      toast.success('Proxy configuration deleted')
      setDeleteModal({ show: false, config: null })
      fetchProxyConfigs()
    } catch (err) {
      toast.error('Failed to delete proxy configuration')
    } finally {
      setDeleting(null)
    }
  }

  const handleRegenerateKey = async (configId: string) => {
    setRegenerating(configId)
    try {
      const result = await regenerateProxyApiKey(configId)
      setNewApiKey({ id: configId, key: result.api_key })
      toast.success('API key regenerated')
    } catch (err) {
      toast.error('Failed to regenerate API key')
    } finally {
      setRegenerating(null)
    }
  }

  const toggleKeyVisibility = (configId: string) => {
    setVisibleKeys((prev) => {
      const next = new Set(prev)
      if (next.has(configId)) {
        next.delete(configId)
      } else {
        next.add(configId)
      }
      return next
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const getProviderColor = (provider: string) => {
    const colors: Record<string, string> = {
      openai: 'bg-emerald-100 text-emerald-700',
      anthropic: 'bg-orange-100 text-orange-700',
      google: 'bg-blue-100 text-blue-700',
    }
    return colors[provider] || 'bg-gray-100 text-gray-700'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50/30">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading proxy configurations...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50/30 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/load-testing"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Load Testing
          </Link>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">LLM Proxy Configurations</h1>
              <p className="text-gray-600 mt-1">
                Configure mock LLM endpoints to test your AI agents without real API costs
              </p>
            </div>

            <Link
              href="/load-testing/proxy/create"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white rounded-xl transition-all shadow-sm hover:shadow-md font-medium"
            >
              <Plus className="w-5 h-5" />
              Create Proxy
            </Link>
          </div>
        </div>

        {/* Info Card */}
        <div className="mb-8 bg-gradient-to-r from-primary-500 to-purple-600 rounded-xl p-6 text-white">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/20 rounded-xl">
              <Server className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-semibold text-lg mb-2">How the LLM Proxy Works</h3>
              <p className="text-primary-100 text-sm mb-3">
                The LLM Proxy provides mock endpoints that simulate real LLM APIs. Configure your AI agent
                to use the proxy URL instead of the real API during load testing to avoid costs.
              </p>
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="text-primary-200">OpenAI:</span>{' '}
                  <code className="bg-white/10 px-2 py-0.5 rounded">proxy.synkora.com/v1/chat/completions</code>
                </div>
                <div>
                  <span className="text-primary-200">Anthropic:</span>{' '}
                  <code className="bg-white/10 px-2 py-0.5 rounded">proxy.synkora.com/v1/messages</code>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Proxy Configs Grid */}
        {proxyConfigs.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
            <div className="w-32 h-32 mx-auto mb-6 relative">
              <div className="absolute inset-0 bg-gradient-to-br from-primary-100 to-primary-50 rounded-2xl transform rotate-6"></div>
              <div className="absolute inset-0 bg-white rounded-2xl shadow-sm border border-gray-100 flex items-center justify-center">
                <Server className="w-12 h-12 text-primary-500" />
              </div>
            </div>

            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Create your first proxy configuration
            </h3>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              Proxy configurations allow you to test your AI agents without consuming real API credits.
            </p>
            <Link
              href="/load-testing/proxy/create"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white rounded-xl transition-all shadow-sm hover:shadow-md font-medium"
            >
              <Plus className="w-5 h-5" />
              Create Proxy Config
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {proxyConfigs.map((config) => (
              <div
                key={config.id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all"
              >
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 bg-primary-100 rounded-xl">
                        <Server className="w-5 h-5 text-primary-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{config.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getProviderColor(config.provider)}`}>
                          {config.provider}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {config.is_active ? (
                        <span className="flex items-center gap-1 text-xs text-green-600">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <XCircle className="w-3.5 h-3.5" />
                          Inactive
                        </span>
                      )}
                    </div>
                  </div>

                  {/* API Key */}
                  <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500 flex items-center gap-1">
                        <Key className="w-3.5 h-3.5" />
                        API Key
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => toggleKeyVisibility(config.id)}
                          className="p-1 text-gray-400 hover:text-gray-600"
                        >
                          {visibleKeys.has(config.id) ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => copyToClipboard(config.api_key_prefix + '...')}
                          className="p-1 text-gray-400 hover:text-gray-600"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleRegenerateKey(config.id)}
                          disabled={regenerating === config.id}
                          className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                        >
                          <RefreshCw className={`w-4 h-4 ${regenerating === config.id ? 'animate-spin' : ''}`} />
                        </button>
                      </div>
                    </div>
                    <code className="text-sm text-gray-700 font-mono">
                      {newApiKey?.id === config.id
                        ? newApiKey.key
                        : visibleKeys.has(config.id)
                        ? config.api_key_prefix + '...'
                        : '••••••••••••••••'}
                    </code>
                    {newApiKey?.id === config.id && (
                      <p className="text-xs text-amber-600 mt-2">
                        Save this key now - it won't be shown again!
                      </p>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="p-2 bg-blue-50 rounded-lg text-center">
                      <div className="text-lg font-semibold text-blue-700">
                        {config.usage_count.toLocaleString()}
                      </div>
                      <div className="text-xs text-blue-600">Requests</div>
                    </div>
                    <div className="p-2 bg-green-50 rounded-lg text-center">
                      <div className="text-lg font-semibold text-green-700">
                        {(config.total_tokens_generated / 1000).toFixed(1)}K
                      </div>
                      <div className="text-xs text-green-600">Tokens</div>
                    </div>
                    <div className="p-2 bg-purple-50 rounded-lg text-center">
                      <div className="text-lg font-semibold text-purple-700">
                        {config.rate_limit}
                      </div>
                      <div className="text-xs text-purple-600">RPS Limit</div>
                    </div>
                  </div>

                  {/* Mock Config Summary */}
                  <div className="text-sm text-gray-600 mb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Settings className="w-4 h-4 text-gray-400" />
                      <span>Mock Config:</span>
                    </div>
                    <div className="ml-6 text-xs space-y-1">
                      <div>
                        Latency: {config.mock_config?.latency?.ttft_min_ms || 100}-
                        {config.mock_config?.latency?.ttft_max_ms || 500}ms TTFT
                      </div>
                      <div>
                        Response: {config.mock_config?.response?.min_tokens || 50}-
                        {config.mock_config?.response?.max_tokens || 500} tokens
                      </div>
                      <div>
                        Error rate: {((config.mock_config?.errors?.rate || 0) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                    <span className="text-xs text-gray-500">
                      Created {formatDate(config.created_at)}
                    </span>
                    <button
                      onClick={() => setDeleteModal({ show: true, config })}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Modal */}
      {deleteModal.show && deleteModal.config && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 bg-red-100 rounded-xl">
                <Trash2 className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Delete Proxy Config</h3>
            </div>

            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <span className="font-semibold text-gray-900">"{deleteModal.config.name}"</span>?
              Any load tests using this proxy will need to be reconfigured.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteModal({ show: false, config: null })}
                disabled={deleting !== null}
                className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting !== null}
                className="px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {deleting === deleteModal.config.id ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
