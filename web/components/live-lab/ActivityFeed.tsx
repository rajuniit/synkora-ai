'use client'

import React, { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils/cn'
import type { ExecutionEvent } from '@/lib/api/live-lab'

interface ActivityFeedProps {
  events: ExecutionEvent[]
  isLive: boolean
}

function getEventIcon(event: ExecutionEvent): { icon: React.ReactNode; color: string } {
  if (event.type === 'tool_status') {
    if (event.status === 'started') {
      return {
        color: 'text-amber-600 bg-amber-50',
        icon: (
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        ),
      }
    }
    if (event.status === 'completed') {
      return {
        color: 'text-green-600 bg-green-50',
        icon: (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ),
      }
    }
    if (event.status === 'error') {
      return {
        color: 'text-red-600 bg-red-50',
        icon: (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ),
      }
    }
  }
  if (event.type === 'status') {
    return {
      color: 'text-blue-600 bg-blue-50',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    }
  }
  if (event.type === 'start') {
    return {
      color: 'text-blue-600 bg-blue-50',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        </svg>
      ),
    }
  }
  if (event.type === 'done') {
    return {
      color: 'text-green-600 bg-green-50',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    }
  }
  if (event.type === 'error') {
    return {
      color: 'text-red-600 bg-red-50',
      icon: (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    }
  }

  return {
    color: 'text-gray-500 bg-gray-100',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  }
}

function getEventText(event: ExecutionEvent): string {
  if (event.type === 'start') return `Agent started`
  if (event.type === 'status') return event.content || 'Processing...'
  if (event.type === 'tool_status') {
    const name = (event.tool_name || '').replace('internal_', '').replace(/_/g, ' ')
    if (event.status === 'started') return event.description || `Using ${name}`
    if (event.status === 'completed') {
      const duration = event.duration_ms ? ` (${event.duration_ms}ms)` : ''
      return `${name} completed${duration}`
    }
    if (event.status === 'error') return `${name} failed`
    return event.description || name
  }
  if (event.type === 'done') return 'Execution complete'
  if (event.type === 'error') return event.error || 'An error occurred'
  if (event.type === 'chunk') return '' // Don't show chunk events
  if (event.type === 'first_token') return '' // Internal metric
  return event.type
}

export function ActivityFeed({ events, isLive }: ActivityFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isLive && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events.length, isLive])

  const visibleEvents = events.filter((e) => {
    const text = getEventText(e)
    return text.length > 0
  })

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-gray-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Activity</h3>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {visibleEvents.length === 0 && (
          <p className="text-xs text-gray-500 text-center py-8">Waiting for events...</p>
        )}
        {visibleEvents.map((event, i) => {
          const { icon, color } = getEventIcon(event)
          const text = getEventText(event)
          return (
            <div
              key={i}
              className={cn(
                'flex items-start gap-2 py-1.5 px-2 rounded-md transition-colors',
                i === visibleEvents.length - 1 && isLive && 'bg-blue-50',
              )}
            >
              <div className={cn('flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center', color)}>
                {icon}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-700 leading-relaxed break-words">{text}</p>
                {event.type === 'tool_status' && event.details && Object.keys(event.details).length > 0 && (
                  <div className="mt-1 text-[10px] text-gray-400 font-mono truncate">
                    {Object.entries(event.details)
                      .slice(0, 2)
                      .map(([k, v]) => `${k}: ${String(v).slice(0, 60)}`)
                      .join(' | ')}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
