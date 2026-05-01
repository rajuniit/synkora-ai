'use client'

import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { Message, SuggestionPrompt } from '../types'
import { ChatMessage } from './ChatMessage'
import { Sparkles, MessageSquare, Lightbulb } from 'lucide-react'

interface ChatConfig {
  chat_title?: string
  chat_logo_url?: string
  chat_welcome_message?: string
  chat_placeholder?: string
  chat_primary_color?: string
  chat_background_color?: string
  chat_font_family?: string
}

interface ToolStatus {
  tool_name: string
  status: 'started' | 'completed' | 'error'
  description: string
  details?: {
    file_path?: string
    path?: string
    command?: string
    repo_url?: string
    url?: string
    branch?: string
  }
  duration_ms?: number
  input_tokens?: number
  output_tokens?: number
}

interface ChatMessagesProps {
  messages: Message[]
  isStreaming?: boolean
  onCopyMessage?: (content: string, messageId: string) => void
  onRetry?: (messageId: string) => void
  onDeleteMessage?: (messageId: string) => void
  thinkingStatus?: string
  toolStatus?: ToolStatus | null
  recentTools?: ToolStatus[]
  streamStartTime?: number | null
  className?: string
  suggestionPrompts?: SuggestionPrompt[]
  onSuggestionClick?: (prompt: string) => void
  onActionClick?: (text: string) => void
  chatConfig?: ChatConfig | null
  agentAvatar?: string
  userAvatar?: string
  agentName?: string
}

/**
 * ChatMessages - Scrollable container for displaying chat messages
 * Implements auto-scroll and virtual scrolling for performance
 */
export function ChatMessages({
  messages,
  isStreaming = false,
  onCopyMessage,
  onRetry,
  onDeleteMessage,
  thinkingStatus,
  toolStatus,
  recentTools = [],
  streamStartTime,
  className,
  suggestionPrompts = [],
  onSuggestionClick,
  onActionClick,
  chatConfig,
  agentAvatar,
  userAvatar,
  agentName,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const shouldAutoScrollRef = useRef(true)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (shouldAutoScrollRef.current) {
      scrollToBottom()
    }
  }, [messages])

  // Check if user has scrolled up
  const handleScroll = () => {
    if (!containerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100

    shouldAutoScrollRef.current = isNearBottom
  }

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior })
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className={cn(
        'flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-6 lg:px-10 py-6',
        className
      )}
    >
      {messages.length === 0 ? (
        <EmptyState
          suggestionPrompts={suggestionPrompts}
          onSuggestionClick={onSuggestionClick}
          chatConfig={chatConfig}
        />
      ) : (
        <div className="max-w-4xl mx-auto space-y-5">
          {messages.map((message, index) => {
            const isLastMessage = index === messages.length - 1
            const isStreamingMessage = isStreaming && isLastMessage

            return (
              <ChatMessage
                key={message.id}
                message={message}
                isStreaming={isStreamingMessage}
                thinkingStatus={isStreamingMessage ? thinkingStatus : undefined}
                toolStatus={isStreamingMessage ? toolStatus : undefined}
                recentTools={isStreamingMessage ? recentTools : []}
                streamStartTime={isStreamingMessage ? streamStartTime : undefined}
                onCopy={onCopyMessage}
                onRetry={onRetry}
                onDelete={onDeleteMessage}
                onActionClick={onActionClick}
                chatConfig={chatConfig}
                agentAvatar={agentAvatar}
                userAvatar={userAvatar}
                agentName={agentName}
              />
            )
          })}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  )
}

interface EmptyStateProps {
  suggestionPrompts?: SuggestionPrompt[]
  onSuggestionClick?: (prompt: string) => void
  chatConfig?: ChatConfig | null
}

