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
  auth_method: string
  client_id: string
  redirect_uri: string
  scopes: string[] | null
  is_active: boolean
  is_default: boolean
  description: string | null
  config: Record<string, any> | null
}

const DEFAULT_SCOPES: Record<string, string[]> = {
  github: ['repo', 'user', 'read:org'],
  SLACK: [
    'channels:history', 'channels:read', 'groups:history', 'groups:read',
    'im:history', 'im:read', 'mpim:history', 'mpim:read', 'users:read', 'team:read',
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
    auth_method: 'oauth',
    client_id: '',
    client_secret: '',
    redirect_uri: '',
    scopes: [] as string[],
    api_token: '',       // new password/token (blank = keep existing)
    is_active: true,
    is_default: false,
    description: '',
    config: {} as Record<string, any>,
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
        auth_method: data.auth_method || 'oauth',
        client_id: data.client_id || '',
        client_secret: '',
        redirect_uri: data.redirect_uri || '',
        scopes: data.scopes || [],
        api_token: '',
        is_active: data.is_active ?? true,
        is_default: data.is_default ?? false,
        description: data.description || '',
        config: data.config || {},
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
      const updateData: any = {
        app_name: formData.app_name,
        redirect_uri: formData.redirect_uri,
        scopes: formData.scopes,
        is_active: formData.is_active,
        is_default: formData.is_default,
        description: formData.description,
        config: formData.config,
      }
      if (formData.auth_method === 'oauth') {
        updateData.client_id = formData.client_id
        if (formData.client_secret) updateData.client_secret = formData.client_secret
      }
      if ((formData.auth_method === 'api_token' || formData.auth_method === 'basic_auth') && formData.api_token) {
        updateData.api_token = formData.api_token
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
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-8">
        <div className="max-w-4xl mx-auto">
          <ErrorAlert message="OAuth app not found" />
        </div>
      </div>
    )
  }

  const availableScopes = DEFAULT_SCOPES[app.provider] || []
  const isMicromobility = app.provider === 'micromobility'

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/oauth-apps"
            className="text-[#ff444f] hover:text-red-700 flex items-center gap-2 mb-4 font-medium"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Connected Accounts
          </Link>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">
            Edit {app.app_name}
          </h1>
          <p className="text-gray-500 mt-1 text-sm capitalize">
            {app.provider} · {app.auth_method?.replace('_', ' ')}
          </p>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorAlert message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Basic Information */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Basic Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Connection Name *</label>
                <input
                  type="text"
                  required
                  value={formData.app_name}
                  onChange={(e) => setFormData({ ...formData, app_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent text-sm"
                  rows={2}
                />
              </div>
              <div className="flex items-center gap-5">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-[#ff444f] border-gray-300 rounded focus:ring-[#ff444f]"
                  />
                  <span className="text-sm text-gray-700">Active</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="w-4 h-4 text-[#ff444f] border-gray-300 rounded focus:ring-[#ff444f]"
                  />
                  <span className="text-sm text-gray-700">Default for this provider</span>
                </label>
              </div>
            </div>
          </div>

          {/* Credentials — OAuth */}
          {formData.auth_method === 'oauth' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-4">OAuth Credentials</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Client ID *</label>
                  <input
                    type="text"
                    required
                    value={formData.client_id}
                    onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Client Secret</label>
                  <input
                    type="password"
                    value={formData.client_secret}
                    onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                    placeholder="Leave blank to keep current secret"
                  />
                  <p className="text-xs text-gray-500 mt-1">Only enter a new value to replace the existing secret.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Redirect URI *</label>
                  <input
                    type="url"
                    required
                    value={formData.redirect_uri}
                    onChange={(e) => setFormData({ ...formData, redirect_uri: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Credentials — Basic Auth (Username + Password → JWT) */}
          {formData.auth_method === 'basic_auth' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-4">Login Credentials</h2>
              <div className="space-y-4">
                {isMicromobility && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        Base URL *
                      </label>
                      <input
                        type="url"
                        required
                        value={formData.config.base_url || ''}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, base_url: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                        placeholder="https://api.your-oto-instance.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Login Endpoint *</label>
                      <input
                        type="text"
                        required
                        value={formData.config.login_endpoint || ''}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, login_endpoint: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                        placeholder="/admin-login-jwt/"
                      />
                      <p className="text-xs text-gray-500 mt-1">Endpoint to POST username/password to receive a JWT</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Token Field in Response *</label>
                      <input
                        type="text"
                        required
                        value={formData.config.token_response_field || ''}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, token_response_field: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                        placeholder="token"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Username *</label>
                      <input
                        type="text"
                        required
                        value={formData.config.username || ''}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, username: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent text-sm"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">Username Field Name</label>
                        <input
                          type="text"
                          value={formData.config.login_username_field || ''}
                          onChange={(e) => setFormData({ ...formData, config: { ...formData.config, login_username_field: e.target.value } })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                          placeholder="username"
                        />
                        <p className="text-xs text-gray-500 mt-1">JSON body field name for username (default: username)</p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">Password Field Name</label>
                        <input
                          type="text"
                          value={formData.config.login_password_field || ''}
                          onChange={(e) => setFormData({ ...formData, config: { ...formData.config, login_password_field: e.target.value } })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                          placeholder="password"
                        />
                        <p className="text-xs text-gray-500 mt-1">JSON body field name for password (default: password)</p>
                      </div>
                    </div>
                  </>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Password {formData.api_token ? '*' : '(leave blank to keep current)'}
                  </label>
                  <input
                    type="password"
                    value={formData.api_token}
                    onChange={(e) => setFormData({ ...formData, api_token: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                    placeholder="Leave blank to keep current password"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Encrypted and stored securely. Changing the password will clear the cached JWT token and trigger a fresh login on next use.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Credentials — API Token */}
          {formData.auth_method === 'api_token' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-4">API Token</h2>
              <div className="space-y-4">
                {isMicromobility && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">Base URL *</label>
                      <input
                        type="url"
                        required
                        value={formData.config.base_url || ''}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, base_url: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                        placeholder="https://api.your-oto-instance.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">API Key Header</label>
                      <input
                        type="text"
                        value={formData.config.api_key_header || 'Authorization'}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, api_key_header: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                        placeholder="Authorization"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">API Key Format</label>
                      <input
                        type="text"
                        value={formData.config.api_key_format || 'Bearer {token}'}
                        onChange={(e) => setFormData({ ...formData, config: { ...formData.config, api_key_format: e.target.value } })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                        placeholder="Bearer {token}"
                      />
                    </div>
                  </>
                )}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    API Token (leave blank to keep current)
                  </label>
                  <input
                    type="password"
                    value={formData.api_token}
                    onChange={(e) => setFormData({ ...formData, api_token: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#ff444f] focus:border-transparent font-mono text-sm"
                    placeholder="Leave blank to keep current token"
                  />
                  <p className="text-xs text-gray-500 mt-1">Only enter a new value to replace the existing token.</p>
                </div>
              </div>
            </div>
          )}

          {/* Scopes (OAuth only) */}
          {formData.auth_method === 'oauth' && availableScopes.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-3">OAuth Scopes</h2>
              <div className="space-y-2">
                {availableScopes.map((scope) => (
                  <label key={scope} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.scopes.includes(scope)}
                      onChange={(e) => handleScopeChange(scope, e.target.checked)}
                      className="w-4 h-4 text-[#ff444f] border-gray-300 rounded focus:ring-[#ff444f]"
                    />
                    <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{scope}</code>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 px-5 py-2.5 bg-[#ff444f] text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
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
              className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm text-center"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
