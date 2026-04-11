'use client'

import AnimatedNav from '@/components/landing/AnimatedNav'
import AnimatedHero from '@/components/landing/AnimatedHero'
import AnimatedFeatures from '@/components/landing/AnimatedFeatures'
import Footer from '@/components/landing/Footer'
import CountdownPage from '@/components/CountdownPage'
import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { Sparkles, Zap, MessageSquare, Star, ArrowRight, Play, Code2, Blocks, Rocket } from 'lucide-react'

gsap.registerPlugin(ScrollTrigger)

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
const COMING_SOON = process.env.NEXT_PUBLIC_COMING_SOON === 'true'

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
}

interface PricingPlan {
  id: string
  name: string
  description: string
  price_monthly: number
  price_yearly: number | null
  credits_monthly: number
  max_agents: number
  max_team_members: number
  features: Record<string, boolean | string | number>
  is_active: boolean
  is_popular?: boolean
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

// Pre-built Agent Card Component - Matches Dashboard Design
const PreBuiltAgentCard = ({
  agent
}: {
  agent: PublicAgent
}) => {
  const getRating = () => {
    const total = agent.likes_count + agent.dislikes_count
    if (total === 0) return 4.5
    const ratio = agent.likes_count / total
    return Math.round((3 + ratio * 2) * 10) / 10
  }

  return (
    <Link href={`/browse/${agent.id}`}>
      <div className="bg-white rounded-3xl overflow-hidden shadow-sm hover:shadow-lg transition-shadow duration-300 flex flex-col">
        {/* Pink Gradient Header with Centered Avatar */}
        <div className="relative bg-gradient-to-br from-red-100 via-pink-50 to-orange-50 pt-10 pb-12 flex items-center justify-center">
          {/* Centered Avatar */}
          {agent.avatar ? (
            <img
              src={agent.avatar}
              alt={agent.agent_name}
              className="w-24 h-24 rounded-2xl object-cover shadow-lg bg-white"
            />
          ) : (
            <div className="w-24 h-24 rounded-2xl bg-white shadow-lg flex items-center justify-center">
              <Sparkles className="w-12 h-12 text-red-500" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6 flex-1 flex flex-col">
          {/* Name and Rating */}
          <div className="flex items-start justify-between gap-3 mb-1">
            <h3 className="text-lg font-bold text-gray-900 line-clamp-1">
              {agent.agent_name}
            </h3>
            {getRating() > 0 && (
              <div className="flex items-center gap-1 text-amber-500 flex-shrink-0">
                <Star className="w-4 h-4 fill-current" />
                <span className="font-semibold text-sm">{getRating().toFixed(1)}</span>
              </div>
            )}
          </div>

          {/* Category */}
          <p className="text-sm text-gray-400 mb-3">
            {agent.category || 'AI Agent'}
          </p>

          {/* Description */}
          <p className="text-sm text-gray-600 leading-relaxed line-clamp-2 mb-4">
            {agent.description || 'No description provided'}
          </p>

          {/* Divider */}
          <div className="border-t border-gray-100 my-4" />

          {/* Stats Row */}
          <div className="flex items-center gap-6 mb-5">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Uses</p>
              <p className="text-xl font-bold text-gray-900">{formatNumber(agent.usage_count || 0)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Likes</p>
              <p className="text-xl font-bold text-gray-900">{agent.likes_count || 0}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Rating</p>
              <p className="text-xl font-bold text-gray-900">{getRating().toFixed(1)}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 mt-auto">
            <button className="flex-1 px-5 py-2.5 border border-red-300 text-red-500 text-sm font-semibold rounded-xl hover:bg-red-50 hover:border-red-400 transition-colors">
              Try Agent
            </button>
            <span className="px-4 py-2.5 text-gray-400 text-sm font-medium hover:text-gray-600 transition-colors">
              View Details
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}

// Loading skeleton for agent cards - Matches Dashboard Design
const AgentCardSkeleton = () => (
  <div className="bg-white rounded-3xl overflow-hidden shadow-sm animate-pulse">
    {/* Pink gradient header placeholder */}
    <div className="bg-gradient-to-br from-red-50 via-pink-50 to-orange-50 pt-10 pb-12 flex items-center justify-center">
      <div className="w-24 h-24 bg-white rounded-2xl shadow-lg" />
    </div>
    {/* Content */}
    <div className="p-6">
      <div className="h-5 bg-gray-200 rounded w-32 mb-2" />
      <div className="h-4 bg-gray-100 rounded w-24 mb-4" />
      <div className="h-4 bg-gray-100 rounded w-full mb-2" />
      <div className="h-4 bg-gray-100 rounded w-3/4 mb-4" />
      <div className="border-t border-gray-100 pt-4 mb-4">
        <div className="flex gap-6">
          <div>
            <div className="h-3 bg-gray-100 rounded w-10 mb-1" />
            <div className="h-6 bg-gray-200 rounded w-8" />
          </div>
          <div>
            <div className="h-3 bg-gray-100 rounded w-10 mb-1" />
            <div className="h-6 bg-gray-200 rounded w-8" />
          </div>
          <div>
            <div className="h-3 bg-gray-100 rounded w-12 mb-1" />
            <div className="h-6 bg-gray-200 rounded w-10" />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-10 bg-gray-100 rounded-xl" />
        <div className="h-10 bg-gray-50 rounded w-24" />
      </div>
    </div>
  </div>
)

export default function LandingPage() {
  // Show countdown page if COMING_SOON env is true
  if (COMING_SOON) {
    return <CountdownPage />
  }

  return <MainLandingPage />
}

function MainLandingPage() {
  const ctaSectionRef = useRef<HTMLElement>(null)
  const footerRef = useRef<HTMLDivElement>(null)
  const agentsSectionRef = useRef<HTMLElement>(null)

  const [publicAgents, setPublicAgents] = useState<PublicAgent[]>([])
  const [pricingPlans, setPricingPlans] = useState<PricingPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [pricingLoading, setPricingLoading] = useState(true)

  // Fetch public agents and pricing plans
  useEffect(() => {
    const fetchPublicAgents = async () => {
      try {
        const params = new URLSearchParams()
        params.append('sort_by', 'popular')
        params.append('limit', '6')

        const response = await fetch(`${API_URL}/api/v1/agents/public?${params}`)
        const data = await response.json()
        if (data.success) {
          setPublicAgents(data.data.agents || [])
        }
      } catch (error) {
        console.error('Failed to fetch public agents:', error)
      } finally {
        setLoading(false)
      }
    }

    const fetchPricingPlans = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/billing/plans`)
        const data = await response.json()
        const plansArray = Array.isArray(data) ? data : (data.data || data.plans || [])
        if (plansArray.length > 0) {
          const sortedPlans = plansArray
            .filter((p: PricingPlan) => p.is_active !== false)
            .sort((a: PricingPlan, b: PricingPlan) => (a.price_monthly || 0) - (b.price_monthly || 0))
            .slice(0, 3) // Only show first 3 plans
          setPricingPlans(sortedPlans)
        }
      } catch (error) {
        console.error('Failed to fetch pricing plans:', error)
      } finally {
        setPricingLoading(false)
      }
    }

    fetchPublicAgents()
    fetchPricingPlans()
  }, [])

  useEffect(() => {
    const triggers: ScrollTrigger[] = []

    // Animate CTA section on scroll
    if (ctaSectionRef.current) {
      const ctaBox = ctaSectionRef.current.querySelector('.cta-box')
      if (ctaBox) {
        const t = ScrollTrigger.create({
          trigger: ctaSectionRef.current,
          start: 'top 80%',
          onEnter: () => {
            gsap.fromTo(ctaBox,
              { opacity: 0, scale: 0.9, y: 50 },
              { opacity: 1, scale: 1, y: 0, duration: 1, ease: 'back.out(1.4)' }
            )
          },
          once: true,
        })
        triggers.push(t)
      }
    }

    // Animate agents section — only when cards are actually in the DOM
    if (agentsSectionRef.current) {
      const agentCards = Array.from(agentsSectionRef.current.querySelectorAll('.agent-card-animated'))
      if (agentCards.length > 0) {
        const t = ScrollTrigger.create({
          trigger: agentsSectionRef.current,
          start: 'top 75%',
          onEnter: () => {
            gsap.fromTo(agentCards,
              { opacity: 0, y: 60, scale: 0.95 },
              { opacity: 1, y: 0, scale: 1, duration: 0.8, stagger: 0.15, ease: 'power3.out' }
            )
          },
          once: true,
        })
        triggers.push(t)
      }
    }

    // Animate footer
    if (footerRef.current) {
      const t = ScrollTrigger.create({
        trigger: footerRef.current,
        start: 'top 90%',
        onEnter: () => {
          gsap.fromTo(footerRef.current,
            { opacity: 0, y: 30 },
            { opacity: 1, y: 0, duration: 0.8 }
          )
        },
        once: true,
      })
      triggers.push(t)
    }

    return () => {
      // Only kill triggers we created — not all global ScrollTrigger instances
      triggers.forEach(t => t.kill())
    }
  }, [publicAgents])

  return (
    <div className="min-h-screen bg-white">
      {/* Animated Navigation */}
      <AnimatedNav />

      {/* Epic Animated Hero Section */}
      <AnimatedHero />

      {/* Demo Video Section */}
      <section className="relative py-20 sm:py-28 px-4 sm:px-6 overflow-hidden bg-gradient-to-b from-white to-gray-50">
        {/* Subtle background blobs */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-red-100/60 rounded-full blur-[100px]" />
        </div>

        <div className="relative max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-red-50 border border-red-100 text-red-600 rounded-full text-sm font-semibold mb-5">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              Product Demo
            </div>
            <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
              See Synkora in action
            </h2>
            <p className="text-lg text-gray-500 max-w-xl mx-auto">
              Build and deploy powerful AI agents — no code required
            </p>
          </div>

          {/* Browser chrome mockup */}
          <div className="relative">
            {/* Drop shadow glow */}
            <div className="absolute -inset-2 bg-gradient-to-b from-red-200/40 to-gray-200/40 rounded-3xl blur-2xl" />

            <div className="relative rounded-2xl overflow-hidden border border-gray-200 shadow-2xl shadow-gray-300/60 bg-white">
              {/* Browser top bar */}
              <div className="flex items-center gap-2 px-4 py-3 bg-gray-100 border-b border-gray-200">
                {/* Traffic lights */}
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
                  <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
                  <div className="w-3 h-3 rounded-full bg-[#28c840]" />
                </div>
                {/* URL bar */}
                <div className="flex-1 mx-4">
                  <div className="flex items-center gap-2 px-3 py-1 bg-white border border-gray-200 rounded-md max-w-xs mx-auto">
                    <svg className="w-3 h-3 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                    <span className="text-xs text-gray-400 font-mono truncate">app.synkora.com</span>
                  </div>
                </div>
              </div>

              {/* Video */}
              <div className="aspect-video bg-gray-100">
                <video
                  src="/demo_video.mp4"
                  poster="https://github.com/user-attachments/assets/4e0b11be-b9d8-4cde-9524-c8ec9467059f"
                  controls
                  playsInline
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>

          {/* CTA below video */}
          <div className="text-center mt-10">
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 px-7 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-red-500/30"
            >
              <Zap className="w-4 h-4" />
              Start Building Free
            </Link>
          </div>
        </div>
      </section>

      {/* Animated Features Section */}
      <AnimatedFeatures />

      {/* How It Works Section - Modern & Compact */}
      <section className="py-14 sm:py-20 px-4 sm:px-6 bg-gradient-to-b from-white to-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold mb-4">
              <Play className="w-4 h-4" />
              How It Works
            </div>
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Build AI Agents in Minutes
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Four simple steps to create, customize, and deploy your AI agent
            </p>
          </div>

          {/* Steps Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { num: '01', icon: Code2, title: 'Create', desc: 'Define your agent with our intuitive interface', color: 'red' },
              { num: '02', icon: Blocks, title: 'Customize', desc: 'Add knowledge bases and integrations', color: 'orange' },
              { num: '03', icon: MessageSquare, title: 'Test', desc: 'Use the playground to refine responses', color: 'blue' },
              { num: '04', icon: Rocket, title: 'Deploy', desc: 'Launch to web, Slack, Discord & more', color: 'green' },
            ].map((step, idx) => (
              <div key={idx} className="relative bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-lg transition-all group">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${
                  step.color === 'red' ? 'bg-red-100' :
                  step.color === 'orange' ? 'bg-orange-100' :
                  step.color === 'blue' ? 'bg-blue-100' : 'bg-green-100'
                }`}>
                  <step.icon className={`w-6 h-6 ${
                    step.color === 'red' ? 'text-red-600' :
                    step.color === 'orange' ? 'text-orange-600' :
                    step.color === 'blue' ? 'text-blue-600' : 'text-green-600'
                  }`} />
                </div>
                <span className="text-4xl font-bold text-gray-100 absolute top-4 right-4">{step.num}</span>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{step.title}</h3>
                <p className="text-gray-600 text-sm">{step.desc}</p>
              </div>
            ))}
          </div>

          {/* Learn More Link */}
          <div className="text-center mt-10">
            <Link
              href="/how-it-works"
              className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-semibold"
            >
              Learn more about the process
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Pre-built Agents Section - Dynamic from Backend */}
      <section ref={agentsSectionRef} className="py-16 sm:py-24 px-4 sm:px-6 bg-gradient-to-b from-gray-50 via-white to-gray-50">
        <div className="max-w-7xl mx-auto">
          {/* Section Header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-full text-sm font-bold mb-6 uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              Pre-built Agents
            </div>
            <h2 className="text-3xl sm:text-5xl font-black text-gray-900 mb-5 tracking-tight">
              Powerful AI Agents
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-red-600 to-rose-600">
                Ready to Deploy
              </span>
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Start with battle-tested agents built by experts, or customize them for your unique needs
            </p>
          </div>

          {/* Agents Grid */}
          {loading ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {[...Array(6)].map((_, i) => (
                <AgentCardSkeleton key={i} />
              ))}
            </div>
          ) : publicAgents.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {publicAgents.map((agent, index) => (
                <div key={agent.id} className="agent-card-animated">
                  <PreBuiltAgentCard agent={agent} />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="w-24 h-24 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Sparkles className="w-12 h-12 text-red-500" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">No Agents Available Yet</h3>
              <p className="text-gray-600 mb-8">Check back soon for amazing pre-built agents!</p>
            </div>
          )}

          {/* Browse All Button */}
          <div className="text-center mt-16">
            <Link
              href="/browse"
              className="inline-flex items-center gap-3 px-10 py-5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white text-lg font-bold rounded-2xl transition-all shadow-xl hover:shadow-2xl hover:shadow-red-500/30 hover:scale-105 group"
            >
              <span>Browse All Agents</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing Preview Section */}
      <section className="py-14 sm:py-20 px-4 sm:px-6 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-xl text-gray-600">
              Start free, scale as you grow
            </p>
          </div>

          {/* Pricing Cards Preview */}
          {pricingLoading ? (
            <div className="grid md:grid-cols-3 gap-6 mb-10">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm animate-pulse">
                  <div className="h-6 bg-gray-200 rounded w-24 mb-2" />
                  <div className="h-4 bg-gray-100 rounded w-32 mb-4" />
                  <div className="h-8 bg-gray-200 rounded w-20 mb-4" />
                  <div className="space-y-2">
                    <div className="h-4 bg-gray-100 rounded w-full" />
                    <div className="h-4 bg-gray-100 rounded w-3/4" />
                    <div className="h-4 bg-gray-100 rounded w-5/6" />
                  </div>
                </div>
              ))}
            </div>
          ) : pricingPlans.length > 0 ? (
            <div className={`grid gap-6 mb-10 ${pricingPlans.length === 1 ? 'max-w-md mx-auto' : pricingPlans.length === 2 ? 'md:grid-cols-2 max-w-3xl mx-auto' : 'md:grid-cols-3'}`}>
              {pricingPlans.map((plan, idx) => {
                const isPopular = plan.is_popular || (pricingPlans.length >= 3 && idx === 1)
                const features: string[] = []
                if (plan.credits_monthly) features.push(`${plan.credits_monthly.toLocaleString()} credits/month`)
                if (plan.max_agents === -1 || plan.max_agents > 100) features.push('Unlimited agents')
                else if (plan.max_agents) features.push(`${plan.max_agents} agent${plan.max_agents > 1 ? 's' : ''}`)
                if (plan.max_team_members === -1 || plan.max_team_members > 100) features.push('Unlimited team members')
                else if (plan.max_team_members > 1) features.push(`${plan.max_team_members} team members`)

                return (
                  <div key={plan.id} className={`relative bg-white rounded-2xl p-6 ${isPopular ? 'ring-2 ring-red-500 shadow-xl' : 'border border-gray-200 shadow-sm'}`}>
                    {isPopular && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-red-500 text-white text-xs font-semibold rounded-full">
                        Popular
                      </div>
                    )}
                    <h3 className="text-xl font-bold text-gray-900 mb-1">{plan.name}</h3>
                    <p className="text-sm text-gray-500 mb-4">{plan.description || 'Choose this plan'}</p>
                    <div className="mb-4">
                      <span className="text-3xl font-bold text-gray-900">${plan.price_monthly || 0}</span>
                      <span className="text-gray-500">/month</span>
                    </div>
                    <ul className="space-y-2 mb-6">
                      {features.slice(0, 3).map((feature, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-10 mb-10">
              <p className="text-gray-500">Pricing plans coming soon</p>
            </div>
          )}

          <div className="text-center">
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-semibold"
            >
              View all pricing details
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section ref={ctaSectionRef} className="py-14 sm:py-20 px-4 sm:px-6 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center">
          <div className="cta-box bg-gradient-to-br from-red-600 via-red-500 to-rose-600 rounded-3xl p-12 md:p-16 shadow-2xl shadow-red-500/20 relative overflow-hidden">
            {/* Background decorations */}
            <div className="absolute inset-0 opacity-30">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/20 rounded-full blur-3xl -translate-y-32 translate-x-32" />
              <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/15 rounded-full blur-2xl translate-y-24 -translate-x-24" />
            </div>

            <div className="relative">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-5">
                Ready to Build Your AI Team?
              </h2>
              <p className="text-lg md:text-xl text-white/90 mb-8 max-w-xl mx-auto">
                Deploy AI agents for product, engineering, marketing, and more. Start for free.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 px-8 py-4 bg-white hover:bg-gray-50 text-red-600 font-semibold rounded-xl transition-all shadow-lg"
                >
                  <Zap className="w-5 h-5" />
                  Get Started Free
                </Link>
                <Link
                  href="/how-it-works"
                  className="inline-flex items-center gap-2 px-8 py-4 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-xl transition-all border border-white/20"
                >
                  Learn How It Works
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <div ref={footerRef}>
        <Footer />
      </div>
    </div>
  )
}
