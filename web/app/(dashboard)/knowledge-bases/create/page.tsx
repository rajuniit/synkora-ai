'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  BookOpen,
  ArrowLeft,
  Upload,
  FileText,
  Globe,
  Plus,
  X,
  ChevronDown,
  ChevronUp,
  Settings,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Loader2
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
      { value: 'voyage/voyage-01', label: 'Voyage AI - voyage-01', dimension: 1024 },
      { value: 'voyage/voyage-02', label: 'Voyage AI - voyage-02', dimension: 1024 },
      { value: 'mistral/mistral-embed', label: 'Mistral AI - mistral-embed', dimension: 1024 },
      { value: 'azure/text-embedding-ada-002', label: 'Azure OpenAI - text-embedding-ada-002', dimension: 1536 },
      { value: 'bedrock/amazon.titan-embed-text-v1', label: 'AWS Bedrock - Titan Embed', dimension: 1536 },
      { value: 'vertex_ai/textembedding-gecko@003', label: 'Google Vertex AI - gecko@003', dimension: 768 },
    ],
  },
]

const CHUNKING_STRATEGIES = [
  { value: 'SEMANTIC', label: 'Automatic (Recommended)', description: 'Best for most documents' },
  { value: 'DOCUMENT', label: 'Document-aware', description: 'Keeps sections together' },
  { value: 'CODE', label: 'Code-optimized', description: 'Best for source code' },
  { value: 'FIXED', label: 'Fixed size', description: 'Traditional chunking' },
]

