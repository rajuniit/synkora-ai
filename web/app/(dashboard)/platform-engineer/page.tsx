'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Settings, Send, Loader2, Lock, ArrowRight, Zap, List, Plug, Pencil, Trash2 } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { ChatMessage } from '@/components/chat/components/ChatMessage'
import type { Message } from '@/components/chat/types'
import { getPlatformAgentStatus, type PlatformAgentStatus } from '@/lib/api/platformEngineerApi'
import { SetupScreen } from '@/components/agents/platform-engineer/screens/SetupScreen'
import { ActionConfirmCard } from '@/components/agents/platform-engineer/cards/ActionConfirmCard'
import { IntegrationPromptCard } from '@/components/agents/platform-engineer/cards/IntegrationPromptCard'
import { AgentCreatedCard } from '@/components/agents/platform-engineer/cards/AgentCreatedCard'
import { parseActionMarkers } from '@/components/agents/platform-engineer/types'
import type { ActionCard, IntegrationCard } from '@/components/agents/platform-engineer/types'
import type { AgentCreateConfig, ActionCardStatus } from '@/components/agents/platform-engineer/cards/ActionConfirmCard'
import { secureStorage } from '@/lib/auth/secure-storage'
import { apiClient } from '@/lib/api/http'
import { enableCapabilitiesBulk } from '@/lib/api/agents'

