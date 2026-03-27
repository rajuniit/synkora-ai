'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'
import { apiClient } from '@/lib/api/client'

interface OAuthApp {
  id: number
  provider: string
  app_name: string
  client_id: string
  redirect_uri: string
  scopes: string[] | null
  is_active: boolean
  is_default: boolean
  description: string | null
}

const PROVIDER_INFO: Record<string, { name: string; icon: string }> = {
  github: { name: 'GitHub', icon: '🐙' },
  SLACK: { name: 'Slack', icon: '💬' },
  gmail: { name: 'Gmail', icon: '📧' },
}

const DEFAULT_SCOPES: Record<string, string[]> = {
  github: ['repo', 'user', 'read:org'],
  SLACK: [
    'channels:history',
    'channels:read',
    'groups:history',
    'groups:read',
    'im:history',
    'im:read',
    'mpim:history',
    'mpim:read',
    'users:read',
    'team:read',
  ],
  gmail: [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
  ],
}

export default function EditOAuthAppPage() {
  const router = useRouter()
  const params = useParams()
  const appId = params?.id as string

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [app, setApp] = useState<OAuthApp | null>(null)

  const [formData, setFormData] = useState({
    app_name: '',
    client_id: '',
    client_secret: '',
    redirect_uri: '',
    scopes: [] as string[],
    is_active: true,
    is_default: false,
    description: '',
  })

  useEffect(() => {
    fetchOAuthApp()
  }, [appId])

  const fetchOAuthApp = async () => {
    if (!appId) return
    
    try {
      setLoading(true)
      const data = await apiClient.getOAuthApp(parseInt(appId))
      setApp(data)
        setFormData({
          app_name: data.app_name || '',
          client_id: data.client_id || '',
          client_secret: '', // Don't populate for security
          redirect_uri: data.redirect_uri || '',
          scopes: data.scopes || [],
          is_active: data.is_active ?? true,
          is_default: data.is_default ?? false,
          description: data.description || '',
        })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleScopeChange = (scope: string, checked: boolean) => {
    if (checked) {
      setFormData({ ...formData, scopes: [...formData.scopes, scope] })
    } else {
      setFormData({ ...formData, scopes: formData.scopes.filter(s => s !== scope) })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      // Only include client_secret if it was changed
      const updateData: any = {
        app_name: formData.app_name,
        client_id: formData.client_id,
        redirect_uri: formData.redirect_uri,
        scopes: formData.scopes,
        is_active: formData.is_active,
        is_default: formData.is_default,
        description: formData.description,
      }

      if (formData.client_secret) {
        updateData.client_secret = formData.client_secret
      }

      await apiClient.updateOAuthApp(parseInt(appId), updateData)
      router.push('/oauth-apps')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!app) {
    return (
      <div className="min-h-screen bg-gray-50 p-4 md:p-8">
        <div className="max-w-4xl mx-auto">
          <ErrorAlert message="OAuth app not found" />
        </div>
      </div>
    )
  }

  const providerInfo = PROVIDER_INFO[app.provider] || { name: app.provider, icon: '🔐' }
  const availableScopes = DEFAULT_SCOPES[app.provider] || []

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/oauth-apps"
            className="text-blue-600 hover:text-blue-700 flex items-center gap-2 mb-4 font-medium"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to OAuth Apps
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-3xl">{providerInfo.icon}</span>
            <div>
              <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Edit {providerInfo.name} OAuth App</h1>
              <p className="text-gray-600 mt-2">
                Update OAuth credentials and settings
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorAlert message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Basic Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  App Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.app_name}
                  onChange={(e) => setFormData({ ...formData, app_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., My GitHub Integration"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={2}
                  placeholder="Optional description for this OAuth app"
                />
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Active</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Set as default for this provider</span>
                </label>
              </div>
            </div>
          </div>

          {/* OAuth Credentials */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">OAuth Credentials</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Client ID *
                </label>
                <input
                  type="text"
                  required
                  value={formData.client_id}
                  onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  placeholder="Enter your OAuth client ID"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Client Secret
                </label>
                <input
                  type="password"
                  value={formData.client_secret}
                  onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                  placeholder="Leave blank to keep current secret"
                />
                <p className="text-sm text-gray-500 mt-1">
                  Only enter a new secret if you want to update it. Leave blank to keep the existing secret.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Redirect URI *
                </label>
                <input
                  type="url"
                  required
                  value={formData.redirect_uri}
                  onChange={(e) => setFormData({ ...formData, redirect_uri: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                />
                <p className="text-sm text-gray-500 mt-1">
                  This must match the redirect URI configured in your {providerInfo.name} app
                </p>
              </div>
            </div>
          </div>

          {/* Scopes */}
          {availableScopes.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">OAuth Scopes</h2>
              <p className="text-sm text-gray-600 mb-4">
                Select the permissions your app needs.
              </p>
              <div className="space-y-2">
                {availableScopes.map((scope) => (
                  <label key={scope} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.scopes.includes(scope)}
                      onChange={(e) => handleScopeChange(scope, e.target.checked)}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">{scope}</code>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {saving ? (
                <span className="flex items-center justify-center gap-2">
                  <LoadingSpinner size="sm" />
                  Saving...
                </span>
              ) : (
                'Save Changes'
              )}
            </button>
            <Link
              href="/oauth-apps"
              className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-center"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
