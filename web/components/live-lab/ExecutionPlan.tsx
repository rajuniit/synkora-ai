'use client'

import { cn } from '@/lib/utils/cn'
import type { ExecutionEvent } from '@/lib/api/live-lab'

interface ExecutionPlanProps {
  events: ExecutionEvent[]
  activeTools: string[]
  isLive: boolean
}

interface PlanStep {
  name: string
  displayName: string
  status: 'completed' | 'active' | 'pending'
  durationMs?: number
  description?: string
}

function buildPlanSteps(events: ExecutionEvent[], activeTools: string[]): PlanStep[] {
  const steps: PlanStep[] = []
  const seen = new Set<string>()

  for (const event of events) {
    if (event.type !== 'tool_status' || !event.tool_name) continue
    const name = event.tool_name
    if (seen.has(name) && event.status !== 'completed') continue

    const displayName = name.replace('internal_', '').replace(/_/g, ' ')

    if (event.status === 'started' && !seen.has(name)) {
      seen.add(name)
      steps.push({
        name,
        displayName,
        status: 'active',
        description: event.description,
      })
    }

    if (event.status === 'completed' || event.status === 'error') {
      const existing = steps.find((s) => s.name === name)
      if (existing) {
        existing.status = 'completed'
        existing.durationMs = event.duration_ms
      } else {
        seen.add(name)
        steps.push({
          name,
          displayName,
          status: 'completed',
          durationMs: event.duration_ms,
          description: event.description,
        })
      }
    }
  }

  // Mark currently active tools
  for (const tool of activeTools) {
    const step = steps.find((s) => s.name === tool)
    if (step) step.status = 'active'
  }

  return steps
}

export function ExecutionPlan({ events, activeTools, isLive }: ExecutionPlanProps) {
  const steps = buildPlanSteps(events, activeTools)

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-gray-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Execution Plan</h3>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {steps.length === 0 && (
          <p className="text-xs text-gray-500 text-center py-8">
            {isLive ? 'Steps will appear as tools are used...' : 'No tools were used'}
          </p>
        )}
        <div className="space-y-0.5">
          {steps.map((step, i) => (
            <div key={`${step.name}-${i}`} className="relative flex items-start gap-2.5 py-1.5">
              {/* Status icon */}
              <div className="flex-shrink-0 mt-0.5">
                {step.status === 'completed' && (
                  <div className="w-5 h-5 rounded-full bg-green-50 flex items-center justify-center">
                    <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
                {step.status === 'active' && (
                  <div className="w-5 h-5 rounded-full bg-amber-50 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  </div>
                )}
                {step.status === 'pending' && (
                  <div className="w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                  </div>
                )}
              </div>

              {/* Step content */}
              <div className="flex-1 min-w-0">
                <p
                  className={cn(
                    'text-xs font-medium capitalize',
                    step.status === 'completed' && 'text-gray-700',
                    step.status === 'active' && 'text-gray-900',
                    step.status === 'pending' && 'text-gray-400',
                  )}
                >
                  {step.displayName}
                </p>
                {step.durationMs !== undefined && (
                  <p className="text-[10px] text-gray-400 font-mono">{step.durationMs}ms</p>
                )}
              </div>

              {/* Connector line to next step */}
              {i < steps.length - 1 && (
                <div className="absolute left-[10px] top-6 w-px h-full bg-gray-200" />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