// Map PE tool-category names → capability IDs (same IDs used by manual agent creation)
const TOOL_CATEGORY_TO_CAPABILITY: Record<string, string> = {
  browser_tools: 'browser-web',
  scheduler_tools: 'scheduling',
  email_tools: 'email',
  gmail_tools: 'email',
  web_search: 'web-research',
  file_tools: 'files-storage',
  command_tools: 'system-commands',
  database_tools: 'database-analytics',
  elasticsearch_tools: 'database-analytics',
  data_analysis_tools: 'database-analytics',
  storage_tools: 'files-storage',
  news_tools: 'web-research',
  document_tools: 'documents',
  github_tools: 'code-github',
  gitlab_tools: 'code-github',
  google_calendar_tools: 'meetings-calendar',
  google_drive_tools: 'files-storage',
  slack_tools: 'communication',
  jira_tools: 'project-mgmt',
  zoom_tools: 'meetings-calendar',
  twitter_tools: 'social-media',
  linkedin_tools: 'social-media',
  youtube_tools: 'social-media',
  clickup_tools: 'project-mgmt',
  spawn_agent_tool: 'agents',
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
const AGENT_NAME = 'platform_engineer_agent'
const MSG_STORAGE_KEY = 'pe-messages'
const CONV_ID_STORAGE_KEY = 'pe-conv-id'

type Screen = 'loading' | 'gate' | 'setup' | 'chat'

interface PEMessage extends Message {
  _actionCard?: ActionCard & { status: ActionCardStatus; createdAgentName?: string }
  _integrationCard?: IntegrationCard
}

const QUICK_ACTIONS = [
  { icon: Zap, label: 'Create an agent', prompt: 'I want to create a new AI agent. Help me design one.' },
  { icon: List, label: 'List my agents', prompt: 'Show me all my current agents' },
  { icon: Plug, label: 'Check integrations', prompt: 'What integrations are available and which ones do I have connected?' },
  { icon: Pencil, label: 'Update an agent', prompt: 'I want to update an existing agent. Which ones do I have?' },
]

export default function PlatformEngineerPage() {
  const [screen, setScreen] = useState<Screen>('loading')
  const [status, setStatus] = useState<PlatformAgentStatus | null>(null)
  const [messages, setMessages] = useState<PEMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const convIdRef = useRef<string>('')

  // Load persisted conversation on mount
  useEffect(() => {
    try {
      const savedConvId = localStorage.getItem(CONV_ID_STORAGE_KEY)
      if (savedConvId) {
        convIdRef.current = savedConvId
      } else {
        const id = crypto.randomUUID()
        localStorage.setItem(CONV_ID_STORAGE_KEY, id)
        convIdRef.current = id
      }
      const saved = localStorage.getItem(MSG_STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved) as PEMessage[]
        setMessages(parsed.map((m) => ({ ...m, timestamp: new Date(m.timestamp as unknown as string) })))
      }
    } catch {
      // ignore storage errors
    }
  }, [])

  // Persist messages whenever they change
  useEffect(() => {
    if (messages.length === 0) return
    try {
      localStorage.setItem(MSG_STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // ignore storage errors
    }
  }, [messages])

  useEffect(() => {
    getPlatformAgentStatus()
      .then((s) => {
        setStatus(s)
        if (!s.has_access) setScreen('gate')
        else if (!s.is_configured) setScreen('setup')
        else setScreen('chat')
      })
      .catch(() => setScreen('chat'))
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const clearConversation = useCallback(() => {
    setMessages([])
    const id = crypto.randomUUID()
    convIdRef.current = id
    try {
      localStorage.setItem(CONV_ID_STORAGE_KEY, id)
      localStorage.removeItem(MSG_STORAGE_KEY)
    } catch { /* ignore */ }
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return

    const userMsg: PEMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }
    const assistantMsg: PEMessage = {
      id: `asst-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setInput('')
    setIsStreaming(true)

    try {
      const token = secureStorage.getAccessToken()
      const response = await fetch(`${API_URL}/api/v1/agents/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({
          agent_name: AGENT_NAME,
          message: content,
          conversation_id: convIdRef.current || undefined,
          conversation_history: messages.slice(-10).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      })

      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullResponse = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (jsonStr === '[DONE]') continue

          let data: Record<string, unknown>
          try {
            data = JSON.parse(jsonStr)
          } catch {
            continue // skip malformed JSON
          }

          if (data.type === 'error') {
            throw new Error((data.error as string) || 'Something went wrong')
          }

          if (data.type === 'chunk') {
            fullResponse += data.content
            const { displayText, actionCard, integrationCard } = parseActionMarkers(fullResponse)
            setMessages((prev) => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last.role === 'assistant') {
                next[next.length - 1] = {
                  ...last,
                  content: displayText,
                  _actionCard: actionCard
                    ? { ...actionCard, status: last._actionCard?.status ?? 'pending' }
                    : last._actionCard,
                  _integrationCard: integrationCard ?? last._integrationCard,
                }
              }
              return next
            })
          }
        }
      }
    } catch (err: any) {
      const msg = err?.message || 'Failed to get response'
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last.role === 'assistant') {
          const existing = last.content ? `${last.content}\n\n` : ''
          next[next.length - 1] = { ...last, content: `${existing}⚠ ${msg}`, isError: true }
        }
        return next
      })
      toast.error(msg)
    } finally {
      setIsStreaming(false)
    }
  }, [isStreaming, messages])

  const handleConfirm = async (config: AgentCreateConfig) => {
    setMessages((prev) =>
      prev.map((m) =>
        m._actionCard?.status === 'pending'
          ? { ...m, _actionCard: { ...m._actionCard!, status: 'creating' } }
          : m
      )
    )
    try {
      const res = await apiClient.axios.post('/api/v1/agents/', {
        config: {
          name: config.name,
          description: config.description,
          system_prompt: config.system_prompt,
          agent_type: 'llm_agent',
          llm_config: {
            provider: config.llm_provider,
            model_name: config.llm_model,
            temperature: 0.7,
            max_tokens: 4096,
            api_key: '',
          },
          tools: [],
          metadata: {},
        },
        agent_type: 'llm',
        is_public: false,
        category: config.category,
        tags: config.tags,
      })
      const created = res.data?.agent_name || config.name
      const agentId: string | undefined = res.data?.agent_id

      // Enable capabilities exactly like the manual create page does
      if (agentId && config.tools_list && config.tools_list.length > 0) {
        const capabilityIds = [...new Set(
          config.tools_list
            .map((t) => TOOL_CATEGORY_TO_CAPABILITY[t])
            .filter(Boolean)
        )]
        if (capabilityIds.length > 0) {
          await enableCapabilitiesBulk(agentId, capabilityIds)
        }
      }
      setMessages((prev) =>
        prev.map((m) =>
          m._actionCard?.status === 'creating'
            ? { ...m, _actionCard: { ...m._actionCard!, status: 'created', createdAgentName: created } }
            : m
        )
      )
    } catch (err: any) {
      const status = err?.response?.status
      const rawDetail = err?.response?.data?.detail

      let detail: string
      if (status === 409) {
        detail = `An agent named "${config.name}" already exists. Ask the Platform Engineer to update it instead (add tools, change prompt, etc.).`
      } else if (Array.isArray(rawDetail)) {
        detail = rawDetail.map((e: any) => `${e.loc?.slice(-1)[0] ?? 'field'}: ${e.msg}`).join('; ')
      } else {
        detail = typeof rawDetail === 'string' ? rawDetail : err?.message || 'Agent creation failed'
      }

      setMessages((prev) =>
        prev.map((m) =>
          m._actionCard?.status === 'creating'
            ? { ...m, _actionCard: { ...m._actionCard!, status: 'pending' } }
            : m
        )
      )
      toast.error(detail)
    }
  }

  const handleCancelAction = () => {
    setMessages((prev) =>
      prev.map((m) =>
        m._actionCard?.status === 'pending'
          ? { ...m, _actionCard: { ...m._actionCard!, status: 'cancelled' } }
          : m
      )
    )
  }

  // ─── Loading ──────────────────────────────────────────────────────────────

  if (screen === 'loading') {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-red-600" />
      </div>
    )
  }

  // ─── Plan Gate ────────────────────────────────────────────────────────────

  if (screen === 'gate') {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-4 text-center space-y-6">
        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
          <Lock className="h-7 w-7 text-red-500" />
        </div>
        <div className="space-y-2">
          <span className="inline-block px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
            You&apos;re on the {status?.plan_tier ? status.plan_tier.charAt(0) + status.plan_tier.slice(1).toLowerCase() : 'Free'} plan
          </span>
          <h3 className="text-xl font-semibold text-gray-900">Platform Engineer Agent</h3>
          <p className="text-sm text-gray-500 max-w-sm leading-relaxed">
            Available on Hobby and above. Create and manage AI agents through natural conversation.
          </p>
        </div>
        <ul className="text-left space-y-2 text-sm text-gray-600 max-w-xs">
          {['Create agents through conversation', 'Check integration status', 'Manage agent configurations', 'Get tool recommendations'].map((f) => (
            <li key={f} className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
              {f}
            </li>
          ))}
        </ul>
        <Link href="/billing/subscription" className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity">
          Upgrade Plan <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    )
  }

  // ─── Setup ────────────────────────────────────────────────────────────────

  if (screen === 'setup') {
    return (
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Sub-header matches chat screen */}
        <div className="flex items-center justify-between px-4 md:px-8 py-3 border-b border-gray-100 bg-white flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 leading-tight">Platform Engineer</p>
              <p className="text-xs text-gray-400 leading-tight">LLM Configuration</p>
            </div>
          </div>
        </div>

        {/* Full-width setup content */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-4 md:px-8 py-6 max-w-7xl mx-auto">
            <SetupScreen
              onConfigured={async () => {
                try {
                  const s = await getPlatformAgentStatus()
                  setStatus(s)
                } catch { /* ignore */ }
                setScreen('chat')
              }}
            />
          </div>
        </div>
      </div>
    )
  }

  // ─── Chat ─────────────────────────────────────────────────────────────────

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Sub-header: agent info + settings */}
      <div className="flex items-center justify-between px-4 md:px-8 py-3 border-b border-gray-100 bg-white flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center">
            <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900 leading-tight">Platform Engineer</p>
            {status?.is_configured && (
              <p className="text-xs text-gray-400 leading-tight">{status.provider} / {status.model_name}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={clearConversation}
              title="Clear conversation"
              className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={() => setScreen('setup')}
            title="Configure LLM"
            className="h-8 w-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages / Hero */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <HeroSection onSend={sendMessage} isStreaming={isStreaming} />
        ) : (
          <div className="px-4 md:px-8 py-6 max-w-7xl mx-auto space-y-2">
            {messages.map((msg, i) => {
              const isLast = i === messages.length - 1
              return (
                <div key={msg.id}>
                  <ChatMessage
                    message={msg}
                    isStreaming={isLast && isStreaming && msg.role === 'assistant'}
                    agentName="Platform Engineer"
                  />
                  {msg._actionCard && msg._actionCard.status !== 'created' && (
                    <div className="ml-10 mt-2">
                      <ActionConfirmCard
                        config={msg._actionCard.config}
                        status={msg._actionCard.status}
                        onConfirm={handleConfirm}
                        onCancel={handleCancelAction}
                      />
                    </div>
                  )}
                  {msg._actionCard?.status === 'created' && msg._actionCard.createdAgentName && (
                    <div className="ml-10 mt-2">
                      <AgentCreatedCard agentName={msg._actionCard.createdAgentName} />
                    </div>
                  )}
                  {msg._integrationCard && (
                    <div className="ml-10 mt-2">
                      <IntegrationPromptCard
                        provider={msg._integrationCard.provider}
                        message={msg._integrationCard.message}
                        connect_url={msg._integrationCard.connect_url}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Input bar */}
      {!isEmpty && (
        <div className="border-t border-gray-100 bg-white px-4 md:px-8 py-3 flex-shrink-0">
          <div className="max-w-7xl mx-auto">
            <ChatInputBar
              value={input}
              onChange={setInput}
              onSend={() => sendMessage(input)}
              isStreaming={isStreaming}
              textareaRef={textareaRef}
            />
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function HeroSection({
  onSend,
  isStreaming,
}: {
  onSend: (msg: string) => void
  isStreaming: boolean
}) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-4 py-16 text-center">
      <div className="w-full max-w-3xl space-y-8">
        <div className="space-y-3">
          <h1 className="text-5xl font-bold text-gray-900 tracking-tight leading-tight">
            What will you build?
          </h1>
          <p className="text-lg text-gray-500">
            Create and manage AI agents through conversation — no code needed.
          </p>
        </div>

        {/* Input */}
        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm px-4 pt-3 pb-2 text-left">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Describe the agent you want to build..."
            rows={2}
            className="w-full text-base text-gray-900 placeholder:text-gray-400 resize-none outline-none bg-transparent leading-relaxed"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                if (value.trim()) onSend(value)
              }
            }}
          />
          <div className="flex items-center justify-end pt-1">
            <button
              onClick={() => { if (value.trim()) onSend(value) }}
              disabled={!value.trim() || isStreaming}
              className="h-9 w-9 flex items-center justify-center bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* Quick actions */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          {QUICK_ACTIONS.map(({ icon: Icon, label, prompt }) => (
            <button
              key={label}
              disabled={isStreaming}
              onClick={() => onSend(prompt)}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-white border border-gray-200 text-gray-700 rounded-full hover:bg-gray-50 hover:border-gray-300 transition-colors disabled:opacity-50"
            >
              <Icon className="h-3.5 w-3.5 text-gray-400" />
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function ChatInputBar({
  value,
  onChange,
  onSend,
  isStreaming,
  textareaRef,
}: {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  isStreaming: boolean
  textareaRef: React.RefObject<HTMLTextAreaElement | null>
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl px-4 pt-3 pb-2 shadow-sm">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ask the Platform Engineer anything..."
        rows={1}
        className="w-full text-sm text-gray-900 placeholder:text-gray-400 resize-none outline-none bg-transparent min-h-[36px] max-h-[120px] overflow-y-auto leading-relaxed"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            onSend()
          }
        }}
      />
      <div className="flex items-center justify-end pt-1">
        <button
          onClick={onSend}
          disabled={!value.trim() || isStreaming}
          className="h-9 w-9 flex items-center justify-center bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}
