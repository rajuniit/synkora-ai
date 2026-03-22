'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams } from 'next/navigation'
import { useAuthStore } from '@/lib/store/authStore'
import {
  ChatMessages,
  ChatInput,
  ChatSidebar,
} from '@/components/chat/components'
import { Message, Agent, Source, Person, NewsItem, Attachment } from '@/components/chat/types'
import { apiClient } from '@/lib/api/client'
import { secureStorage } from '@/lib/auth/secure-storage'
import { useAgentLLMConfigs } from '@/hooks/useAgentLLMConfigs'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

interface ChatConfig {
  chat_title: string
  chat_welcome_message: string
  chat_placeholder: string
  chat_primary_color: string
  chat_logo_url: string
  chat_background_color: string
  chat_font_family: string
  chat_footer_text?: string
  chat_footer_links?: Array<{ text: string; url: string }>
  // Widget-based customization
  layout?: 'centered' | 'left' | 'right' | 'full'
  show_sidebar?: boolean
  sidebar_widgets?: Array<{
    type: 'profile' | 'social' | 'resume' | 'about' | 'links' | 'stats' | 'custom'
    title?: string
    content?: any
    position?: 'left' | 'right'
    order?: number
  }>
}

interface Conversation {
  id: string
  name: string
  created_at: string
  updated_at: string
  message_count?: number
}

