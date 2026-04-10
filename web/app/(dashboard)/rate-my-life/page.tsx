'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { LifeAuditForm } from '@/components/rate-my-life/LifeAuditForm'
import { createLifeAudit, listLifeAudits } from '@/lib/api/rate-my-life'
import type { DimensionAnswer, LifeAuditResult } from '@/lib/api/rate-my-life'

export default function RateMyLifePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [history, setHistory] = useState<LifeAuditResult[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listLifeAudits()
      .then((res) => setHistory(res.audits || []))
      .catch(() => {})
  }, [])

  const handleSubmit = async (answers: DimensionAnswer[]) => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await createLifeAudit(answers)
      router.push(`/rate-my-life/${result.id}`)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create life audit'
      setError(msg)
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
      <div className="max-w-4xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-100 text-red-600 text-xs font-semibold mb-4">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            AI Life Audit
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight mb-2">Rate My Life</h1>
          <p className="text-gray-500 max-w-lg mx-auto">
            Answer 6 quick questions, then watch 5 specialist AI agents debate your scores
            in real-time and produce a shareable life scorecard.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Form */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 mb-10">
          <LifeAuditForm onSubmit={handleSubmit} isLoading={isLoading} />
        </div>

        {/* History */}
        {history.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">
              Past Audits
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {history.map((audit) => (
                <button
                  key={audit.id}
                  onClick={() => router.push(`/rate-my-life/${audit.id}`)}
                  className="text-left bg-white rounded-xl border border-gray-200 p-4 hover:border-red-200 hover:shadow-sm transition-all"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className="text-2xl font-bold tabular-nums"
                      style={{ color: audit.scores.overall < 4 ? '#ef4444' : audit.scores.overall <= 6 ? '#f59e0b' : '#22c55e' }}
                    >
                      {audit.scores.overall}
                    </span>
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      audit.status === 'completed'
                        ? 'bg-green-50 text-green-600'
                        : audit.status === 'active'
                          ? 'bg-blue-50 text-blue-600'
                          : 'bg-gray-50 text-gray-500'
                    }`}>
                      {audit.status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400">
                    {new Date(audit.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
