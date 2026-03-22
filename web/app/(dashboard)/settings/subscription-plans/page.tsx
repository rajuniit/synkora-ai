'use client'

import { useState, useEffect } from 'react'
import { Lock } from 'lucide-react'
import { apiClient } from '@/lib/api/client'
import { usePermissions } from '@/hooks/usePermissions'

interface SubscriptionPlan {
  id: string
  name: string
  description: string
  price_monthly: number
  price_yearly: number
  credits_monthly: number
  features: string[]
  is_active: boolean
  stripe_price_id_monthly?: string
  stripe_price_id_yearly?: string
}

export default function SubscriptionPlansPage() {
  const { hasPermission, loading: permissionsLoading } = usePermissions()
  const [plans, setPlans] = useState<SubscriptionPlan[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPlans()
  }, [])

  const loadPlans = async () => {
    try {
      const response: any = await apiClient.request('GET', '/api/v1/subscription-plans')
      setPlans(response.data || [])
    } catch (error) {
      console.error('Failed to load plans:', error)
    } finally {
      setLoading(false)
    }
  }

  // Check if user is platform owner
  const isPlatformOwner = hasPermission('platform', 'read')

  if (loading || permissionsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // Check platform owner permission
  if (!isPlatformOwner) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-6 text-center">
          <Lock className="mx-auto h-12 w-12 text-primary-600 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Access Denied
          </h3>
          <p className="text-gray-600">
            You do not have permission to access subscription plans configuration. This feature is only available to platform owners.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-primary-50/30 to-white p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Subscription Plans</h1>
          <p className="mt-1 text-sm text-gray-600">Manage subscription tiers and pricing</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((plan) => (
            <div key={plan.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:border-primary-300 hover:shadow-md transition-all">
              <div className="mb-4">
                <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                <p className="text-gray-600 mt-1.5 text-sm">{plan.description}</p>
              </div>

              <div className="mb-5">
                <div className="flex items-baseline">
                  <span className="text-3xl font-bold text-gray-900">${plan.price_monthly}</span>
                  <span className="text-gray-600 ml-2 text-sm">/month</span>
                </div>
                {plan.price_yearly > 0 && (
                  <div className="mt-1.5 text-xs text-gray-600">
                    ${plan.price_yearly}/year (save ${(plan.price_monthly * 12 - plan.price_yearly).toFixed(2)})
                  </div>
                )}
              </div>

              <div className="mb-5">
                <div className="text-xs font-semibold text-primary-700 bg-primary-50 px-2.5 py-1.5 rounded-md inline-block">
                  {plan.credits_monthly.toLocaleString()} credits/month
                </div>
              </div>

              <div className="space-y-2.5 mb-5">
                {plan.features.map((feature, index) => (
                  <div key={index} className="flex items-start">
                    <svg className="w-4 h-4 text-emerald-500 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-xs text-gray-600">{feature}</span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-3.5 border-t border-gray-200">
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${plan.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-800'}`}>
                  {plan.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 bg-primary-50 border border-primary-200 rounded-lg p-5">
          <h3 className="text-sm font-semibold text-primary-800 mb-2">Seeding Instructions</h3>
          <p className="text-xs text-primary-700 mb-3">
            To seed the default subscription plans, run the following command in the API container:
          </p>
          <code className="block bg-primary-900 text-primary-100 p-3 rounded font-mono text-xs overflow-x-auto">
            docker-compose exec api python -c "from src.services.billing.seed_plans import seed_subscription_plans; import asyncio; asyncio.run(seed_subscription_plans())"
          </code>
        </div>
      </div>
    </div>
  )
}
