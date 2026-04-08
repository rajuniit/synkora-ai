'use client'

import { CheckCircle, ExternalLink, MessageSquare } from 'lucide-react'
import Link from 'next/link'

interface Props {
  agentName: string
}

export function AgentCreatedCard({ agentName }: Props) {
  const encoded = encodeURIComponent(agentName)

  return (
    <div className="border border-green-200 bg-green-50 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
        <span className="font-semibold text-green-900 text-sm">Agent created: {agentName}</span>
      </div>

      <div className="flex gap-2">
        <Link
          href={`/agents/${encoded}/view`}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border border-green-300 text-green-700 hover:bg-green-100 rounded-lg text-xs font-medium transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          View Agent
        </Link>
        <Link
          href={`/agents/${encoded}/chat`}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-medium transition-colors"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Chat Now
        </Link>
      </div>
    </div>
  )
}
