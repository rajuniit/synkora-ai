'use client'

import { useEffect, useState } from 'react'
import { Clock, Wrench, BarChart3, DollarSign } from 'lucide-react'
import { TriggerSourceBadge } from './TriggerSourceBadge'

interface MetricsBarProps {
  startedAt: string
  completedAt?: string
  status: string
  tokens: number
  toolCount: number
  cost: number
  triggerSource: string
  triggerDetail?: string
  agentName: string
  messagePreview?: string
}

function formatElapsed(startedAt: string, completedAt?: string): string {
  const start = new Date(startedAt).getTime()
  const end = completedAt ? new Date(completedAt).getTime() : Date.now()
  const seconds = Math.floor((end - start) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  if (minutes < 60) return `${minutes}m ${remaining}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

export function MetricsBar({
  startedAt,
  completedAt,
  status,
  tokens,
  toolCount,
  cost,
  triggerSource,
  triggerDetail,
  agentName,
  messagePreview,
}: MetricsBarProps) {
  const [elapsed, setElapsed] = useState(() => formatElapsed(startedAt, completedAt))

  useEffect(() => {
    if (status !== 'running') {
      setElapsed(formatElapsed(startedAt, completedAt))
      return
    }
    const interval = setInterval(() => {
      setElapsed(formatElapsed(startedAt))
    }, 1000)
    return () => clearInterval(interval)
  }, [startedAt, completedAt, status])

  const statusConfig: Record<string, { label: string; color: string }> = {
    running: { label: 'Live', color: 'bg-green-500 animate-pulse' },
    complete: { label: 'Completed', color: 'bg-blue-500' },
    error: { label: 'Error', color: 'bg-red-500' },
    cancelled: { label: 'Cancelled', color: 'bg-gray-400' },
  }

  const statusInfo = statusConfig[status] || statusConfig.running

  return (
    <div className="bg-white border-b border-gray-200">
      {/* Top row: Agent name + task + status */}
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 bg-gradient-to-br from-red-500 to-red-600 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
            {agentName.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-gray-900 truncate">{agentName}</h2>
            {messagePreview && (
              <p className="text-xs text-gray-500 truncate max-w-md">&ldquo;{messagePreview}&rdquo;</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <TriggerSourceBadge source={triggerSource} detail={triggerDetail} size="md" />
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-white rounded-full ${statusInfo.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${status === 'running' ? 'bg-white animate-pulse' : 'bg-white/60'}`} />
            {statusInfo.label}
          </span>
        </div>
      </div>

      {/* Bottom row: Metrics */}
      <div className="flex items-center gap-6 px-4 py-2 border-t border-gray-100 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          <span className="font-mono text-gray-900">{elapsed}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Wrench className="w-3.5 h-3.5" />
          <span><span className="text-gray-900 font-medium">{toolCount}</span> tools</span>
        </div>
        <div className="flex items-center gap-1.5">
          <BarChart3 className="w-3.5 h-3.5" />
          <span><span className="text-gray-900 font-medium">{tokens.toLocaleString()}</span> tokens</span>
        </div>
        {cost > 0 && (
          <div className="flex items-center gap-1.5">
            <DollarSign className="w-3.5 h-3.5" />
            <span className="text-gray-900 font-medium">${cost.toFixed(4)}</span>
          </div>
        )}
      </div>
    </div>
  )
}
