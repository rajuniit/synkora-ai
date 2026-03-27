'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Smartphone,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Star,
  MessageSquare,
  Calendar,
  RefreshCw,
  Settings,
  BarChart3,
  AlertCircle,
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'

export default function AppStoreSourceDetailsPage() {
  const params = useParams()
  const sourceId = params.id as string

  const [source, setSource] = useState<any>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [reviews, setReviews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [selectedPeriod, setSelectedPeriod] = useState('daily')

  useEffect(() => {
    loadData()
  }, [sourceId, selectedPeriod])

  const loadData = async () => {
    try {
      setLoading(true)
      const [sourceData, insightsData, reviewsData] = await Promise.all([
        apiClient.getAppStoreSource(sourceId),
        apiClient.getAppStoreInsights(sourceId, { period: selectedPeriod }),
        apiClient.getAppStoreReviews(sourceId, { limit: 10 }),
      ])
      setSource(sourceData)
      setAnalytics(insightsData)
      // Handle both array response and object with reviews property
      const reviewsList = Array.isArray(reviewsData) 
        ? reviewsData 
        : ((reviewsData as any)?.reviews || [])
      setReviews(reviewsList)
    } catch (err) {
      console.error('Failed to load data:', err)
      toast.error('Failed to load app source details')
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      await apiClient.syncAppStoreReviews(sourceId)
      toast.success('Sync started successfully')
      setTimeout(loadData, 2000)
    } catch (err) {
      console.error('Failed to sync:', err)
      toast.error('Failed to start sync')
    } finally {
      setSyncing(false)
    }
  }

  const getRatingColor = (rating: number) => {
    if (rating >= 4) return 'text-green-600'
    if (rating >= 3) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'bg-green-100 text-green-800'
      case 'negative':
        return 'bg-red-100 text-red-800'
      case 'neutral':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-blue-100 text-blue-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading app source details...</p>
        </div>
      </div>
    )
  }

  if (!source) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600">App source not found</p>
          <Link
            href="/app-store-reviews"
            className="mt-4 inline-block text-blue-600 hover:text-blue-700"
          >
            Back to list
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/app-store-reviews"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to App Store Reviews
          </Link>

          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-600 rounded-lg shadow-sm">
                <Smartphone className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-xl sm:text-3xl font-bold text-gray-900">{source.app_name}</h1>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    {source.store_type === 'google_play' ? '🤖' : '🍎'}
                    {source.store_type === 'google_play' ? 'Google Play' : 'App Store'}
                  </span>
                  <span>•</span>
                  <span>{source.app_id}</span>
                  <span>•</span>
                  <span className="capitalize">{source.status}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Syncing...' : 'Sync Now'}
              </button>
              <Link
                href={`/app-store-reviews/${sourceId}/edit`}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Settings className="w-4 h-4" />
                Edit
              </Link>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Total Reviews</span>
              <MessageSquare className="w-5 h-5 text-blue-600" />
            </div>
            <div className="text-xl sm:text-3xl font-bold text-gray-900">
              {source.total_reviews_collected?.toLocaleString() || 0}
            </div>
            {analytics?.review_volume_change !== undefined && (
              <div className="flex items-center gap-1 mt-2 text-sm">
                {analytics.review_volume_change >= 0 ? (
                  <TrendingUp className="w-4 h-4 text-green-600" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-600" />
                )}
                <span
                  className={
                    analytics.review_volume_change >= 0 ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {Math.abs(analytics.review_volume_change).toFixed(1)}%
                </span>
                <span className="text-gray-500">vs last period</span>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Average Rating</span>
              <Star className="w-5 h-5 text-yellow-500" />
            </div>
            <div className={`text-xl sm:text-3xl font-bold ${getRatingColor(analytics?.average_rating || 0)}`}>
              {analytics?.average_rating?.toFixed(1) || 'N/A'}
            </div>
            {analytics?.rating_change !== undefined && (
              <div className="flex items-center gap-1 mt-2 text-sm">
                {analytics.rating_change >= 0 ? (
                  <TrendingUp className="w-4 h-4 text-green-600" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-600" />
                )}
                <span className={analytics.rating_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {analytics.rating_change >= 0 ? '+' : ''}
                  {analytics.rating_change?.toFixed(2)}
                </span>
                <span className="text-gray-500">vs last period</span>
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Sentiment</span>
              <BarChart3 className="w-5 h-5 text-purple-600" />
            </div>
            <div className="text-xl sm:text-3xl font-bold text-gray-900 capitalize">
              {analytics?.sentiment_trend || 'N/A'}
            </div>
            {analytics?.sentiment_distribution && (
              <div className="flex gap-2 mt-2">
                {Object.entries(analytics.sentiment_distribution).map(([key, value]: [string, any]) => (
                  <div key={key} className="text-xs">
                    <span className="capitalize">{key}:</span> {value}%
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Last Sync</span>
              <Calendar className="w-5 h-5 text-gray-600" />
            </div>
            <div className="text-lg font-semibold text-gray-900">
              {source.last_sync_at
                ? new Date(source.last_sync_at).toLocaleDateString()
                : 'Never'}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              Next: {source.next_sync_at ? new Date(source.next_sync_at).toLocaleDateString() : 'N/A'}
            </div>
          </div>
        </div>

        {/* Period Selector */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">Time Period:</span>
            <div className="flex gap-2">
              {['daily', 'weekly', 'monthly'].map((period) => (
                <button
                  key={period}
                  onClick={() => setSelectedPeriod(period)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedPeriod === period
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {period.charAt(0).toUpperCase() + period.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Rating Distribution */}
        {analytics?.rating_distribution && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Rating Distribution</h2>
            <div className="space-y-3">
              {[5, 4, 3, 2, 1].map((rating) => {
                const count = analytics.rating_distribution[rating] || 0
                const total = Object.values(analytics.rating_distribution).reduce(
                  (a: any, b: any) => a + b,
                  0
                ) as number
                const percentage = total > 0 ? (count / total) * 100 : 0

                return (
                  <div key={rating} className="flex items-center gap-4">
                    <div className="flex items-center gap-1 w-20">
                      <span className="text-sm font-medium">{rating}</span>
                      <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                    </div>
                    <div className="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                      <div
                        className="bg-blue-600 h-full rounded-full transition-all"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-600 w-20 text-right">
                      {count} ({percentage.toFixed(1)}%)
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Top Issues & Features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {analytics?.top_issues && analytics.top_issues.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Top Issues</h2>
              <div className="space-y-3">
                {analytics.top_issues.slice(0, 5).map((issue: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">{issue.name}</span>
                    <span className="text-sm font-medium text-red-600">{issue.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analytics?.top_features && analytics.top_features.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Top Features</h2>
              <div className="space-y-3">
                {analytics.top_features.slice(0, 5).map((feature: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">{feature.name}</span>
                    <span className="text-sm font-medium text-green-600">{feature.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Recent Reviews */}
        {reviews.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Reviews</h2>
            <div className="space-y-4">
              {reviews.map((review: any) => (
                <div key={review.id} className="border-b border-gray-200 pb-4 last:border-0">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        {[...Array(5)].map((_, i) => (
                          <Star
                            key={i}
                            className={`w-4 h-4 ${
                              i < review.rating
                                ? 'text-yellow-500 fill-yellow-500'
                                : 'text-gray-300'
                            }`}
                          />
                        ))}
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {review.author_name}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(review.review_date).toLocaleDateString()}
                    </span>
                  </div>
                  {review.title && (
                    <h3 className="font-medium text-gray-900 mb-1">{review.title}</h3>
                  )}
                  <p className="text-sm text-gray-600 mb-2">{review.content}</p>
                  {review.sentiment && (
                    <span
                      className={`inline-block px-2 py-1 rounded text-xs font-medium ${getSentimentColor(
                        review.sentiment
                      )}`}
                    >
                      {review.sentiment}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
