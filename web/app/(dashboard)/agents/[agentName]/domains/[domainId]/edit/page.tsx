'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { ArrowLeft, Save, Globe, Palette } from 'lucide-react'
import { useAgentDomains } from '@/hooks/useAgentDomains'

export default function EditDomainPage() {
  const params = useParams()
  const router = useRouter()
  const agentName = params.agentName as string
  const domainId = params.domainId as string

  const { domains, loading, error, updateDomain } = useAgentDomains({ agentId: agentName })
  const [saving, setSaving] = useState(false)

  const domain = domains.find((d) => d.id === domainId)

  // DNS Settings
  const [dnsSettings, setDnsSettings] = useState({
    subdomain: '',
    domain: '',
    is_custom_domain: true,
  })

  useEffect(() => {
    if (domain) {
      setDnsSettings({
        subdomain: domain.subdomain || '',
        domain: domain.domain || '',
        is_custom_domain: domain.is_custom_domain,
      })
    }
  }, [domain])

  const handleSave = async () => {
    try {
      setSaving(true)
      // Ensure subdomain is explicitly set (empty string if blank)
      const updateData = {
        ...dnsSettings,
        subdomain: dnsSettings.subdomain || '',
      }
      await updateDomain(domainId, updateData)
      toast.success('DNS settings saved successfully!')
      router.push(`/agents/${agentName}/domains`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save DNS settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-amber-50 via-yellow-50/30 to-amber-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading domain...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-yellow-50/30 to-amber-50 p-4 md:p-8">
        <div className="max-w-3xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
            {error}
          </div>
        </div>
      </div>
    )
  }

  if (!domain) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-amber-50 via-yellow-50/30 to-amber-50 p-4 md:p-8">
        <div className="max-w-3xl mx-auto">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800">
            Domain not found
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-yellow-50/30 to-amber-50 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={() => router.push(`/agents/${agentName}/domains`)}
          className="flex items-center gap-2 text-amber-600 hover:text-amber-700 mb-6 transition-colors text-sm font-medium"
        >
          <ArrowLeft size={16} />
          Back to Domains
        </button>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Edit Domain Settings</h1>
            <p className="text-gray-600 mt-1 text-sm">
              Configure DNS settings for {domain.domain}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => router.push(`/agents/${agentName}/chat-customization`)}
              className="px-4 py-2 text-sm bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-white hover:border-amber-300 transition-colors shadow-sm font-medium"
            >
              <Palette className="w-4 h-4 mr-2 inline" />
              Chat Customization
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 text-sm bg-gradient-to-r from-amber-500 to-yellow-500 text-white rounded-lg hover:from-amber-600 hover:to-yellow-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm font-medium"
            >
              <Save className="w-4 h-4 mr-2 inline" />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* DNS Settings */}
        <div className="space-y-5">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Globe className="w-4 h-4 text-amber-600" />
              Domain Configuration
            </h2>
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-2">
                  Domain Type
                </label>
                <div className="space-y-2">
                  <label className="flex items-start gap-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-amber-200 hover:bg-amber-50/50 transition-colors">
                    <input
                      type="radio"
                      checked={dnsSettings.is_custom_domain}
                      onChange={() => setDnsSettings({ ...dnsSettings, is_custom_domain: true })}
                      className="mt-0.5 w-4 h-4 text-amber-600 focus:ring-amber-500"
                    />
                    <div className="flex-1">
                      <span className="font-medium text-gray-900 block mb-0.5 text-sm">
                        Custom Domain
                      </span>
                      <span className="text-xs text-gray-600">
                        Use your own domain (e.g., chat.yourdomain.com)
                      </span>
                    </div>
                  </label>
                  <label className="flex items-start gap-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-amber-200 hover:bg-amber-50/50 transition-colors">
                    <input
                      type="radio"
                      checked={!dnsSettings.is_custom_domain}
                      onChange={() => setDnsSettings({ ...dnsSettings, is_custom_domain: false })}
                      className="mt-0.5 w-4 h-4 text-amber-600 focus:ring-amber-500"
                    />
                    <div className="flex-1">
                      <span className="font-medium text-gray-900 block mb-0.5 text-sm">
                        Platform Subdomain
                      </span>
                      <span className="text-xs text-gray-600">
                        Use a subdomain on our platform
                      </span>
                    </div>
                  </label>
                </div>
              </div>

              {dnsSettings.is_custom_domain ? (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Domain Name *
                    </label>
                    <input
                      type="text"
                      value={dnsSettings.domain}
                      onChange={(e) => setDnsSettings({ ...dnsSettings, domain: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      placeholder="yourdomain.com"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter your root domain (e.g., yourdomain.com)
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-2">
                      Platform Subdomain *
                    </label>
                    <input
                      type="text"
                      value={dnsSettings.subdomain}
                      onChange={(e) => setDnsSettings({ ...dnsSettings, subdomain: e.target.value })}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      placeholder="myagent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Required: A platform subdomain is always needed for fallback access and DNS mapping (e.g., myagent.synkora.ai)
                    </p>
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    Subdomain *
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={dnsSettings.subdomain}
                      onChange={(e) => setDnsSettings({ ...dnsSettings, subdomain: e.target.value })}
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      placeholder="yourname"
                    />
                    <span className="text-gray-600 text-sm">.platform.com</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Choose a unique subdomain for your agent
                  </p>
                </div>
              )}

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mt-4">
                <h3 className="font-medium text-amber-900 text-xs mb-2">Current Domain</h3>
                <p className="text-amber-800 text-sm font-mono">
                  {domain?.subdomain ? `${domain.subdomain}.${domain.domain}` : domain?.domain}
                </p>
                {domain?.is_verified ? (
                  <p className="text-green-600 text-xs mt-2 flex items-center gap-1">
                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                    Verified
                  </p>
                ) : (
                  <p className="text-amber-600 text-xs mt-2 flex items-center gap-1">
                    <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                    Pending Verification
                  </p>
                )}
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <h3 className="font-medium text-amber-900 text-sm mb-2 flex items-center gap-1.5">
                  <span className="text-amber-600">⚠️</span>
                  Important
                </h3>
                <ul className="text-amber-800 text-xs space-y-1.5">
                  <li className="flex items-start gap-2">
                    <span className="text-amber-600 mt-0.5">•</span>
                    <span>Changing domain settings will require DNS reconfiguration</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-amber-600 mt-0.5">•</span>
                    <span>You will need to verify the new domain before it becomes active</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-amber-600 mt-0.5">•</span>
                    <span>The old domain will remain active until the new one is verified</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
