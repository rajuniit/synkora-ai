'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Image from 'next/image'
import { ArrowLeft, ThumbsUp, ThumbsDown, MessageSquare, Eye, Star, Zap, Brain, Bell, Loader2, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { apiClient } from '@/lib/api/client'
import { getLLMConfigs } from '@/lib/api/agent-llm-configs'
import { subscribeToAgent } from '@/lib/api/subscriptions'
import type { AgentLLMConfig } from '@/types/agent-llm-config'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

interface PublicAgent {
  id: string
  agent_name: string
  description: string
  avatar?: string
  category: string
  tags: string[]
  likes_count: number
  dislikes_count: number
  usage_count: number
  model_name: string
  created_at: string
  user_rating?: 'like' | 'dislike' | null
  system_prompt?: string
  tools?: any[]
  provider?: string
  allow_subscriptions?: boolean
}

const getInitials = (name: string) =>
  name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

// Generate gradient based on category - Red theme
const getCategoryGradient = (category: string) => {
  const gradients: Record<string, string> = {
    'Productivity': 'from-red-600 to-red-700',
    'Support': 'from-red-500 to-red-600',
    'Engineering': 'from-red-700 to-orange-600',
    'Sales': 'from-red-600 to-orange-600',
    'Marketing': 'from-red-500 to-pink-600',
    'Research': 'from-red-700 to-red-800',
    'Analytics': 'from-red-600 to-red-700',
    'Content': 'from-red-600 to-orange-600',
  }
  return gradients[category] || 'from-red-600 to-red-700'
}

export default function AgentDetailPage() {
  const router = useRouter()
  const params = useParams()
  const agentId = params.agentId as string

  const [agent, setAgent] = useState<PublicAgent | null>(null)
  const [defaultLLMConfig, setDefaultLLMConfig] = useState<AgentLLMConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [userId, setUserId] = useState<string | null>(null)
  const [showSubscribeForm, setShowSubscribeForm] = useState(false)
  const [subscribeEmail, setSubscribeEmail] = useState('')
  const [subscribeStatus, setSubscribeStatus] = useState<'idle' | 'loading' | 'success' | 'already_subscribed'>('idle')

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const user = await apiClient.getCurrentUser()
        setUserId(user.id)
      } catch (error) {
        console.error('Failed to fetch user:', error)
        setUserId(`session_${Date.now()}`)
      }
    }
    fetchUser()
  }, [])

  useEffect(() => {
    if (agentId && userId) {
      fetchAgentDetails()
    }
  }, [agentId, userId])

  const fetchAgentDetails = async () => {
    if (!userId) return
    
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/agents/public/${agentId}?user_id=${encodeURIComponent(userId)}`)
      const data = await response.json()
      if (data.success) {
        setAgent(data.data)
        
        // Fetch the default LLM config from the database
        try {
          const llmConfigs = await getLLMConfigs(data.data.id)
          const defaultConfig = llmConfigs.find(config => config.is_default)
          setDefaultLLMConfig(defaultConfig || null)
        } catch (error) {
          console.error('Failed to fetch LLM configs:', error)
        }
      } else {
        toast.error('Failed to load agent details')
        router.push('/browse')
      }
    } catch (error) {
      console.error('Failed to fetch agent details:', error)
      toast.error('Failed to load agent details')
      router.push('/browse')
    } finally {
      setLoading(false)
    }
  }

  const handleRating = async (rating: 'like' | 'dislike') => {
    if (!agent || !userId) return

    try {
      const response = await fetch(`${API_URL}/api/v1/agents/public/${agent.id}/rate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, rating }),
      })

      const data = await response.json()
      if (data.success) {
        toast.success(`Agent ${rating}d!`)
        fetchAgentDetails()
      }
    } catch (error) {
      console.error('Failed to rate agent:', error)
      toast.error('Failed to rate agent')
    }
  }

  const handleSubscribe = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!agent || !subscribeEmail.trim()) return
    try {
      setSubscribeStatus('loading')
      const result = await subscribeToAgent(agent.id, subscribeEmail.trim())
      if (result.message === 'Already subscribed') {
        setSubscribeStatus('already_subscribed')
      } else {
        setSubscribeStatus('success')
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to subscribe')
      setSubscribeStatus('idle')
    }
  }

  const getRatingPercentage = () => {
    if (!agent) return 0
    const total = agent.likes_count + agent.dislikes_count
    if (total === 0) return 0
    return Math.round((agent.likes_count / total) * 100)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-14 w-14 border-4 border-red-600 border-t-transparent"></div>
          <p className="mt-4 text-gray-600 font-medium">Loading agent details...</p>
        </div>
      </div>
    )
  }

  if (!agent) {
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40">
      {/* Header - Clean White Design */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Back Button */}
          <button
            onClick={() => router.push('/browse')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6 transition-colors"
          >
            <ArrowLeft size={18} />
            <span className="text-sm font-medium">Back to Browse</span>
          </button>

          {/* Agent Header - More Compact */}
          <div className="flex items-start gap-5">
            <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center text-white font-bold text-xl overflow-hidden relative shadow-md">
              {agent.avatar ? (
                agent.avatar.startsWith('http://') || agent.avatar.startsWith('https://') ? (
                  // Use regular img tag for external URLs (presigned URLs with query parameters)
                  <img
                    src={agent.avatar}
                    alt={agent.agent_name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  // Use Next.js Image for relative/local URLs
                  <Image
                    src={agent.avatar}
                    alt={agent.agent_name}
                    fill
                    className="object-cover"
                  />
                )
              ) : (
                getInitials(agent.agent_name)
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">{agent.agent_name}</h1>
                <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full border border-gray-200">
                  {agent.category}
                </span>
              </div>
              <p className="text-base text-gray-600 mb-3 max-w-3xl leading-relaxed">
                {agent.description || 'A powerful AI agent ready to assist you with various tasks.'}
              </p>
              
              {/* Stats - More Compact */}
              <div className="flex items-center gap-4 text-gray-600 text-sm">
                <div className="flex items-center gap-1.5">
                  <Eye size={16} />
                  <span className="font-medium">{agent.usage_count} uses</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <ThumbsUp size={16} />
                  <span className="font-medium">{agent.likes_count} likes</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Star size={16} className="fill-gray-600" />
                  <span className="font-medium">{getRatingPercentage()}% positive</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => router.push(`/agents/${agent.agent_name}/chat`)}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg transition-all shadow-sm hover:shadow-md font-semibold text-sm"
              >
                <MessageSquare size={18} />
                <span>Start Chat</span>
              </button>
              {agent.allow_subscriptions && (
                <button
                  onClick={() => setShowSubscribeForm(true)}
                  className="flex items-center gap-2 px-4 py-2.5 bg-white border border-gray-200 hover:border-red-300 hover:bg-red-50 text-gray-700 hover:text-red-600 rounded-lg transition-all font-semibold text-sm"
                >
                  <Bell size={16} />
                  Subscribe
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content - More Compact */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-5">
            {/* Tags */}
            {agent.tags && agent.tags.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-900 text-base mb-3">Tags</h2>
                <div className="flex flex-wrap gap-2">
                  {agent.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-4 py-2 bg-gradient-to-r from-gray-100 to-gray-50 text-gray-700 text-sm font-medium rounded-full border border-gray-200"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Tools & Capabilities */}
            {agent.description && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-900 text-base mb-3 flex items-center gap-2">
                  <Zap size={18} className="text-red-600" />
                  Tools & Capabilities
                </h2>
                <p className="text-sm text-gray-700 leading-relaxed">
                  {agent.description}
                </p>
              </div>
            )}

          </div>

          {/* Sidebar - More Compact */}
          <div className="space-y-4">
            {/* Model Info */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
                <Brain size={16} className="text-red-600" />
                Model Configuration
              </h2>
              <div className="space-y-2.5">
                {defaultLLMConfig ? (
                  <>
                    <div>
                      <div className="text-xs text-gray-600 mb-0.5">Provider</div>
                      <div className="font-semibold text-gray-900 text-sm capitalize">{defaultLLMConfig.provider}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600 mb-0.5">Model</div>
                      <div className="font-semibold text-gray-900 text-sm">{defaultLLMConfig.model_name}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600 mb-0.5">Temperature</div>
                      <div className="font-semibold text-gray-900 text-sm">{defaultLLMConfig.temperature}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600 mb-0.5">Max Tokens</div>
                      <div className="font-semibold text-gray-900 text-sm">{defaultLLMConfig.max_tokens || 'Auto'}</div>
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-gray-500 italic">No LLM configuration available</div>
                )}
                <div className="pt-2 border-t border-gray-200">
                  <div className="text-xs text-gray-600 mb-0.5">Created</div>
                  <div className="font-semibold text-gray-900 text-sm">
                    {new Date(agent.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>

            {/* Rating */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 text-sm mb-3">Rate This Agent</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => handleRating('like')}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg transition-all font-semibold text-sm ${
                    agent.user_rating === 'like'
                      ? 'bg-emerald-100 text-emerald-700 border-2 border-emerald-300'
                      : 'bg-gray-100 text-gray-700 hover:bg-emerald-50 hover:text-emerald-600 border border-gray-200'
                  }`}
                >
                  <ThumbsUp size={16} />
                  <span>Like</span>
                </button>
                <button
                  onClick={() => handleRating('dislike')}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg transition-all font-semibold text-sm ${
                    agent.user_rating === 'dislike'
                      ? 'bg-red-100 text-red-700 border-2 border-red-300'
                      : 'bg-gray-100 text-gray-700 hover:bg-red-50 hover:text-red-600 border border-gray-200'
                  }`}
                >
                  <ThumbsDown size={16} />
                  <span>Dislike</span>
                </button>
              </div>
            </div>

            {/* Stats Card */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 text-sm mb-3">Statistics</h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-xs">Total Uses</span>
                  <span className="font-bold text-gray-900 text-sm">{agent.usage_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-xs">Likes</span>
                  <span className="font-bold text-emerald-600 text-sm">{agent.likes_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-xs">Dislikes</span>
                  <span className="font-bold text-red-600 text-sm">{agent.dislikes_count}</span>
                </div>
                <div className="pt-3 border-t border-gray-200">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-600 text-xs">Rating</span>
                    <span className="font-bold text-red-600 text-sm">{getRatingPercentage()}%</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-red-500 to-red-600"
                      style={{ width: `${getRatingPercentage()}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Subscribe Modal */}
      {showSubscribeForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            {subscribeStatus === 'success' ? (
              <div className="text-center py-4">
                <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle size={28} className="text-green-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-1">You&apos;re subscribed!</h3>
                <p className="text-gray-500 text-sm mb-5">You&apos;ll receive reports from <span className="font-medium text-gray-700">{agent.agent_name}</span> in your inbox.</p>
                <button
                  onClick={() => { setShowSubscribeForm(false); setSubscribeStatus('idle'); setSubscribeEmail('') }}
                  className="px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium text-sm transition-colors"
                >
                  Close
                </button>
              </div>
            ) : subscribeStatus === 'already_subscribed' ? (
              <div className="text-center py-4">
                <div className="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Bell size={28} className="text-amber-600" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-1">Already subscribed</h3>
                <p className="text-gray-500 text-sm mb-5"><span className="font-medium text-gray-700">{subscribeEmail}</span> is already subscribed to this agent&apos;s reports.</p>
                <button
                  onClick={() => { setShowSubscribeForm(false); setSubscribeStatus('idle'); setSubscribeEmail('') }}
                  className="px-5 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium text-sm transition-colors"
                >
                  Close
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                      <Bell size={20} className="text-red-600" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-gray-900">Subscribe to reports</h3>
                      <p className="text-xs text-gray-500">{agent.agent_name}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => { setShowSubscribeForm(false); setSubscribeEmail('') }}
                    className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  Get this agent&apos;s scheduled reports delivered to your inbox automatically.
                </p>
                <form onSubmit={handleSubscribe} className="space-y-3">
                  <input
                    type="email"
                    required
                    autoFocus
                    value={subscribeEmail}
                    onChange={e => setSubscribeEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => { setShowSubscribeForm(false); setSubscribeEmail('') }}
                      className="flex-1 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={subscribeStatus === 'loading'}
                      className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-60"
                    >
                      {subscribeStatus === 'loading' ? <Loader2 size={14} className="animate-spin" /> : <Bell size={14} />}
                      {subscribeStatus === 'loading' ? 'Subscribing...' : 'Subscribe'}
                    </button>
                  </div>
                  <p className="text-center text-xs text-gray-400">You can unsubscribe anytime via the link in emails.</p>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
