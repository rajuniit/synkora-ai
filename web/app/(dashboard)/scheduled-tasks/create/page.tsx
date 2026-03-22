'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Clock,
  ArrowLeft,
  Save,
  Loader2,
  Database,
  Calendar,
  Mail,
  MessageSquare,
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'
import { getAgents } from '@/lib/api/agents'

interface TaskFormData {
  name: string
  description: string
  task_type: string
  interval_seconds: number
  database_connection_id: string
  query: string
  agent_id: string
  agent_prompt: string
  config: any
  notification_config: {
    email_enabled: boolean
    email_recipients: string[]
    slack_enabled: boolean
    slack_webhook_url: string
    notify_on_success: boolean
    notify_on_failure: boolean
  }
  is_active: boolean
}

interface DatabaseConnection {
  id: string
  name: string
  type: string
}

interface Agent {
  id: string
  name: string
}

// Common interval presets
const intervalPresets = [
  { label: 'Every minute', value: 60 },
  { label: 'Every 5 minutes', value: 300 },
  { label: 'Every 15 minutes', value: 900 },
  { label: 'Every 30 minutes', value: 1800 },
  { label: 'Every hour', value: 3600 },
  { label: 'Every 2 hours', value: 7200 },
  { label: 'Every 6 hours', value: 21600 },
  { label: 'Every 12 hours', value: 43200 },
  { label: 'Every day', value: 86400 },
  { label: 'Every week', value: 604800 },
]