function EmptyState({ suggestionPrompts = [], onSuggestionClick, chatConfig }: EmptyStateProps) {
  const primaryColor = chatConfig?.chat_primary_color || '#0d9488'
  const welcomeMessage = chatConfig?.chat_welcome_message || 'Ask me anything! I\'m here to help you with information, analysis, and creative tasks.'
  const hasConfiguredPrompts = suggestionPrompts.length > 0

  const getIconComponent = (iconName?: string) => {
    if (!iconName) {
      return <Sparkles size={22} />
    }
    if (iconName.length <= 4 && /\p{Emoji}/u.test(iconName)) {
      return <span className="text-2xl">{iconName}</span>
    }
    switch (iconName.toLowerCase()) {
      case 'sparkles':
        return <Sparkles size={22} />
      case 'message':
      case 'messagesquare':
        return <MessageSquare size={22} />
      case 'lightbulb':
      case 'bulb':
        return <Lightbulb size={22} />
      default:
        return <span className="text-2xl">{iconName}</span>
    }
  }

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      {/* Hero Icon */}
      <div
        className="w-20 h-20 rounded-3xl flex items-center justify-center mb-8"
        style={{
          background: `linear-gradient(135deg, ${primaryColor}20, ${primaryColor}10)`
        }}
      >
        <Sparkles
          size={40}
          style={{ color: primaryColor }}
        />
      </div>

      {/* Bold Heading */}
      <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 tracking-tight">
        How can I help you today?
      </h1>
      <p className="text-lg text-gray-500 max-w-xl mb-12 leading-relaxed">
        {welcomeMessage}
      </p>

      {/* Suggestion Cards */}
      {hasConfiguredPrompts ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
          {suggestionPrompts.map((prompt, index) => (
            <button
              key={index}
              onClick={() => onSuggestionClick?.(prompt.prompt)}
              className="group flex items-start gap-4 p-6 text-left bg-gray-50/80 hover:bg-gray-100 rounded-2xl transition-all duration-200 border border-gray-100 hover:border-gray-200 hover:shadow-sm"
            >
              <div
                className="shrink-0 w-12 h-12 rounded-xl flex items-center justify-center"
                style={{
                  background: `linear-gradient(135deg, ${primaryColor}15, ${primaryColor}25)`
                }}
              >
                <div style={{ color: primaryColor }}>
                  {getIconComponent(prompt.icon)}
                </div>
              </div>
              <div className="flex-1 min-w-0 pt-0.5">
                <div className="text-base font-semibold text-gray-900 mb-1">
                  {prompt.title}
                </div>
                {prompt.description && (
                  <div className="text-sm text-gray-500 leading-relaxed">
                    {prompt.description}
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-3xl">
          <SuggestionCard
            icon="💡"
            title="Get Ideas"
            description="Brainstorm creative solutions and explore possibilities"
            onSuggestionClick={onSuggestionClick}
          />
          <SuggestionCard
            icon="📊"
            title="Analyze Data"
            description="Extract insights and patterns from your information"
            onSuggestionClick={onSuggestionClick}
          />
          <SuggestionCard
            icon="✍️"
            title="Write Content"
            description="Create engaging copy, articles, and documentation"
            onSuggestionClick={onSuggestionClick}
          />
          <SuggestionCard
            icon="🔍"
            title="Research"
            description="Deep dive into topics and gather information"
            onSuggestionClick={onSuggestionClick}
          />
        </div>
      )}
    </div>
  )
}

interface SuggestionCardProps {
  icon: string
  title: string
  description?: string
  onSuggestionClick?: (prompt: string) => void
}

function SuggestionCard({ icon, title, description, onSuggestionClick }: SuggestionCardProps) {
  return (
    <button
      onClick={() => onSuggestionClick?.(title)}
      className="group flex items-start gap-4 p-6 text-left bg-gray-50/80 hover:bg-gray-100 rounded-2xl transition-all duration-200 border border-gray-100 hover:border-gray-200 hover:shadow-sm"
    >
      <span className="text-3xl">{icon}</span>
      <div className="flex-1 min-w-0 pt-0.5">
        <div className="text-base font-semibold text-gray-900 mb-1">{title}</div>
        {description && (
          <div className="text-sm text-gray-500 leading-relaxed">{description}</div>
        )}
      </div>
    </button>
  )
}
