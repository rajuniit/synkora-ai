'use client'

import { useEffect, useCallback, useRef } from 'react'
import { useLiveLabStore } from '@/lib/store/liveLabStore'
import { getExecutions } from '@/lib/api/live-lab'
import { ActiveExecutionsList } from '@/components/live-lab/ActiveExecutionsList'
import { RecentExecutionsList } from '@/components/live-lab/RecentExecutionsList'
import {
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  Wrench,
} from 'lucide-react'

export default function LiveLabPage() {
  const {
    activeExecutions,
    recentExecutions,
    isLoading,
    setActiveExecutions,
    setRecentExecutions,
    setLoading,
  } = useLiveLabStore()

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const data = await getExecutions('all', 100)
      setActiveExecutions(data.active || [])
      setRecentExecutions(data.recent || [])
    } catch (err) {
      console.error('Failed to fetch executions:', err)
    } finally {
      setLoading(false)
    }
  }, [setActiveExecutions, setRecentExecutions, setLoading])

  useEffect(() => {
    fetchData()
    intervalRef.current = setInterval(fetchData, 3000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchData])

  const successCount = recentExecutions.filter((e) => e.status === 'complete').length
  const errorCount = recentExecutions.filter((e) => e.status === 'error').length
  const totalToolsUsed = recentExecutions.reduce((sum, e) => sum + e.total_tools, 0)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Live Lab</h1>
              <p className="text-gray-600 mt-1 text-sm hidden sm:block">
                Real-time agent execution monitoring
              </p>
            </div>

            {activeExecutions.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-full flex-shrink-0">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm font-medium text-green-600">
                  {activeExecutions.length} running
                </span>
              </div>
            )}
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-emerald-100 rounded-lg">
                  <Activity className="w-4 h-4 text-emerald-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Active Now</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{activeExecutions.length}</p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <Clock className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Recent</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{recentExecutions.length}</p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-green-100 rounded-lg">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Successful</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{successCount}</p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <XCircle className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Errors</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{errorCount}</p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-1">
                <div className="p-1.5 bg-red-100 rounded-lg">
                  <Wrench className="w-4 h-4 text-red-600" />
                </div>
                <p className="text-xs font-medium text-gray-600">Tools Used</p>
              </div>
              <p className="text-2xl font-bold text-gray-900">{totalToolsUsed}</p>
            </div>
          </div>
        </div>

        {/* Active Executions */}
        <section className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <h2 className="text-base font-semibold text-gray-900">Active Executions</h2>
            <span className="text-xs text-gray-500 ml-1">
              {activeExecutions.length} running
            </span>
          </div>
          <ActiveExecutionsList executions={activeExecutions} />
        </section>

        {/* Recent Executions */}
        <section>
          <h2 className="text-base font-semibold text-gray-900 mb-3">Recent Executions</h2>
          <RecentExecutionsList executions={recentExecutions} />
        </section>
      </div>
    </div>
  )
}
