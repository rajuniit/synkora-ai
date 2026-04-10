'use client'

import { useEffect, useRef } from 'react'

interface LiveWorkspaceProps {
  content: string
  isStreaming: boolean
}

export function LiveWorkspace({ content, isStreaming }: LiveWorkspaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isStreaming && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [content, isStreaming])

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-gray-200 bg-white flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Output</h3>
        {isStreaming && (
          <span className="flex items-center gap-1.5 text-[10px] text-green-600">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            Streaming
          </span>
        )}
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 bg-white">
        {!content ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-gray-500">
              {isStreaming ? 'Waiting for output...' : 'No output generated'}
            </p>
          </div>
        ) : (
          <div className="prose prose-sm max-w-none">
            <div className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed font-mono">
              {content}
              {isStreaming && (
                <span className="inline-block w-2 h-4 bg-red-500 animate-pulse ml-0.5 align-text-bottom" />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
