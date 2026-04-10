'use client'

import { useEffect, useCallback, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getLifeAudit, getLifeAuditStreamUrl } from '@/lib/api/rate-my-life'
import { getDebate } from '@/lib/api/war-room'
import type { DebateEvent } from '@/lib/api/war-room'
import { useWarRoomStore } from '@/lib/store/warRoomStore'
import { secureStorage } from '@/lib/auth/secure-storage'
import { LifeDebateArena } from '@/components/rate-my-life/LifeDebateArena'
import { LifeScorecard } from '@/components/rate-my-life/LifeScorecard'
import type { LifeAuditResult } from '@/lib/api/rate-my-life'
import { cn } from '@/lib/utils/cn'

type ViewMode = 'debate' | 'scorecard'

export default function LifeAuditResultPage() {
  const params = useParams()
  const router = useRouter()
  const auditId = params.id as string
  const abortRef = useRef<AbortController | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>('debate')
  const [auditResult, setAuditResult] = useState<LifeAuditResult | null>(null)

  const { currentDebate, streamingParticipantId, streamingContent, setDebate, clearDebate, handleEvent } =
    useWarRoomStore()

  // Start the debate SSE stream
  const startStream = useCallback(async () => {
    const token = secureStorage.getAccessToken()
    const url = getLifeAuditStreamUrl(auditId)
    abortRef.current = new AbortController()

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
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
            const event: DebateEvent = JSON.parse(line.slice(6))
            handleEvent(event)
          } catch {
            // skip malformed events
          }
        }
      }

      // Stream completed -- fetch the parsed scores
      const result = await getLifeAudit(auditId)
      setAuditResult(result)
      setViewMode('scorecard')
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      console.error('Life audit stream error:', err)
    }
  }, [auditId, handleEvent])

  // Load the debate session on mount
  useEffect(() => {
    async function load() {
      try {
        // Load as a debate session (it IS a DebateSession)
        const debate = await getDebate(auditId)
        setDebate(debate)

        if (debate.status === 'completed') {
          // Already completed -- load scorecard directly
          const result = await getLifeAudit(auditId)
          setAuditResult(result)
          setViewMode('scorecard')
        } else if (debate.status === 'pending') {
          // Auto-start the debate
          startStream()
        }
      } catch (err) {
        console.error('Failed to load life audit:', err)
        router.push('/rate-my-life')
      }
    }
    load()
    return () => {
      abortRef.current?.abort()
      clearDebate()
    }
  }, [auditId, setDebate, clearDebate, router, startStream])

  if (!currentDebate) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-gray-200 border-t-red-500 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading your life audit...</p>
        </div>
      </div>
    )
  }

  const isLive = currentDebate.status === 'active' || currentDebate.status === 'synthesizing'
  const isCompleted = currentDebate.status === 'completed'

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="mx-4 mt-4 bg-white/80 backdrop-blur-sm rounded-lg shadow-sm border border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => router.push('/rate-my-life')}
              className="text-gray-500 hover:text-gray-700 flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900">Rate My Life</h2>
              <div className="flex items-center gap-3 mt-0.5">
                <span className={cn(
                  'text-xs font-medium flex items-center gap-1.5',
                  isLive ? 'text-green-600' : isCompleted ? 'text-blue-600' : 'text-gray-500'
                )}>
                  {isLive && <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />}
                  {isLive ? 'Agents debating...' : isCompleted ? 'Completed' : 'Starting...'}
                </span>
                <span className="text-[11px] text-gray-500">
                  {currentDebate.participants.length} agents | Round {currentDebate.current_round}/{currentDebate.rounds}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* View toggle */}
            {isCompleted && auditResult && (
              <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setViewMode('scorecard')}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium rounded-md transition-all',
                    viewMode === 'scorecard' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  Scorecard
                </button>
                <button
                  onClick={() => setViewMode('debate')}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium rounded-md transition-all',
                    viewMode === 'debate' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  Debate
                </button>
              </div>
            )}

            {/* Share */}
            {currentDebate.share_token && isCompleted && (
              <button
                onClick={() => {
                  const url = `${window.location.origin}/war-room/${currentDebate.share_token}/live`
                  navigator.clipboard.writeText(url)
                }}
                className="px-3 py-1.5 text-xs text-gray-600 border border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors font-medium"
              >
                Share
              </button>
            )}
          </div>
        </div>

        {/* Participant pills -- only show when not live (arena has its own status bar) */}
        {!isLive && (
          <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-1">
            {currentDebate.participants.map((p) => (
              <span
                key={p.id}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium text-gray-700 border flex-shrink-0"
                style={{ backgroundColor: `${p.color}10`, borderColor: `${p.color}30` }}
              >
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                {p.agent_name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      {viewMode === 'scorecard' && auditResult ? (
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <LifeScorecard
              scores={auditResult.scores}
              highlights={auditResult.agent_highlights}
              verdict={auditResult.verdict}
              shareToken={currentDebate.share_token}
            />
          </div>
        </div>
      ) : (
        <LifeDebateArena
          messages={currentDebate.messages}
          participants={currentDebate.participants}
          streamingParticipantId={streamingParticipantId}
          streamingContent={streamingContent}
          verdict={currentDebate.verdict}
          currentRound={currentDebate.current_round}
          totalRounds={currentDebate.rounds}
        />
      )}
    </div>
  )
}
