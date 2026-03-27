'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Send } from 'lucide-react'
import { integrationsApi } from '@/lib/api/integrations'
import { usePermissions } from '@/hooks/usePermissions'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/ErrorAlert'

const PAYMENT_PROVIDERS = [
  { value: 'stripe', label: 'Stripe', description: 'Accept payments with Stripe' },
  { value: 'paddle', label: 'Paddle', description: 'Accept payments with Paddle (Merchant of Record)' },
  { value: 'paypal', label: 'PayPal', description: 'Accept payments with PayPal (Coming Soon)', disabled: true },
  { value: 'square', label: 'Square', description: 'Accept payments with Square (Coming Soon)', disabled: true },
]

export default function CreatePaymentIntegrationPage() {
  const router = useRouter()
  const { hasPermission } = usePermissions()
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Check if user is a Platform Owner
  const isPlatformOwner = hasPermission('platform', 'create')

  const [provider, setProvider] = useState('stripe')
  // Stripe fields
  const [secretKey, setSecretKey] = useState('')
  const [publishableKey, setPublishableKey] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [currency, setCurrency] = useState('usd')
  const [captureMethod, setCaptureMethod] = useState('automatic')
  // Paddle fields
  const [paddleApiKey, setPaddleApiKey] = useState('')
  const [paddleClientToken, setPaddleClientToken] = useState('')
  const [paddleWebhookSecret, setPaddleWebhookSecret] = useState('')
  const [paddleEnvironment, setPaddleEnvironment] = useState('sandbox')
  const [paddleCreditsProductId, setPaddleCreditsProductId] = useState('')
  // Common fields
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(false)
  const [isPlatformConfig, setIsPlatformConfig] = useState(true)

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)

    try {
      let configData: any = { version: '1.0' }

      if (provider === 'stripe') {
        configData = {
          version: '1.0',
          credentials: {
            secret_key: secretKey,
            publishable_key: publishableKey,
            webhook_secret: webhookSecret || undefined,
          },
          settings: {
            currency,
            capture_method: captureMethod,
          },
        }
      } else if (provider === 'paddle') {
        configData = {
          version: '1.0',
          credentials: {
            api_key: paddleApiKey,
            client_side_token: paddleClientToken,
            webhook_secret: paddleWebhookSecret || undefined,
          },
          settings: {
            environment: paddleEnvironment,
            credits_product_id: paddleCreditsProductId || undefined,
          },
        }
      }

      const response = await fetch('/api/integration-configs/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          integration_type: 'payment',
          provider,
          config_data: configData,
        }),
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setTestResult({ success: true, message: 'Connection successful!' })
      } else {
        setTestResult({ success: false, message: data.error || 'Connection failed' })
      }
    } catch (err: any) {
      setTestResult({ success: false, message: err.message })
    } finally {
      setTesting(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      let configData: any = { version: '1.0' }

      if (provider === 'stripe') {
        configData = {
          version: '1.0',
          credentials: {
            secret_key: secretKey,
            publishable_key: publishableKey,
            webhook_secret: webhookSecret || undefined,
          },
          settings: {
            currency,
            capture_method: captureMethod,
          },
          metadata: {
            description: description || 'Stripe payment integration',
          },
        }
      } else if (provider === 'paddle') {
        configData = {
          version: '1.0',
          credentials: {
            api_key: paddleApiKey,
            client_side_token: paddleClientToken,
            webhook_secret: paddleWebhookSecret || undefined,
          },
          settings: {
            environment: paddleEnvironment,
            credits_product_id: paddleCreditsProductId || undefined,
          },
          metadata: {
            description: description || 'Paddle payment integration (Merchant of Record)',
          },
        }
      }

      await integrationsApi.createConfig({
        integration_type: 'payment',
        provider,
        config_data: configData,
        is_active: isActive,
        is_platform_config: isPlatformConfig,
      })

      router.push('/settings/integrations?tab=payment')
    } catch (err: any) {
      setError(err.message || 'Failed to create integration')
    } finally {
      setLoading(false)
    }
  }

  const isFormValid = provider === 'stripe'
    ? secretKey && publishableKey
    : provider === 'paddle'
      ? paddleApiKey && paddleClientToken
      : false

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-5">
          <button
            onClick={() => router.push('/settings/integrations?tab=payment')}
            className="flex items-center gap-2 text-red-600 hover:text-red-700 mb-4 text-sm font-medium"
          >
            <ArrowLeft size={16} />
            Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Add Payment Integration</h1>
          <p className="text-gray-600 mt-0.5 text-sm">
            Configure a payment provider to accept payments
          </p>
        </div>

        {error && (
          <div className="mb-5">
            <ErrorAlert message={error} />
          </div>
        )}

        {testResult && (
          <div className={`mb-5 p-3 rounded-lg border text-sm ${
            testResult.success 
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            {testResult.message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-5">
          {/* Provider Selection */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Payment Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              required
            >
              {PAYMENT_PROVIDERS.map((prov) => (
                <option key={prov.value} value={prov.value} disabled={prov.disabled}>
                  {prov.label} - {prov.description}
                </option>
              ))}
            </select>
          </div>

          {/* Stripe Configuration */}
          {provider === 'stripe' && (
            <>
              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">Stripe Credentials</h3>
                
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Secret Key *
                  </label>
                  <input
                    type="password"
                    value={secretKey}
                    onChange={(e) => setSecretKey(e.target.value)}
                    placeholder="sk_test_..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your Stripe secret key (starts with sk_)
                  </p>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Publishable Key *
                  </label>
                  <input
                    type="text"
                    value={publishableKey}
                    onChange={(e) => setPublishableKey(e.target.value)}
                    placeholder="pk_test_..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your Stripe publishable key (starts with pk_)
                  </p>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Webhook Secret (Optional)
                  </label>
                  <input
                    type="password"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                    placeholder="whsec_..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Webhook signing secret for verifying webhook events
                  </p>
                </div>
              </div>

              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">Payment Settings</h3>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Default Currency
                    </label>
                    <select
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    >
                      <option value="usd">USD - US Dollar</option>
                      <option value="eur">EUR - Euro</option>
                      <option value="gbp">GBP - British Pound</option>
                      <option value="cad">CAD - Canadian Dollar</option>
                      <option value="aud">AUD - Australian Dollar</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Capture Method
                    </label>
                    <select
                      value={captureMethod}
                      onChange={(e) => setCaptureMethod(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    >
                      <option value="automatic">Automatic - Capture immediately</option>
                      <option value="manual">Manual - Capture later</option>
                    </select>
                  </div>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Description (Optional)
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g., Production Stripe account"
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>
              </div>
            </>
          )}

          {/* Paddle Configuration */}
          {provider === 'paddle' && (
            <>
              <div className="border-t pt-5">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                  <p className="text-xs text-blue-800">
                    <strong>Paddle as Merchant of Record:</strong> Paddle handles all VAT/tax compliance,
                    invoicing, and payment processing globally. This is ideal for selling to customers
                    in the EU and other regions with complex tax requirements.
                  </p>
                </div>

                <h3 className="text-base font-semibold text-gray-900 mb-3">Paddle Credentials</h3>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    API Key *
                  </label>
                  <input
                    type="password"
                    value={paddleApiKey}
                    onChange={(e) => setPaddleApiKey(e.target.value)}
                    placeholder="pdl_..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Your Paddle API key from the Developer Tools section
                  </p>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Client-Side Token *
                  </label>
                  <input
                    type="text"
                    value={paddleClientToken}
                    onChange={(e) => setPaddleClientToken(e.target.value)}
                    placeholder="test_..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Client-side token for Paddle.js initialization (from Developer Tools)
                  </p>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Webhook Secret (Optional)
                  </label>
                  <input
                    type="password"
                    value={paddleWebhookSecret}
                    onChange={(e) => setPaddleWebhookSecret(e.target.value)}
                    placeholder="pdl_ntfset_..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Webhook secret key for verifying webhook notifications
                  </p>
                </div>
              </div>

              <div className="border-t pt-5">
                <h3 className="text-base font-semibold text-gray-900 mb-3">Paddle Settings</h3>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Environment *
                    </label>
                    <select
                      value={paddleEnvironment}
                      onChange={(e) => setPaddleEnvironment(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    >
                      <option value="sandbox">Sandbox - For testing</option>
                      <option value="production">Production - Live payments</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Credits Product ID (Optional)
                    </label>
                    <input
                      type="text"
                      value={paddleCreditsProductId}
                      onChange={(e) => setPaddleCreditsProductId(e.target.value)}
                      placeholder="pro_..."
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Product ID for credit top-ups
                    </p>
                  </div>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Description (Optional)
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g., Production Paddle account"
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="text-xs text-gray-600">
                    <strong>Webhook URL:</strong> Configure this URL in your Paddle dashboard:
                  </p>
                  <code className="text-xs text-gray-800 bg-gray-100 px-2 py-1 rounded mt-1 block">
                    https://your-domain.com/api/v1/billing/webhook/paddle
                  </code>
                </div>
              </div>
            </>
          )}

          {/* Platform Configuration Option - Only visible to Platform Owners */}
          {isPlatformOwner && (
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
                      Enable this to make this configuration available platform-wide. Only Platform Owners can create platform configurations.
                    </p>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* Activate Integration */}
          <div className="border-t pt-5">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="mt-1 w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
              />
              <div>
                <span className="text-xs font-medium text-gray-900">Activate Integration</span>
                <p className="text-xs text-gray-600 mt-1">
                  Make this the active payment provider
                </p>
              </div>
            </label>
          </div>

          {/* Actions */}
          <div className="flex justify-between gap-3 pt-5 border-t">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={!isFormValid || testing}
              className="px-5 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-white hover:border-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {testing ? (
                <span className="flex items-center gap-2">
                  <LoadingSpinner />
                  Testing...
                </span>
              ) : (
                'Test Connection'
              )}
            </button>

            <div className="flex gap-3">
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
                disabled={!isFormValid || loading}
                className="flex items-center gap-2 px-5 py-2 text-sm bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
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
          </div>
        </form>
      </div>
    </div>
  )
}
