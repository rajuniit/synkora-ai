'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  BookOpen,
  ArrowLeft,
  Settings,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertCircle,
  Loader2,
  Save
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

// Provider configurations (kept for advanced options)
const VECTOR_DB_PROVIDERS = [
  {
    value: 'QDRANT',
    label: 'Qdrant',
    description: 'High-performance vector search engine',
    icon: '🔍',
    fields: ['url', 'collection_name', 'api_key'],
    defaults: { url: 'http://localhost:6333' },
  },
  {
    value: 'PINECONE',
    label: 'Pinecone',
    description: 'Managed vector database',
    icon: '🌲',
    fields: ['api_key', 'environment', 'index_name'],
    defaults: { environment: 'us-east-1-aws' },
  },
  {
    value: 'WEAVIATE',
    label: 'Weaviate',
    description: 'Open-source vector database',
    icon: '🔷',
    fields: ['url', 'api_key'],
    defaults: { url: 'http://localhost:8080' },
  },
  {
    value: 'CHROMA',
    label: 'Chroma',
    description: 'AI-native embedding database',
    icon: '🎨',
    fields: ['url', 'collection_name'],
    defaults: { url: 'http://localhost:8000' },
  },
  {
    value: 'MILVUS',
    label: 'Milvus',
    description: 'Open-source vector database',
    icon: '⚡',
    fields: ['url', 'collection_name'],
    defaults: { url: 'http://localhost:19530' },
  },
]

const EMBEDDING_PROVIDERS = [
  {
    value: 'SENTENCE_TRANSFORMERS',
    label: 'Sentence Transformers',
    icon: '🤖',
    description: 'Open-source, runs locally',
    models: [
      { value: 'all-MiniLM-L6-v2', label: 'all-MiniLM-L6-v2', dimension: 384 },
      { value: 'all-mpnet-base-v2', label: 'all-mpnet-base-v2', dimension: 768 },
    ],
  },
  {
    value: 'OPENAI',
    label: 'OpenAI',
    icon: '🔮',
    description: 'Powerful, requires API key',
    models: [
      { value: 'text-embedding-ada-002', label: 'text-embedding-ada-002', dimension: 1536 },
      { value: 'text-embedding-3-small', label: 'text-embedding-3-small', dimension: 1536 },
    ],
  },
  {
    value: 'COHERE',
    label: 'Cohere',
    icon: '🌐',
    description: 'High-quality embeddings',
    models: [
      { value: 'embed-english-v3.0', label: 'embed-english-v3.0', dimension: 1024 },
      { value: 'embed-multilingual-v3.0', label: 'embed-multilingual-v3.0', dimension: 1024 },
    ],
  },
  {
    value: 'LITELLM',
    label: 'LiteLLM',
    icon: '⚡',
    description: 'Universal API - supports 100+ providers',
    models: [
      { value: 'openai/text-embedding-ada-002', label: 'OpenAI - text-embedding-ada-002', dimension: 1536 },
      { value: 'openai/text-embedding-3-small', label: 'OpenAI - text-embedding-3-small', dimension: 1536 },
      { value: 'openai/text-embedding-3-large', label: 'OpenAI - text-embedding-3-large', dimension: 3072 },
      { value: 'cohere/embed-english-v3.0', label: 'Cohere - embed-english-v3.0', dimension: 1024 },
      { value: 'cohere/embed-multilingual-v3.0', label: 'Cohere - embed-multilingual-v3.0', dimension: 1024 },
    ],
  },
]

const CHUNKING_STRATEGIES = [
  { value: 'SEMANTIC', label: 'Automatic (Recommended)', description: 'Best for most documents' },
  { value: 'DOCUMENT', label: 'Document-aware', description: 'Keeps sections together' },
  { value: 'CODE', label: 'Code-optimized', description: 'Best for source code' },
  { value: 'FIXED', label: 'Fixed size', description: 'Traditional chunking' },
]

