'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { Check, Zap, Building2, Sparkles, ArrowRight, Loader2 } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

interface SubscriptionPlan {
  id: string
  name: string
  description: string
  price_monthly: number
  price_yearly: number | null
  credits_monthly: number
  max_agents: number
  max_knowledge_bases?: number
  max_team_members: number
  features: string[] | Record<string, boolean | string | number>
  is_active: boolean
  is_popular?: boolean
  display_order?: number
}

const getIconForPlan = (name: string, index: number) => {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('free') || nameLower.includes('starter')) {
    return <Sparkles className="w-5 h-5 text-gray-600" />
  }
  if (nameLower.includes('pro') || nameLower.includes('professional')) {
    return <Zap className="w-5 h-5 text-red-500" />
  }
  if (nameLower.includes('enterprise') || nameLower.includes('business')) {
    return <Building2 className="w-5 h-5 text-purple-600" />
  }
  // Fallback based on index
  if (index === 0) return <Sparkles className="w-5 h-5 text-gray-600" />
  if (index === 1) return <Zap className="w-5 h-5 text-red-500" />
  return <Building2 className="w-5 h-5 text-purple-600" />
}

const formatFeatures = (plan: SubscriptionPlan): string[] => {
  const featureList: string[] = []

  // Add credit info
  if (plan.credits_monthly) {
    featureList.push(`${plan.credits_monthly.toLocaleString()} credits/month`)
  }

  // Add limits
  if (plan.max_agents === -1 || plan.max_agents > 100) {
    featureList.push('Unlimited agents')
  } else if (plan.max_agents) {
    featureList.push(`${plan.max_agents} agent${plan.max_agents > 1 ? 's' : ''}`)
  }

  if (plan.max_knowledge_bases !== undefined) {
    if (plan.max_knowledge_bases === -1 || plan.max_knowledge_bases > 100) {
      featureList.push('Unlimited knowledge bases')
    } else if (plan.max_knowledge_bases > 0) {
      featureList.push(`${plan.max_knowledge_bases} knowledge base${plan.max_knowledge_bases > 1 ? 's' : ''}`)
    }
  }

  if (plan.max_team_members === -1 || plan.max_team_members > 100) {
    featureList.push('Unlimited team members')
  } else if (plan.max_team_members && plan.max_team_members > 1) {
    featureList.push(`${plan.max_team_members} team members`)
  }

  // Add features from the features field
  if (Array.isArray(plan.features)) {
    featureList.push(...plan.features)
  } else if (plan.features && typeof plan.features === 'object') {
    Object.entries(plan.features).forEach(([key, value]) => {
      // Convert camelCase or snake_case to readable format
      const readable = key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .toLowerCase()
        .replace(/^\w/, c => c.toUpperCase())
        .trim()

      if (value === true) {
        featureList.push(readable)
      } else if (typeof value === 'string' && value) {
        featureList.push(`${readable}: ${value}`)
      } else if (typeof value === 'number' && value > 0) {
        featureList.push(`${readable}: ${value}`)
      }
    })
  }

  return featureList
}

