'use client'

import { useState, useEffect } from 'react'
import { ExternalLink, Info, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  AgentLLMConfig,
  AgentLLMConfigCreate,
  AgentLLMConfigUpdate,
} from '@/types/agent-llm-config'
import { getLLMProviders, getProviderModels, ProviderPreset, ModelPreset } from '@/lib/api/llm-providers'

interface LLMConfigFormProps {
  config?: AgentLLMConfig
  onSubmit: (data: AgentLLMConfigCreate | AgentLLMConfigUpdate) => Promise<void>
  onCancel: () => void
  isSubmitting?: boolean
}

export default function LLMConfigForm({
  config,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: LLMConfigFormProps) {
  const [providers, setProviders] = useState<ProviderPreset[]>([])
  const [models, setModels] = useState<ModelPreset[]>([])
  const [selectedProvider, setSelectedProvider] = useState<ProviderPreset | null>(null)
  const [selectedModel, setSelectedModel] = useState<ModelPreset | null>(null)
  const [loadingProviders, setLoadingProviders] = useState(true)
  const [loadingModels, setLoadingModels] = useState(false)

  const [formData, setFormData] = useState({
    name: config?.name || '',
    provider: config?.provider || '',
    model_name: config?.model_name || '',
    api_key: '',
    api_base: config?.api_base || '',
    temperature: config?.temperature?.toString() || '0.7',
    max_tokens: config?.max_tokens?.toString() || '16384',
    top_p: config?.top_p?.toString() || '1.0',
    enabled: config?.enabled !== undefined ? config.enabled : true,
  })

  const [showApiKey, setShowApiKey] = useState(false)

  // Load providers on mount
  useEffect(() => {
    const loadProviders = async () => {
      try {
        setLoadingProviders(true)
        const data = await getLLMProviders()
        setProviders(data)
        
        // If editing, find the provider and load its models
        if (config?.provider) {
          const provider = data.find((p: ProviderPreset) => p.provider_id === config.provider)
          if (provider) {
            setSelectedProvider(provider)
            await loadModelsForProvider(config.provider)
          }
        }
      } catch (error) {
        console.error('Failed to load providers:', error)
        toast.error('Failed to load LLM providers')
      } finally {
        setLoadingProviders(false)
      }
    }

    loadProviders()
  }, [config])

  // Load models when provider changes
  const loadModelsForProvider = async (providerId: string) => {
    if (!providerId) return

    try {
      setLoadingModels(true)
      const providerModels = await getProviderModels(providerId)
      setModels(providerModels)
      
      // If editing and model exists, select it
      if (config?.model_name) {
        const model = providerModels.find((m: ModelPreset) => m.model_name === config.model_name)
        if (model) {
          setSelectedModel(model)
        }
      }
    } catch (error) {
      console.error('Failed to load models:', error)
      toast.error('Failed to load models for provider')
    } finally {
      setLoadingModels(false)
    }
  }

  // Handle provider change
  const handleProviderChange = (providerId: string) => {
    const provider = providers.find((p: ProviderPreset) => p.provider_id === providerId)
    setSelectedProvider(provider || null)
    setFormData(prev => ({
      ...prev,
      provider: providerId,
      model_name: '',
      api_base: provider?.default_api_base || '',
    }))
    setSelectedModel(null)
    
    if (providerId) {
      loadModelsForProvider(providerId)
    } else {
      setModels([])
    }
  }

  // Handle model change
  const handleModelChange = (modelName: string) => {
    const model = models.find((m: ModelPreset) => m.model_name === modelName)
    setSelectedModel(model || null)
    setFormData(prev => ({
      ...prev,
      model_name: modelName,
      // Auto-populate max_tokens with model's recommended default (only if not editing existing config)
      ...(model?.default_max_tokens && !config ? { max_tokens: model.default_max_tokens.toString() } : {})
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.name.trim()) {
      toast.error('Please enter a configuration name')
      return
    }

    if (!formData.model_name) {
      toast.error('Please select a model')
      return
    }

    if (!config && selectedProvider?.requires_api_key && !formData.api_key.trim()) {
      toast.error('Please enter an API key')
      return
    }

    try {
      const data: any = {
        name: formData.name.trim(),
        provider: formData.provider,
        model_name: formData.model_name,
        api_base: formData.api_base.trim() || undefined,
        temperature: parseFloat(formData.temperature) || undefined,
        max_tokens: parseInt(formData.max_tokens) || undefined,
        top_p: parseFloat(formData.top_p) || undefined,
        enabled: formData.enabled, // Include enabled flag
      }

      // Only include API key if it's provided
      if (formData.api_key.trim()) {
        data.api_key = formData.api_key.trim()
      } else if (!config && !selectedProvider?.requires_api_key) {
        data.api_key = 'not-required'
      }

      await onSubmit(data)
    } catch (error) {
      console.error('Form submission error:', error)
    }
  }

  if (loadingProviders) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-sm text-gray-500">Loading providers...</p>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Configuration Name */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-900 mb-2">
          Configuration Name *
        </label>
        <input
          type="text"
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="e.g., Primary GPT-4, Backup Claude"
          className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          disabled={isSubmitting}
        />
      </div>

      {/* Provider Selection */}
      <div>
        <label htmlFor="provider" className="block text-sm font-medium text-gray-900 mb-2">
          Provider *
        </label>
        <select
          id="provider"
          value={formData.provider}
          onChange={(e) => handleProviderChange(e.target.value)}
          className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          disabled={isSubmitting}
        >
          <option value="">Select a provider</option>
          {providers.map((provider: ProviderPreset) => (
            <option key={provider.provider_id} value={provider.provider_id}>
              {provider.provider_name}
            </option>
          ))}
        </select>
        {selectedProvider && (
          <div className="mt-2 p-3 bg-red-50 rounded-lg border border-red-200">
            <p className="text-sm text-red-900">{selectedProvider.description}</p>
            {selectedProvider.documentation_url && (
              <a
                href={selectedProvider.documentation_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-red-600 hover:text-red-700 mt-2"
              >
                View documentation <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}
      </div>

      {/* Model Selection */}
      {formData.provider && (
        <div>
          <label htmlFor="model_name" className="block text-sm font-medium text-gray-900 mb-2">
            Model *
          </label>
          <select
            id="model_name"
            value={formData.model_name}
            onChange={(e) => handleModelChange(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            disabled={isSubmitting || loadingModels}
          >
            <option value="">
              {loadingModels ? 'Loading models...' : 'Select a model'}
            </option>
            {models.map((model: ModelPreset) => (
              <option key={model.model_name} value={model.model_name}>
                {model.name}
              </option>
            ))}
          </select>
          {selectedModel && (
            <div className="mt-2 space-y-1">
              <p className="text-sm text-gray-600">{selectedModel.description}</p>
              {(selectedModel.max_input_tokens || selectedModel.max_output_tokens) && (
                <div className="flex gap-4 text-xs text-gray-500">
                  {selectedModel.max_input_tokens && (
                    <span>
                      <span className="font-medium text-gray-700">Context window:</span>{' '}
                      {selectedModel.max_input_tokens.toLocaleString()} tokens
                    </span>
                  )}
                  {selectedModel.max_output_tokens && (
                    <span>
                      <span className="font-medium text-gray-700">Max output:</span>{' '}
                      {selectedModel.max_output_tokens.toLocaleString()} tokens
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* API Key */}
      {selectedProvider && selectedProvider.requires_api_key && (
        <div>
          <label htmlFor="api_key" className="block text-sm font-medium text-gray-900 mb-2">
            API Key {!config && '*'}
          </label>
          <div className="relative">
            <input
              type={showApiKey ? 'text' : 'password'}
              id="api_key"
              value={formData.api_key}
              onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
              placeholder={config ? 'Leave blank to keep existing key' : 'Enter API key'}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent pr-24"
              disabled={isSubmitting}
            />
            <button
              type="button"
              onClick={() => setShowApiKey(!showApiKey)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-gray-500 hover:text-gray-700 px-2 py-1"
            >
              {showApiKey ? 'Hide' : 'Show'}
            </button>
          </div>
          {selectedProvider.setup_instructions && (
            <p className="text-xs text-gray-500 mt-1">
              <Info className="w-3 h-3 inline mr-1" />
              {selectedProvider.setup_instructions}
            </p>
          )}
          {config && (
            <p className="text-xs text-gray-500 mt-1">
              Leave blank to keep the existing API key
            </p>
          )}
        </div>
      )}

      {/* API Base URL */}
      {selectedProvider && (selectedProvider.requires_api_base || selectedProvider.default_api_base) && (
        <div>
          <label htmlFor="api_base" className="block text-sm font-medium text-gray-900 mb-2">
            API Base URL {selectedProvider.requires_api_base && '*'}
          </label>
          <input
            type="url"
            id="api_base"
            value={formData.api_base}
            onChange={(e) => setFormData({ ...formData, api_base: e.target.value })}
            placeholder={selectedProvider.default_api_base || 'https://api.example.com/v1'}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            disabled={isSubmitting}
          />
          <p className="text-xs text-gray-500 mt-1">
            Custom API endpoint URL
          </p>
        </div>
      )}

      {/* Warning for special providers */}
      {selectedProvider && ['bedrock', 'vertex_ai', 'azure_openai'].includes(selectedProvider.provider_id) && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-900">Additional Configuration Required</p>
              <p className="text-sm text-yellow-800 mt-1">
                {selectedProvider.setup_instructions}
              </p>
              <p className="text-xs text-yellow-700 mt-2">
                You may need to add credentials in the additional_params field through the API
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Enable/Disable Toggle */}
      <div className="border-t border-gray-200 pt-6">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="enabled"
            checked={formData.enabled}
            onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
            className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500 focus:ring-2"
            disabled={isSubmitting}
          />
          <label htmlFor="enabled" className="text-sm font-medium text-gray-900">
            Enable this configuration
          </label>
        </div>
        <p className="text-xs text-gray-500 mt-1 ml-7">
          Disabled configurations will not be used by the agent
        </p>
      </div>

      {/* Advanced Settings */}
      <div className="border-t border-gray-200 pt-6">
        <h3 className="text-sm font-medium text-gray-900 mb-4">Advanced Settings</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Temperature */}
          <div>
            <label htmlFor="temperature" className="block text-sm font-medium text-gray-900 mb-2">
              Temperature
            </label>
            <input
              type="number"
              id="temperature"
              value={formData.temperature}
              onChange={(e) => setFormData({ ...formData, temperature: e.target.value })}
              min="0"
              max="2"
              step="0.1"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">0.0 - 2.0</p>
          </div>

          {/* Max Tokens */}
          <div>
            <label htmlFor="max_tokens" className="block text-sm font-medium text-gray-900 mb-2">
              Max Tokens
            </label>
            <input
              type="number"
              id="max_tokens"
              value={formData.max_tokens}
              onChange={(e) => setFormData({ ...formData, max_tokens: e.target.value })}
              min="1"
              max={selectedModel?.max_output_tokens || 200000}
              step="1"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              {selectedModel?.max_output_tokens
                ? `Max output tokens for this model: ${selectedModel.max_output_tokens.toLocaleString()}`
                : selectedModel?.default_max_tokens
                  ? `Recommended: ${selectedModel.default_max_tokens.toLocaleString()}`
                  : 'Max output tokens'}
            </p>
          </div>

          {/* Top P */}
          <div>
            <label htmlFor="top_p" className="block text-sm font-medium text-gray-900 mb-2">
              Top P
            </label>
            <input
              type="number"
              id="top_p"
              value={formData.top_p}
              onChange={(e) => setFormData({ ...formData, top_p: e.target.value })}
              min="0"
              max="1"
              step="0.1"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">0.0 - 1.0</p>
          </div>
        </div>
      </div>

      {/* Form Actions */}
      <div className="flex items-center justify-end gap-3 pt-6 border-t border-gray-200">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-6 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          {isSubmitting ? 'Saving...' : config ? 'Update Configuration' : 'Create Configuration'}
        </button>
      </div>
    </form>
  )
}