export default function EditKnowledgeBasePage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState(1)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    vector_db_provider: 'QDRANT',
    vector_db_config: {} as Record<string, string>,
    embedding_config: {
      provider: 'SENTENCE_TRANSFORMERS',
      model_name: 'all-MiniLM-L6-v2',
      dimension: 384,
      api_key: '',
      api_base: '',
    },
    chunking_strategy: 'SEMANTIC',
    chunk_size: 1500,
    chunk_overlap: 150,
    min_chunk_size: 500,
    max_chunk_size: 3000,
    chunking_config: {} as Record<string, any>,
  })

  const selectedVectorDB = VECTOR_DB_PROVIDERS.find(p => p.value === formData.vector_db_provider)
  const selectedEmbedding = EMBEDDING_PROVIDERS.find(p => p.value === formData.embedding_config.provider)

  useEffect(() => {
    fetchKnowledgeBase()
  }, [id])

  const fetchKnowledgeBase = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getKnowledgeBase(id)
      setFormData({
        name: data.name || '',
        description: data.description || '',
        vector_db_provider: data.vector_db_provider || 'QDRANT',
        vector_db_config: data.vector_db_config || {},
        embedding_config: {
          provider: data.embedding_provider || 'SENTENCE_TRANSFORMERS',
          model_name: data.embedding_model || 'all-MiniLM-L6-v2',
          dimension: data.embedding_config?.dimension || 384,
          api_key: '',
          api_base: data.embedding_config?.api_base || '',
        },
        chunking_strategy: data.chunking_strategy || 'SEMANTIC',
        chunk_size: data.chunk_size || 1500,
        chunk_overlap: data.chunk_overlap || 150,
        min_chunk_size: data.min_chunk_size || 500,
        max_chunk_size: data.max_chunk_size || 3000,
        chunking_config: data.chunking_config || {},
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        vector_db_provider: formData.vector_db_provider,
        vector_db_config: formData.vector_db_config,
        embedding_provider: formData.embedding_config.provider,
        embedding_model: formData.embedding_config.model_name,
        embedding_config: {
          ...(formData.embedding_config.api_key && { api_key: formData.embedding_config.api_key }),
          ...(formData.embedding_config.api_base && { api_base: formData.embedding_config.api_base }),
          dimension: formData.embedding_config.dimension,
        },
        chunking_strategy: formData.chunking_strategy,
        chunk_size: formData.chunk_size,
        chunk_overlap: formData.chunk_overlap,
        min_chunk_size: formData.min_chunk_size,
        max_chunk_size: formData.max_chunk_size,
        chunking_config: formData.chunking_config,
      }

      await apiClient.updateKnowledgeBase(id, payload)
      toast.success('Knowledge base updated successfully!')
      router.push(`/knowledge-bases/${id}`)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      toast.error(`Failed to update: ${errorMessage}`)
    } finally {
      setSaving(false)
    }
  }

  const updateVectorDBConfig = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      vector_db_config: { ...prev.vector_db_config, [field]: value },
    }))
  }

  const handleProviderChange = (provider: string) => {
    const selected = VECTOR_DB_PROVIDERS.find(p => p.value === provider)
    if (provider !== formData.vector_db_provider) {
      setFormData(prev => ({
        ...prev,
        vector_db_provider: provider,
        vector_db_config: selected?.defaults || {},
      }))
    }
  }

  const handleEmbeddingProviderChange = (provider: string) => {
    const selected = EMBEDDING_PROVIDERS.find(p => p.value === provider)
    const firstModel = selected?.models[0]
    setFormData(prev => ({
      ...prev,
      embedding_config: {
        provider,
        model_name: firstModel?.value || '',
        dimension: firstModel?.dimension || 384,
        api_key: '',
        api_base: '',
      },
    }))
  }

  const handleModelChange = (modelValue: string) => {
    const model = selectedEmbedding?.models.find(m => m.value === modelValue)
    setFormData(prev => ({
      ...prev,
      embedding_config: {
        ...prev.embedding_config,
        model_name: modelValue,
        dimension: model?.dimension || prev.embedding_config.dimension,
      },
    }))
  }

  const updateEmbeddingConfig = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      embedding_config: { ...prev.embedding_config, [field]: value },
    }))
  }

  const steps = [
    { num: 1, label: 'Edit', description: 'Update details' },
    { num: 2, label: 'Review', description: 'Save changes' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-red-50 via-white to-red-50/30">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading knowledge base...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-white to-red-50/30">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/knowledge-bases/${id}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Knowledge Base
          </Link>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Edit Knowledge Base</h1>
              <p className="text-gray-600 mt-1">
                Update the settings for your knowledge base
              </p>
            </div>
            <div className="text-sm text-gray-500">
              Step {currentStep} of {steps.length}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center gap-2">
            {steps.map((step, idx) => (
              <div key={step.num} className="flex items-center flex-1">
                <div className="flex items-center gap-3 flex-1">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                      currentStep >= step.num
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {currentStep > step.num ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      step.num
                    )}
                  </div>
                  <div className="hidden sm:block">
                    <p className={`text-sm font-medium ${currentStep >= step.num ? 'text-gray-900' : 'text-gray-500'}`}>
                      {step.label}
                    </p>
                    <p className="text-xs text-gray-500">{step.description}</p>
                  </div>
                </div>
                {idx < steps.length - 1 && (
                  <div className={`h-1 flex-1 mx-4 rounded-full ${currentStep > step.num ? 'bg-red-500' : 'bg-gray-200'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Step 1: Edit Name and Description */}
          {currentStep === 1 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2.5 bg-red-100 rounded-xl">
                  <BookOpen className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Basic Information</h2>
                  <p className="text-sm text-gray-500">Update the name and description</p>
                </div>
              </div>

              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    placeholder="e.g., Product Documentation, Support Articles"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description <span className="text-gray-400">(optional)</span>
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                    placeholder="Briefly describe what kind of information is stored here..."
                  />
                </div>
              </div>

              <div className="flex justify-end mt-8">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  disabled={!formData.name}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Review & Save */}
          {currentStep === 2 && (
            <div className="space-y-6">
              {/* Summary Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2.5 bg-red-100 rounded-xl">
                    <CheckCircle className="w-5 h-5 text-red-600" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Review Changes</h2>
                    <p className="text-sm text-gray-500">Confirm your updates before saving</p>
                  </div>
                </div>

                {/* Summary */}
                <div className="bg-gray-50 rounded-xl p-5">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-white rounded-xl shadow-sm">
                      <BookOpen className="w-8 h-8 text-red-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900">{formData.name}</h3>
                      <p className="text-gray-600 mt-1">
                        {formData.description || 'No description provided'}
                      </p>
                      <div className="flex flex-wrap gap-2 mt-3">
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                          {formData.vector_db_provider}
                        </span>
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                          {formData.embedding_config.model_name}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Advanced Options (Collapsible) */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Settings className="w-5 h-5 text-gray-500" />
                    <div className="text-left">
                      <p className="font-medium text-gray-900">Advanced Settings</p>
                      <p className="text-sm text-gray-500">Configure storage and processing options</p>
                    </div>
                  </div>
                  {showAdvanced ? (
                    <ChevronUp className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {showAdvanced && (
                  <div className="px-6 pb-6 border-t border-gray-100">
                    {/* Vector Database Section */}
                    <div className="pt-5 pb-5 border-b border-gray-100">
                      <h3 className="font-medium text-gray-900 mb-4">Vector Database</h3>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                        {VECTOR_DB_PROVIDERS.map((provider) => (
                          <button
                            key={provider.value}
                            type="button"
                            onClick={() => handleProviderChange(provider.value)}
                            className={`p-3 rounded-xl border-2 transition-all text-left ${
                              formData.vector_db_provider === provider.value
                                ? 'border-red-500 bg-red-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="text-xl mb-1">{provider.icon}</div>
                            <div className="font-medium text-sm text-gray-900">{provider.label}</div>
                          </button>
                        ))}
                      </div>

                      {/* Dynamic Vector DB Fields */}
                      {selectedVectorDB && (
                        <div className="space-y-3 mt-4">
                          {selectedVectorDB.fields.includes('url') && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Database URL
                              </label>
                              <input
                                type="text"
                                value={formData.vector_db_config.url || ''}
                                onChange={(e) => updateVectorDBConfig('url', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder={selectedVectorDB.defaults?.url || 'http://localhost:6333'}
                              />
                            </div>
                          )}
                          {selectedVectorDB.fields.includes('api_key') && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                API Key {selectedVectorDB.value === 'PINECONE' && <span className="text-red-500">*</span>}
                              </label>
                              <input
                                type="password"
                                value={formData.vector_db_config.api_key || ''}
                                onChange={(e) => updateVectorDBConfig('api_key', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder="Enter API key (leave blank to keep existing)"
                              />
                            </div>
                          )}
                          {selectedVectorDB.fields.includes('environment') && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Environment
                              </label>
                              <input
                                type="text"
                                value={formData.vector_db_config.environment || ''}
                                onChange={(e) => updateVectorDBConfig('environment', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder="e.g., us-east-1-aws"
                              />
                            </div>
                          )}
                          {selectedVectorDB.fields.includes('collection_name') && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Collection Name
                              </label>
                              <input
                                type="text"
                                value={formData.vector_db_config.collection_name || ''}
                                onChange={(e) => updateVectorDBConfig('collection_name', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder="Auto-generated if not provided"
                              />
                            </div>
                          )}
                          {selectedVectorDB.fields.includes('index_name') && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Index Name
                              </label>
                              <input
                                type="text"
                                value={formData.vector_db_config.index_name || ''}
                                onChange={(e) => updateVectorDBConfig('index_name', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder="Enter index name"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Embedding Model Section */}
                    <div className="pt-5 pb-5 border-b border-gray-100">
                      <h3 className="font-medium text-gray-900 mb-4">Embedding Model</h3>
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        {EMBEDDING_PROVIDERS.map((provider) => (
                          <button
                            key={provider.value}
                            type="button"
                            onClick={() => handleEmbeddingProviderChange(provider.value)}
                            className={`p-3 rounded-xl border-2 transition-all text-left ${
                              formData.embedding_config.provider === provider.value
                                ? 'border-red-500 bg-red-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="text-xl mb-1">{provider.icon}</div>
                            <div className="font-medium text-sm text-gray-900">{provider.label}</div>
                            <div className="text-xs text-gray-500">{provider.description}</div>
                          </button>
                        ))}
                      </div>

                      {selectedEmbedding && (
                        <div className="space-y-3">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
                            <select
                              value={formData.embedding_config.model_name}
                              onChange={(e) => handleModelChange(e.target.value)}
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                            >
                              {selectedEmbedding.models.map((model) => (
                                <option key={model.value} value={model.value}>
                                  {model.label} ({model.dimension}d)
                                </option>
                              ))}
                            </select>
                          </div>

                          {(formData.embedding_config.provider === 'OPENAI' ||
                            formData.embedding_config.provider === 'COHERE' ||
                            formData.embedding_config.provider === 'LITELLM') && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                API Key
                              </label>
                              <input
                                type="password"
                                value={formData.embedding_config.api_key}
                                onChange={(e) => updateEmbeddingConfig('api_key', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder="Enter API key (leave blank to keep existing)"
                              />
                            </div>
                          )}

                          {formData.embedding_config.provider === 'LITELLM' && (
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Custom Base URL (Optional)
                              </label>
                              <input
                                type="text"
                                value={formData.embedding_config.api_base}
                                onChange={(e) => updateEmbeddingConfig('api_base', e.target.value)}
                                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                placeholder="e.g., https://api.openai.com/v1"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Chunking Settings Section */}
                    <div className="pt-5">
                      <h3 className="font-medium text-gray-900 mb-4">Text Processing</h3>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Processing Strategy</label>
                          <select
                            value={formData.chunking_strategy}
                            onChange={(e) => {
                              const strategy = e.target.value
                              setFormData(prev => ({
                                ...prev,
                                chunking_strategy: strategy,
                                chunk_size: strategy === 'CODE' ? 2000 : 1500,
                                chunk_overlap: strategy === 'CODE' ? 300 : 150,
                              }))
                            }}
                            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                          >
                            {CHUNKING_STRATEGIES.map((strategy) => (
                              <option key={strategy.value} value={strategy.value}>
                                {strategy.label} - {strategy.description}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Chunk Size</label>
                            <input
                              type="number"
                              min="500"
                              max="3000"
                              value={formData.chunk_size}
                              onChange={(e) => setFormData(prev => ({ ...prev, chunk_size: parseInt(e.target.value) }))}
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Characters per chunk</p>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Overlap</label>
                            <input
                              type="number"
                              min="0"
                              max="500"
                              value={formData.chunk_overlap}
                              onChange={(e) => setFormData(prev => ({ ...prev, chunk_overlap: parseInt(e.target.value) }))}
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">Overlap between chunks</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Navigation Buttons */}
              <div className="flex justify-between">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-5 h-5" />
                      Save Changes
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
