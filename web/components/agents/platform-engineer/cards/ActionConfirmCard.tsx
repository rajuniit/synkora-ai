'use client'

import { Loader2, X, Check, Wrench, KeyRound } from 'lucide-react'

export interface AgentCreateConfig {
  name: string
  description: string
  system_prompt: string
  llm_provider?: string
  llm_model?: string
  tools_list?: string[]
  category?: string
  tags?: string[]
}

export type ActionCardStatus = 'pending' | 'creating' | 'created' | 'cancelled'

interface Props {
  config: AgentCreateConfig
  status: ActionCardStatus
  onConfirm: (config: AgentCreateConfig) => void
  onCancel: () => void
}

export function ActionConfirmCard({ config, status, onConfirm, onCancel }: Props) {
  if (status === 'cancelled') {
    return (
      <div className="border border-gray-200 bg-gray-50 rounded-xl p-4 text-sm text-gray-500 italic">
        Agent creation cancelled.
      </div>
    )
  }

  return (
    <div className="border-2 border-red-200 bg-red-50 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Wrench className="h-4 w-4 text-red-600 flex-shrink-0" />
        <span className="font-semibold text-red-900 text-sm">Create Agent: {config.name}</span>
      </div>

      {config.description && (
        <p className="text-xs text-red-700 leading-relaxed line-clamp-3">{config.description}</p>
      )}

      <div className="flex flex-wrap gap-2 text-xs">
        {(config.llm_provider || config.llm_model) && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full font-medium">
            {config.llm_provider} / {config.llm_model}
          </span>
        )}
        {config.category && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full">
            {config.category}
          </span>
        )}
      </div>

      {config.tools_list && config.tools_list.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {config.tools_list.map((tool) => (
            <span
              key={tool}
              className="px-2 py-0.5 bg-white border border-red-200 text-red-600 rounded text-xs"
            >
              {tool}
            </span>
          ))}
        </div>
      )}

      {/* API key inheritance notice */}
      <div className="flex items-center gap-1.5 text-xs text-red-600/70">
        <KeyRound className="h-3 w-3 flex-shrink-0" />
        <span>API key inherited from your Platform Engineer configuration</span>
      </div>

      {status === 'pending' && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onConfirm(config)}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-medium transition-colors"
          >
            <Check className="h-3.5 w-3.5" />
            Confirm &amp; Create
          </button>
          <button
            onClick={onCancel}
            className="flex items-center justify-center gap-1.5 px-3 py-2 border border-red-300 text-red-600 hover:bg-red-100 rounded-lg text-xs font-medium transition-colors"
          >
            <X className="h-3.5 w-3.5" />
            Cancel
          </button>
        </div>
      )}

      {status === 'creating' && (
        <div className="flex items-center gap-2 text-xs text-red-600 pt-1">
          <Loader2 className="h-4 w-4 animate-spin" />
          Creating agent...
        </div>
      )}
    </div>
  )
}