export default function PricingPage() {
  const [isYearly, setIsYearly] = useState(false)
  const [plans, setPlans] = useState<SubscriptionPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await fetch(`${API_URL}/api/v1/billing/plans`)
        const data = await response.json()

        // Handle both array response and wrapped response { success, data }
        const plansArray = Array.isArray(data) ? data : (data.data || data.plans || [])

        if (plansArray.length > 0) {
          // Sort by display_order or price
          const sortedPlans = plansArray
            .filter((p: SubscriptionPlan) => p.is_active !== false)
            .sort((a: SubscriptionPlan, b: SubscriptionPlan) => {
              if (a.display_order !== undefined && b.display_order !== undefined) {
                return a.display_order - b.display_order
              }
              return (a.price_monthly || 0) - (b.price_monthly || 0)
            })
          setPlans(sortedPlans)
        } else {
          setError('No pricing plans available')
        }
      } catch (err) {
        console.error('Failed to fetch plans:', err)
        setError('Unable to load pricing plans')
      } finally {
        setLoading(false)
      }
    }
    fetchPlans()
  }, [])

  useEffect(() => {
    // Animate cards after they load
    if (!loading && plans.length > 0 && containerRef.current) {
      gsap.fromTo(
        containerRef.current.querySelectorAll('.pricing-card'),
        { opacity: 0, y: 40 },
        { opacity: 1, y: 0, duration: 0.6, stagger: 0.15, ease: 'power3.out' }
      )
    }
  }, [loading, plans])

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 sm:gap-3">
              <div className="w-9 h-9 sm:w-10 sm:h-10 bg-red-500 rounded-xl flex items-center justify-center">
                <Zap className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              </div>
              <span className="text-xl sm:text-2xl font-bold text-gray-900">Synkora</span>
            </Link>
            <div className="flex items-center gap-2 sm:gap-4">
              <Link href="/" className="hidden sm:block text-gray-600 hover:text-gray-900 font-medium">
                Home
              </Link>
              <Link href="/how-it-works" className="hidden sm:block text-gray-600 hover:text-gray-900 font-medium">
                How It Works
              </Link>
              <Link href="/signin" className="hidden sm:block text-gray-600 hover:text-gray-900 font-medium">
                Sign in
              </Link>
              <Link
                href="/signup"
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition-colors text-sm sm:text-base"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-28 sm:pt-32 pb-12 sm:pb-16 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-full text-sm font-semibold mb-6">
            <Sparkles className="w-4 h-4" />
            Simple, Transparent Pricing
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-gray-900 mb-4 sm:mb-6">
            Choose the plan that fits your needs
          </h1>
          <p className="text-base sm:text-xl text-gray-600 mb-8 sm:mb-10">
            Start free, scale as you grow. All plans include our core features.
          </p>

          {/* Billing Toggle */}
          <div className="flex items-center justify-center gap-4 mb-12">
            <span className={`font-medium ${!isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
              Monthly
            </span>
            <button
              onClick={() => setIsYearly(!isYearly)}
              className={`relative w-14 h-7 rounded-full transition-colors ${
                isYearly ? 'bg-red-500' : 'bg-gray-300'
              }`}
            >
              <div
                className={`absolute top-1 w-5 h-5 bg-white rounded-full transition-transform ${
                  isYearly ? 'translate-x-8' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`font-medium ${isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
              Yearly
              <span className="ml-2 text-sm text-green-600 font-semibold">Save 20%</span>
            </span>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-16 sm:pb-24 px-4 sm:px-6" ref={containerRef}>
        <div className="max-w-6xl mx-auto">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-red-500 animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-20">
              <p className="text-gray-500 mb-4">{error}</p>
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 px-6 py-3 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-xl transition-colors"
              >
                Get Started Free
              </Link>
            </div>
          ) : (
            <div className={`grid gap-8 ${plans.length === 1 ? 'max-w-md mx-auto' : plans.length === 2 ? 'md:grid-cols-2 max-w-3xl mx-auto' : 'md:grid-cols-3'}`}>
              {plans.map((plan, index) => {
                const features = formatFeatures(plan)
                const isPopular = plan.is_popular || (plans.length >= 3 && index === 1)

                return (
                  <div
                    key={plan.id}
                    className={`pricing-card relative bg-white rounded-2xl p-8 ${
                      isPopular
                        ? 'ring-2 ring-red-500 shadow-xl shadow-red-500/10'
                        : 'border border-gray-200 shadow-lg'
                    }`}
                  >
                    {isPopular && (
                      <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-red-500 text-white text-sm font-semibold rounded-full">
                        Most Popular
                      </div>
                    )}

                    <div className="mb-6">
                      <div className="flex items-center gap-2 mb-2">
                        {getIconForPlan(plan.name, index)}
                        <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                      </div>
                      <p className="text-gray-600 text-sm">{plan.description || 'Choose this plan to get started'}</p>
                    </div>

                    <div className="mb-6">
                      <div className="flex items-baseline gap-1">
                        <span className="text-4xl font-bold text-gray-900">
                          ${isYearly && plan.price_yearly ? Math.round(plan.price_yearly / 12) : plan.price_monthly || 0}
                        </span>
                        <span className="text-gray-500">/month</span>
                      </div>
                      {isYearly && plan.price_yearly && plan.price_yearly > 0 && (
                        <p className="text-sm text-gray-500 mt-1">
                          ${plan.price_yearly} billed annually
                        </p>
                      )}
                    </div>

                    <Link
                      href="/signup"
                      className={`block w-full py-3 text-center font-semibold rounded-xl transition-all mb-8 ${
                        isPopular
                          ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30'
                          : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
                      }`}
                    >
                      {(plan.price_monthly || 0) === 0 ? 'Start Free' : 'Get Started'}
                    </Link>

                    <ul className="space-y-3">
                      {features.slice(0, 8).map((feature, idx) => (
                        <li key={idx} className="flex items-start gap-3">
                          <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                          <span className="text-gray-700 text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-14 sm:py-20 px-4 sm:px-6 bg-gray-50">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 text-center mb-8 sm:mb-12">
            Frequently Asked Questions
          </h2>

          <div className="space-y-6">
            {[
              {
                q: 'What are credits?',
                a: 'Credits measure platform usage. 1 credit = 1 action (message, tool use, knowledge base query, or agent execution). File uploads cost 2 credits. Since you use your own LLM API keys, all models cost the same credits. Unused credits roll over on Professional and Enterprise plans.'
              },
              {
                q: 'Can I change plans anytime?',
                a: 'Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we\'ll prorate any differences.'
              },
              {
                q: 'What payment methods do you accept?',
                a: 'We accept all major credit cards, PayPal, and bank transfers for enterprise plans. Payments are securely processed by Paddle.'
              },
              {
                q: 'Is there a refund policy?',
                a: 'Yes, we offer a 30-day money-back guarantee for new subscriptions. See our Terms of Service for full details.'
              },
              {
                q: 'Do you offer discounts for startups or nonprofits?',
                a: 'Yes! We offer special pricing for qualified startups and nonprofit organizations. Contact us to learn more.'
              },
              {
                q: 'Do I need to pay for LLM API costs separately?',
                a: 'Yes, you use your own LLM API keys (OpenAI, Anthropic, Google, etc.). Our pricing only covers platform features - agents, knowledge bases, tools, and integrations. This gives you full control over your AI costs and model selection.'
              }
            ].map((faq, idx) => (
              <div key={idx} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h3 className="font-semibold text-gray-900 mb-2">{faq.q}</h3>
                <p className="text-gray-600">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-14 sm:py-20 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="bg-gradient-to-br from-red-500 to-rose-600 rounded-3xl p-8 sm:p-12 shadow-2xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">
              Ready to supercharge your workflows?
            </h2>
            <p className="text-white/90 mb-6 sm:mb-8 text-base sm:text-lg">
              Start building AI agents today. No credit card required.
            </p>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white hover:bg-gray-50 text-red-600 font-semibold rounded-xl transition-all shadow-lg"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Simple Footer */}
      <footer className="py-8 px-6 border-t border-gray-200">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-gray-600">© 2026 Synkora. All rights reserved.</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/terms" className="text-gray-600 hover:text-gray-900 text-sm">
              Terms
            </Link>
            <Link href="/privacy" className="text-gray-600 hover:text-gray-900 text-sm">
              Privacy
            </Link>
            <Link href="/" className="text-gray-600 hover:text-gray-900 text-sm">
              Home
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
