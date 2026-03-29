'use client'

import { useState } from 'react'
import { Save, Loader2, AlertCircle, Info, Copy, Check, Eye, EyeOff } from 'lucide-react'
import { useWebhooks } from '@/hooks/useWebhooks'
import toast from 'react-hot-toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

export interface WebhookFormProps {
  agentName: string
  onSuccess?: () => void
  onCancel?: () => void
}

interface WebhookCreatedData {
  webhookUrl: string
  secret: string
  verifySignature: boolean
}

const providerOptions = [
  { value: 'github', label: 'GitHub', events: ['pull_request', 'issues', 'push', 'release'], defaultVerify: true },
  { value: 'sentry', label: 'Sentry', events: ['issue', 'error', 'event_alert', 'issue_alert', 'metric_alert'], defaultVerify: false },
  { value: 'clickup', label: 'ClickUp', events: ['taskCreated', 'taskUpdated', 'taskDeleted', 'taskCommentPosted'], defaultVerify: true },
  { value: 'jira', label: 'Jira', events: ['issue_created', 'issue_updated', 'issue_deleted', 'comment_created'], defaultVerify: true },
  { value: 'slack', label: 'Slack', events: ['message', 'app_mention', 'reaction_added'], defaultVerify: true },
  { value: 'custom', label: 'Custom', events: ['webhook'], defaultVerify: false }
]

