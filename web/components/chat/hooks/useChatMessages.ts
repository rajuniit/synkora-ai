/**
 * Custom hook for managing chat messages
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { Message, Attachment } from '../types'
import { generateId } from '../utils'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

interface UseChatMessagesProps {
  agentName: string
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

interface UseChatMessagesReturn {
  messages: Message[]
  isStreaming: boolean
  sendMessage: (content: string, attachments?: Attachment[]) => Promise<void>
  clearMessages: () => void
  addMessage: (message: Message) => void
  thinkingStatus: string
  toolStatus: ToolStatus | null
  recentTools: ToolStatus[]
}

export function useChatMessages({ agentName }: UseChatMessagesProps): UseChatMessagesReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [thinkingStatus, setThinkingStatus] = useState('')
  const [toolStatus, setToolStatus] = useState<ToolStatus | null>(null)
  const [recentTools, setRecentTools] = useState<ToolStatus[]>([])
  // Debounce timer ref for localStorage saves — avoids 50+ synchronous writes
  // during a single streaming response
  const saveHistoryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load chat history from localStorage ONLY on initial mount
  // Never reload while component is active to prevent overwriting streamed content
  useEffect(() => {
    loadChatHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentName]) // Only depend on agentName changes, not isStreaming

  // Save chat history whenever messages change.
  // Debounced to 1.5 s — during streaming a 500-token response fires 50+ state
  // updates.  Without debouncing that means 50+ synchronous JSON.stringify +
  // localStorage.setItem calls on the main thread per response.
  useEffect(() => {
    if (messages.length === 0) return
    if (saveHistoryTimerRef.current) clearTimeout(saveHistoryTimerRef.current)
    saveHistoryTimerRef.current = setTimeout(saveChatHistory, 1500)
    return () => {
      if (saveHistoryTimerRef.current) {
        clearTimeout(saveHistoryTimerRef.current)
        saveHistoryTimerRef.current = null
      }
    }
  }, [messages, saveChatHistory])

  const loadChatHistory = useCallback(() => {
    try {
      const historyKey = `chat_history_${agentName}`
      const savedHistory = localStorage.getItem(historyKey)
      if (savedHistory) {
        const parsed = JSON.parse(savedHistory)
        setMessages(parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        })))
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }, [agentName])
  
  const saveChatHistory = useCallback(() => {
    try {
      const historyKey = `chat_history_${agentName}`
      localStorage.setItem(historyKey, JSON.stringify(messages))
    } catch (error) {
      console.error('Failed to save chat history:', error)
    }
  }, [agentName, messages])

  const clearMessages = useCallback(() => {
    setMessages([])
    try {
      const historyKey = `chat_history_${agentName}`
      localStorage.removeItem(historyKey)
    } catch (error) {
      console.error('Failed to clear chat history:', error)
    }
  }, [agentName])

  const addMessage = useCallback((message: Message) => {
    setMessages((prev: Message[]) => [...prev, message])
  }, [])

  const sendMessage = useCallback(async (content: string, attachments?: Attachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) {
      return
    }
    if (isStreaming) {
      return
    }

    // Add user message
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
      attachments
    }

    setMessages((prev: Message[]) => [...prev, userMessage])
    setIsStreaming(true)
    setThinkingStatus('Thinking...')

    // Create assistant message placeholder
    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date()
    }

    setMessages((prev: Message[]) => [...prev, assistantMessage])

    try {
      const response = await fetch(`${API_URL}/api/v1/agents/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          agent_name: agentName,
          message: content,
          attachments,
          conversation_history: messages.map((msg: Message) => ({
            role: msg.role,
            content: msg.content,
            attachments: msg.attachments
          }))
        }),
      })

      // Handle HTTP errors before trying to read the stream
      if (!response.ok) {
        let errorMessage = 'An error occurred while processing your request.'

        // Handle specific HTTP status codes
        if (response.status === 413) {
          errorMessage = 'The conversation has grown too large. Please clear the chat history and start a new conversation.'
        } else if (response.status === 429) {
          errorMessage = 'Rate limit exceeded. Please wait a moment and try again.'
        } else if (response.status === 401 || response.status === 403) {
          errorMessage = 'Authentication error. Please refresh the page and try again.'
        } else if (response.status >= 500) {
          errorMessage = 'Server error. Please try again later.'
        }

        throw new Error(errorMessage)
      }

      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let startTime: number | null = null
      let elapsedInterval: ReturnType<typeof setInterval> | null = null

      // Helper function to process a single SSE line
      const processLine = (line: string) => {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'start') {
              startTime = Date.now() / 1000
              // Update thinking status with elapsed time
              // 500 ms — 2 re-renders/sec instead of 10 while waiting for first token
              elapsedInterval = setInterval(() => {
                if (startTime) {
                  const elapsed = ((Date.now() / 1000) - startTime).toFixed(1)
                  setThinkingStatus(`Thinking... ${elapsed}s`)
                }
              }, 500)
            } else if (data.type === 'first_token') {
              if (elapsedInterval) {
                clearInterval(elapsedInterval)
                elapsedInterval = null
              }
              setThinkingStatus('')
            } else if (data.type === 'status') {
              // Update thinking status with backend messages
              setThinkingStatus(data.content || 'Processing...')
            } else if (data.type === 'tool_status') {
              // Handle rich tool status events with metrics
              const newToolStatus: ToolStatus = {
                tool_name: data.tool_name,
                status: data.status,
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
            } else if (data.type === 'chunk') {
              setThinkingStatus('') // Clear thinking status once we start getting content
              setMessages((prev: Message[]) => {
                const newMessages = [...prev]
                const lastIndex = newMessages.length - 1
                if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    content: newMessages[lastIndex].content + data.content
                  }
                }
                return newMessages
              })
            } else if (data.type === 'done') {
              // Handle completion with sources and metadata
              if (elapsedInterval) {
                clearInterval(elapsedInterval)
                elapsedInterval = null
              }
              setThinkingStatus('')
              setMessages((prev: Message[]) => {
                const newMessages = [...prev]
                const lastIndex = newMessages.length - 1
                if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                  // CRITICAL FIX: Only use data.content if no chunks were streamed
                  // For multi-agent workflows, chunks are already streamed, so don't overwrite
                  const currentContent = newMessages[lastIndex].content
                  const finalContent = currentContent || data.content || ''

                  // Extract metadata from done event
                  const metadata = data.metadata || {}

                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    content: finalContent,
                    sources: data.sources,
                    metadata: {
                      ...newMessages[lastIndex].metadata,
                      workflow: data.workflow_metadata,
                      // Token usage - include all available fields
                      usage: metadata.input_tokens || metadata.output_tokens || metadata.total_tokens ? {
                        input_tokens: metadata.input_tokens || 0,
                        output_tokens: metadata.output_tokens || 0,
                        total_tokens: metadata.total_tokens || (metadata.input_tokens || 0) + (metadata.output_tokens || 0)
                      } : undefined,
                      // Timing information
                      timing: metadata.total_time || metadata.time_to_first_token ? {
                        duration: metadata.total_time,
                        time_to_first_token: metadata.time_to_first_token
                      } : undefined
                    }
                  }
                }
                return newMessages
              })
            } else if (data.type === 'chart') {
              // Handle chart data - transform to match ChartData interface
              setMessages((prev: Message[]) => {
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
            } else if (data.type === 'error') {
              console.error('Streaming error:', data.error)
              if (elapsedInterval) {
                clearInterval(elapsedInterval)
                elapsedInterval = null
              }
              setThinkingStatus('')
              setMessages((prev: Message[]) => {
                const newMessages = [...prev]
                const lastIndex = newMessages.length - 1
                const errorContent = `Error: ${data.error}`

                // If last message is assistant, update it with error
                if (lastIndex >= 0 && newMessages[lastIndex].role === 'assistant') {
                  newMessages[lastIndex] = {
                    ...newMessages[lastIndex],
                    content: data.error,
                    isError: true
                  }
                } else {
                  // No assistant message exists yet - create one with the error
                  newMessages.push({
                    id: `error-${Date.now()}`,
                    role: 'assistant',
                    content: data.error,
                    isError: true,
                    timestamp: new Date()
                  })
                }
                return newMessages
              })
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE event:', line, parseError)
          }
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          // Process any remaining data in buffer when stream ends
          if (buffer.trim()) {
            const remainingLines = buffer.split('\n')
            for (const line of remainingLines) {
              processLine(line)
            }
          }
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')

        buffer = lines.pop() || ''

        for (const line of lines) {
          processLine(line)
        }
      }

      // After stream ends, check if assistant message is empty (error may not have been received)
      setMessages((prev: Message[]) => {
        const newMessages = [...prev]
        const lastMessage = newMessages[newMessages.length - 1]
        if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.content) {
          // No content was received - show a fallback error
          lastMessage.content = 'Error: Failed to get a response. Please check your API key configuration and try again.'
        }
        return newMessages
      })
    } catch (error) {
      console.error('Failed to send message:', error)
      setThinkingStatus('')
      setMessages((prev: Message[]) => {
        const newMessages = [...prev]
        const lastMessage = newMessages[newMessages.length - 1]
        if (lastMessage.role === 'assistant') {
          const errorMsg = error instanceof Error ? error.message : 'Sorry, I encountered an error. Please try again.'
          lastMessage.content = errorMsg
          lastMessage.isError = true
        }
        return newMessages
      })
    } finally {
      setIsStreaming(false)
      setThinkingStatus('')
      setToolStatus(null)
      setRecentTools([])
    }
  }, [agentName, messages, isStreaming])

  return {
    messages,
    isStreaming,
    sendMessage,
    clearMessages,
    addMessage,
    thinkingStatus,
    toolStatus,
    recentTools,
  }
}
