'use client'

import { useParams } from 'next/navigation'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { ArrowLeft, BookOpen, LayoutGrid, Share2, Zap } from 'lucide-react'
import { apiClient } from '@/lib/api/client'
import { WikiBrowser } from '@/components/knowledge-autopilot/WikiBrowser'
import { WikiGraph } from '@/components/knowledge-autopilot/WikiGraph'
import { cn } from '@/lib/utils/cn'

export default function WikiPage() {
  const params = useParams()
  const kbId = params.id as string
  const [kbName, setKbName] = useState('')
  const [view, setView] = useState<'list' | 'graph'>('list')

  useEffect(() => {
    apiClient.getKnowledgeBase(kbId).then((data: any) => {
      setKbName(data.name || 'Knowledge Base')
    }).catch(() => {
      setKbName('Knowledge Base')
    })
  }, [kbId])

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      <div className="border-b border-gray-200 bg-white px-4 md:px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href={`/knowledge-bases/${kbId}`}
              className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={18} />
              <span className="text-sm font-medium">Back</span>
            </Link>
            <div className="w-px h-6 bg-gray-200" />
            <div className="w-9 h-9 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center shadow-sm shadow-primary-500/20">
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight text-gray-900">{kbName} <span className="text-primary-500">Wiki</span></h1>
              <p className="text-[11px] text-gray-400 font-medium tracking-wide">AI-COMPILED KNOWLEDGE ARTICLES</p>
            </div>
          </div>

          {/* View toggle */}
          <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
            <button
              onClick={() => setView('list')}
              className={cn(
                'flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg transition-all',
                view === 'list'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              Articles
            </button>
            <button
              onClick={() => setView('graph')}
              className={cn(
                'flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-lg transition-all',
                view === 'graph'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <Share2 className="w-3.5 h-3.5" />
              Knowledge Graph
            </button>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        {view === 'list' ? (
          <WikiBrowser kbId={kbId} kbName={kbName} />
        ) : (
          <WikiGraph kbId={kbId} />
        )}
      </div>
    </div>
  )
}
