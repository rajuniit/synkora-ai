'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/client'

interface PlatformSettings {
  id?: string
  stripe_publishable_key?: string
  stripe_secret_key?: string
  stripe_webhook_secret?: string
  created_at?: string
  updated_at?: string
}

export default function PlatformSettingsPage() {
  const [settings, setSettings] = useState<PlatformSettings>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await apiClient.request('GET', '/api/v1/platform-settings')
      if (data) {
        setSettings({
          stripe_publishable_key: data.stripe_publishable_key || '',
          stripe_secret_key: '', // Not returned by backend for security
          stripe_webhook_secret: '', // Not returned by backend for security
        })
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    try {
      // Update Stripe keys
      await apiClient.request('PUT', '/api/v1/platform-settings/stripe-keys', {
        secret_key: settings.stripe_secret_key || undefined,
        publishable_key: settings.stripe_publishable_key || undefined,
        webhook_secret: settings.stripe_webhook_secret || undefined
      })

      setMessage({ type: 'success', text: 'Stripe settings saved successfully!' })
      // Clear sensitive fields after save
      setSettings({
        ...settings,
        stripe_secret_key: '',
        stripe_webhook_secret: ''
      })
      loadSettings()
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Platform Settings</h1>
        <p className="mt-2 text-gray-600">Configure Stripe payment integration for the platform</p>
      </div>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Stripe Configuration */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Stripe Configuration</h2>
          <p className="text-sm text-gray-600 mb-4">
            Configure your Stripe API keys to enable payment processing. You can find these keys in your{' '}
            <a href="https://dashboard.stripe.com/apikeys" target="_blank" rel="noopener noreferrer" className="text-emerald-600 hover:text-emerald-700">
              Stripe Dashboard
            </a>.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Stripe Publishable Key
              </label>
              <input
                type="text"
                value={settings.stripe_publishable_key || ''}
                onChange={(e) => setSettings({ ...settings, stripe_publishable_key: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="pk_test_..."
              />
              <p className="mt-1 text-xs text-gray-500">
                This key is safe to expose in your frontend code
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Stripe Secret Key
              </label>
              <input
                type="password"
                value={settings.stripe_secret_key || ''}
                onChange={(e) => setSettings({ ...settings, stripe_secret_key: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="sk_test_..."
              />
              <p className="mt-1 text-xs text-gray-500">
                Keep this key secure and never expose it in frontend code
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Stripe Webhook Secret
              </label>
              <input
                type="password"
                value={settings.stripe_webhook_secret || ''}
                onChange={(e) => setSettings({ ...settings, stripe_webhook_secret: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="whsec_..."
              />
              <p className="mt-1 text-xs text-gray-500">
                Used to verify webhook events from Stripe
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  )
}
