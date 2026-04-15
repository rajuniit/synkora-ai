'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { ArrowLeft, Box, CheckCircle, Info, Loader2, TestTube, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/api/client'

interface SandboxStatus {
  sandbox_service_url: string | null
  sandbox_available: boolean
}

export default function ComputeSettingsPage() {
  const router = useRouter()
  const [status, setStatus] = useState<SandboxStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    apiClient.request('GET', '/api/v1/compute/status')
      .then(setStatus)
      .catch(() => toast.error('Failed to load compute status'))
      .finally(() => setLoading(false))
  }, [])

  const handleTest = async () => {
    setTesting(true)
    try {
      const data = await apiClient.request('POST', '/api/v1/compute/test')
      if (data.success) {
        toast.success(`Sandbox test passed (${data.latency_ms}ms)`)
      } else {
        toast.error(data.error || 'Sandbox test failed')
      }
    } catch {
      toast.error('Sandbox test failed')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-violet-50/60 via-white to-indigo-50/40 p-4 md:p-6">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <button
            onClick={() => router.push('/settings')}
            className="inline-flex items-center gap-2 text-violet-600 hover:text-violet-700 font-medium mb-3 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Settings
          </button>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-violet-100 rounded-lg">
              <Box className="w-6 h-6 text-violet-600" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Compute</h1>
              <p className="text-gray-500 mt-0.5 text-sm">Sandbox service for agent code execution</p>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-8 h-8 text-violet-500 animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">synkora-sandbox</h2>
              <div className="flex items-start gap-3">
                {status?.sandbox_available ? (
                  <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
                )}
                <div className="text-sm text-gray-700 space-y-1">
                  <p className={status?.sandbox_available ? 'text-emerald-700 font-medium' : 'text-red-600 font-medium'}>
                    {status?.sandbox_available ? 'Service is running' : 'Service unavailable'}
                  </p>
                  {status?.sandbox_service_url && (
                    <p className="text-xs text-gray-400 font-mono">{status.sandbox_service_url}</p>
                  )}
                </div>
              </div>

              <div className="mt-4 bg-gray-50 rounded-lg px-4 py-3 flex items-start gap-2">
                <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                <p className="text-xs text-gray-500 leading-relaxed">
                  Each agent gets an isolated workspace directory. Workspaces are ephemeral —
                  they are created at conversation start and deleted when the conversation ends.
                  No configuration required.
                </p>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handleTest}
                disabled={testing || !status?.sandbox_available}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-lg hover:bg-violet-100 transition-all disabled:opacity-50"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
                Test Sandbox
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