export default function AdvancedChatPage() {
  const params = useParams()
  const agentName = decodeURIComponent(params.agentName as string)

  // Get user from auth store
  const { user } = useAuthStore()
  
  // State
  const [agentId, setAgentId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [agent, setAgent] = useState<Agent | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [thinkingStatus, setThinkingStatus] = useState<string>('')
  const [toolStatus, setToolStatus] = useState<{
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
  } | null>(null)
  const [recentTools, setRecentTools] = useState<Array<{
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
  }>>([])
  const [agentLoadError, setAgentLoadError] = useState<string | null>(null)
  const [chatConfig, setChatConfig] = useState<ChatConfig | null>(null)
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false) // Default to collapsed
  const [totalMessages, setTotalMessages] = useState<number>(0)
  const [inputResetKey, setInputResetKey] = useState(0) // Key to force ChatInput remount
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null)

  // Demo placeholder widgets - dynamically generated from agent data
  const getDemoWidgets = () => ({
    layout: 'centered',
    show_sidebar: true,
    sidebar_widgets: [
      {
        type: 'profile',
        position: 'left',
        order: 1,
        content: {
          name: agent?.agent_name || 'AI Assistant',
          title: agent?.agent_type || 'Your Digital Assistant',
          bio: agent?.description || 'I can help you with questions, provide information, and assist with various tasks. Feel free to ask me anything!'
        }
      },
      {
        type: 'social',
        position: 'left',
        order: 2,
        title: 'Connect',
        content: {
          links: [
            { label: 'Twitter', handle: '@synkora', url: 'https://twitter.com/synkora', icon: '🐦' },
            { label: 'LinkedIn', handle: 'company/synkora', url: 'https://linkedin.com/company/synkora', icon: '💼' },
            { label: 'GitHub', handle: '@rajuniit/synkora-ai', url: 'https://github.com/rajuniit/synkora-ai', icon: '💻' },
            { label: 'Email', handle: 'hello@synkora.ai', url: 'mailto:hello@synkora.ai', icon: '✉️' }
          ]
        }
      },
      {
        type: 'stats',
        position: 'right',
        order: 1,
        title: 'Quick Stats',
        content: {
          items: [
            { label: 'Conversations', value: conversations.length.toLocaleString() },
            { label: 'Total Messages', value: totalMessages.toLocaleString() },
            { label: 'Success Rate', value: agent?.success_rate ? `${Math.round(agent.success_rate)}%` : 'N/A' },
            { label: 'Executions', value: agent?.execution_count ? agent.execution_count.toLocaleString() : '0' }
          ]
        }
      },
      {
        type: 'about',
        position: 'right',
        order: 2,
        title: 'About This Agent',
        content: {
          text: agent?.description || 'This is an AI-powered assistant designed to help you with your questions and tasks. Powered by advanced language models and customized for your specific needs. Ask me anything and I\'ll do my best to assist you!'
        }
      },
    ]
  })

  // Context data (will be populated from message metadata)
  // Note: These are set but currently not displayed in the UI
  const [, setSources] = useState<Source[]>([])
  const [, setKeyPeople] = useState<Person[]>([])
  const [, setNews] = useState<NewsItem[]>([])
  
  // Agent configuration
  // Note: These are fetched but currently not displayed in the UI
  const [, setMcpServers] = useState<any[]>([])
  const [, setKnowledgeBases] = useState<any[]>([])
  const [, setTools] = useState<any[]>([])
  const [, setContextFiles] = useState<any[]>([])

  // LLM Configs - Use hook to fetch LLM configs
  const { data: llmConfigs} = useAgentLLMConfigs(agentName, false)
  const [selectedModelId, setSelectedModelId] = useState<string | undefined>(undefined)

  useEffect(() => {
    if (llmConfigs && llmConfigs.length > 0 && !selectedModelId) {
      const defaultConfig = llmConfigs.find((config) => config.is_default && config.enabled)
      if (defaultConfig) {
        setSelectedModelId(defaultConfig.id)
      }
    }
  }, [llmConfigs, selectedModelId])
  
  const fetchAgentInfo = useCallback(async () => {
    try {
      const data = await apiClient.getAgentStats(agentName)

      if (!data.agent_id) {
        throw new Error('Agent ID not found in response')
      }
      
      const agentData = {
        agent_name: data.agent_name,
        agent_type: data.agent_type,
        description: data.description,
        avatar: data.avatar,
        status: data.status,
        model: data.llm_config?.model,
        provider: data.llm_config?.provider,
        suggestion_prompts: data.suggestion_prompts || [],
        likes_count: data.likes_count || 0,
        dislikes_count: data.dislikes_count || 0,
        usage_count: data.usage_count || 0,
        creator_name: data.creator_name,
        created_at: data.created_at,
        execution_count: data.execution_count || 0,
        success_rate: data.success_rate || 0,
        successful_executions: data.successful_executions || 0,
        failed_executions: data.failed_executions || 0,
      }
      setAgent(agentData)
      setAgentId(data.agent_id)
      setAgentLoadError(null)
    } catch (error) {
      console.error('Failed to fetch agent info:', error)
      const errorMessage = error instanceof Error ? error.message : 'Failed to load agent'
      setAgentLoadError(errorMessage)
    }
  }, [agentName])

  const fetchChatConfig = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/agents/${encodeURIComponent(agentName)}/chat-config`)
      if (response.ok) {
        const result = await response.json()
        if (result.success && result.data) {
          setChatConfig(result.data)
          // Apply customization to the page
          applyCustomization(result.data)
        }
      }
    } catch (error) {
      console.error('Failed to fetch chat config:', error)
      // Continue with default styling if config fetch fails
    }
  }, [agentName])

  const applyCustomization = (config: ChatConfig) => {
    // Apply CSS custom properties for theming
    const root = document.documentElement
    
    if (config.chat_primary_color) {
      root.style.setProperty('--chat-primary-color', config.chat_primary_color)
    }
    
    if (config.chat_background_color) {
      root.style.setProperty('--chat-background-color', config.chat_background_color)
    }
    
    if (config.chat_font_family) {
      root.style.setProperty('--chat-font-family', config.chat_font_family)
    }
  }

  // Get dynamic styles based on chat config
  const getChatStyles = () => {
    if (!chatConfig) return {}
    
    return {
      fontFamily: chatConfig.chat_font_family || undefined,
    }
  }


  const fetchAgentConfiguration = useCallback(async () => {
    if (!agentId) return

    try {
      // Fetch MCP servers
      const mcpData = await apiClient.getAgentMCPServers(agentId)
      setMcpServers(mcpData || [])

      // Fetch knowledge bases
      const kbData = await apiClient.getAgentKnowledgeBases(agentId)
      setKnowledgeBases(kbData || [])

      // Fetch tools
      const toolsData = await apiClient.getAgentToolsForAgent(agentId)
      setTools(toolsData || [])

      // Fetch context files
      const filesData = await apiClient.getAgentContextFiles(agentName)
      setContextFiles(filesData || [])
    } catch (error) {
      console.error('Failed to fetch agent configuration:', error)
    }
  }, [agentId, agentName])

  const loadConversations = useCallback(async () => {
    if (!agentId) return

    try {
      const convs = await apiClient.getAgentConversations(agentId, 50)
      setConversations(convs)
      
      // Calculate total messages across all conversations
      const total = convs.reduce((sum, conv) => sum + (conv.message_count || 0), 0)
      setTotalMessages(total)
      
      // Only set first conversation if truly none selected
      if (!currentConversation && convs.length > 0) {
        setCurrentConversation(convs[0])
      }
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }, [agentId]) // Removed currentConversation from dependencies

  // Track if we just created a new conversation (to skip loading messages)
  const skipLoadMessagesRef = useRef(false)

  // Load messages when conversation changes (skip if streaming or just created)
  useEffect(() => {
    if (currentConversation?.id && !isStreaming && !skipLoadMessagesRef.current) {
      loadConversationMessages(currentConversation.id)
    }
    // Reset the skip flag after checking
    if (skipLoadMessagesRef.current) {
      skipLoadMessagesRef.current = false
    }
  }, [currentConversation?.id]) // Only depend on ID to avoid unnecessary reloads

  const loadConversationMessages = async (conversationId: string) => {
    // Don't load if we're streaming - it would overwrite streaming messages
    if (isStreaming) return

    try {
      const msgs = await apiClient.getConversationMessages(conversationId)
      // Double-check we're not streaming before setting messages
      if (!isStreaming) {
        setMessages(
          msgs.map((msg: any) => ({
            id: msg.id,
            role: msg.role.toLowerCase(), // Convert "USER" -> "user", "ASSISTANT" -> "assistant"
            content: msg.content,
            timestamp: new Date(msg.created_at),
            sources: msg.metadata?.sources || [],
            metadata: msg.metadata || {},
          }))
        )
      }
    } catch (error) {
      console.error('Failed to load conversation messages:', error)
      if (!isStreaming) {
        setMessages([])
      }
    }
  }

  const createNewConversation = async (): Promise<Conversation | null> => {
    if (!agentId) return null

    try {
      const newConv = await apiClient.createAgentConversation(agentId, 'New Conversation')
      setConversations([newConv, ...conversations])
      // Skip loading messages for newly created conversation (it's empty)
      skipLoadMessagesRef.current = true
      setCurrentConversation(newConv)
      setMessages([])
      setSources([])
      setKeyPeople([])
      setNews([])
      return newConv
    } catch (error) {
      console.error('Failed to create conversation:', error)
      return null
    }
  }

  const handleNewChat = async () => {
    // Reset UI state immediately before async operation
    setInputResetKey(prev => prev + 1)
    setMessages([])
    setThinkingStatus('')
    setCurrentConversation(null) // Clear current conversation so handleSend creates a new one
    await createNewConversation()
  }

  const updateContextFromMessages = useCallback(() => {
    const allSources: Source[] = []
    const allPeople: Person[] = []
    const allNews: NewsItem[] = []

    messages.forEach((msg) => {
      // Handle sources from RAG
      if (msg.sources && msg.sources.length > 0) {
        msg.sources.forEach((source: any) => {
          allSources.push({
            title: source.kb_name || 'Knowledge Base',
            url: `#kb-${source.kb_id}`,
            snippet: source.text,
            relevance: source.score,
          })
        })
      }
      
      if (msg.metadata) {
        if (msg.metadata.sources) allSources.push(...msg.metadata.sources)
        if (msg.metadata.keyPeople) allPeople.push(...msg.metadata.keyPeople)
        if (msg.metadata.news) allNews.push(...msg.metadata.news)
      }
    })

    setSources(Array.from(new Map(allSources.map((s) => [s.url, s])).values()))
    setKeyPeople(Array.from(new Map(allPeople.map((p) => [p.name, p])).values()))
    setNews(Array.from(new Map(allNews.map((n) => [n.url, n])).values()))
  }, [messages])

  // Load agent info and chat config on mount
  useEffect(() => {
    fetchAgentInfo()
    fetchChatConfig()
  }, [agentName, fetchAgentInfo, fetchChatConfig])

  // Load conversations when agent ID is available
  useEffect(() => {
    if (agentId) {
      fetchAgentConfiguration()
      loadConversations()
    }
  }, [agentId, fetchAgentConfiguration, loadConversations])

  // Note: Messages are loaded by the useEffect at line 280-285 that watches currentConversation?.id
  // Removed duplicate useEffect here to prevent race conditions with streaming

  // Update context from messages — only run when not streaming to avoid running on every chunk
  useEffect(() => {
    if (messages.length > 0 && !isStreaming) {
      updateContextFromMessages()
    }
  }, [messages, isStreaming, updateContextFromMessages])

  const handleSend = async (message: string, attachments?: Attachment[]) => {
    // Allow sending if there's either a message or attachments
    if ((!message.trim() && (!attachments || attachments.length === 0)) || isStreaming) return

    // Track if this is the first message in a new conversation
    const isFirstMessage = messages.length === 0 || (currentConversation?.name === 'New Conversation')

    // Show user message and assistant placeholder immediately — before any API calls
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
      attachments: attachments,
    }

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      metadata: {
        sources: [],
      },
    }

    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setIsStreaming(true)
    setStreamStartTime(Date.now())
    setThinkingStatus('Thinking...')

    // Resolve or create conversation ID (non-blocking relative to UI update above)
    let activeConversation = currentConversation
    if (!currentConversation && agentId) {
      const newConv = await createNewConversation()
      if (newConv) {
        activeConversation = newConv
      } else {
        console.error('Failed to create conversation')
      }
    }

    // Update conversation name with first user message — fire and forget
    if (isFirstMessage && activeConversation?.id && message.trim()) {
      const truncatedName = message.trim().length > 50
        ? message.trim().substring(0, 50) + '...'
        : message.trim()
      apiClient.updateConversationName(activeConversation.id, truncatedName)
        .then(() => {
          setConversations(prev => prev.map(conv =>
            conv.id === activeConversation!.id
              ? { ...conv, name: truncatedName }
              : conv
          ))
          setCurrentConversation(prev => prev ? { ...prev, name: truncatedName } : prev)
        })
        .catch((error) => console.error('Failed to update conversation name:', error))
    }

    try {
      // Get the access token from secure storage
      const token = secureStorage.getAccessToken()
      
      const response = await fetch(`${API_URL}/api/v1/agents/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
        },
        body: JSON.stringify({
          agent_name: agentName,
          message: message,
          conversation_id: activeConversation?.id,
          attachments: attachments,
          llm_config_id: selectedModelId || undefined,
          conversation_history: messages.slice(-10).map((msg) => ({
            role: msg.role,
            content: msg.content,
          })),
        }),
      })

      if (!response.ok) {
        if (response.status === 402) {
          try {
            const errorData = await response.json()
            const msg = errorData?.detail?.message || errorData?.message || 'Insufficient credits or subscription issue.'
            throw new Error(msg)
          } catch (e) {
            if (e instanceof SyntaxError) throw new Error('Insufficient credits or subscription issue.')
            throw e
          }
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullResponse = ''
      let responseSources: Source[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue

          try {
            const jsonStr = line.slice(6).trim()
            if (jsonStr === '[DONE]') continue

            const data = JSON.parse(jsonStr)

            if (data.type === 'chunk') {
              fullResponse += data.content
              // Clear thinking status when we have actual content to display
              setThinkingStatus('')
              setMessages((prev: Message[]) => {
                const newMessages = [...prev]
                const lastIndex = newMessages.length - 1
                if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    content: fullResponse,
                  }
                }
                return newMessages
              })
            } else if (data.type === 'status') {
              if (!data.content.includes('completed')) {
                const statusText = data.content || 'Thinking...'
                setThinkingStatus(statusText)
              }
            } else if (data.type === 'tool_status') {
              // Handle rich tool status events with metrics
              const newToolStatus = {
                tool_name: data.tool_name,
                status: data.status as 'started' | 'completed' | 'error',
                description: data.description || `Using ${data.tool_name}`,
                details: data.details,
                duration_ms: data.duration_ms,
                input_tokens: data.input_tokens,
                output_tokens: data.output_tokens,
              }

              if (data.status === 'started') {
                setToolStatus(newToolStatus)
                setThinkingStatus(data.description || `Using ${data.tool_name}...`)
              } else if (data.status === 'completed') {
                // Add to recent tools list (keep last 5) with metrics
                setRecentTools(prev => {
                  const updated = [...prev, { ...newToolStatus, status: 'completed' as const }]
                  return updated.slice(-5)
                })
                setToolStatus(null)
              } else if (data.status === 'error') {
                setRecentTools(prev => {
                  const updated = [...prev, { ...newToolStatus, status: 'error' as const }]
                  return updated.slice(-5)
                })
                setToolStatus(null)
              }
            } else if (data.type === 'chart') {
              // Handle chart data
              setMessages((prev) => {
                const newMessages = [...prev]
                const lastIndex = newMessages.length - 1

                if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                  const currentMetadata = newMessages[lastIndex].metadata || {}
                  const currentCharts = currentMetadata.charts || []

                  // Transform chart data to match ChartData interface from types.ts
                  // Backend sends: {type: "chart", chart: {chart_type, library, title, data, ...}}
                  const chart = data.chart || data // Support both formats
                  const chartData = {
                    type: chart.chart_type || data.chart_type || 'bar',
                    title: chart.title || 'Chart',
                    data: chart.data || data.chart_data || {},
                    config: chart.config || data.chart_config || {}
                  }

                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    metadata: {
                      ...currentMetadata,
                      charts: [...currentCharts, chartData]
                    }
                  }
                }

                return newMessages
              })
            } else if (data.type === 'done') {
              setThinkingStatus('')
              const sources = data.sources || []
              responseSources = sources
              
              // Update message with sources and metadata (timing + tokens)
              setMessages((prev) => {
                const newMessages = [...prev]
                const lastIndex = newMessages.length - 1
                if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    sources: sources,
                    metadata: {
                      ...newMessages[lastIndex].metadata,
                      sources: sources,
                      usage: data.metadata ? {
                        input_tokens: data.metadata.input_tokens || 0,
                        output_tokens: data.metadata.output_tokens || 0,
                        total_tokens: data.metadata.total_tokens || 0
                      } : undefined,
                      timing: data.metadata ? {
                        duration: data.metadata.total_time,
                        time_to_first_token: data.metadata.time_to_first_token
                      } : undefined
                    },
                  }
                }
                return newMessages
              })
              
              // Reload conversations to update message count
              if (agentId) {
                loadConversations()
              }
            } else if (data.type === 'error') {
              console.error('Streaming error:', data.error)
              throw new Error(data.error)
            }
          } catch (e) {
            if (e instanceof SyntaxError) {
              console.error('SSE parse error:', e)
            } else {
              throw e
            }
          }
        }
      }

      // Update context sidebar with sources from the response
      if (responseSources.length > 0) {
        setSources((prev) => {
          const combined = [...prev, ...responseSources]
          return Array.from(new Map(combined.map((s) => [s.url || s.title, s])).values())
        })
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages((prev) => {
        const newMessages = [...prev]
        const lastIndex = newMessages.length - 1
        if (lastIndex >= 0 && newMessages[lastIndex]?.role === 'assistant') {
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
          }
        }
        return newMessages
      })
    } finally {
      setIsStreaming(false)
      setThinkingStatus('')
      setToolStatus(null)
      setRecentTools([])
      setStreamStartTime(null)
    }
  }

  const handleCopyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const handleRetry = (messageId: string) => {
    const messageIndex = messages.findIndex((m) => m.id === messageId)
    if (messageIndex > 0) {
      const previousUserMessage = messages[messageIndex - 1]
      if (previousUserMessage.role === 'user') {
        setMessages((prev) => prev.slice(0, messageIndex))
        handleSend(previousUserMessage.content)
      }
    }
  }

  // Render widget based on type
  const renderWidget = (widget: any) => {
    const primaryColor = chatConfig?.chat_primary_color || '#ff444f'
    
    switch (widget.type) {
      case 'profile':
        return (
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <div className="flex flex-col items-center text-center">
              <div 
                className="w-24 h-24 rounded-full mb-4 flex items-center justify-center text-white text-3xl font-bold shadow-lg"
                style={{ background: `linear-gradient(135deg, ${primaryColor}, ${primaryColor}dd)` }}
              >
                {agent?.avatar ? (
                  <img src={agent.avatar} alt={agent.agent_name} className="w-full h-full rounded-full object-cover" />
                ) : (
                  agent?.agent_name?.charAt(0).toUpperCase()
                )}
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-1">{widget.content?.name || agent?.agent_name}</h3>
              <p className="text-sm text-gray-600 mb-4">{widget.content?.title || agent?.description}</p>
              {widget.content?.bio && (
                <p className="text-xs text-gray-500 leading-relaxed">{widget.content.bio}</p>
              )}
            </div>
          </div>
        )
      
      case 'social':
        return (
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              {widget.title || 'Connect With Me'}
            </h3>
            <div className="space-y-2">
              {widget.content?.links?.map((link: any, idx: number) => (
                <a
                  key={idx}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-all group"
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-white shadow-sm"
                    style={{ background: `linear-gradient(135deg, ${primaryColor}, ${primaryColor}dd)` }}
                  >
                    {link.icon || '🔗'}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900 group-hover:text-gray-700">{link.label}</p>
                    <p className="text-xs text-gray-500">{link.handle || link.url}</p>
                  </div>
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>
              ))}
            </div>
          </div>
        )
      
      case 'resume':
        return (
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {widget.title || 'Resume'}
            </h3>
            <a
              href={widget.content?.url}
              download
              className="flex items-center justify-center gap-2 p-3 rounded-xl border-2 border-dashed hover:border-solid transition-all group"
              style={{ borderColor: primaryColor }}
            >
              <svg className="w-5 h-5" style={{ color: primaryColor }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-semibold" style={{ color: primaryColor }}>Download Resume</span>
            </a>
          </div>
        )
      
      case 'about':
        return (
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {widget.title || 'About'}
            </h3>
            
            {/* Agent Avatar */}
            {agent?.avatar && (
              <div className="flex justify-center mb-4">
                <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-gray-100 shadow-sm">
                  <img 
                    src={agent.avatar} 
                    alt={agent.agent_name} 
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
            )}
            
            {/* Description */}
            <div className="prose prose-sm max-w-none mb-4">
              <p className="text-xs text-gray-600 leading-relaxed">{widget.content?.text}</p>
            </div>
            
            {/* Interactions & Engagement Stats */}
            <div className="space-y-3 pt-4 border-t border-gray-100">
              {/* Interactions Count */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <span className="text-xs text-gray-600">Interactions</span>
                </div>
                <span className="text-sm font-semibold" style={{ color: primaryColor }}>
                  {agent?.usage_count?.toLocaleString() || '0'}
                </span>
              </div>
              
              {/* Likes & Dislikes */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1">
                    <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3zM7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3v11z" />
                    </svg>
                    <span className="text-xs text-gray-600">{agent?.likes_count || 0}</span>
                  </div>
                  <div className="flex items-center gap-1 ml-2">
                    <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3zm7-13h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17V2z" />
                    </svg>
                    <span className="text-xs text-gray-600">{agent?.dislikes_count || 0}</span>
                  </div>
                </div>
                <span className="text-xs text-gray-500">
                  {agent?.likes_count && agent?.dislikes_count 
                    ? `${Math.round((agent.likes_count / (agent.likes_count + agent.dislikes_count)) * 100)}% positive`
                    : 'No ratings yet'}
                </span>
              </div>
              
              {/* Creator */}
              {agent?.creator_name && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span className="text-xs text-gray-600">Created by</span>
                  </div>
                  <span className="text-xs font-semibold text-gray-900">{agent.creator_name}</span>
                </div>
              )}
              
              {/* Created Date */}
              {agent?.created_at && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs text-gray-600">Created</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(agent.created_at).toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric', 
                      year: 'numeric' 
                    })}
                  </span>
                </div>
              )}
            </div>
          </div>
        )
      
      case 'stats':
        return (
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <h3 className="text-sm font-bold text-gray-900 mb-4">{widget.title || 'Stats'}</h3>
            <div className="grid grid-cols-2 gap-3">
              {widget.content?.items?.map((stat: any, idx: number) => (
                <div key={idx} className="text-center p-3 rounded-xl bg-gray-50">
                  <p className="text-2xl font-bold" style={{ color: primaryColor }}>{stat.value}</p>
                  <p className="text-xs text-gray-600 mt-1">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        )
      
      case 'links':
        return (
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
            <h3 className="text-sm font-bold text-gray-900 mb-4">{widget.title || 'Quick Links'}</h3>
            <div className="space-y-2">
              {widget.content?.items?.map((link: any, idx: number) => (
                <a
                  key={idx}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 transition-all group"
                >
                  <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">{link.label}</span>
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              ))}
            </div>
          </div>
        )
      
      default:
        return null
    }
  }

  // Use demo widgets if no config from backend yet
  const demoWidgets = getDemoWidgets()
  const activeConfig = chatConfig?.sidebar_widgets ? chatConfig : demoWidgets
  const layout = activeConfig?.layout || 'centered'
  const showSidebar = true // Always show sidebar with demo widgets
  const leftWidgets = activeConfig?.sidebar_widgets?.filter((w: any) => w.position === 'left').sort((a: any, b: any) => (a.order || 0) - (b.order || 0)) || []
  const rightWidgets = activeConfig?.sidebar_widgets?.filter((w: any) => w.position === 'right').sort((a: any, b: any) => (a.order || 0) - (b.order || 0)) || []

  return (
    <div style={getChatStyles()} className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 custom-scrollbar-container">
      <style jsx global>{`
        /* Custom scrollbar styling */
        .custom-scrollbar-container ::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }

        .custom-scrollbar-container ::-webkit-scrollbar-track {
          background: transparent;
        }

        .custom-scrollbar-container ::-webkit-scrollbar-thumb {
          background: ${chatConfig?.chat_primary_color || '#ff444f'};
          border-radius: 3px;
        }

        .custom-scrollbar-container ::-webkit-scrollbar-thumb:hover {
          background: ${chatConfig?.chat_primary_color ? `${chatConfig.chat_primary_color}dd` : '#ff444f'};
        }

        /* Firefox scrollbar */
        .custom-scrollbar-container * {
          scrollbar-width: thin;
          scrollbar-color: ${chatConfig?.chat_primary_color || '#ff444f'} transparent;
        }
      `}</style>

      {/* Layout with Chat Left Sidebar + Chat + Right Widgets */}
      <div className="flex h-screen">
        {/* Left Sidebar - Chat History (Auto-collapse, hover to expand) */}
        <div 
          className="relative"
          onMouseEnter={() => setIsSidebarExpanded(true)}
          onMouseLeave={() => setIsSidebarExpanded(false)}
        >
          <div 
            className={`transition-all duration-300 ease-in-out ${isSidebarExpanded ? 'w-56' : 'w-14'} h-full bg-white border-r border-gray-200/80 shadow-sm relative overflow-hidden`}
          >
            {/* Collapsed State - Show Icons */}
            {!isSidebarExpanded && (
              <div className="flex flex-col h-full pt-3 bg-gray-50/50">
                {/* Synkora Logo */}
                <div className="flex justify-center mb-4">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                </div>

                {/* Navigation Icons */}
                <div className="flex-1 flex flex-col items-center space-y-2">
                  <button
                    onClick={() => window.location.href = '/agents'}
                    className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white hover:shadow-sm text-gray-500 hover:text-gray-700 transition-all"
                    title="Home"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                    </svg>
                  </button>

                  <button
                    onClick={() => {
                      if (conversations.length > 0) {
                        setCurrentConversation(conversations[0])
                      }
                    }}
                    className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white hover:shadow-sm text-gray-500 hover:text-gray-700 transition-all"
                    title="Chat History"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </button>
                </div>

                {/* Bottom Menu Icons */}
                <div className="pb-4 flex flex-col items-center space-y-2">
                  <button
                    onClick={() => window.location.href = '/settings/profile'}
                    className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white hover:shadow-sm text-gray-500 hover:text-gray-700 transition-all"
                    title="Profile"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </button>

                  <button
                    onClick={() => {
                      window.location.href = `/agents/${agentName}/edit`
                    }}
                    className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white hover:shadow-sm text-gray-500 hover:text-gray-700 transition-all"
                    title="Settings"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>

                  <button
                    onClick={() => {
                      localStorage.removeItem('token')
                      window.location.href = '/signin'
                    }}
                    className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-all"
                    title="Logout"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                  </button>
                </div>
              </div>
            )}
            
            {/* Expanded State - Show Full Sidebar */}
            {isSidebarExpanded && (
              <ChatSidebar
                sessions={conversations.map(conv => ({
                  id: conv.id,
                  title: conv.name,
                  agentName: agentName,
                  timestamp: new Date(conv.updated_at),
                  isActive: conv.id === currentConversation?.id,
                  lastMessage: conv.message_count ? `${conv.message_count} messages` : undefined,
                }))}
                activeSessionId={currentConversation?.id}
                onSessionSelect={(sessionId) => {
                  const conv = conversations.find(c => c.id === sessionId)
                  if (conv) {
                    setCurrentConversation(conv)
                  }
                }}
                onNewChat={handleNewChat}
                chatConfig={chatConfig}
                agentName={agent?.agent_name}
                agentAvatar={agent?.avatar}
              />
            )}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Center - Chat Widget */}
          <div className="flex-1 flex flex-col h-screen bg-white">
              {/* Error Message */}
              {agentLoadError && (
                <div className="flex-shrink-0 p-3 bg-red-50 border-b border-red-200">
                  <div className="flex items-center gap-2 text-red-800">
                    <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <div>
                      <p className="font-semibold text-sm">Failed to load agent</p>
                      <p className="text-xs">{agentLoadError}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Compact Chat Header */}
              <div className="flex-shrink-0 px-5 py-3 border-b border-gray-100 bg-gradient-to-r" style={{ 
                background: `linear-gradient(135deg, ${chatConfig?.chat_primary_color || '#ff444f'}15, ${chatConfig?.chat_primary_color || '#ff444f'}05)` 
              }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-md"
                      style={{ background: `linear-gradient(135deg, ${chatConfig?.chat_primary_color || '#ff444f'}, ${chatConfig?.chat_primary_color || '#ff444f'}dd)` }}
                    >
                      {agent?.avatar ? (
                        <img src={agent.avatar} alt={agent.agent_name} className="w-full h-full rounded-full object-cover" />
                      ) : (
                        agent?.agent_name?.charAt(0).toUpperCase()
                      )}
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">{chatConfig?.chat_title || agent?.agent_name}</h2>
                      <p className="text-xs font-medium text-gray-500">Online • Ready to help</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {llmConfigs && llmConfigs.length > 0 && (
                      <select
                        value={selectedModelId || ''}
                        onChange={(e) => setSelectedModelId(e.target.value)}
                        className="text-xs px-2 py-1 border border-gray-200 rounded-lg focus:outline-none focus:ring-2"
                        style={{
                          '--tw-ring-color': chatConfig?.chat_primary_color || '#ff444f'
                        } as React.CSSProperties}
                      >
                        {llmConfigs.map((config) => (
                          <option key={config.id} value={config.id}>
                            {config.model_name}
                          </option>
                        ))}
                      </select>
                    )}
                    <button
                      onClick={handleNewChat}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-600 hover:text-gray-900"
                      title="New Chat"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      <span className="text-xs font-medium">New chat</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto">
                <ChatMessages
                  messages={messages}
                  isStreaming={isStreaming}
                  onCopyMessage={handleCopyMessage}
                  onRetry={handleRetry}
                  thinkingStatus={thinkingStatus}
                  toolStatus={toolStatus}
                  recentTools={recentTools}
                  streamStartTime={streamStartTime}
                  suggestionPrompts={agent?.suggestion_prompts || []}
                  onSuggestionClick={(prompt) => handleSend(prompt)}
                  chatConfig={chatConfig}
                  agentAvatar={agent?.avatar}
                  userAvatar={user?.avatar}
                  agentName={agent?.agent_name}
                />
              </div>

              {/* Chat Input */}
              <ChatInput
                key={`chat-input-${inputResetKey}`}
                onSend={handleSend}
                disabled={isStreaming || !agentId || !!agentLoadError}
                conversationId={currentConversation?.id}
                chatConfig={chatConfig}
                placeholder={
                  agentLoadError
                    ? 'Agent failed to load'
                    : !agentId
                      ? 'Loading agent...'
                      : chatConfig?.chat_placeholder || 'Type your message...'
                }
              />
          </div>

          {/* Right Sidebar - Widgets */}
          {showSidebar && rightWidgets.length > 0 && (
            <div className="w-72 bg-white border-l border-gray-200/80 shadow-sm overflow-y-auto p-3 space-y-3">
              {rightWidgets.map((widget, idx) => (
                <div key={idx}>{renderWidget(widget)}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
