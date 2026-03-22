'use client'

import { CreditTransaction } from '@/types/billing'
import { ArrowUpRight, ArrowDownRight, Clock } from 'lucide-react'

interface CreditTransactionHistoryProps {
  transactions: CreditTransaction[]
  loading?: boolean
}

export default function CreditTransactionHistory({
  transactions,
  loading = false,
}: CreditTransactionHistoryProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-1/4 rounded bg-gray-200" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded bg-gray-100" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Transaction History
        </h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Clock className="mb-3 h-12 w-12 text-gray-400" />
          <p className="text-gray-600">No transactions yet</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h3 className="mb-4 text-lg font-semibold text-gray-900">
        Transaction History
      </h3>
      <div className="space-y-3">
        {transactions.map((transaction) => {
          const isCredit = (transaction.credits_amount ?? 0) > 0
          return (
            <div
              key={transaction.id}
              className="flex items-center justify-between rounded-lg border border-gray-100 p-4 transition-colors hover:bg-gray-50"
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`rounded-full p-2 ${
                    isCredit ? 'bg-green-100' : 'bg-primary-100'
                  }`}
                >
                  {isCredit ? (
                    <ArrowDownRight className="h-4 w-4 text-green-600" />
                  ) : (
                    <ArrowUpRight className="h-4 w-4 text-primary-600" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-gray-900">
                    {transaction.description || transaction.transaction_type}
                  </p>
                  <p className="text-sm text-gray-600">
                    {new Date(transaction.created_at).toLocaleString()}
                  </p>
                  {transaction.action_type && (
                    <p className="text-xs text-gray-500">
                      {transaction.action_type}
                    </p>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p
                  className={`text-lg font-semibold ${
                    isCredit ? 'text-green-600' : 'text-primary-600'
                  }`}
                >
                  {isCredit ? '+' : ''}
                  {(transaction.credits_amount ?? 0).toLocaleString()} credits
                </p>
                <p className="text-sm text-gray-600">
                  Balance: {(transaction.balance_after ?? 0).toLocaleString()}
                </p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
