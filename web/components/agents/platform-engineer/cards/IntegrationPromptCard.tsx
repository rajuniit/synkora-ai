'use client'

import { ExternalLink, AlertCircle, KeyRound } from 'lucide-react'

interface Props {
  provider: string
  message: string
  connect_url: string
  type?: 'oauth' | 'api_key'
}

export function IntegrationPromptCard({ provider, message, connect_url, type = 'oauth' }: Props) {
  const displayName = provider.charAt(0).toUpperCase() + provider.slice(1).replace(/_/g, ' ')
  const isApiKey = type === 'api_key'

  return (
    <div className="border border-amber-200 bg-amber-50 rounded-xl p-4 space-y-3">
      <div className="flex items-start gap-2">
        {isApiKey
          ? <KeyRound className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
          : <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
        }
        <div>
          <p className="font-semibold text-amber-900 text-sm">
            {isApiKey ? `${displayName} API key required` : `${displayName} not connected`}
          </p>
          <p className="text-xs text-amber-700 mt-0.5 leading-relaxed">{message}</p>
        </div>
      </div>

      <a
        href={connect_url}
        className="flex items-center justify-center gap-1.5 px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-medium transition-colors w-full"
      >
        <ExternalLink className="h-3.5 w-3.5" />
        {isApiKey ? `Add ${displayName} API Key` : `Connect ${displayName}`}
      </a>
    </div>
  )
}
