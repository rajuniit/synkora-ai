'use client'

import { useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useLiveLabStore } from '@/lib/store/liveLabStore'
import { getExecution, getExecutionStreamUrl } from '@/lib/api/live-lab'
import type { ExecutionEvent } from '@/lib/api/live-lab'
import { secureStorage } from '@/lib/auth/secure-storage'
import { ArrowLeft } from 'lucide-react'
import { MetricsBar } from '@/components/live-lab/MetricsBar'
import { ActivityFeed } from '@/components/live-lab/ActivityFeed'
import { LiveWorkspace } from '@/components/live-lab/LiveWorkspace'
import { ExecutionPlan } from '@/components/live-lab/ExecutionPlan'

export default function ExecutionDetailPage() {
  const params = useParams()
  const router = useRouter()
  const executionId = params.executionId as string

  const {
    currentExecution,
    initCurrentExecution,
    clearCurrentExecution,
    appendEvent,
  } = useLiveLabStore()

  const abortRef = useRef<AbortController | null>(null)

  const startStream = useCallback(
    async (execId: string) => {
      const token = secureStorage.getAccessToken()
      const url = getExecutionStreamUrl(execId)

      abortRef.current = new AbortController()

      try {
        const response = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: abortRef.current.signal,
        })

        if (!response.ok || !response.body) return

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.trim() || !line.startsWith('data: ')) continue
            try {
              const event: ExecutionEvent = JSON.parse(line.slice(6))
              if (event.type === 'stream_end') return
              appendEvent(event)
            } catch {
              // skip malformed events
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        console.error('Stream error:', err)
      }
    },
    [appendEvent],
  )

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const exec = await getExecution(executionId)
        if (cancelled) return

        initCurrentExecution(exec)

        // Load stored events for completed executions
        if (exec.events && exec.events.length > 0) {
          for (const event of exec.events) {
            appendEvent(event)
          }
        }

        // If still running, start SSE stream for new events
        if (exec.status === 'running') {
          startStream(executionId)
        }
      } catch (err) {
        console.error('Failed to load execution:', err)
      }
    }

    load()

    return () => {
      cancelled = true
      abortRef.current?.abort()
      clearCurrentExecution()
    }
  }, [executionId, initCurrentExecution, clearCurrentExecution, appendEvent, startStream])

  if (!currentExecution) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-red-600 rounded-full animate-spin" />
      </div>
    )
  }

  const isLive = currentExecution.status === 'running'

  return (
    <div className="h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex flex-col overflow-hidden">
      {/* Back button */}
      <div className="flex items-center gap-3 px-4 md:px-6 py-3">
        <button
          onClick={() => router.push('/live-lab')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="font-medium text-sm">Back to Live Lab</span>
        </button>
      </div>

      {/* Metrics Bar */}
      <MetricsBar
        startedAt={currentExecution.metrics.startedAt}
        completedAt={currentExecution.metrics.completedAt || undefined}
        status={currentExecution.status}
        tokens={currentExecution.metrics.tokens}
        toolCount={currentExecution.metrics.toolCount}
        cost={currentExecution.metrics.cost}
        triggerSource={currentExecution.triggerSource}
        triggerDetail={currentExecution.triggerDetail || undefined}
        agentName={currentExecution.agentName}
        messagePreview={currentExecution.messagePreview}
      />

      {/* Three-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Activity Feed */}
        <div className="w-72 flex-shrink-0 border-r border-gray-200 bg-white hidden md:flex">
          <ActivityFeed events={currentExecution.events} isLive={isLive} />
        </div>

        {/* Center: Live Workspace */}
        <div className="flex-1 bg-gray-50 flex">
          <LiveWorkspace content={currentExecution.workspaceContent} isStreaming={isLive} />
        </div>

        {/* Right: Execution Plan */}
        <div className="w-64 flex-shrink-0 border-l border-gray-200 bg-white hidden lg:flex">
          <ExecutionPlan
            events={currentExecution.events}
            activeTools={currentExecution.activeTools}
            isLive={isLive}
          />
        </div>
      </div>

      {/* Error banner */}
      {currentExecution.status === 'error' && currentExecution.error && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200 flex items-center gap-2">
          <svg className="w-4 h-4 text-red-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-xs text-red-600">{currentExecution.error}</span>
        </div>
      )}
    </div>
  )
}
