'use client'

import { useState, useEffect } from 'react'
import { X, Copy, Link, Check, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { createConversationShare, listConversationShares, revokeConversationShare } from '@/lib/api/conversations'
import type { ShareLink } from '@/lib/api/conversations'

interface ShareModalProps {
  conversationId: string
  onClose: () => void
}

const PRESET_DURATIONS = [
  { label: '1h', seconds: 3600 },
  { label: '6h', seconds: 21600 },
  { label: '24h', seconds: 86400 },
  { label: '7d', seconds: 604800 },
]

function formatExpiry(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now()
  if (diff <= 0) return 'Expired'
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  if (h >= 24) return `${Math.floor(h / 24)}d ${h % 24}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

export function ShareModal({ conversationId, onClose }: ShareModalProps) {
  const [selectedPreset, setSelectedPreset] = useState(3600)
  const [customHours, setCustomHours] = useState('')
  const [useCustom, setUseCustom] = useState(false)
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [shares, setShares] = useState<ShareLink[]>([])
  const [isLoadingShares, setIsLoadingShares] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadShares()
  }, [conversationId])

  async function loadShares() {
    setIsLoadingShares(true)
    try {
      const data = await listConversationShares(conversationId)
      setShares(data)
    } catch {
      // Non-fatal — show empty list
    } finally {
      setIsLoadingShares(false)
    }
  }

  async function handleGenerate() {
    setError(null)
    const seconds = useCustom
      ? Math.round(parseFloat(customHours) * 3600)
      : selectedPreset

    if (!seconds || seconds <= 0) {
      setError('Please enter a valid duration.')
      return
    }
    if (seconds > 604800) {
      setError('Maximum duration is 7 days.')
      return
    }

    setIsCreating(true)
    try {
      const share = await createConversationShare(conversationId, seconds)
      setGeneratedUrl(share.share_url || '')
      await loadShares()
    } catch {
      setError('Failed to generate share link. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  async function handleRevoke(share: ShareLink) {
    try {
      await revokeConversationShare(share.id, conversationId)
      setShares(prev => prev.filter(s => s.id !== share.id))
      if (generatedUrl && shares.find(s => s.id === share.id)) {
        setGeneratedUrl(null)
      }
    } catch {
      setError('Failed to revoke share link.')
    }
  }

  async function handleCopy(url: string) {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Failed to copy to clipboard.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Link size={18} className="text-gray-600" />
            <h2 className="text-base font-semibold text-gray-900">Share Conversation</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={16} className="text-gray-500" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Duration picker */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Expiry duration</p>
            <div className="flex flex-wrap gap-2">
              {PRESET_DURATIONS.map(({ label, seconds }) => (
                <button
                  key={label}
                  onClick={() => { setSelectedPreset(seconds); setUseCustom(false) }}
                  className={cn(
                    'px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors',
                    !useCustom && selectedPreset === seconds
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'
                  )}
                >
                  {label}
                </button>
              ))}
              <button
                onClick={() => setUseCustom(true)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors',
                  useCustom
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'
                )}
              >
                Custom
              </button>
            </div>

            {useCustom && (
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="number"
                  min="0.1"
                  max="168"
                  step="0.5"
                  placeholder="Hours"
                  value={customHours}
                  onChange={e => setCustomHours(e.target.value)}
                  className="w-24 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300"
                />
                <span className="text-sm text-gray-500">hours</span>
              </div>
            )}
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={isCreating}
            className="w-full py-2.5 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isCreating ? 'Generating…' : 'Generate Share Link'}
          </button>

          {error && (
            <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}

          {/* Freshly generated URL */}
          {generatedUrl && (
            <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5">
              <span className="flex-1 text-xs text-gray-700 truncate font-mono">{generatedUrl}</span>
              <button
                onClick={() => handleCopy(generatedUrl)}
                className="flex-shrink-0 flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                {copied ? <Check size={13} className="text-green-600" /> : <Copy size={13} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          )}

          {/* Active links */}
          {shares.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Active Links</p>
              <div className="space-y-2">
                {isLoadingShares ? (
                  <p className="text-sm text-gray-400">Loading…</p>
                ) : (
                  shares.map(share => (
                    <div
                      key={share.id}
                      className="flex items-center justify-between bg-gray-50 rounded-xl px-3 py-2.5 gap-2"
                    >
                      <span className="text-xs text-gray-500 truncate">
                        Expires in {formatExpiry(share.expires_at)}
                      </span>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {share.share_url && (
                          <button
                            onClick={() => handleCopy(share.share_url!)}
                            className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors"
                            title="Copy link"
                          >
                            <Copy size={13} className="text-gray-500" />
                          </button>
                        )}
                        <button
                          onClick={() => handleRevoke(share)}
                          className="p-1.5 hover:bg-red-50 rounded-lg transition-colors"
                          title="Revoke"
                        >
                          <Trash2 size={13} className="text-gray-400 hover:text-red-500" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
