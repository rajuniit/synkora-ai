'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Mail, Send } from 'lucide-react'
import { integrationsApi } from '@/lib/api/integrations'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'

const INTEGRATION_TYPES = [
  { value: 'email', label: 'Email', icon: Mail },
]

const EMAIL_PROVIDERS = [
  { value: 'smtp', label: 'SMTP', description: 'Standard SMTP email service' },
  { value: 'sendgrid', label: 'SendGrid', description: 'SendGrid email API' },
  { value: 'mailgun', label: 'Mailgun', description: 'Mailgun email REST API' },
  { value: 'brevo', label: 'Brevo', description: 'Brevo transactional email API (recommended)' },
]

export default function CreateIntegrationPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [integrationType, setIntegrationType] = useState('email')
  const [provider, setProvider] = useState('smtp')
  
  // SMTP fields
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState('587')
  const [smtpUsername, setSmtpUsername] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [smtpUseTls, setSmtpUseTls] = useState(true)
  const [smtpUseSsl, setSmtpUseSsl] = useState(false)
  const [fromEmail, setFromEmail] = useState('')
  const [fromName, setFromName] = useState('')
  
  // SendGrid fields
  const [sendgridApiKey, setSendgridApiKey] = useState('')
  const [replyTo, setReplyTo] = useState('')
  
  // Mailgun fields
  const [mailgunApiKey, setMailgunApiKey] = useState('')
  const [mailgunDomain, setMailgunDomain] = useState('')

  // Brevo fields
  const [brevoApiKey, setBrevoApiKey] = useState('')
  
  // Platform config
  const [isPlatformConfig, setIsPlatformConfig] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const configData: any = {
        version: '1.0',
        credentials: {},
        settings: {},
      }

      if (provider === 'smtp') {
        configData.credentials = {
          username: smtpUsername,
          password: smtpPassword,
        }
        configData.settings = {
          host: smtpHost,
          port: parseInt(smtpPort),
          use_tls: smtpUseTls,
          use_ssl: smtpUseSsl,
          from_email: fromEmail,
          from_name: fromName,
        }
      } else if (provider === 'sendgrid') {
        configData.credentials = {
          api_key: sendgridApiKey,
        }
        configData.settings = {
          from_email: fromEmail,
          from_name: fromName,
          reply_to: replyTo,
        }
      } else if (provider === 'mailgun') {
        configData.credentials = {
          api_key: mailgunApiKey,
          domain: mailgunDomain,
        }
        configData.settings = {
          from_email: fromEmail,
          from_name: fromName,
          reply_to: replyTo,
        }
      } else if (provider === 'brevo') {
        configData.credentials = {
          api_key: brevoApiKey,
        }
        configData.settings = {
          from_email: fromEmail,
          from_name: fromName,
          reply_to: replyTo,
        }
      }

      await integrationsApi.createConfig({
        integration_type: integrationType,
        provider,
        config_data: configData,
        is_platform_config: isPlatformConfig,
      })

      router.push('/settings/integrations')
    } catch (err: any) {
      setError(err.message || 'Failed to create integration')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-rose-50/30 to-red-50 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-5">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-red-600 hover:text-red-700 mb-4 text-sm font-medium"
          >
            <ArrowLeft size={16} />
            Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Add Integration</h1>
          <p className="text-gray-600 mt-0.5 text-sm">
            Configure a new third-party service integration
          </p>
        </div>

        {error && (
          <div className="mb-5">
            <ErrorAlert message={error} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-5">
          {/* Integration Type */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Integration Type
            </label>
            <select
              value={integrationType}
              onChange={(e) => setIntegrationType(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            >
              {INTEGRATION_TYPES.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Provider */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            >
              {EMAIL_PROVIDERS.map(prov => (
                <option key={prov.value} value={prov.value}>
                  {prov.label} - {prov.description}
                </option>
              ))}
            </select>
          </div>

          {/* SMTP Configuration */}
          {provider === 'smtp' && (
            <>
              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">SMTP Configuration</h3>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      SMTP Host *
                    </label>
                    <input
                      type="text"
                      value={smtpHost}
                      onChange={(e) => setSmtpHost(e.target.value)}
                      placeholder="smtp.gmail.com"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      SMTP Port *
                    </label>
                    <input
                      type="number"
                      value={smtpPort}
                      onChange={(e) => setSmtpPort(e.target.value)}
                      placeholder="587"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Username *
                    </label>
                    <input
                      type="text"
                      value={smtpUsername}
                      onChange={(e) => setSmtpUsername(e.target.value)}
                      placeholder="your-email@gmail.com"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Password *
                    </label>
                    <input
                      type="password"
                      value={smtpPassword}
                      onChange={(e) => setSmtpPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>
                </div>

                <div className="flex gap-6 mt-3">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={smtpUseTls}
                      onChange={(e) => setSmtpUseTls(e.target.checked)}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-xs text-gray-700">Use TLS</span>
                  </label>

                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={smtpUseSsl}
                      onChange={(e) => setSmtpUseSsl(e.target.checked)}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-xs text-gray-700">Use SSL</span>
                  </label>
                </div>
              </div>
            </>
          )}

          {/* SendGrid Configuration */}
          {provider === 'sendgrid' && (
            <>
              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">SendGrid Configuration</h3>
                
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    API Key *
                  </label>
                  <input
                    type="password"
                    value={sendgridApiKey}
                    onChange={(e) => setSendgridApiKey(e.target.value)}
                    placeholder="SG.••••••••"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Reply To
                  </label>
                  <input
                    type="email"
                    value={replyTo}
                    onChange={(e) => setReplyTo(e.target.value)}
                    placeholder="support@example.com"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
              </div>
            </>
          )}

          {/* Mailgun Configuration */}
          {provider === 'mailgun' && (
            <>
              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">Mailgun Configuration</h3>
                
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    API Key *
                  </label>
                  <input
                    type="password"
                    value={mailgunApiKey}
                    onChange={(e) => setMailgunApiKey(e.target.value)}
                    placeholder="key-••••••••••••••••••••••••••••"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Domain *
                  </label>
                  <input
                    type="text"
                    value={mailgunDomain}
                    onChange={(e) => setMailgunDomain(e.target.value)}
                    placeholder="mg.example.com"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your Mailgun sending domain (e.g., mg.example.com)
                  </p>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Reply To
                  </label>
                  <input
                    type="email"
                    value={replyTo}
                    onChange={(e) => setReplyTo(e.target.value)}
                    placeholder="support@example.com"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
              </div>
            </>
          )}

          {/* Brevo Configuration */}
          {provider === 'brevo' && (
            <>
              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">Brevo Configuration</h3>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    API Key *
                  </label>
                  <input
                    type="password"
                    value={brevoApiKey}
                    onChange={(e) => setBrevoApiKey(e.target.value)}
                    placeholder="xkeysib-••••••••••••••••••••••••••••"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Found in Brevo dashboard → SMTP & API → API Keys
                  </p>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Reply To
                  </label>
                  <input
                    type="email"
                    value={replyTo}
                    onChange={(e) => setReplyTo(e.target.value)}
                    placeholder="support@example.com"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
              </div>
            </>
          )}

          {/* Platform Configuration Option */}
          <div className="border-t pt-5">
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isPlatformConfig}
                  onChange={(e) => setIsPlatformConfig(e.target.checked)}
                  className="mt-1 w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                />
                <div>
                  <span className="text-xs font-medium text-gray-900">Platform Configuration</span>
                  <p className="text-xs text-gray-600 mt-1">
                    Enable this to make this configuration available to all tenants as a fallback when they don't have their own email configuration.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Common Email Settings */}
          <div className="border-t pt-5">
            <h3 className="text-base font-semibold text-gray-900 mb-3">Email Settings</h3>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-2">
                  From Email *
                </label>
                <input
                  type="email"
                  value={fromEmail}
                  onChange={(e) => setFromEmail(e.target.value)}
                  placeholder="noreply@example.com"
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-2">
                  From Name *
                </label>
                <input
                  type="text"
                  value={fromName}
                  onChange={(e) => setFromName(e.target.value)}
                  placeholder="My Platform"
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  required
                />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-5 border-t">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-5 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-white hover:border-red-300 transition-colors font-medium"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 text-sm bg-gradient-to-r from-red-500 to-rose-500 text-white rounded-lg hover:from-red-600 hover:to-rose-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
            >
              {loading ? (
                <>
                  <LoadingSpinner />
                  Creating...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Create Integration
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