export default function CreateKnowledgeBasePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState(1)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Form data with sensible defaults
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    // Default to Qdrant with local defaults
    vector_db_provider: 'QDRANT',
    vector_db_config: { url: 'http://localhost:6333' } as Record<string, string>,
    // Default to Sentence Transformers (no API key needed)
    embedding_config: {
      provider: 'SENTENCE_TRANSFORMERS',
      model_name: 'all-MiniLM-L6-v2',
      dimension: 384,
      api_key: '',
      api_base: '',
    },
    // Default chunking settings
    chunking_strategy: 'SEMANTIC',
    chunk_size: 1500,
    chunk_overlap: 150,
    min_chunk_size: 500,
    max_chunk_size: 3000,
    chunking_config: {} as Record<string, any>,
  })

  const selectedVectorDB = VECTOR_DB_PROVIDERS.find(p => p.value === formData.vector_db_provider)
  const selectedEmbedding = EMBEDDING_PROVIDERS.find(p => p.value === formData.embedding_config.provider)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
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

      const data = await apiClient.createKnowledgeBase(payload)
      toast.success('Knowledge base created successfully!')
      router.push(`/knowledge-bases/${data.id}`)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      toast.error(`Failed to create knowledge base: ${errorMessage}`)
    } finally {
      setLoading(false)
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
    setFormData(prev => ({
      ...prev,
      vector_db_provider: provider,
      vector_db_config: selected?.defaults || {},
    }))
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
    { num: 1, label: 'Name', description: 'Give it a name' },
    { num: 2, label: 'Review', description: 'Review & create' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-white to-red-50/30">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/knowledge-bases"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Knowledge
          </Link>

          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Create Knowledge Base</h1>
              <p className="text-gray-600 mt-1">
                Set up a place to store information your AI agents can use
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Form */}
          <div className="lg:col-span-2">
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
              {/* Step 1: Name and Description */}
              {currentStep === 1 && (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2.5 bg-red-100 rounded-xl">
                      <BookOpen className="w-5 h-5 text-red-600" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900">Name Your Knowledge Base</h2>
                      <p className="text-sm text-gray-500">Choose a name that describes what information it contains</p>
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
                        placeholder="e.g., Product Documentation, Support Articles, Company Policies"
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
                        placeholder="Briefly describe what kind of information you'll store here..."
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

              {/* Step 2: Review & Create */}
              {currentStep === 2 && (
                <div className="space-y-6">
                  {/* Summary Card */}
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="p-2.5 bg-red-100 rounded-xl">
                        <CheckCircle className="w-5 h-5 text-red-600" />
                      </div>
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900">Review Your Knowledge Base</h2>
                        <p className="text-sm text-gray-500">Make sure everything looks good before creating</p>
                      </div>
                    </div>

                    {/* Summary */}
                    <div className="bg-gray-50 rounded-xl p-5 mb-6">
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
                              Ready to add content
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* What happens next */}
                    <div className="border-t border-gray-100 pt-5">
                      <h4 className="font-medium text-gray-900 mb-3">What happens next?</h4>
                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-xs font-semibold text-red-600">1</span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">Create knowledge base</p>
                            <p className="text-sm text-gray-500">We'll set up your knowledge base with optimal settings</p>
                          </div>
                        </div>
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-xs font-semibold text-red-600">2</span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">Add your content</p>
                            <p className="text-sm text-gray-500">Upload documents, paste text, or add website URLs</p>
                          </div>
                        </div>
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-xs font-semibold text-red-600">3</span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">Connect to agents</p>
                            <p className="text-sm text-gray-500">Your AI agents will use this knowledge to answer questions</p>
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
                          <p className="text-sm text-gray-500">Configure storage and processing options (optional)</p>
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
                                    required={selectedVectorDB.value === 'PINECONE'}
                                    value={formData.vector_db_config.api_key || ''}
                                    onChange={(e) => updateVectorDBConfig('api_key', e.target.value)}
                                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                    placeholder="Enter your API key"
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
                                    API Key <span className="text-red-500">*</span>
                                  </label>
                                  <input
                                    type="password"
                                    required
                                    value={formData.embedding_config.api_key}
                                    onChange={(e) => updateEmbeddingConfig('api_key', e.target.value)}
                                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                                    placeholder="Enter your API key"
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
                                <p className="text-xs text-gray-500 mt-1">Characters per chunk (500-3000)</p>
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
                                <p className="text-xs text-gray-500 mt-1">Overlap between chunks (0-500)</p>
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
                      disabled={loading}
                      className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        <>
                          <Plus className="w-5 h-5" />
                          Create Knowledge Base
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </form>
          </div>

          {/* Sidebar - Illustration & Help */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-6">
              {/* Illustration Card */}
              <div className="bg-gradient-to-br from-red-50 to-red-100/50 rounded-2xl p-6 text-center">
                {/* Illustration */}
                <div className="relative w-40 h-40 mx-auto mb-6">
                  {/* Stacked cards effect */}
                  <div className="absolute top-4 left-4 right-4 h-32 bg-white/60 rounded-xl transform rotate-6 shadow-sm"></div>
                  <div className="absolute top-2 left-2 right-2 h-32 bg-white/80 rounded-xl transform rotate-3 shadow-sm"></div>
                  <div className="absolute inset-0 bg-white rounded-xl shadow-md flex flex-col p-4">
                    <div className="h-2 w-3/4 bg-gray-200 rounded mb-2"></div>
                    <div className="h-2 w-full bg-gray-100 rounded mb-2"></div>
                    <div className="h-2 w-5/6 bg-gray-100 rounded mb-2"></div>
                    <div className="h-2 w-full bg-gray-100 rounded mb-2"></div>
                    <div className="flex-1"></div>
                    <div className="self-end">
                      <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-red-600" />
                      </div>
                    </div>
                  </div>
                </div>

                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Knowledge Base
                </h3>
                <p className="text-sm text-gray-600">
                  Your AI agents will use this knowledge to provide accurate, relevant answers based on your content.
                </p>
              </div>

              {/* Tips Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                <h4 className="font-medium text-gray-900 mb-4">Tips for great results</h4>
                <ul className="space-y-3 text-sm">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-600">Use a descriptive name that reflects the content</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-600">Keep related documents in the same knowledge base</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-600">Add descriptions to help organize multiple knowledge bases</span>
                  </li>
                </ul>
              </div>

              {/* Content Types Card */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
                <h4 className="font-medium text-gray-900 mb-4">Supported content</h4>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Upload className="w-4 h-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Documents</p>
                      <p className="text-xs text-gray-500">PDF, DOCX, TXT, MD, HTML, CSV</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <FileText className="w-4 h-4 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Text</p>
                      <p className="text-xs text-gray-500">Paste text directly</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-100 rounded-lg">
                      <Globe className="w-4 h-4 text-red-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Websites</p>
                      <p className="text-xs text-gray-500">Crawl content from URLs</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
