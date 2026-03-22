'use client'

import { useState } from 'react'
import { AgentPricing } from '@/types/billing'
import { DollarSign, Percent } from 'lucide-react'

interface AgentPricingFormProps {
  agentId: string
  initialPricing?: AgentPricing
  onSubmit: (pricing: Partial<AgentPricing>) => Promise<void>
  loading?: boolean
}

export default function AgentPricingForm({
  agentId,
  initialPricing,
  onSubmit,
  loading = false,
}: AgentPricingFormProps) {
  const [formData, setFormData] = useState({
    pricing_model: initialPricing?.pricing_model || 'free',
    base_credit_cost: initialPricing?.base_credit_cost || 0,
    subscription_price_monthly: initialPricing?.subscription_price_monthly || 0,
    min_credits_per_use: initialPricing?.min_credits_per_use || 1,
    is_monetized: initialPricing?.is_monetized || false,
    revenue_share_percentage: initialPricing?.revenue_share_percentage || 0,
    is_public: initialPricing?.is_public ?? true,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit({
      agent_id: agentId,
      ...formData,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Pricing Model
        </label>
        <select
          value={formData.pricing_model}
          onChange={(e) =>
            setFormData({ ...formData, pricing_model: e.target.value as 'free' | 'per_use' | 'subscription' })
          }
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        >
          <option value="free">Free</option>
          <option value="per_use">Per Use</option>
          <option value="subscription">Subscription</option>
        </select>
      </div>

      {formData.pricing_model === 'per_use' && (
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Base Credit Cost
          </label>
          <div className="relative mt-1">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <DollarSign className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.base_credit_cost}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  base_credit_cost: parseFloat(e.target.value),
                })
              }
              className="block w-full rounded-md border border-gray-300 pl-10 pr-3 py-2 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="0.00"
            />
          </div>
        </div>
      )}

      {formData.pricing_model === 'subscription' && (
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Monthly Subscription Price
          </label>
          <div className="relative mt-1">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <DollarSign className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.subscription_price_monthly || 0}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  subscription_price_monthly: parseFloat(e.target.value),
                })
              }
              className="block w-full rounded-md border border-gray-300 pl-10 pr-3 py-2 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="0.00"
            />
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Minimum Credits Per Use
        </label>
        <div className="relative mt-1">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <Percent className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="number"
            min="1"
            value={formData.min_credits_per_use}
            onChange={(e) =>
              setFormData({
                ...formData,
                min_credits_per_use: parseInt(e.target.value),
              })
            }
            className="block w-full rounded-md border border-gray-300 pl-10 pr-3 py-2 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="1"
          />
        </div>
        <p className="mt-1 text-sm text-gray-500">
          Minimum number of credits consumed per agent use
        </p>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {loading ? 'Saving...' : 'Save Pricing'}
        </button>
      </div>
    </form>
  )
}
