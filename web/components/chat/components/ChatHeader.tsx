'use client'

import { useState } from 'react'
import Image from 'next/image'
import { 
  Sparkles, 
  Settings, 
  Share2, 
  MoreVertical,
  Download,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SuggestionPrompt {
  title: string
  description?: string
  icon?: string
  prompt: string
}

interface Agent {
  agent_name: string
  agent_type: string
  description?: string
  avatar?: string
  status: string
  model?: string
  provider?: string
  suggestion_prompts?: SuggestionPrompt[]
}

interface ChatConfig {
  chat_title?: string
  chat_logo_url?: string
  chat_welcome_message?: string
  chat_placeholder?: string
  chat_primary_color?: string
  chat_background_color?: string
  chat_font_family?: string
}

interface LLMConfig {
  id: string
  name?: string
  provider: string
  model_name: string
  enabled: boolean
  is_default: boolean
}

interface ChatHeaderProps {
  agent: Agent | null
  chatConfig?: ChatConfig | null
  llmConfigs?: LLMConfig[]
  selectedLLMConfigId?: string
  onLLMConfigChange?: (configId: string) => void
  onSettingsClick?: () => void
  onShareClick?: () => void
  onExportClick?: () => void
  onClearChat?: () => void
  onRefresh?: () => void
  className?: string
}

/**
 * ChatHeader - Header component with agent info and action buttons
 */
export function ChatHeader({
  agent,
  chatConfig,
  llmConfigs,
  selectedLLMConfigId,
  onLLMConfigChange,
  onSettingsClick,
  onShareClick,
  onExportClick,
  onClearChat,
  onRefresh,
  className,
}: ChatHeaderProps) {
  const [showMenu, setShowMenu] = useState(false)
  
  // Get enabled LLM configs for dropdown
  const enabledConfigs = llmConfigs?.filter(config => config.enabled) || []
  
  // Use custom title if available, otherwise fall back to agent name
  const displayTitle = chatConfig?.chat_title || agent?.agent_name || 'Agent'
  
  // Prioritize agent avatar for header display (logo is for sidebar only)
  const hasAgentAvatar = agent?.avatar
  
  // Get primary color for theming
  const primaryColor = chatConfig?.chat_primary_color || '#0d9488' // teal-600 as default
  
  // Generate gradient background for logo
  const logoGradient = `linear-gradient(135deg, ${primaryColor}, ${primaryColor}dd)`

  return (
    <div
      className={cn(
        'flex items-center justify-between px-4 py-2.5 border-b border-gray-200/80 bg-white/95 backdrop-blur-sm',
        className
      )}
    >
      {/* Agent Info - More Compact */}
      <div className="flex items-center gap-3">
        {hasAgentAvatar ? (
          <div className="w-9 h-9 rounded-lg overflow-hidden shadow-md flex items-center justify-center bg-white relative ring-2 ring-gray-100">
            {agent.avatar && (agent.avatar.startsWith('http://') || agent.avatar.startsWith('https://')) ? (
              <img
                src={agent.avatar}
                alt={displayTitle}
                className="w-full h-full object-cover"
              />
            ) : (
              <Image
                src={agent.avatar!}
                alt={displayTitle}
                fill
                className="object-cover"
              />
            )}
          </div>
        ) : (
          <div 
            className="w-9 h-9 rounded-lg flex items-center justify-center shadow-md ring-2 ring-white"
            style={{ background: logoGradient }}
          >
            <Sparkles size={18} className="text-white" />
          </div>
        )}
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold text-gray-900">
              {displayTitle}
            </h1>
            <span
              className={cn(
                'px-1.5 py-0.5 rounded text-[10px] font-medium',
                agent?.status === 'active'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-gray-100 text-gray-700'
              )}
            >
              {agent?.status || 'Unknown'}
            </span>
          </div>
          <p className="text-xs text-gray-500 line-clamp-1">
            {agent?.agent_type === 'digital_clone' ? '🤖 Digital Clone' : agent?.description || agent?.agent_type || 'AI Assistant'}
          </p>
        </div>
      </div>

      {/* Action Buttons - More Compact */}
      <div className="flex items-center gap-1.5">
        {/* LLM Config Dropdown - Compact */}
        {enabledConfigs.length > 0 && (
          <select
            value={selectedLLMConfigId || ''}
            onChange={(e) => {
              if (onLLMConfigChange && e.target.value) {
                onLLMConfigChange(e.target.value)
              }
            }}
            className="px-2.5 py-1.5 rounded-lg bg-gray-50 border border-gray-200 text-xs font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent cursor-pointer"
            style={{
              minWidth: '160px',
            }}
          >
            {enabledConfigs.map((config) => (
              <option key={config.id} value={config.id}>
                {config.provider}/{config.model_name}{config.is_default ? ' ⭐' : ''}
              </option>
            ))}
          </select>
        )}
        
        {(!enabledConfigs.length && agent?.model) && (
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-50 border border-gray-200">
            <span className="text-xs font-medium text-gray-700">{agent.model}</span>
          </div>
        )}

        {/* Refresh - Compact */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1.5 rounded-lg transition-colors hover:bg-amber-50"
            style={{
              color: primaryColor,
            }}
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        )}

        {/* Share - Compact */}
        {onShareClick && (
          <button
            onClick={onShareClick}
            className="p-1.5 rounded-lg transition-colors hover:bg-amber-50"
            style={{
              color: primaryColor,
            }}
            title="Share"
          >
            <Share2 size={16} />
          </button>
        )}

        {/* Settings - Compact */}
        {onSettingsClick && (
          <button
            onClick={onSettingsClick}
            className="p-1.5 rounded-lg transition-colors hover:bg-amber-50"
            style={{
              color: primaryColor,
            }}
            title="Settings"
          >
            <Settings size={16} />
          </button>
        )}

        {/* More Menu - Compact */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1.5 rounded-lg hover:bg-gray-50 transition-colors"
            title="More"
          >
            <MoreVertical size={16} className="text-gray-600" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-20">
                {onExportClick && (
                  <button
                    onClick={() => {
                      onExportClick()
                      setShowMenu(false)
                    }}
                    className="w-full px-3 py-1.5 text-left text-xs text-gray-700 hover:bg-amber-50 flex items-center gap-2 transition-colors"
                  >
                    <Download size={14} />
                    Export
                  </button>
                )}
                {onClearChat && (
                  <button
                    onClick={() => {
                      onClearChat()
                      setShowMenu(false)
                    }}
                    className="w-full px-3 py-1.5 text-left text-xs text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors"
                  >
                    <Trash2 size={14} />
                    Clear
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