export default function CreateScheduledTaskPage() {
  const router = useRouter()
  const [formData, setFormData] = useState<TaskFormData>({
    name: '',
    description: '',
    task_type: 'database_query',
    interval_seconds: 3600,
    database_connection_id: '',
    query: '',
    agent_id: '',
    agent_prompt: '',
    config: null,
    notification_config: {
      email_enabled: false,
      email_recipients: [],
      slack_enabled: false,
      slack_webhook_url: '',
      notify_on_success: false,
      notify_on_failure: true
    },
    is_active: true
  })

  const [connections, setConnections] = useState<DatabaseConnection[]>([])
  const [loadingConnections, setLoadingConnections] = useState(true)
  const [agents, setAgents] = useState<Agent[]>([])
  const [loadingAgents, setLoadingAgents] = useState(true)
  const [saving, setSaving] = useState(false)
  const [emailInput, setEmailInput] = useState('')

  useEffect(() => {
    fetchConnections()
    fetchAgents()
  }, [])

  const fetchConnections = async () => {
    try {
      const data = await apiClient.getDatabaseConnections()
      setConnections(data)
    } catch {
      toast.error('Failed to load database connections')
    } finally {
      setLoadingConnections(false)
    }
  }

  const fetchAgents = async () => {
    try {
      const data = await getAgents()
      setAgents(Array.isArray(data) ? data : data.items || [])
    } catch {
      toast.error('Failed to load agents')
    } finally {
      setLoadingAgents(false)
    }
  }

  const handleInputChange = (field: keyof TaskFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleNotificationChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      notification_config: {
        ...prev.notification_config,
        [field]: value
      }
    }))
  }

  const addEmailRecipient = () => {
    if (emailInput && emailInput.includes('@')) {
      setFormData(prev => ({
        ...prev,
        notification_config: {
          ...prev.notification_config,
          email_recipients: [...prev.notification_config.email_recipients, emailInput]
        }
      }))
      setEmailInput('')
    } else {
      toast.error('Please enter a valid email address')
    }
  }

  const removeEmailRecipient = (email: string) => {
    setFormData(prev => ({
      ...prev,
      notification_config: {
        ...prev.notification_config,
        email_recipients: prev.notification_config.email_recipients.filter(e => e !== email)
      }
    }))
  }

  const formatInterval = (seconds: number): string => {
    if (seconds >= 86400) {
      const days = Math.floor(seconds / 86400)
      return `${days} day${days > 1 ? 's' : ''}`
    } else if (seconds >= 3600) {
      const hours = Math.floor(seconds / 3600)
      return `${hours} hour${hours > 1 ? 's' : ''}`
    } else if (seconds >= 60) {
      const minutes = Math.floor(seconds / 60)
      return `${minutes} minute${minutes > 1 ? 's' : ''}`
    }
    return `${seconds} second${seconds > 1 ? 's' : ''}`
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name) {
      toast.error('Please enter a task name')
      return
    }

    if (formData.interval_seconds < 60) {
      toast.error('Interval must be at least 60 seconds')
      return
    }

    if (formData.task_type === 'agent_task') {
      if (!formData.agent_id) {
        toast.error('Please select an agent for this task')
        return
      }
      if (!formData.agent_prompt) {
        toast.error('Please enter a prompt for this task')
        return
      }
    }

    setSaving(true)

    try {
      const config: Record<string, any> = { ...(formData.config || {}) }
      if (formData.task_type === 'agent_task') {
        config.agent_id = formData.agent_id
        config.prompt = formData.agent_prompt
      }

      await apiClient.createScheduledTask({
        name: formData.name,
        description: formData.description,
        task_type: formData.task_type,
        interval_seconds: formData.interval_seconds,
        database_connection_id: formData.database_connection_id || undefined,
        query: formData.query || undefined,
        config,
        is_active: formData.is_active,
      })
      toast.success('Scheduled task created successfully')
      router.push('/scheduled-tasks')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create task')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-red-50/30 to-red-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/scheduled-tasks"
            className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium mb-3 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Scheduled Tasks
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 rounded-lg">
              <Clock className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Create Scheduled Task</h1>
              <p className="text-gray-600 mt-1 text-sm">Schedule automated tasks to run at regular intervals</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Basic Information */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Basic Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Task Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Daily Sales Report"
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  placeholder="Generate daily sales report and send to team"
                  rows={3}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Task Type
                </label>
                <select
                  value={formData.task_type}
                  onChange={(e) => handleInputChange('task_type', e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  <option value="database_query">Database Query</option>
                  <option value="chart_generation">Chart Generation</option>
                  <option value="agent_task">Agent Task</option>
                </select>
              </div>
            </div>
          </div>

          {/* Schedule Configuration */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Schedule Interval
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Run Every <span className="text-red-500">*</span>
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    value={formData.interval_seconds}
                    onChange={(e) => handleInputChange('interval_seconds', parseInt(e.target.value) || 60)}
                    min="60"
                    className="w-32 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <span className="text-sm text-gray-600">seconds</span>
                  <span className="text-sm text-gray-500">
                    ({formatInterval(formData.interval_seconds)})
                  </span>
                </div>
              </div>

              {/* Quick Select Presets */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Quick Select
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {intervalPresets.map((preset) => (
                    <button
                      key={preset.value}
                      type="button"
                      onClick={() => handleInputChange('interval_seconds', preset.value)}
                      className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                        formData.interval_seconds === preset.value
                          ? 'bg-red-100 text-red-700 border-2 border-red-300'
                          : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Database & Query Configuration - Only show for database tasks */}
          {(formData.task_type === 'database_query' || formData.task_type === 'chart_generation') && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Database className="w-4 h-4" />
                Database & Query
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Database Connection
                  </label>
                  {loadingConnections ? (
                    <div className="flex items-center gap-2 text-gray-500 text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading connections...
                    </div>
                  ) : connections.length === 0 ? (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-sm text-yellow-800">
                        No database connections found.{' '}
                        <Link href="/database-connections/create" className="font-medium underline">
                          Create one first
                        </Link>
                      </p>
                    </div>
                  ) : (
                    <select
                      value={formData.database_connection_id}
                      onChange={(e) => handleInputChange('database_connection_id', e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    >
                      <option value="">Select a connection (optional)</option>
                      {connections.map((conn) => (
                        <option key={conn.id} value={conn.id}>
                          {conn.name} ({conn.type})
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    SQL Query
                  </label>
                  <textarea
                    value={formData.query}
                    onChange={(e) => handleInputChange('query', e.target.value)}
                    placeholder="SELECT * FROM sales WHERE date = CURRENT_DATE"
                    rows={6}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Leave empty to use agent&apos;s default query generation
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Agent Task Configuration */}
          {formData.task_type === 'agent_task' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Agent Task
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Agent <span className="text-red-500">*</span>
                  </label>
                  {loadingAgents ? (
                    <div className="flex items-center gap-2 text-gray-500 text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading agents...
                    </div>
                  ) : agents.length === 0 ? (
                    <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-sm text-yellow-800">No agents found. Create an agent first.</p>
                    </div>
                  ) : (
                    <select
                      value={formData.agent_id}
                      onChange={(e) => handleInputChange('agent_id', e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    >
                      <option value="">Select an agent</option>
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Prompt <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={formData.agent_prompt}
                    onChange={(e) => handleInputChange('agent_prompt', e.target.value)}
                    placeholder="What should the agent do when this task runs?"
                    rows={4}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                </div>
              </div>
            </div>
          )}

          {/* Notification Configuration */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Notifications</h2>
            <div className="space-y-5">
              {/* Email Notifications */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    checked={formData.notification_config.email_enabled}
                    onChange={(e) => handleNotificationChange('email_enabled', e.target.checked)}
                    className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                  />
                  <Mail className="w-4 h-4 text-gray-600" />
                  <label className="text-sm font-medium text-gray-700">
                    Email Notifications
                  </label>
                </div>

                {formData.notification_config.email_enabled && (
                  <div className="ml-6 space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        Recipients
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="email"
                          value={emailInput}
                          onChange={(e) => setEmailInput(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addEmailRecipient())}
                          placeholder="email@example.com"
                          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        />
                        <button
                          type="button"
                          onClick={addEmailRecipient}
                          className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm"
                        >
                          Add
                        </button>
                      </div>
                      {formData.notification_config.email_recipients.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {formData.notification_config.email_recipients.map((email) => (
                            <span
                              key={email}
                              className="inline-flex items-center gap-1 px-3 py-1 bg-red-50 text-red-700 rounded-full text-sm"
                            >
                              {email}
                              <button
                                type="button"
                                onClick={() => removeEmailRecipient(email)}
                                className="hover:text-red-900"
                              >
                                x
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Slack Notifications */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    checked={formData.notification_config.slack_enabled}
                    onChange={(e) => handleNotificationChange('slack_enabled', e.target.checked)}
                    className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                  />
                  <MessageSquare className="w-4 h-4 text-gray-600" />
                  <label className="text-sm font-medium text-gray-700">
                    Slack Notifications
                  </label>
                </div>

                {formData.notification_config.slack_enabled && (
                  <div className="ml-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Webhook URL
                    </label>
                    <input
                      type="url"
                      value={formData.notification_config.slack_webhook_url}
                      onChange={(e) => handleNotificationChange('slack_webhook_url', e.target.value)}
                      placeholder="https://hooks.slack.com/services/..."
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>
                )}
              </div>

              {/* Notification Conditions */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notify When
                </label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.notification_config.notify_on_success}
                      onChange={(e) => handleNotificationChange('notify_on_success', e.target.checked)}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-sm text-gray-700">Task succeeds</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.notification_config.notify_on_failure}
                      onChange={(e) => handleNotificationChange('notify_on_failure', e.target.checked)}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-sm text-gray-700">Task fails</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Task Status */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => handleInputChange('is_active', e.target.checked)}
                className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Activate task immediately after creation
              </span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-5">
            <Link
              href="/scheduled-tasks"
              className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Create Task
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
