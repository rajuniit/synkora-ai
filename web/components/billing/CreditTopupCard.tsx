'use client'

import { CreditTopup } from '@/types/billing'
import { Plus } from 'lucide-react'

interface CreditTopupCardProps {
  topup: CreditTopup
  onSelect: (topupId: string) => void
  loading?: boolean
}

export default function CreditTopupCard({
  topup,
  onSelect,
  loading = false,
}: CreditTopupCardProps) {
  const pricePerCredit = topup.price_paid / topup.credits_amount

  return (
    <div className="rounded-lg border-2 border-gray-200 bg-white p-6 transition-all hover:border-primary-400">
      <div className="mb-4">
        <h3 className="text-2xl font-bold text-gray-900">
          {topup.credits_amount.toLocaleString()} Credits
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Status: <span className={`font-medium ${topup.status === 'completed' ? 'text-green-600' : topup.status === 'pending' ? 'text-yellow-600' : 'text-red-600'}`}>{topup.status}</span>
        </p>
      </div>

      <div className="mb-4">
        <div className="flex items-baseline">
          <span className="text-3xl font-bold text-gray-900">
            ${topup.price_paid.toFixed(2)}
          </span>
          <span className="ml-2 text-sm text-gray-600">
            ${pricePerCredit.toFixed(4)} per credit
          </span>
        </div>
      </div>

      {topup.payment_method && (
        <p className="mb-4 text-sm text-gray-600">Payment: {topup.payment_method}</p>
      )}

      <button
        onClick={() => onSelect(topup.id)}
        disabled={loading}
        className="flex w-full items-center justify-center rounded-lg bg-primary-500 px-4 py-2 font-semibold text-white transition-colors hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Plus className="mr-2 h-4 w-4" />
        {loading ? 'Processing...' : 'Purchase'}
      </button>
    </div>
  )
}
