'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { Smartphone, ArrowLeft, Info, Database, Settings, Globe } from 'lucide-react'
import { apiClient } from '@/lib/api/client'

const STORE_TYPES = [
  {
    value: 'google_play',
    label: 'Google Play Store',
    icon: '🤖',
    description: 'Android app reviews',
    appIdPlaceholder: 'com.example.app',
    appIdLabel: 'Package Name',
    appIdHelp: 'e.g., com.whatsapp',
  },
  {
    value: 'apple_app_store',
    label: 'Apple App Store',
    icon: '🍎',
    description: 'iOS app reviews',
    appIdPlaceholder: '123456789',
    appIdLabel: 'App ID',
    appIdHelp: 'Numeric ID from App Store URL',
  },
]

const SYNC_FREQUENCIES = [
  { value: 'hourly', label: 'Hourly', description: 'Check for new reviews every hour' },
  { value: 'daily', label: 'Daily', description: 'Check once per day' },
  { value: 'weekly', label: 'Weekly', description: 'Check once per week' },
  { value: 'manual', label: 'Manual', description: 'Only sync when triggered manually' },
]

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ar', label: 'Arabic' },
  { value: 'hi', label: 'Hindi' },
  { value: 'ru', label: 'Russian' },
]

const COUNTRIES = [
  { value: 'us', label: 'United States' },
  { value: 'gb', label: 'United Kingdom' },
  { value: 'ca', label: 'Canada' },
  { value: 'au', label: 'Australia' },
  { value: 'de', label: 'Germany' },
  { value: 'fr', label: 'France' },
  { value: 'es', label: 'Spain' },
  { value: 'it', label: 'Italy' },
  { value: 'jp', label: 'Japan' },
  { value: 'kr', label: 'South Korea' },
  { value: 'cn', label: 'China' },
  { value: 'in', label: 'India' },
  { value: 'br', label: 'Brazil' },
  { value: 'mx', label: 'Mexico' },
]

