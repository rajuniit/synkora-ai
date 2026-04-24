import { getSharedConversation } from '@/lib/api/conversations'
import { SharedChatView } from './SharedChatView'

interface Props {
  params: Promise<{ token: string }>
}

export default async function SharePage({ params }: Props) {
  const { token } = await params

  let data = null
  let error: 'not_found' | 'error' | null = null

  try {
    data = await getSharedConversation(token)
  } catch (e: any) {
    error = e?.message === 'not_found' ? 'not_found' : 'error'
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-sm px-6">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">Link not available</h1>
          <p className="text-sm text-gray-500">
            This share link has expired, been revoked, or does not exist.
          </p>
        </div>
      </div>
    )
  }

  return <SharedChatView data={data} />
}
