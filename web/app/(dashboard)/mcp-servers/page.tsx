'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { Plus, Server, Edit, Trash2, TestTube, ArrowLeft } from 'lucide-react'
import { apiClient } from '@/lib/api/http'

interface MCPServer {
  id: string
  name: string
  url: string
  description: string
  transport_type?: string
  command?: string
  args?: string[]
  env_vars?: Record<string, string>
  server_type: string
  auth_type: string
  auth_config?: any
  headers?: any
  status: string
  capabilities: any
  metadata: any
  created_at: string
  updated_at: string
}

export default function MCPServersPage() {
  const router = useRouter()
  const [servers, setServers] = useState<MCPServer[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null)

  useEffect(() => {
    fetchServers()
  }, [])

  const fetchServers = async () => {
    try {
      const { data } = await apiClient.axios.get('/api/v1/mcp/servers')
      if (data.success) {
        setServers(data.data.servers)
      }
    } catch (error) {
      console.error('Failed to fetch MCP servers:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (serverId: string) => {
    if (!confirm('Are you sure you want to delete this MCP server?')) return

    try {
      const { data } = await apiClient.axios.delete(`/api/v1/mcp/servers/${serverId}`)
      if (data.success) {
        fetchServers()
      }
    } catch (error) {
      console.error('Failed to delete server:', error)
    }
  }

  const handleTest = async (serverId: string) => {
    try {
      const { data } = await apiClient.axios.post(`/api/v1/mcp/servers/${serverId}/test`)
      if (data.success) {
        toast.success(`Connection successful! Response time: ${data.data.response_time_ms}ms`)
      }
    } catch (error) {
      console.error('Failed to test server:', error)
      toast.error('Connection test failed')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header - More Compact */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/agents')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-3 text-sm"
          >
            <ArrowLeft size={18} />
            Back to Agents
          </button>
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">MCP Servers</h1>
              <p className="text-gray-600 mt-1 text-sm">
                Manage Model Context Protocol servers to extend agent capabilities
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-5 py-2.5 rounded-lg transition-all shadow-sm hover:shadow-md text-sm font-medium"
            >
              <Plus size={18} />
              Add MCP Server
            </button>
          </div>
        </div>

        {/* Stats - More Compact */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs font-medium">Total Servers</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{servers.length}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs font-medium">Active Servers</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">
              {servers.filter(s => s.status === 'active').length}
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <div className="text-gray-600 text-xs font-medium">Server Types</div>
            <div className="text-2xl font-bold text-red-600 mt-1">
              {new Set(servers.map(s => s.server_type)).size}
            </div>
          </div>
        </div>

        {/* Servers List - More Compact */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-200">
            <h2 className="text-base font-semibold text-gray-900">Configured Servers</h2>
          </div>

          {loading ? (
            <div className="p-12 text-center text-gray-500 text-sm">Loading servers...</div>
          ) : servers.length === 0 ? (
            <div className="p-12 text-center">
              <Server className="mx-auto text-gray-400 mb-3" size={40} />
              <p className="text-gray-500 mb-3 text-sm">No MCP servers configured yet</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-red-600 hover:text-red-700 font-medium text-sm"
              >
                Add your first MCP server
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {servers.map((server) => (
                <div key={server.id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Server className="text-red-600" size={18} />
                        <h3 className="text-base font-semibold text-gray-900">{server.name}</h3>
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            server.status === 'active'
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {server.status}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                          {server.server_type}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                          {server.auth_type}
                        </span>
                      </div>
                      <p className="text-gray-600 mb-1.5 text-sm">{server.description}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        {server.transport_type === 'stdio' ? (
                          <span className="font-mono">{server.command} {server.args?.join(' ')}</span>
                        ) : (
                          <span className="font-mono">{server.url}</span>
                        )}
                        <span>•</span>
                        <span>Added {new Date(server.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 ml-4">
                      <button
                        onClick={() => handleTest(server.id)}
                        className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                        title="Test Connection"
                      >
                        <TestTube size={18} />
                      </button>
                      <button
                        onClick={() => setEditingServer(server)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Edit Server"
                      >
                        <Edit size={18} />
                      </button>
                      <button
                        onClick={() => handleDelete(server.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete Server"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {(showCreateModal || editingServer) && (
        <MCPServerModal
          server={editingServer}
          onClose={() => {
            setShowCreateModal(false)
            setEditingServer(null)
          }}
          onSuccess={() => {
            setShowCreateModal(false)
            setEditingServer(null)
            fetchServers()
          }}
        />
      )}
    </div>
  )
}

// MCP Server Modal Component
function MCPServerModal({
  server,
  onClose,
  onSuccess,
}: {
  server: MCPServer | null
  onClose: () => void
  onSuccess: () => void
}) {
  // Get auth_config and headers from the server object directly (not from metadata)
  const serverAuthConfig = server?.auth_config || {}
  const serverHeaders = server?.headers || {}
  const serverMetadata = server?.metadata || {}
  
  const [formData, setFormData] = useState({
    name: server?.name || '',
    url: server?.url || '',
    description: server?.description || '',
    transport_type: server?.transport_type || 'http',
    command: server?.command || '',
    args: server?.args || [],
    env_vars: server?.env_vars || {},
    server_type: server?.server_type || 'http',
    auth_type: server?.auth_type || 'none',
    auth_config: serverAuthConfig,
    headers: serverHeaders,
    use_sse: serverMetadata.use_sse !== undefined ? serverMetadata.use_sse : true,
  })
  const [authConfigJson, setAuthConfigJson] = useState(
    JSON.stringify(serverAuthConfig, null, 2)
  )
  const [headersJson, setHeadersJson] = useState(
    JSON.stringify(serverHeaders, null, 2)
  )
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      // Parse JSON fields
      let authConfig = {}
      let headers = {}
      
      try {
        authConfig = authConfigJson.trim() ? JSON.parse(authConfigJson) : {}
      } catch {
        toast.error('Invalid JSON in Auth Config')
        setSaving(false)
        return
      }
      
      try {
        headers = headersJson.trim() ? JSON.parse(headersJson) : {}
      } catch {
        toast.error('Invalid JSON in Headers')
        setSaving(false)
        return
      }

      const path = server
        ? `/api/v1/mcp/servers/${server.id}`
        : `/api/v1/mcp/servers`

      const payload = {
        ...formData,
        auth_config: authConfig,
        headers: headers,
        server_metadata: {
          use_sse: formData.use_sse,
        },
      }

      const { data } = server
        ? await apiClient.axios.put(path, payload)
        : await apiClient.axios.post(path, payload)

      if (data.success) {
        toast.success(`Server ${server ? 'updated' : 'created'} successfully!`)
        onSuccess()
      } else {
        toast.error('Failed to save server: ' + data.message)
      }
    } catch (error) {
      console.error('Failed to save server:', error)
      toast.error('Failed to save server')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-red-50 to-red-100">
          <h2 className="text-xl font-bold text-gray-900">
            {server ? 'Edit MCP Server' : 'Add MCP Server'}
          </h2>
          <p className="text-sm text-gray-600 mt-0.5">
            Configure your Model Context Protocol server
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto max-h-[calc(90vh-180px)]">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Server Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="My MCP Server"
              required
            />
          </div>

          {/* Transport Type Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Transport Type *
            </label>
            <select
              value={formData.transport_type}
              onChange={(e) => setFormData({ ...formData, transport_type: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            >
              <option value="http">HTTP/SSE (Remote Server)</option>
              <option value="stdio">Stdio (Local Command)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {formData.transport_type === 'http' 
                ? 'Connect to a remote MCP server via HTTP'
                : 'Run a local MCP server using a command (e.g., npx, python)'}
            </p>
          </div>

          {/* Conditional Fields based on transport type */}
          {formData.transport_type === 'http' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Server URL *
              </label>
              <input
                type="url"
                value={formData.url}
                onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="https://synkora.ai"
                required={formData.transport_type === 'http'}
              />
            </div>
          ) : (
            <>
              {/* Command Field */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Command *
                </label>
                <input
                  type="text"
                  value={formData.command}
                  onChange={(e) => setFormData({ ...formData, command: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="npx"
                  required={formData.transport_type === 'stdio'}
                />
                <p className="text-xs text-gray-500 mt-1">
                  The command to execute (e.g., npx, python, node)
                </p>
              </div>

              {/* Args Field */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Arguments
                </label>
                <div className="space-y-2">
                  {formData.args.map((arg: string, index: number) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={arg}
                        onChange={(e) => {
                          const newArgs = [...formData.args]
                          newArgs[index] = e.target.value
                          setFormData({ ...formData, args: newArgs })
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        placeholder="Argument"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const newArgs = formData.args.filter((_: string, i: number) => i !== index)
                          setFormData({ ...formData, args: newArgs })
                        }}
                        className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, args: [...formData.args, ''] })}
                    className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    + Add Argument
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Example for GitHub MCP: ["-y", "@modelcontextprotocol/server-github"]
                </p>
              </div>

              {/* Environment Variables */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Environment Variables
                </label>
                <div className="space-y-2">
                  {Object.entries(formData.env_vars).map(([key, value], index) => (
                    <div key={index} className="flex gap-2">
                      <input
                        type="text"
                        value={key}
                        onChange={(e) => {
                          const newEnvVars = { ...formData.env_vars }
                          delete newEnvVars[key]
                          newEnvVars[e.target.value] = value
                          setFormData({ ...formData, env_vars: newEnvVars })
                        }}
                        className="w-1/3 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        placeholder="KEY"
                      />
                      <input
                        type="text"
                        value={value}
                        onChange={(e) => {
                          const newEnvVars = { ...formData.env_vars }
                          newEnvVars[key] = e.target.value
                          setFormData({ ...formData, env_vars: newEnvVars })
                        }}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        placeholder="value"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const newEnvVars = { ...formData.env_vars }
                          delete newEnvVars[key]
                          setFormData({ ...formData, env_vars: newEnvVars })
                        }}
                        className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => {
                      const newEnvVars = { ...formData.env_vars }
                      newEnvVars[''] = ''
                      setFormData({ ...formData, env_vars: newEnvVars })
                    }}
                    className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    + Add Environment Variable
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Example: GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxx
                </p>
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description *
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              rows={3}
              placeholder="Describe what this MCP server provides..."
              required
            />
          </div>

          {/* Only show auth and server type for HTTP transport */}
          {formData.transport_type === 'http' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Server Type
                </label>
                <select
                  value={formData.server_type}
                  onChange={(e) => setFormData({ ...formData, server_type: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  <option value="http">HTTP</option>
                  <option value="websocket">WebSocket</option>
                  <option value="grpc">gRPC</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Authentication
                </label>
                <select
                  value={formData.auth_type}
                  onChange={(e) => setFormData({ ...formData, auth_type: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  <option value="none">None</option>
                  <option value="api_key">API Key</option>
                  <option value="bearer">Bearer Token</option>
                  <option value="oauth">OAuth</option>
                </select>
              </div>
            </div>
          )}

          {/* Auth Config - Show when auth_type is not 'none' and transport is HTTP */}
          {formData.transport_type === 'http' && formData.auth_type !== 'none' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Auth Config (JSON)
              </label>
              <textarea
                value={authConfigJson}
                onChange={(e) => setAuthConfigJson(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
                rows={6}
                placeholder={`{\n  "token": "your_token_here"\n}`}
              />
              <p className="text-xs text-gray-500 mt-1">
                {formData.auth_type === 'bearer' && 'Example: {"token": "ghp_xxxxx"}'}
                {formData.auth_type === 'api_key' && 'Example: {"api_key": "your_key", "header_name": "X-API-Key"}'}
                {formData.auth_type === 'oauth' && 'Example: {"client_id": "xxx", "client_secret": "yyy"}'}
              </p>
            </div>
          )}

          {/* Headers - Only for HTTP transport */}
          {formData.transport_type === 'http' && (
            <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Headers (JSON) - Optional
            </label>
            <textarea
              value={headersJson}
              onChange={(e) => setHeadersJson(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
              rows={4}
              placeholder={`{\n  "Content-Type": "application/json"\n}`}
            />
            <p className="text-xs text-gray-500 mt-1">
              Add custom HTTP headers for requests to this server
            </p>
            </div>
          )}

          {/* Use SSE Toggle - Only for HTTP transport */}
          {formData.transport_type === 'http' && (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Use Server-Sent Events (SSE)
              </label>
              <p className="text-xs text-gray-500">
                Enable SSE for streaming responses. Disable for servers that only support POST requests (e.g., GitHub MCP).
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={formData.use_sse}
                onChange={(e) => setFormData({ ...formData, use_sse: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
            </label>
            </div>
          )}

          <div className="bg-red-50 border border-red-200 rounded-lg p-3.5">
            <h4 className="text-sm font-semibold text-red-900 mb-1">About MCP Servers</h4>
            <p className="text-xs text-red-800 leading-relaxed">
              MCP (Model Context Protocol) servers provide additional tools and resources that your agents can use.
              They extend agent capabilities beyond built-in tools by connecting to external APIs, databases, or services.
            </p>
          </div>
        </form>

        {/* Fixed Footer with Buttons */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 text-gray-700 hover:bg-gray-200 bg-gray-100 rounded-lg transition-colors font-medium text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            onClick={(e) => {
              e.preventDefault()
              const form = e.currentTarget.closest('div')?.previousElementSibling as HTMLFormElement
              form?.requestSubmit()
            }}
            className="px-6 py-2 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
          >
            {saving ? 'Saving...' : server ? 'Update Server' : 'Create Server'}
          </button>
        </div>
      </div>
    </div>
  )
}
