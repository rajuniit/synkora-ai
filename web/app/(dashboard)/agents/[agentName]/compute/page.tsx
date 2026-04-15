'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import {
  ArrowLeft,
  Server,
  Save,
  Loader2,
  CheckCircle,
  XCircle,
  Wifi,
  WifiOff,
  Trash2,
  Eye,
  EyeOff,
  Box,
  Settings,
  ExternalLink,
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

type ComputeType = 'platform_managed' | 'remote_server' | 'local'
type ComputeStatus = 'active' | 'inactive' | 'error'
type AuthType = 'password' | 'key'

interface ComputeConfig {
  configured: boolean
  compute_type: ComputeType
  status?: ComputeStatus
  remote_host?: string
  remote_port?: number
  remote_user?: string
  remote_auth_type?: AuthType
  remote_base_path?: string
  timeout_seconds?: number
  max_output_chars?: number
  last_connected_at?: string
  error_message?: string
}

const STATUS_STYLES: Record<ComputeStatus, { dot: string; badge: string; label: string }> = {
  active: { dot: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200', label: 'Active' },
  inactive: { dot: 'bg-gray-400', badge: 'bg-gray-50 text-gray-600 ring-1 ring-gray-200', label: 'Inactive' },
  error: { dot: 'bg-red-500', badge: 'bg-red-50 text-red-700 ring-1 ring-red-200', label: 'Error' },
}

export default function AgentComputePage() {
  const params = useParams()
  const router = useRouter()
  const agentName = decodeURIComponent((params?.agentName as string) || '')

  const [agentId, setAgentId] = useState<string | null>(null)
  const [config, setConfig] = useState<ComputeConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [showCredentials, setShowCredentials] = useState(false)

  const [computeType, setComputeType] = useState<ComputeType>('platform_managed')
  const [remoteHost, setRemoteHost] = useState('')
  const [remotePort, setRemotePort] = useState('22')
  const [remoteUser, setRemoteUser] = useState('root')
  const [authType, setAuthType] = useState<AuthType>('password')
  const [credentials, setCredentials] = useState('')
  const [basePath, setBasePath] = useState('/tmp/agent_workspace')
  const [timeoutSecs, setTimeoutSecs] = useState('300')
  const [maxOutput, setMaxOutput] = useState('8000')

  useEffect(() => {
    loadConfig()
  }, [agentName])

  const loadConfig = async (resolvedId?: string) => {
    try {
      setLoading(true)
      const id = resolvedId ?? agentId
      if (!id) {
        const agent = await apiClient.getAgent(agentName)
        setAgentId(agent.id)
        return loadConfig(agent.id)
      }
      const data: ComputeConfig = await apiClient.request('GET', `/api/v1/agents/${id}/compute`)
      setConfig(data)
      if (data.configured) {
        setComputeType(data.compute_type)
        if (data.compute_type === 'remote_server') {
          setRemoteHost(data.remote_host || '')
          setRemotePort(String(data.remote_port || 22))
          setRemoteUser(data.remote_user || 'root')
          setAuthType((data.remote_auth_type as AuthType) || 'password')
          setBasePath(data.remote_base_path || '/tmp/agent_workspace')
          setTimeoutSecs(String(data.timeout_seconds || 300))
          setMaxOutput(String(data.max_output_chars || 8000))
        }
      }
    } catch {
      toast.error('Failed to load compute configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (computeType === 'remote_server' && !remoteHost.trim()) {
      toast.error('Remote host is required')
      return
    }
    if (!agentId) return
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        compute_type: computeType,
        remote_host: computeType === 'remote_server' ? remoteHost.trim() : undefined,
        remote_port: computeType === 'remote_server' ? parseInt(remotePort, 10) : undefined,
        remote_user: computeType === 'remote_server' ? remoteUser.trim() : undefined,
        remote_auth_type: computeType === 'remote_server' ? authType : undefined,
        remote_credentials: computeType === 'remote_server' && credentials.trim() ? credentials : undefined,
        remote_base_path: computeType === 'remote_server' ? basePath.trim() : undefined,
        timeout_seconds: parseInt(timeoutSecs, 10),
        max_output_chars: parseInt(maxOutput, 10),
      }
      const data: ComputeConfig = await apiClient.request('POST', `/api/v1/agents/${agentId}/compute`, body)
      setConfig(data)
      setCredentials('')
      toast.success('Compute configuration saved')
    } catch {
      toast.error('Failed to save compute configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!agentId) return
    setTesting(true)
    try {
      const data = await apiClient.request('POST', `/api/v1/agents/${agentId}/compute/test`)
      if (data.success) {
        toast.success(`Connection successful (${data.latency_ms ?? '?'}ms)`)
        await loadConfig()
      } else {
        toast.error(data.error || 'Test failed')
      }
    } catch {
      toast.error('Test failed')
    } finally {
      setTesting(false)
    }
  }

  const handleRemove = async () => {
    if (!confirm('Remove compute configuration? The agent will revert to platform managed.')) return
    if (!agentId) return
    setRemoving(true)
    try {
      await apiClient.request('DELETE', `/api/v1/agents/${agentId}/compute`)
      setConfig({ configured: false, compute_type: 'platform_managed' })
      setComputeType('platform_managed')
      setRemoteHost('')
      setCredentials('')
      toast.success('Compute configuration removed')
    } catch {
      toast.error('Failed to remove compute configuration')
    } finally {
      setRemoving(false)
    }
  }

  const statusInfo = config?.status ? STATUS_STYLES[config.status] : null

  const inputClass =
    'w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent bg-white placeholder-gray-400'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push(`/agents/${encodeURIComponent(agentName)}/view`)}
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Agent
          </button>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center">
                <Server className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Compute</h1>
                <p className="text-sm text-gray-500">
                  Execution environment for <span className="font-medium text-gray-700">{agentName}</span>
                </p>
              </div>
            </div>
            {statusInfo && (
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusInfo.badge}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${statusInfo.dot}`} />
                {statusInfo.label}
              </span>
            )}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-6 h-6 text-red-500 animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">

            {/* Compute Type */}
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-900 mb-1">Compute Target</h2>
              <p className="text-xs text-gray-500 mb-4">Where this agent runs commands and file operations</p>

              <div className="space-y-2">
                {([
                  {
                    value: 'platform_managed' as const,
                    icon: Box,
                    title: 'Platform Managed',
                    desc: 'Isolated container provisioned automatically per conversation.',
                    badge: 'Recommended',
                  },
                  {
                    value: 'remote_server' as const,
                    icon: Server,
                    title: 'Remote Server',
                    desc: 'Execute on your own machine via SSH.',
                    badge: null,
                  },
                ]).map(({ value, icon: Icon, title, desc, badge }) => (
                  <button
                    key={value}
                    onClick={() => setComputeType(value)}
                    className={`w-full flex items-start gap-3 p-4 rounded-lg border-2 text-left transition-all ${
                      computeType === value
                        ? 'border-red-500 bg-red-50'
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                  >
                    <div className={`mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      computeType === value ? 'bg-red-50' : 'bg-gray-100'
                    }`}>
                      <Icon className={`w-4 h-4 ${computeType === value ? 'text-red-600' : 'text-gray-500'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-semibold ${computeType === value ? 'text-red-900' : 'text-gray-800'}`}>
                          {title}
                        </span>
                        {badge && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-700">
                            {badge}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                    </div>
                    {computeType === value && (
                      <CheckCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Platform Managed info */}
            {computeType === 'platform_managed' && (
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                    <Settings className="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Managed container</p>
                    <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                      The platform provisions an ephemeral container for each conversation. The container image and
                      backend (Docker, Lambda, Fargate) are configured in your tenant settings.
                    </p>
                    <button
                      onClick={() => router.push('/settings/compute')}
                      className="inline-flex items-center gap-1.5 mt-2.5 text-xs font-medium text-red-600 hover:text-red-800 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Configure tenant compute backend
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* SSH Configuration */}
            {computeType === 'remote_server' && (
              <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-semibold text-gray-900">SSH Configuration</h2>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Host <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={remoteHost}
                      onChange={e => setRemoteHost(e.target.value)}
                      placeholder="192.168.1.100 or server.example.com"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Port</label>
                    <input
                      type="number"
                      value={remotePort}
                      onChange={e => setRemotePort(e.target.value)}
                      min={1}
                      max={65535}
                      className={inputClass}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={remoteUser}
                    onChange={e => setRemoteUser(e.target.value)}
                    placeholder="root"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">Authentication</label>
                  <div className="flex gap-2 mb-3">
                    {(['password', 'key'] as const).map(type => (
                      <button
                        key={type}
                        onClick={() => setAuthType(type)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                          authType === type
                            ? 'bg-red-600 text-white border-red-600'
                            : 'text-gray-600 border-gray-300 hover:border-red-400 bg-white'
                        }`}
                      >
                        {type === 'password' ? 'Password' : 'SSH Key'}
                      </button>
                    ))}
                  </div>
                  <div className="relative">
                    <textarea
                      value={credentials}
                      onChange={e => setCredentials(e.target.value)}
                      placeholder={
                        authType === 'password'
                          ? 'Enter password (leave blank to keep existing)'
                          : 'Paste private key (-----BEGIN ... KEY-----)\nLeave blank to keep existing'
                      }
                      rows={authType === 'key' ? 5 : 1}
                      className={`${inputClass} resize-none font-mono`}
                      style={!showCredentials && credentials ? { WebkitTextSecurity: 'disc' } as React.CSSProperties : {}}
                    />
                    {credentials && (
                      <button
                        type="button"
                        onClick={() => setShowCredentials(v => !v)}
                        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        {showCredentials ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    )}
                  </div>
                  {config?.configured && (
                    <p className="text-xs text-gray-400 mt-1">Leave blank to keep the existing credential.</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Working Directory</label>
                  <input
                    type="text"
                    value={basePath}
                    onChange={e => setBasePath(e.target.value)}
                    placeholder="/tmp/agent_workspace"
                    className={`${inputClass} font-mono`}
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Timeout (seconds)</label>
                    <input
                      type="number"
                      value={timeoutSecs}
                      onChange={e => setTimeoutSecs(e.target.value)}
                      min={10}
                      max={3600}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Max Output (chars)</label>
                    <input
                      type="number"
                      value={maxOutput}
                      onChange={e => setMaxOutput(e.target.value)}
                      min={1000}
                      max={100000}
                      className={inputClass}
                    />
                  </div>
                </div>

                {config?.error_message && (
                  <div className="flex items-start gap-2.5 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <XCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-red-700">{config.error_message}</p>
                  </div>
                )}

                {config?.last_connected_at && (
                  <p className="text-xs text-gray-400">
                    Last connected: {new Date(config.last_connected_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2">
                {config?.configured && computeType === 'remote_server' && (
                  <button
                    onClick={handleTest}
                    disabled={testing || saving}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-all disabled:opacity-50"
                  >
                    {testing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : config.status === 'active' ? (
                      <Wifi className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <WifiOff className="w-4 h-4 text-gray-400" />
                    )}
                    Test Connection
                  </button>
                )}
                {config?.configured && (
                  <button
                    onClick={handleRemove}
                    disabled={removing || saving}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-200 rounded-lg hover:bg-red-50 transition-all disabled:opacity-50"
                  >
                    {removing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    Remove
                  </button>
                )}
              </div>
              <button
                onClick={handleSave}
                disabled={saving || testing}
                className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save
              </button>
            </div>

          </div>
        )}
      </div>
    </div>
  )
}
