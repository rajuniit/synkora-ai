'use client'

import { useState } from 'react'
import { extractErrorMessage } from '@/lib/api/error'
import { Trash2, AlertTriangle } from 'lucide-react'

interface MemoryMessage {
  id: string
  role: string
  content: string
  created_at: string
}

interface Props {
  agentName: string
  messages: MemoryMessage[]
  onCleared: () => void
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function isRememberMessage(content: string): boolean {
  return content.startsWith('[AUTONOMOUS MEMORY]')
}

function parseMemoryKey(content: string): string {
  // Extract the JSON key from "[AUTONOMOUS MEMORY] {"key": "value", ...}"
  try {
    const jsonStr = content.replace('[AUTONOMOUS MEMORY]', '').trim()
    const data = JSON.parse(jsonStr)
    return Object.keys(data).join(', ')
  } catch {
    return content.slice(0, 60)
  }
}

export function AutonomousMemoryViewer({ agentName, messages, onCleared }: Props) {
  const [confirming, setConfirming] = useState(false)
  const [clearing, setClearing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const memoryMessages = messages.filter(m => m.role === 'SYSTEM' && isRememberMessage(m.content))
  const conversationMessages = messages.filter(m => !isRememberMessage(m.content) || m.role !== 'SYSTEM')

  async function handleClear() {
    setError(null)
    setClearing(true)
    try {
      const { apiClient } = await import('@/lib/api/client')
      await apiClient.request(
        'DELETE',
        `/api/v1/agents/${encodeURIComponent(agentName)}/autonomous/memory`
      )
      setConfirming(false)
      onCleared()
    } catch (err: any) {
      setError(extractErrorMessage(err, 'Clear failed'))
    } finally {
      setClearing(false)
    }
  }

  if (messages.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-gray-500">
        No memory yet. Memory is written after the first autonomous run.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Persistent key-value memory */}
      {memoryMessages.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Persistent facts</h3>
          <div className="divide-y divide-gray-100 border border-gray-200 rounded-md overflow-hidden">
            {memoryMessages.map(m => (
              <div key={m.id} className="flex items-center gap-3 px-4 py-2.5 bg-white">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 font-mono truncate">
                    {parseMemoryKey(m.content)}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{formatDate(m.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent conversation messages */}
      {conversationMessages.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Recent conversation</h3>
          <div className="space-y-2">
            {conversationMessages.slice(-10).map(m => (
              <div
                key={m.id}
                className={`rounded-md px-3 py-2 text-sm ${
                  m.role === 'USER'
                    ? 'bg-gray-100 text-gray-800'
                    : m.role === 'ASSISTANT'
                    ? 'bg-red-50 text-gray-800'
                    : 'bg-yellow-50 text-gray-700 text-xs font-mono'
                }`}
              >
                <span className="text-xs font-medium text-gray-500 uppercase mr-2">{m.role}</span>
                {m.content.slice(0, 300)}
                {m.content.length > 300 && '…'}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clear all button */}
      <div className="pt-2 border-t border-gray-200">
        {confirming ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertTriangle className="w-4 h-4" />
              This will delete all memory. Are you sure?
            </div>
            <button
              onClick={handleClear}
              disabled={clearing}
              className="px-3 py-1.5 rounded-md text-sm font-medium text-white bg-red-500 hover:bg-red-600 disabled:opacity-50"
            >
              {clearing ? 'Clearing…' : 'Yes, clear all'}
            </button>
            <button
              onClick={() => setConfirming(false)}
              className="px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 border border-gray-300 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            className="inline-flex items-center gap-2 text-sm text-red-600 hover:text-red-700"
          >
            <Trash2 className="w-4 h-4" />
            Clear all memory
          </button>
        )}
      </div>
    </div>
  )
}
