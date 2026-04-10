'use client'

import { useEffect, useCallback, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getDebate, getDebateStartStreamUrl, stopDebate } from '@/lib/api/war-room'
import type { DebateEvent } from '@/lib/api/war-room'
import { useWarRoomStore } from '@/lib/store/warRoomStore'
import { secureStorage } from '@/lib/auth/secure-storage'
import { DebateArena } from '@/components/war-room/DebateArena'
import { ArrowLeft, GitPullRequest, ExternalLink, PlugZap } from 'lucide-react'
import { ConnectAgentModal } from '@/components/war-room/ConnectAgentModal'
import { cn } from '@/lib/utils/cn'

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: 'Ready to Start', color: 'text-gray-500' },
  active: { label: 'Live', color: 'text-green-600' },
  synthesizing: { label: 'Synthesizing Verdict...', color: 'text-amber-600' },
  completed: { label: 'Completed', color: 'text-blue-600' },
  error: { label: 'Error', color: 'text-red-600' },
}

export default function DebateSessionPage() {
  const params = useParams()
  const router = useRouter()
  const debateId = params.id as string
  const abortRef = useRef<AbortController | null>(null)
  const [showConnectModal, setShowConnectModal] = useState(false)

  const { currentDebate, streamingParticipantId, streamingContent, setDebate, clearDebate, handleEvent } =
    useWarRoomStore()

  const startStream = useCallback(async () => {
    const token = secureStorage.getAccessToken()
    const url = getDebateStartStreamUrl(debateId)
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
            // skip
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      console.error('Debate stream error:', err)
    }
  }, [debateId, handleEvent])

  useEffect(() => {
    async function load() {
      try {
        const debate = await getDebate(debateId)
        setDebate(debate)
      } catch (err) {
        console.error('Failed to load debate:', err)
        router.push('/war-room')
      }
    }
    load()
    return () => {
      abortRef.current?.abort()
      clearDebate()
    }
  }, [debateId, setDebate, clearDebate, router])

  if (!currentDebate) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-gray-200 border-t-red-500 rounded-full animate-spin" />
      </div>
    )
  }

  const statusInfo = STATUS_CONFIG[currentDebate.status] || STATUS_CONFIG.pending
  const canStart = currentDebate.status === 'pending' || currentDebate.status === 'error'
  const isLive = currentDebate.status === 'active' || currentDebate.status === 'synthesizing'

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="mx-4 mt-4 bg-white/80 backdrop-blur-sm rounded-lg shadow-sm border border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => router.push('/war-room')} className="text-gray-500 hover:text-gray-700 flex-shrink-0">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900 truncate">{currentDebate.topic}</h2>
              <div className="flex items-center gap-3 mt-0.5">
                <span className={cn('text-xs font-medium flex items-center gap-1.5', statusInfo.color)}>
                  {isLive && <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />}
                  {statusInfo.label}
                </span>
                <span className="text-[11px] text-gray-500">
                  {currentDebate.participants.length} agents | Round {currentDebate.current_round}/{currentDebate.rounds}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {canStart && (
              <button
                onClick={() => router.push(`/war-room/create?edit=${debateId}`)}
                className="px-3 py-1.5 text-xs text-gray-600 border border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors font-medium"
              >
                Edit
              </button>
            )}
            {currentDebate.allow_external && currentDebate.share_token && (
              <button
                onClick={() => setShowConnectModal(true)}
                className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded-lg hover:border-red-300 hover:bg-red-50 transition-colors font-medium inline-flex items-center gap-1.5"
              >
                <PlugZap className="w-3.5 h-3.5" />
                Connect Agent
              </button>
            )}
            {currentDebate.share_token && (
              <button
                onClick={() => {
                  const url = `${window.location.origin}/war-room/${currentDebate.share_token}/live`
                  navigator.clipboard.writeText(url)
                }}
                className="px-3 py-1.5 text-xs text-gray-600 border border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors"
              >
                Copy Share Link
              </button>
            )}
            {isLive && (
              <button
                onClick={async () => {
                  try {
                    abortRef.current?.abort()
                    const updated = await stopDebate(debateId)
                    setDebate(updated)
                  } catch (err) {
                    console.error('Failed to stop debate:', err)
                  }
                }}
                className="px-4 py-1.5 bg-red-500 text-white text-xs font-medium rounded-lg hover:bg-red-600 transition-all"
              >
                Stop Debate
              </button>
            )}
            {canStart && (
              <button
                onClick={startStream}
                className="px-4 py-1.5 bg-gradient-to-r from-red-500 to-red-600 text-white text-xs font-medium rounded-lg hover:from-red-600 hover:to-red-700 transition-all"
              >
                Start Debate
              </button>
            )}
          </div>
        </div>

        {/* PR Context Badge */}
        {currentDebate.debate_metadata?.context?.type === 'github_pr' && (
          <div className="flex items-center gap-2 mt-3 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
            <GitPullRequest className="w-4 h-4 text-green-600 flex-shrink-0" />
            <span className="text-xs font-medium text-gray-700 truncate">
              {currentDebate.debate_metadata.context.pr_title}
            </span>
            <span className="text-[10px] text-gray-400 flex-shrink-0">
              {currentDebate.debate_metadata.context.repo_full_name}#{currentDebate.debate_metadata.context.pr_number}
            </span>
            {currentDebate.debate_metadata.context.github_url && (
              <a
                href={currentDebate.debate_metadata.context.github_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        )}

        {/* Participant pills */}
        <div className="flex items-center gap-2 mt-3 overflow-x-auto pb-1">
          {currentDebate.participants.map((p) => (
            <span
              key={p.id}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium text-gray-700 border flex-shrink-0"
              style={{ backgroundColor: `${p.color}10`, borderColor: `${p.color}30` }}
            >
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
              {p.agent_name}
              {p.role && <span className="text-gray-500">({p.role})</span>}
              {p.is_external && <span className="text-red-600 text-[10px]">EXT</span>}
            </span>
          ))}
        </div>
      </div>

      {/* Arena */}
      <DebateArena
        messages={currentDebate.messages}
        participants={currentDebate.participants}
        streamingParticipantId={streamingParticipantId}
        streamingContent={streamingContent}
        verdict={currentDebate.verdict}
      />

      {/* Connect Agent Modal */}
      {currentDebate.share_token && (
        <ConnectAgentModal
          isOpen={showConnectModal}
          onClose={() => setShowConnectModal(false)}
          shareToken={currentDebate.share_token}
          topic={currentDebate.topic}
        />
      )}
    </div>
  )
}
