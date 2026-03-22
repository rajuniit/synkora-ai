'use client'

import { useAuth } from '@/lib/hooks/useAuth'
import { useRouter } from 'next/navigation'
import { useSubscription, useCredits } from '@/hooks/useBilling'

export function Header() {
  const { user, signOut } = useAuth()
  const router = useRouter()
  const { subscription, loading: subscriptionLoading } = useSubscription()
  const { balance, loading: balanceLoading } = useCredits()

  const handleSignOut = async () => {
    await signOut()
    router.push('/signin')
  }

  const handleUpgradeClick = () => {
    router.push('/billing')
  }

  // Calculate credit display
  const usedCredits = balance?.used_credits || 0
  const totalCredits = balance?.total_credits || 0

  // Determine subscription status
  const subscriptionName = subscription?.plan_name || 'Free'
  const hasSubscription = subscription !== null
  
  // Combined loading state
  const loading = subscriptionLoading || balanceLoading

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-end px-6">
      <div className="flex items-center gap-4">
        {/* Credits Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-red-50 to-pink-50 border border-red-200 rounded-lg cursor-pointer hover:bg-gradient-to-r hover:from-red-100 hover:to-pink-100 transition-colors" onClick={() => router.push('/billing')}>
          <div className={`w-2 h-2 rounded-full ${hasSubscription ? 'bg-primary-500' : 'bg-gray-400'}`}></div>
          <span className="text-sm text-gray-600">{subscriptionName}</span>
          {loading ? (
            <span className="text-sm font-semibold text-gray-900 min-w-[60px] inline-block">&nbsp;</span>
          ) : (
            <span className="text-sm font-semibold text-gray-900 min-w-[60px] inline-block">
              {usedCredits}/{totalCredits}
            </span>
          )}
        </div>

        {/* Upgrade Button - Only show if no subscription */}
        {!hasSubscription && (
          <button 
            onClick={handleUpgradeClick}
            className="px-4 py-2 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white text-sm font-medium rounded-lg transition-all shadow-md hover:shadow-lg"
          >
            Upgrade now
          </button>
        )}

        {/* User Menu */}
        <div className="relative group">
          <button className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 rounded-lg transition-colors">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <span className="text-sm font-medium text-gray-700">{user?.name || 'User'}</span>
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Dropdown Menu */}
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
            <div className="py-1">
              <button
                onClick={handleSignOut}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
