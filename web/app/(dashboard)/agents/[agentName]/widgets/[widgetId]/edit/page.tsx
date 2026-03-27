'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { ArrowLeft } from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface WidgetFormData {
  widget_name: string
  allowed_domains: string[]
  theme_config: {
    primaryColor: string
    position: string
    buttonText: string
  }
  rate_limit: number
  is_active: boolean
}

export default function EditWidgetPage() {
  const params = useParams()
  const router = useRouter()
  const agentName = params.agentName as string
  const widgetId = params.widgetId as string

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<WidgetFormData>({
    widget_name: '',
    allowed_domains: [],
    theme_config: {
      primaryColor: '#3B82F6',
      position: 'bottom-right',
      buttonText: 'Chat with us'
    },
    rate_limit: 100,
    is_active: true
  })
  const [domainInput, setDomainInput] = useState('')

  useEffect(() => {
    fetchWidget()
  }, [widgetId])

  const fetchWidget = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getWidget(widgetId)
      setFormData({
        widget_name: data.widget_name,
        allowed_domains: data.allowed_domains || [],
        theme_config: data.theme_config || {
          primaryColor: '#3B82F6',
          position: 'bottom-right',
          buttonText: 'Chat with us'
        },
        rate_limit: data.rate_limit || 100,
        is_active: data.is_active
      })
    } catch (error) {
      toast.error('Failed to load widget')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.widget_name.trim()) {
      toast.error('Widget name is required')
      return
    }

    try {
      setSaving(true)
      await apiClient.updateWidget(widgetId, formData)
      toast.success('Widget updated successfully!')
      router.push(`/agents/${agentName}/widgets`)
    } catch (error) {
      toast.error('Failed to update widget')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const addDomain = () => {
    if (domainInput.trim() && !formData.allowed_domains.includes(domainInput.trim())) {
      setFormData({
        ...formData,
        allowed_domains: [...formData.allowed_domains, domainInput.trim()]
      })
      setDomainInput('')
    }
  }

  const removeDomain = (domain: string) => {
    setFormData({
      ...formData,
      allowed_domains: formData.allowed_domains.filter(d => d !== domain)
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading widget...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
      <button
        onClick={() => router.push(`/agents/${agentName}/widgets`)}
        className="flex items-center text-red-600 hover:text-red-700 mb-6 font-medium"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Widgets
      </button>

      <h1 className="text-xl sm:text-3xl font-bold mb-8">Edit Widget</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Widget Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Widget Name *
          </label>
          <input
            type="text"
            value={formData.widget_name}
            onChange={(e) => setFormData({ ...formData, widget_name: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            placeholder="My Website Widget"
            required
          />
        </div>

        {/* Allowed Domains */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Allowed Domains
          </label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addDomain())}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="example.com"
            />
            <button
              type="button"
              onClick={addDomain}
              className="px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 shadow-sm font-medium"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.allowed_domains.map((domain) => (
              <span
                key={domain}
                className="inline-flex items-center gap-2 px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm"
              >
                {domain}
                <button
                  type="button"
                  onClick={() => removeDomain(domain)}
                  className="text-red-600 hover:text-red-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <p className="text-sm text-gray-500 mt-2">
            Leave empty to allow all domains (not recommended for production)
          </p>
        </div>

        {/* Theme Configuration */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Theme Configuration</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Primary Color
            </label>
            <input
              type="color"
              value={formData.theme_config.primaryColor}
              onChange={(e) => setFormData({
                ...formData,
                theme_config: { ...formData.theme_config, primaryColor: e.target.value }
              })}
              className="h-10 w-20 border border-gray-300 rounded cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Position
            </label>
            <select
              value={formData.theme_config.position}
              onChange={(e) => setFormData({
                ...formData,
                theme_config: { ...formData.theme_config, position: e.target.value }
              })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            >
              <option value="bottom-right">Bottom Right</option>
              <option value="bottom-left">Bottom Left</option>
              <option value="top-right">Top Right</option>
              <option value="top-left">Top Left</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Button Text
            </label>
            <input
              type="text"
              value={formData.theme_config.buttonText}
              onChange={(e) => setFormData({
                ...formData,
                theme_config: { ...formData.theme_config, buttonText: e.target.value }
              })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              placeholder="Chat with us"
            />
          </div>
        </div>

        {/* Rate Limit */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Rate Limit (requests per hour)
          </label>
          <input
            type="number"
            value={formData.rate_limit}
            onChange={(e) => setFormData({ ...formData, rate_limit: parseInt(e.target.value) })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            min="1"
            max="1000"
          />
        </div>

        {/* Active Status */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_active"
            checked={formData.is_active}
            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
            className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
          />
          <label htmlFor="is_active" className="ml-2 text-sm font-medium text-gray-700">
            Widget is active
          </label>
        </div>

        {/* Submit Button */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 disabled:opacity-50 shadow-sm font-medium"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            onClick={() => router.push(`/agents/${agentName}/widgets`)}
            className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
          >
            Cancel
          </button>
        </div>
      </form>
      </div>
    </div>
  )
}
