'use client'

import { useSubscription } from '@/hooks/useBilling'
import { AlertCircle, TrendingUp, Users, Database, Zap, Lock } from 'lucide-react'
import Link from 'next/link'

interface ResourceLimit {
  name: string
  current: number
  limit: number
  icon: React.ReactNode
  upgradeRequired?: boolean
}

interface PlanLimitsCardProps {
  limits?: ResourceLimit[]
  showUpgradePrompt?: boolean
}

export default function PlanLimitsCard({ limits, showUpgradePrompt = true }: PlanLimitsCardProps) {
  const { subscription } = useSubscription()

  // Default limits if not provided
  const defaultLimits: ResourceLimit[] = [
    {
      name: 'Agents',
      current: 0,
      limit: subscription?.plan?.max_agents || 5,
      icon: <Users className="h-5 w-5" />,
    },
    {
      name: 'Knowledge Bases',
      current: 0,
      limit: subscription?.plan?.max_knowledge_bases || 3,
      icon: <Database className="h-5 w-5" />,
    },
    {
      name: 'Team Members',
      current: 0,
      limit: subscription?.plan?.max_team_members || 5,
      icon: <Users className="h-5 w-5" />,
    },
  ]

  const displayLimits = limits || defaultLimits

  const getProgressColor = (current: number, limit: number) => {
    const percentage = (current / limit) * 100
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 75) return 'bg-yellow-500'
    return 'bg-emerald-500'
  }

  const getProgressPercentage = (current: number, limit: number) => {
    if (limit === -1) return 0 // Unlimited
    return Math.min((current / limit) * 100, 100)
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Plan Usage</h3>
        {subscription && (
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-800">
            {subscription.plan_name}
          </span>
        )}
      </div>

      <div className="space-y-4">
        {displayLimits.map((resource, index) => {
          const isUnlimited = resource.limit === -1
          const isNearLimit = !isUnlimited && resource.current >= resource.limit * 0.9
          const isAtLimit = !isUnlimited && resource.current >= resource.limit

          return (
            <div key={index} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="text-gray-600">{resource.icon}</div>
                  <span className="text-sm font-medium text-gray-700">
                    {resource.name}
                  </span>
                  {resource.upgradeRequired && (
                    <Lock className="h-4 w-4 text-gray-400" />
                  )}
                </div>
                <span className="text-sm text-gray-600">
                  {isUnlimited ? (
                    <span className="font-medium text-emerald-600">Unlimited</span>
                  ) : (
                    <>
                      <span className={isAtLimit ? 'font-semibold text-red-600' : ''}>
                        {resource.current}
                      </span>
                      {' / '}
                      {resource.limit}
                    </>
                  )}
                </span>
              </div>

              {!isUnlimited && (
                <>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                    <div
                      className={`h-full transition-all duration-300 ${getProgressColor(
                        resource.current,
                        resource.limit
                      )}`}
                      style={{
                        width: `${getProgressPercentage(resource.current, resource.limit)}%`,
                      }}
                    />
                  </div>

                  {isNearLimit && (
                    <div className="flex items-start gap-2 rounded-md bg-yellow-50 p-2">
                      <AlertCircle className="h-4 w-4 flex-shrink-0 text-yellow-600" />
                      <p className="text-xs text-yellow-800">
                        {isAtLimit
                          ? `You've reached your ${resource.name.toLowerCase()} limit. Upgrade to add more.`
                          : `You're approaching your ${resource.name.toLowerCase()} limit.`}
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          )
        })}
      </div>

      {showUpgradePrompt && (
        <div className="mt-6 rounded-lg bg-gradient-to-r from-emerald-50 to-teal-50 p-4">
          <div className="flex items-start gap-3">
            <TrendingUp className="h-5 w-5 flex-shrink-0 text-emerald-600" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-gray-900">
                Need more resources?
              </h4>
              <p className="mt-1 text-xs text-gray-600">
                Upgrade your plan to unlock higher limits and premium features.
              </p>
              <Link
                href="/billing/subscription"
                className="mt-2 inline-flex items-center text-sm font-medium text-emerald-600 hover:text-emerald-700"
              >
                View Plans
                <Zap className="ml-1 h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
