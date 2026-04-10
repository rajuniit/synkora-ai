'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  ArrowLeft,
  Server,
  Settings,
  Users,
  Save,
  Plus,
  Trash2,
  Globe,
  Radio,
  MessageSquare,
} from 'lucide-react'
import { createLoadTest, getProxyConfigs, type ProxyConfig } from '@/lib/api/load-testing'
import { useEffect } from 'react'

interface LoadStage {
  duration: string
  target: number
}

export default function CreateLoadTestPage() {
  const router = useRouter()
  const [saving, setSaving] = useState(false)
  const [proxyConfigs, setProxyConfigs] = useState<ProxyConfig[]>([])

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [targetUrl, setTargetUrl] = useState('')
  const [targetType, setTargetType] = useState<'http' | 'sse' | 'websocket'>('http')

  // Authentication
  const [authType, setAuthType] = useState<'none' | 'bearer' | 'basic' | 'custom'>('none')
  const [apiKey, setApiKey] = useState('')
  const [basicUsername, setBasicUsername] = useState('')
  const [basicPassword, setBasicPassword] = useState('')
  const [customHeaders, setCustomHeaders] = useState<Array<{ key: string; value: string }>>([])

  // HTTP config
  const [httpMethod, setHttpMethod] = useState('POST')
  const [contentType, setContentType] = useState('application/json')
  const [requestBody, setRequestBody] = useState('{\n  "message": "Hello, how can you help me?"\n}')
  const [additionalHeaders, setAdditionalHeaders] = useState<Array<{ key: string; value: string }>>([])

  // SSE config
  const [sseConnectionTimeout, setSseConnectionTimeout] = useState(30000)
  const [sseReadTimeout, setSseReadTimeout] = useState(60000)

  // WebSocket config
  const [wsInitialMessage, setWsInitialMessage] = useState('')
  const [wsMessageTemplate, setWsMessageTemplate] = useState('{\n  "type": "chat",\n  "message": "{{message}}"\n}')
  const [wsConnectionTimeout, setWsConnectionTimeout] = useState(10000)
  const [wsResponseTimeout, setWsResponseTimeout] = useState(60000)

  // Proxy
  const [proxyConfigId, setProxyConfigId] = useState<string>('')

  // Load config
  const [stages, setStages] = useState<LoadStage[]>([
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ])
  const [maxVUs, setMaxVUs] = useState(100)
  const [thinkTimeMin, setThinkTimeMin] = useState(1000)
  const [thinkTimeMax, setThinkTimeMax] = useState(3000)

  useEffect(() => {
    fetchProxyConfigs()
  }, [])

  const fetchProxyConfigs = async () => {
    try {
      const response = await getProxyConfigs(true)
      setProxyConfigs(response.items || [])
    } catch (err) {
      console.error('Failed to fetch proxy configs:', err)
    }
  }

  const addStage = () => {
    setStages([...stages, { duration: '30s', target: 10 }])
  }

  const removeStage = (index: number) => {
    setStages(stages.filter((_, i) => i !== index))
  }

  const updateStage = (index: number, field: keyof LoadStage, value: string | number) => {
    const newStages = [...stages]
    newStages[index] = { ...newStages[index], [field]: value }
    setStages(newStages)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      toast.error('Please enter a test name')
      return
    }

    if (!targetUrl.trim()) {
      toast.error('Please enter a target URL')
      return
    }

    setSaving(true)
    try {
      // Build auth config based on auth type
      let authConfig: Record<string, unknown> | undefined = undefined
      if (authType === 'bearer' && apiKey) {
        authConfig = { type: 'bearer', api_key: apiKey }
      } else if (authType === 'basic' && basicUsername) {
        authConfig = { type: 'basic', username: basicUsername, password: basicPassword }
      } else if (authType === 'custom' && customHeaders.length > 0) {
        const headers: Record<string, string> = {}
        customHeaders.forEach(h => {
          if (h.key.trim()) headers[h.key.trim()] = h.value
        })
        authConfig = { type: 'custom', headers }
      }

      // Build request config based on target type
      let requestConfig: Record<string, unknown> = {}

      // Add additional headers if any
      const extraHeaders: Record<string, string> = {}
      additionalHeaders.forEach(h => {
        if (h.key.trim()) extraHeaders[h.key.trim()] = h.value
      })

      if (targetType === 'http') {
        requestConfig = {
          method: httpMethod,
          content_type: contentType,
          body: requestBody,
          headers: Object.keys(extraHeaders).length > 0 ? extraHeaders : undefined,
        }
      } else if (targetType === 'sse') {
        requestConfig = {
          method: httpMethod,
          content_type: contentType,
          body: requestBody,
          headers: Object.keys(extraHeaders).length > 0 ? extraHeaders : undefined,
          connection_timeout_ms: sseConnectionTimeout,
          read_timeout_ms: sseReadTimeout,
        }
      } else if (targetType === 'websocket') {
        requestConfig = {
          initial_message: wsInitialMessage || undefined,
          message_template: wsMessageTemplate,
          connection_timeout_ms: wsConnectionTimeout,
          response_timeout_ms: wsResponseTimeout,
          headers: Object.keys(extraHeaders).length > 0 ? extraHeaders : undefined,
        }
      }

      const loadTest = await createLoadTest({
        name: name.trim(),
        description: description.trim() || undefined,
        target_url: targetUrl.trim(),
        target_type: targetType,
        auth_config: authConfig,
        request_config: requestConfig,
        load_config: {
          executor: 'ramping-vus',
          stages,
          max_vus: maxVUs,
          think_time_min_ms: thinkTimeMin,
          think_time_max_ms: thinkTimeMax,
        },
        proxy_config_id: proxyConfigId || undefined,
      })

      toast.success('Load test created successfully!')
      router.push(`/load-testing/${loadTest.id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create load test')
    } finally {
      setSaving(false)
    }
  }

  const getPlaceholderUrl = () => {
    switch (targetType) {
      case 'http':
        return 'https://api.example.com/v1/chat'
      case 'sse':
        return 'https://api.example.com/v1/chat/stream'
      case 'websocket':
        return 'wss://api.example.com/ws/chat'
      default:
        return 'https://api.example.com/endpoint'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/load-testing"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Load Tests
          </Link>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Create Load Test</h1>
          <p className="text-gray-600 mt-1">
            Configure a new load test for your API endpoint
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Info */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary-600" />
              Basic Information
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Test Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Production Load Test"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the purpose of this load test..."
                  rows={3}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>

          {/* Target Configuration */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Server className="w-5 h-5 text-primary-600" />
              Target Configuration
            </h2>

            <div className="space-y-4">
              {/* Endpoint Type Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Endpoint Type
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { value: 'http', label: 'HTTP/REST', icon: Globe, description: 'Standard HTTP requests' },
                    { value: 'sse', label: 'SSE', icon: Radio, description: 'Server-Sent Events' },
                    { value: 'websocket', label: 'WebSocket', icon: MessageSquare, description: 'Bidirectional connection' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setTargetType(option.value as typeof targetType)}
                      className={`flex flex-col items-center p-4 rounded-lg border-2 transition-all ${
                        targetType === option.value
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <option.icon className={`w-6 h-6 mb-2 ${
                        targetType === option.value ? 'text-primary-600' : 'text-gray-400'
                      }`} />
                      <span className={`text-sm font-medium ${
                        targetType === option.value ? 'text-primary-700' : 'text-gray-700'
                      }`}>
                        {option.label}
                      </span>
                      <span className="text-xs text-gray-500 mt-1">{option.description}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Target URL *
                </label>
                <input
                  type="text"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder={getPlaceholderUrl()}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  {targetType === 'websocket'
                    ? 'Use ws:// or wss:// protocol'
                    : 'Use http:// or https:// protocol'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Use Mock Proxy (for LLM calls)
                </label>
                <select
                  value={proxyConfigId}
                  onChange={(e) => setProxyConfigId(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="">No proxy (real API)</option>
                  {proxyConfigs.map((proxy) => (
                    <option key={proxy.id} value={proxy.id}>
                      {proxy.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Configure your app to use the mock proxy URL to avoid LLM API costs during testing.
                </p>
              </div>

              {/* Authentication Section */}
              <div className="border-t border-gray-100 pt-4 mt-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Authentication
                </label>
                <div className="grid grid-cols-4 gap-2 mb-4">
                  {[
                    { value: 'none', label: 'None' },
                    { value: 'bearer', label: 'Bearer Token' },
                    { value: 'basic', label: 'Basic Auth' },
                    { value: 'custom', label: 'Custom Headers' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setAuthType(option.value as typeof authType)}
                      className={`px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
                        authType === option.value
                          ? 'bg-primary-50 border-primary-500 text-primary-700'
                          : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>

                {authType === 'bearer' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Key / Bearer Token
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="sk-... or Bearer token"
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Will be sent as: Authorization: Bearer &lt;token&gt;
                    </p>
                  </div>
                )}

                {authType === 'basic' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Username
                      </label>
                      <input
                        type="text"
                        value={basicUsername}
                        onChange={(e) => setBasicUsername(e.target.value)}
                        placeholder="username"
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Password
                      </label>
                      <input
                        type="password"
                        value={basicPassword}
                        onChange={(e) => setBasicPassword(e.target.value)}
                        placeholder="password"
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                )}

                {authType === 'custom' && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="block text-sm font-medium text-gray-700">
                        Custom Headers
                      </label>
                      <button
                        type="button"
                        onClick={() => setCustomHeaders([...customHeaders, { key: '', value: '' }])}
                        className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                      >
                        <Plus className="w-4 h-4" />
                        Add Header
                      </button>
                    </div>
                    <div className="space-y-2">
                      {customHeaders.map((header, index) => (
                        <div key={index} className="flex items-center gap-2">
                          <input
                            type="text"
                            value={header.key}
                            onChange={(e) => {
                              const newHeaders = [...customHeaders]
                              newHeaders[index].key = e.target.value
                              setCustomHeaders(newHeaders)
                            }}
                            placeholder="Header name (e.g., X-API-Key)"
                            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          />
                          <input
                            type="text"
                            value={header.value}
                            onChange={(e) => {
                              const newHeaders = [...customHeaders]
                              newHeaders[index].value = e.target.value
                              setCustomHeaders(newHeaders)
                            }}
                            placeholder="Header value"
                            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          />
                          <button
                            type="button"
                            onClick={() => setCustomHeaders(customHeaders.filter((_, i) => i !== index))}
                            className="p-2 text-gray-400 hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                      {customHeaders.length === 0 && (
                        <p className="text-sm text-gray-500 py-2">
                          Click &quot;Add Header&quot; to add custom authentication headers.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Request Configuration */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary-600" />
              Request Configuration
            </h2>

            {/* HTTP/SSE Configuration */}
            {(targetType === 'http' || targetType === 'sse') && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      HTTP Method
                    </label>
                    <select
                      value={httpMethod}
                      onChange={(e) => setHttpMethod(e.target.value)}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                      <option value="GET">GET</option>
                      <option value="POST">POST</option>
                      <option value="PUT">PUT</option>
                      <option value="PATCH">PATCH</option>
                      <option value="DELETE">DELETE</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Content-Type
                    </label>
                    <select
                      value={contentType}
                      onChange={(e) => setContentType(e.target.value)}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                      <option value="application/json">application/json</option>
                      <option value="application/x-www-form-urlencoded">application/x-www-form-urlencoded</option>
                      <option value="text/plain">text/plain</option>
                      <option value="multipart/form-data">multipart/form-data</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Request Body
                  </label>
                  <textarea
                    value={requestBody}
                    onChange={(e) => setRequestBody(e.target.value)}
                    placeholder='{"message": "Hello"}'
                    rows={6}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Use {"{{variable}}"} for dynamic values in test scenarios.
                  </p>
                </div>

                {targetType === 'sse' && (
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Connection Timeout (ms)
                      </label>
                      <input
                        type="number"
                        value={sseConnectionTimeout}
                        onChange={(e) => setSseConnectionTimeout(parseInt(e.target.value))}
                        min="1000"
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Read Timeout (ms)
                      </label>
                      <input
                        type="number"
                        value={sseReadTimeout}
                        onChange={(e) => setSseReadTimeout(parseInt(e.target.value))}
                        min="1000"
                        className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Maximum time to wait for the complete SSE stream.
                      </p>
                    </div>
                  </div>
                )}

                {/* Additional Headers */}
                <div className="pt-4 border-t border-gray-100">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Additional Headers
                    </label>
                    <button
                      type="button"
                      onClick={() => setAdditionalHeaders([...additionalHeaders, { key: '', value: '' }])}
                      className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Add Header
                    </button>
                  </div>
                  <div className="space-y-2">
                    {additionalHeaders.map((header, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <input
                          type="text"
                          value={header.key}
                          onChange={(e) => {
                            const newHeaders = [...additionalHeaders]
                            newHeaders[index].key = e.target.value
                            setAdditionalHeaders(newHeaders)
                          }}
                          placeholder="Header name"
                          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                        <input
                          type="text"
                          value={header.value}
                          onChange={(e) => {
                            const newHeaders = [...additionalHeaders]
                            newHeaders[index].value = e.target.value
                            setAdditionalHeaders(newHeaders)
                          }}
                          placeholder="Header value"
                          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                        <button
                          type="button"
                          onClick={() => setAdditionalHeaders(additionalHeaders.filter((_, i) => i !== index))}
                          className="p-2 text-gray-400 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    {additionalHeaders.length === 0 && (
                      <p className="text-sm text-gray-500 py-1">
                        Optional headers (Content-Type and auth headers are set automatically).
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* WebSocket Configuration */}
            {targetType === 'websocket' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Initial Connection Message (optional)
                  </label>
                  <textarea
                    value={wsInitialMessage}
                    onChange={(e) => setWsInitialMessage(e.target.value)}
                    placeholder='{"type": "auth", "token": "..."}'
                    rows={3}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Sent immediately after connection (e.g., for authentication).
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Message Template
                  </label>
                  <textarea
                    value={wsMessageTemplate}
                    onChange={(e) => setWsMessageTemplate(e.target.value)}
                    placeholder='{"type": "chat", "message": "{{message}}"}'
                    rows={4}
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Template for chat messages. Use {"{{variable}}"} for dynamic values.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Connection Timeout (ms)
                    </label>
                    <input
                      type="number"
                      value={wsConnectionTimeout}
                      onChange={(e) => setWsConnectionTimeout(parseInt(e.target.value))}
                      min="1000"
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Response Timeout (ms)
                    </label>
                    <input
                      type="number"
                      value={wsResponseTimeout}
                      onChange={(e) => setWsResponseTimeout(parseInt(e.target.value))}
                      min="1000"
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Maximum time to wait for a response after sending a message.
                    </p>
                  </div>
                </div>

                {/* WebSocket Headers */}
                <div className="pt-4 border-t border-gray-100">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Connection Headers
                    </label>
                    <button
                      type="button"
                      onClick={() => setAdditionalHeaders([...additionalHeaders, { key: '', value: '' }])}
                      className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      Add Header
                    </button>
                  </div>
                  <div className="space-y-2">
                    {additionalHeaders.map((header, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <input
                          type="text"
                          value={header.key}
                          onChange={(e) => {
                            const newHeaders = [...additionalHeaders]
                            newHeaders[index].key = e.target.value
                            setAdditionalHeaders(newHeaders)
                          }}
                          placeholder="Header name"
                          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                        <input
                          type="text"
                          value={header.value}
                          onChange={(e) => {
                            const newHeaders = [...additionalHeaders]
                            newHeaders[index].value = e.target.value
                            setAdditionalHeaders(newHeaders)
                          }}
                          placeholder="Header value"
                          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                        <button
                          type="button"
                          onClick={() => setAdditionalHeaders(additionalHeaders.filter((_, i) => i !== index))}
                          className="p-2 text-gray-400 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    {additionalHeaders.length === 0 && (
                      <p className="text-sm text-gray-500 py-1">
                        Headers sent during the WebSocket handshake.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Load Configuration */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-primary-600" />
              Load Configuration
            </h2>

            <div className="space-y-4">
              {/* Stages */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Load Stages
                  </label>
                  <button
                    type="button"
                    onClick={addStage}
                    className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                  >
                    <Plus className="w-4 h-4" />
                    Add Stage
                  </button>
                </div>

                <div className="space-y-2">
                  {stages.map((stage, index) => (
                    <div key={index} className="flex items-center gap-3">
                      <div className="flex-1 grid grid-cols-2 gap-3">
                        <input
                          type="text"
                          value={stage.duration}
                          onChange={(e) => updateStage(index, 'duration', e.target.value)}
                          placeholder="30s"
                          className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                        <input
                          type="number"
                          value={stage.target}
                          onChange={(e) => updateStage(index, 'target', parseInt(e.target.value))}
                          placeholder="VUs"
                          min="0"
                          className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => removeStage(index)}
                        disabled={stages.length <= 1}
                        className="p-2 text-gray-400 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Duration: 30s, 1m, 5m, etc. Target: Number of virtual users.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max VUs
                  </label>
                  <input
                    type="number"
                    value={maxVUs}
                    onChange={(e) => setMaxVUs(parseInt(e.target.value))}
                    min="1"
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Think Time Min (ms)
                  </label>
                  <input
                    type="number"
                    value={thinkTimeMin}
                    onChange={(e) => setThinkTimeMin(parseInt(e.target.value))}
                    min="0"
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Think Time Max (ms)
                  </label>
                  <input
                    type="number"
                    value={thinkTimeMax}
                    onChange={(e) => setThinkTimeMax(parseInt(e.target.value))}
                    min="0"
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-4">
            <Link
              href="/load-testing"
              className="px-6 py-2.5 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors font-medium"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Create Test
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