export default function CreateAppStoreSourcePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState(1)
  const [knowledgeBases, setKnowledgeBases] = useState<any[]>([])
  const [loadingKBs, setLoadingKBs] = useState(false)

  const [formData, setFormData] = useState({
    store_type: 'google_play',
    app_id: '',
    app_name: '',
    knowledge_base_id: '',
    sync_frequency: 'daily',
    min_rating: 1,
    languages: ['en'],
    countries: ['us'],
  })

  const selectedStore = STORE_TYPES.find(s => s.value === formData.store_type)

  // Load knowledge bases when reaching step 2
  const loadKnowledgeBases = async () => {
    if (knowledgeBases.length > 0) return
    
    setLoadingKBs(true)
    try {
      const data = await apiClient.getKnowledgeBases()
      setKnowledgeBases(data)
    } catch (err) {
      console.error('Failed to load knowledge bases:', err)
      toast.error('Failed to load knowledge bases')
    } finally {
      setLoadingKBs(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const payload = {
        store_type: formData.store_type,
        app_id: formData.app_id,
        app_name: formData.app_name,
        knowledge_base_id: formData.knowledge_base_id,
        sync_frequency: formData.sync_frequency,
        min_rating: formData.min_rating,
        languages: formData.languages,
        countries: formData.countries,
      }

      await apiClient.createAppStoreSource(payload)
      toast.success('App source created successfully!')
      router.push('/app-store-reviews')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      toast.error(`Failed to create app source: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const toggleLanguage = (lang: string) => {
    setFormData(prev => ({
      ...prev,
      languages: prev.languages.includes(lang)
        ? prev.languages.filter(l => l !== lang)
        : [...prev.languages, lang],
    }))
  }

  const toggleCountry = (country: string) => {
    setFormData(prev => ({
      ...prev,
      countries: prev.countries.includes(country)
        ? prev.countries.filter(c => c !== country)
        : [...prev.countries, country],
    }))
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/app-store-reviews"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to App Store Reviews
          </Link>
          
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-teal-600 rounded-lg shadow-sm">
              <Smartphone className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Add App Source
              </h1>
              <p className="text-gray-600 mt-1">
                Connect an app to collect and analyze reviews
              </p>
            </div>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="mb-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            {[
              { num: 1, label: 'App Info', icon: Info },
              { num: 2, label: 'Knowledge Base', icon: Database },
              { num: 3, label: 'Sync Settings', icon: Settings },
              { num: 4, label: 'Filters', icon: Globe },
            ].map((step, idx) => (
              <div key={step.num} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center font-semibold transition-all ${
                      currentStep >= step.num
                        ? 'bg-teal-600 text-white shadow-sm'
                        : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    <step.icon className="w-5 h-5" />
                  </div>
                  <span className={`text-sm mt-2 font-medium ${currentStep >= step.num ? 'text-teal-600' : 'text-gray-400'}`}>
                    {step.label}
                  </span>
                </div>
                {idx < 3 && (
                  <div className={`h-1 flex-1 mx-4 rounded-full ${currentStep > step.num ? 'bg-teal-600' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg">
            <p className="text-red-700 font-medium">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Step 1: App Information */}
          {currentStep === 1 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
              <div className="flex items-center gap-3 mb-6">
                <Info className="w-6 h-6 text-teal-600" />
                <h2 className="text-xl font-semibold text-gray-900">App Information</h2>
              </div>
              
              <div className="space-y-6">
                {/* Store Type Selection */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Select Store <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {STORE_TYPES.map((store) => (
                      <button
                        key={store.value}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, store_type: store.value, app_id: '' }))}
                        className={`p-4 rounded-lg border-2 transition-all text-left ${
                          formData.store_type === store.value
                            ? 'border-teal-500 bg-teal-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-3xl mb-2">{store.icon}</div>
                        <div className="font-semibold text-gray-900">{store.label}</div>
                        <div className="text-xs text-gray-500 mt-1">{store.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* App ID */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    {selectedStore?.appIdLabel} <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.app_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, app_id: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    placeholder={selectedStore?.appIdPlaceholder}
                  />
                  <p className="text-sm text-gray-500 mt-2">{selectedStore?.appIdHelp}</p>
                </div>

                {/* App Name */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    App Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.app_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, app_name: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                    placeholder="e.g., WhatsApp Messenger"
                  />
                </div>
              </div>

              <div className="flex justify-end mt-8">
                <button
                  type="button"
                  onClick={() => {
                    setCurrentStep(2)
                    loadKnowledgeBases()
                  }}
                  disabled={!formData.app_id || !formData.app_name}
                  className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Knowledge Base */}
          {currentStep === 2 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
              <div className="flex items-center gap-3 mb-6">
                <Database className="w-6 h-6 text-teal-600" />
                <h2 className="text-xl font-semibold text-gray-900">Knowledge Base</h2>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Select Knowledge Base <span className="text-red-500">*</span>
                  </label>
                  <p className="text-sm text-gray-600 mb-4">
                    Reviews will be synced to this knowledge base for AI analysis and search
                  </p>

                  {loadingKBs ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : knowledgeBases.length === 0 ? (
                    <div className="p-6 bg-gray-50 border border-gray-200 rounded-lg text-center">
                      <Database className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-600 mb-4">No knowledge bases found</p>
                      <Link
                        href="/knowledge-bases/create"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
                      >
                        Create Knowledge Base
                      </Link>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {knowledgeBases.map((kb) => (
                        <button
                          key={kb.id}
                          type="button"
                          onClick={() => setFormData(prev => ({ ...prev, knowledge_base_id: kb.id }))}
                          className={`p-4 rounded-lg border-2 transition-all text-left ${
                            formData.knowledge_base_id === kb.id
                              ? 'border-teal-500 bg-teal-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="font-semibold text-gray-900">{kb.name}</div>
                              {kb.description && (
                                <div className="text-sm text-gray-500 mt-1">{kb.description}</div>
                              )}
                              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                                <span>Provider: {kb.vector_db_provider}</span>
                                <span>Embedding: {kb.embedding_provider}</span>
                              </div>
                            </div>
                            {formData.knowledge_base_id === kb.id && (
                              <div className="w-6 h-6 bg-teal-600 rounded-full flex items-center justify-center">
                                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              </div>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-between mt-8">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  disabled={!formData.knowledge_base_id}
                  className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Sync Settings */}
          {currentStep === 3 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
              <div className="flex items-center gap-3 mb-6">
                <Settings className="w-6 h-6 text-teal-600" />
                <h2 className="text-xl font-semibold text-gray-900">Sync Settings</h2>
              </div>

              <div className="space-y-6">
                {/* Sync Frequency */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Sync Frequency <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {SYNC_FREQUENCIES.map((freq) => (
                      <button
                        key={freq.value}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, sync_frequency: freq.value }))}
                        className={`p-4 rounded-lg border-2 transition-all text-left ${
                          formData.sync_frequency === freq.value
                            ? 'border-teal-500 bg-teal-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="font-semibold text-gray-900">{freq.label}</div>
                        <div className="text-xs text-gray-500 mt-1">{freq.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Minimum Rating Filter */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">
                    Minimum Rating Filter
                  </label>
                  <select
                    value={formData.min_rating}
                    onChange={(e) => setFormData(prev => ({ ...prev, min_rating: parseInt(e.target.value) }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                  >
                    <option value={1}>1 Star and above (All reviews)</option>
                    <option value={2}>2 Stars and above</option>
                    <option value={3}>3 Stars and above</option>
                    <option value={4}>4 Stars and above</option>
                    <option value={5}>5 Stars only</option>
                  </select>
                  <p className="text-sm text-gray-500 mt-2">
                    Only collect reviews with this rating or higher
                  </p>
                </div>
              </div>

              <div className="flex justify-between mt-8">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentStep(4)}
                  className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Language & Country Filters */}
          {currentStep === 4 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
              <div className="flex items-center gap-3 mb-6">
                <Globe className="w-6 h-6 text-teal-600" />
                <h2 className="text-xl font-semibold text-gray-900">Language & Country Filters</h2>
              </div>

              <div className="space-y-6">
                {/* Languages */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Languages <span className="text-red-500">*</span>
                  </label>
                  <p className="text-sm text-gray-600 mb-3">
                    Select languages to collect reviews in (at least one required)
                  </p>
                  <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
                    {LANGUAGES.map((lang) => (
                      <button
                        key={lang.value}
                        type="button"
                        onClick={() => toggleLanguage(lang.value)}
                        className={`px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                          formData.languages.includes(lang.value)
                            ? 'border-teal-500 bg-teal-50 text-teal-700'
                            : 'border-gray-200 hover:border-gray-300 text-gray-700'
                        }`}
                      >
                        {lang.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Countries */}
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    Countries <span className="text-red-500">*</span>
                  </label>
                  <p className="text-sm text-gray-600 mb-3">
                    Select countries to collect reviews from (at least one required)
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {COUNTRIES.map((country) => (
                      <button
                        key={country.value}
                        type="button"
                        onClick={() => toggleCountry(country.value)}
                        className={`px-3 py-2 rounded-lg border-2 transition-all text-sm ${
                          formData.countries.includes(country.value)
                            ? 'border-teal-500 bg-teal-50 text-teal-700'
                            : 'border-gray-200 hover:border-gray-300 text-gray-700'
                        }`}
                      >
                        {country.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-4 bg-teal-50 border border-teal-200 rounded-lg">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-teal-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-teal-900">Review Collection</p>
                      <p className="text-xs text-teal-700 mt-1">
                        Reviews will be collected based on your selected languages and countries. 
                        The first sync will happen immediately after creation.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between mt-8">
                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading || formData.languages.length === 0 || formData.countries.length === 0}
                  className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {loading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Smartphone className="w-5 h-5" />
                      Create App Source
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
