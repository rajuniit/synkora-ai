'use client'

import { useState } from 'react'
import { useSubscription, useSubscriptionPlans } from '@/hooks/useBilling'
import { SubscriptionPlanCard } from '@/components/billing'
import {
  Loader2,
  CreditCard,
  Calendar,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react'

export default function SubscriptionManagementPage() {
  const { subscription, loading: subscriptionLoading, upgrade, cancel, reactivate } = useSubscription()
  const { plans, loading: plansLoading } = useSubscriptionPlans()
  const [processingPlanId, setProcessingPlanId] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [resuming, setResuming] = useState(false)

  const handleUpgrade = async (planId: string) => {
    try {
      setProcessingPlanId(planId)
      await upgrade({ plan_id: planId })
      alert('Subscription upgraded successfully!')
    } catch (error) {
      console.error('Failed to upgrade subscription:', error)
      alert('Failed to upgrade subscription. Please try again.')
    } finally {
      setProcessingPlanId(null)
    }
  }

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? It will remain active until the end of the current billing period.')) {
      return
    }

    try {
      setCancelling(true)
      await cancel()
      alert('Subscription cancelled successfully. It will remain active until the end of the current period.')
    } catch (error) {
      console.error('Failed to cancel subscription:', error)
      alert('Failed to cancel subscription. Please try again.')
    } finally {
      setCancelling(false)
    }
  }

  const handleResume = async () => {
    try {
      setResuming(true)
      await reactivate()
      alert('Subscription resumed successfully!')
    } catch (error) {
      console.error('Failed to resume subscription:', error)
      alert('Failed to resume subscription. Please try again.')
    } finally {
      setResuming(false)
    }
  }

  if (subscriptionLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Subscription Management</h1>
        <p className="mt-2 text-gray-600">
          Manage your subscription plan and billing settings
        </p>
      </div>

      {/* Current Subscription Details */}
      {subscription && (
        <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Current Plan</h2>
            {subscription.status === 'active' && !subscription.cancel_at_period_end && (
              <span className="flex items-center rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
                <CheckCircle className="mr-1 h-4 w-4" />
                Active
              </span>
            )}
            {subscription.cancel_at_period_end && (
              <span className="flex items-center rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-800">
                <AlertCircle className="mr-1 h-4 w-4" />
                Cancels at period end
              </span>
            )}
            {subscription.status === 'cancelled' && (
              <span className="flex items-center rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800">
                <XCircle className="mr-1 h-4 w-4" />
                Cancelled
              </span>
            )}
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <h3 className="mb-4 text-lg font-medium text-gray-900">Plan Details</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Plan Name</dt>
                  <dd className="mt-1 text-sm text-gray-900">{subscription.plan_name}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1 text-sm capitalize text-gray-900">
                    {subscription.status}
                  </dd>
                </div>
                {subscription.stripe_subscription_id && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Subscription ID</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {subscription.stripe_subscription_id}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <div>
              <h3 className="mb-4 text-lg font-medium text-gray-900">Billing Information</h3>
              <dl className="space-y-3">
                {subscription.current_period_start && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Current Period Start</dt>
                    <dd className="mt-1 flex items-center text-sm text-gray-900">
                      <Calendar className="mr-2 h-4 w-4 text-gray-400" />
                      {new Date(subscription.current_period_start).toLocaleDateString()}
                    </dd>
                  </div>
                )}
                {subscription.current_period_end && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      {subscription.cancel_at_period_end ? 'Cancels On' : 'Renews On'}
                    </dt>
                    <dd className="mt-1 flex items-center text-sm text-gray-900">
                      <Calendar className="mr-2 h-4 w-4 text-gray-400" />
                      {new Date(subscription.current_period_end).toLocaleDateString()}
                    </dd>
                  </div>
                )}
                {subscription.stripe_customer_id && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Customer ID</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {subscription.stripe_customer_id}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 flex gap-4 border-t border-gray-200 pt-6">
            {subscription.cancel_at_period_end ? (
              <button
                onClick={handleResume}
                disabled={resuming}
                className="flex items-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {resuming ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Resuming...
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Resume Subscription
                  </>
                )}
              </button>
            ) : subscription.status === 'active' && (
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="flex items-center rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                {cancelling ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Cancelling...
                  </>
                ) : (
                  <>
                    <XCircle className="mr-2 h-4 w-4" />
                    Cancel Subscription
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Available Plans */}
      <div>
        <h2 className="mb-4 text-xl font-semibold text-gray-900">
          {subscription ? 'Upgrade or Change Plan' : 'Choose a Plan'}
        </h2>
        {plansLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {plans.map((plan) => (
              <SubscriptionPlanCard
                key={plan.id}
                plan={plan}
                currentPlanId={subscription?.plan_id}
                onSelect={handleUpgrade}
                loading={processingPlanId === plan.id}
              />
            ))}
          </div>
        )}
      </div>

      {/* Payment Method Section */}
      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Payment Method</h3>
            <p className="mt-1 text-sm text-gray-600">
              Manage your payment methods and billing information
            </p>
          </div>
          <button className="flex items-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            <CreditCard className="mr-2 h-4 w-4" />
            Manage Payment Methods
          </button>
        </div>
      </div>

      {/* Billing History Section */}
      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Billing History</h3>
            <p className="mt-1 text-sm text-gray-600">
              View and download your past invoices
            </p>
          </div>
          <button className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            View Invoices
          </button>
        </div>
      </div>
    </div>
  )
}
