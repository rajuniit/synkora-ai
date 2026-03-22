'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { Bell, CheckCircle, Loader2 } from 'lucide-react'
import { subscribeToAgent } from '@/lib/api/subscriptions'

export default function SubscribePage() {
  const params = useParams()
  const agentId = params?.agentId as string

  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    try {
      setStatus('loading')
      const result = await subscribeToAgent(agentId, email.trim())
      setMessage(result.message)
      setStatus('success')
    } catch (err: any) {
      setMessage(err.message || 'Something went wrong. Please try again.')
      setStatus('error')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-white to-pink-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 w-full max-w-md p-8">
        {status === 'success' ? (
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">You&apos;re subscribed!</h2>
            <p className="text-gray-600 text-sm">{message}</p>
            <p className="text-gray-400 text-xs mt-3">
              You&apos;ll receive an email each time a new report is published. Check your inbox for a confirmation.
            </p>
          </div>
        ) : (
          <>
            <div className="text-center mb-6">
              <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bell className="w-7 h-7 text-red-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">Subscribe to reports</h1>
              <p className="text-gray-500 text-sm mt-2">
                Get this agent&apos;s scheduled reports delivered to your inbox automatically.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-colors"
                />
              </div>

              {status === 'error' && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{message}</p>
              )}

              <button
                type="submit"
                disabled={status === 'loading'}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-medium rounded-lg transition-all shadow-sm hover:shadow-md disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {status === 'loading' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Subscribing...
                  </>
                ) : (
                  <>
                    <Bell className="w-4 h-4" />
                    Subscribe
                  </>
                )}
              </button>

              <p className="text-center text-xs text-gray-400">
                You can unsubscribe at any time via the link in each email.
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
