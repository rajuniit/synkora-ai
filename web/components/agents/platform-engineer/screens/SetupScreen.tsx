'use client'

import { useState, useEffect } from 'react'
import { Wrench } from 'lucide-react'
import toast from 'react-hot-toast'
import LLMConfigForm from '@/components/agents/llm-configs/LLMConfigForm'
import { getPlatformAgentLLMConfig, upsertPlatformAgentLLMConfig } from '@/lib/api/platformEngineerApi'
import type { AgentLLMConfig, AgentLLMConfigCreate, AgentLLMConfigUpdate } from '@/types/agent-llm-config'
import type { PlatformAgentLLMConfigUpsert } from '@/lib/api/platformEngineerApi'

interface Props {
  onConfigured: () => void
}

export function SetupScreen({ onConfigured }: Props) {
  const [existingConfig, setExistingConfig] = useState<AgentLLMConfig | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const cfg = await getPlatformAgentLLMConfig()
        if (cfg) setExistingConfig(cfg)
      } catch {
        // no config yet — create mode
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSubmit = async (data: AgentLLMConfigCreate | AgentLLMConfigUpdate) => {
    setIsSubmitting(true)
    try {
      // Build upsert payload — omit api_key when blank (keep existing key on update)
      const payload: PlatformAgentLLMConfigUpsert = {
        name: (data as AgentLLMConfigCreate).name,
        provider: (data as AgentLLMConfigCreate).provider,
        model_name: (data as AgentLLMConfigCreate).model_name,
        api_base: data.api_base ?? undefined,
        temperature: data.temperature ?? undefined,
        max_tokens: data.max_tokens ?? undefined,
        top_p: data.top_p ?? undefined,
        enabled: data.enabled ?? true,
      }
      const apiKey = (data as AgentLLMConfigCreate).api_key
      if (apiKey && apiKey.trim()) payload.api_key = apiKey.trim()
      await upsertPlatformAgentLLMConfig(payload)
      toast.success(existingConfig ? 'LLM configuration updated' : 'LLM configuration saved')
      onConfigured()
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to save configuration'
      toast.error(detail)
      throw err
    } finally {
      setIsSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-4 pb-6 border-b border-gray-100">
        <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center flex-shrink-0">
          <Wrench className="h-5 w-5 text-primary-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {existingConfig ? 'Update LLM Configuration' : 'Configure LLM Provider'}
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">
            {existingConfig
              ? 'Update the provider or API key used by the Platform Engineer.'
              : 'Choose a provider and enter your API key to get started. Your key is encrypted at rest.'}
          </p>
        </div>
      </div>

      {/* Form */}
      <LLMConfigForm
        config={existingConfig}
        onSubmit={handleSubmit}
        onCancel={onConfigured}
        isSubmitting={isSubmitting}
      />
    </div>
  )
}
