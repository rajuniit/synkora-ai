'use client'

import { useMemo } from 'react'
import { ChatMessages } from '@/components/chat/components'
import type { SharedConversationData } from '@/lib/api/conversations'
import type { Message } from '@/components/chat/types'

interface Props {
  data: SharedConversationData
}

function formatExpiry(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now()
  if (diff <= 0) return 'expired'
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function SharedChatView({ data }: Props) {
  const { conversation, messages: rawMessages, agent, expires_at } = data

  const messages: Message[] = useMemo(
    () =>
      rawMessages
        .filter((msg: any) => {
          const role = (msg.role as string).toLowerCase()
          return role === 'user' || role === 'assistant'
        })
        .map((msg: any) => ({
          id: msg.id,
          role: (msg.role as string).toLowerCase() as Message['role'],
          content: msg.content,
          timestamp: new Date(msg.created_at),
          sources: msg.metadata?.sources || [],
          metadata: msg.metadata || {},
        })),
    [rawMessages]
  )

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 flex-shrink-0">
        {agent?.avatar ? (
          <img
            src={agent.avatar}
            alt={agent.name}
            className="w-9 h-9 rounded-full object-cover flex-shrink-0"
          />
        ) : (
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-sm font-bold">
              {agent?.name?.charAt(0)?.toUpperCase() || 'A'}
            </span>
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-gray-900 truncate">
            {conversation?.name || 'Shared Conversation'}
          </h1>
          {agent?.name && (
            <p className="text-xs text-gray-500">{agent.name}</p>
          )}
        </div>
        <span className="flex-shrink-0 text-xs text-gray-400 bg-gray-100 px-2.5 py-1 rounded-full">
          Read-only · expires in {formatExpiry(expires_at)}
        </span>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto w-full px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <p className="text-sm">No messages in this conversation.</p>
          </div>
        ) : (
          <ChatMessages
            messages={messages}
            isStreaming={false}
            agentName={agent?.name}
            agentAvatar={agent?.avatar}
          />
        )}
      </div>

      {/* Read-only footer */}
      <div className="border-t border-gray-200 bg-white px-4 py-3 flex-shrink-0">
        <div>
          <p className="text-xs text-center text-gray-400">
            This conversation is read-only · Shared via Synkora
          </p>
        </div>
      </div>
    </div>
  )
}