export function WebhookForm({ agentName, onSuccess, onCancel }: WebhookFormProps) {
  const { createWebhook } = useWebhooks(agentName)
  const [saving, setSaving] = useState(false)
  const [createdWebhook, setCreatedWebhook] = useState<WebhookCreatedData | null>(null)
  const [showSecret, setShowSecret] = useState(false)
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedSecret, setCopiedSecret] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    provider: 'github',
    event_types: [] as string[],
    verify_signature: true
  })

  const selectedProvider = providerOptions.find(p => p.value === formData.provider)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      toast.error('Please enter a webhook name')
      return
    }

    if (formData.event_types.length === 0) {
      toast.error('Please select at least one event type')
      return
    }

    setSaving(true)

    try {
      const result = await createWebhook({
        name: formData.name,
        provider: formData.provider as any,
        event_types: formData.event_types,
        is_active: true,
        config: { verify_signature: formData.verify_signature }
      } as any)
      
      // Show the secret modal
      setCreatedWebhook({
        webhookUrl: result.webhook_url,
        secret: result.config?.secret || '',
        verifySignature: formData.verify_signature
      })
      
      toast.success('Webhook created successfully!')
    } catch (error: any) {
      toast.error(error.message || 'Failed to create webhook')
    } finally {
      setSaving(false)
    }
  }

  const toggleEventType = (event: string) => {
    setFormData(prev => ({
      ...prev,
      event_types: prev.event_types.includes(event)
        ? prev.event_types.filter(e => e !== event)
        : [...prev.event_types, event]
    }))
  }

  const copyToClipboard = async (text: string, type: 'url' | 'secret') => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === 'url') {
        setCopiedUrl(true)
        setTimeout(() => setCopiedUrl(false), 2000)
      } else {
        setCopiedSecret(true)
        setTimeout(() => setCopiedSecret(false), 2000)
      }
      toast.success('Copied to clipboard!')
    } catch (error) {
      toast.error('Failed to copy')
    }
  }

  const handleClose = () => {
    setCreatedWebhook(null)
    onSuccess?.()
  }

  // Show secret modal after creation
  if (createdWebhook) {
    const fullUrl = `${API_URL}${createdWebhook.webhookUrl}`
    
    return (
      <div className="p-6">
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Webhook Created Successfully! 🎉</h3>
          <p className="text-sm text-gray-600">
            {createdWebhook.verifySignature
              ? 'Save these credentials now. The secret will only be shown once for security.'
              : 'Your webhook is ready. Signature verification is disabled — all incoming requests will be accepted.'}
          </p>
        </div>

        <div className="space-y-4 mb-6">
          {/* Webhook URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Webhook URL
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={fullUrl}
                readOnly
                className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-gray-50 font-mono"
              />
              <button
                type="button"
                onClick={() => copyToClipboard(fullUrl, 'url')}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="Copy URL"
              >
                {copiedUrl ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Secret — only show if signature verification is enabled */}
          {createdWebhook.verifySignature && createdWebhook.secret && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Webhook Secret
              </label>
              <div className="flex items-center gap-2">
                <input
                  type={showSecret ? 'text' : 'password'}
                  value={createdWebhook.secret}
                  readOnly
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-gray-50 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  title={showSecret ? 'Hide secret' : 'Show secret'}
                >
                  {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
                <button
                  type="button"
                  onClick={() => copyToClipboard(createdWebhook.secret, 'secret')}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Copy secret"
                >
                  {copiedSecret ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-red-600 mt-1.5 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                This secret will only be shown once. Save it securely!
              </p>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Next Steps:</h4>
          <ol className="text-xs text-blue-800 space-y-1 list-decimal list-inside">
            <li>Copy the webhook URL above</li>
            <li>Go to your {selectedProvider?.label} settings and add this URL</li>
            {createdWebhook.verifySignature && createdWebhook.secret && (
              <li>Configure the webhook secret in {selectedProvider?.label} for signature verification</li>
            )}
          </ol>
        </div>

        {/* Close Button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleClose}
            className="px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md"
          >
            Done
          </button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="p-6">
      <div className="space-y-6">
        {/* Basic Information */}
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-4">Basic Information</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Webhook Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="GitHub PR Review Webhook"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Provider <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.provider}
                onChange={(e) => {
                  const p = providerOptions.find(o => o.value === e.target.value)
                  setFormData(prev => ({ ...prev, provider: e.target.value, event_types: [], verify_signature: p?.defaultVerify ?? false }))
                }}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                required
              >
                {providerOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Event Types */}
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            Event Types <span className="text-red-500">*</span>
          </h3>
          <p className="text-xs text-gray-600 mb-3">
            Select the events that should trigger this webhook
          </p>
          
          {selectedProvider && selectedProvider.events.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              {selectedProvider.events.map(event => (
                <label
                  key={event}
                  className={`flex items-center gap-2.5 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                    formData.event_types.includes(event)
                      ? 'border-red-500 bg-red-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={formData.event_types.includes(event)}
                    onChange={() => toggleEventType(event)}
                    className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                  />
                  <span className="text-sm font-medium text-gray-900">{event}</span>
                </label>
              ))}
            </div>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-blue-700">
                  For custom webhooks, you can specify event types after creation in the configuration.
                </p>
              </div>
            </div>
          )}
        </div>


        {/* Signature Verification Toggle */}
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-1">Signature Verification</h3>
          <p className="text-xs text-gray-600 mb-3">
            Verify that incoming requests are genuinely from {selectedProvider?.label} using HMAC signature
          </p>
          <label className="flex items-center gap-3 cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                className="sr-only"
                checked={formData.verify_signature}
                onChange={(e) => setFormData(prev => ({ ...prev, verify_signature: e.target.checked }))}
              />
              <div className={`w-10 h-6 rounded-full transition-colors ${formData.verify_signature ? 'bg-red-500' : 'bg-gray-300'}`} />
              <div className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${formData.verify_signature ? 'translate-x-4' : 'translate-x-0'}`} />
            </div>
            <div>
              <span className="text-sm font-medium text-gray-900">
                {formData.verify_signature ? 'Enabled' : 'Disabled'}
              </span>
              <p className="text-xs text-gray-500">
                {formData.verify_signature
                  ? 'Requests without a valid signature will be rejected'
                  : 'All incoming requests will be accepted without signature check'}
              </p>
            </div>
          </label>
        </div>

        {/* Info Box */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-red-800">
              <p className="font-medium mb-1">After creating the webhook:</p>
              <ul className="list-disc list-inside space-y-0.5 ml-1">
                <li>You'll receive a unique webhook URL</li>
                <li>Configure this URL in your {selectedProvider?.label} settings</li>
                <li>The agent will automatically process incoming events</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-5 border-t border-gray-200">
          <button
            type="button"
            onClick={onCancel}
            className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !formData.name || formData.event_types.length === 0}
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
                Create Webhook
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  )
}
