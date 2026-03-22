'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import Link from 'next/link'

export default function AnimatedHero() {
  const heroRef = useRef<HTMLDivElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Epic title animation - word by word reveal
      const titleWords = titleRef.current ? Array.from(titleRef.current.querySelectorAll('.word')) : []

      if (titleWords.length > 0) {
        gsap.fromTo(titleWords,
          {
            opacity: 0,
            scale: 0.5,
            filter: 'blur(20px)',
            y: 100,
          },
          {
            opacity: 1,
            scale: 1,
            filter: 'blur(0px)',
            y: 0,
            duration: 1.2,
            stagger: 0.15,
            ease: 'expo.out',
            delay: 0.3
          }
        )
      }

      // Animate badge
      gsap.fromTo('.hero-badge',
        { opacity: 0, y: -30, scale: 0.8 },
        { opacity: 1, y: 0, scale: 1, duration: 0.8, ease: 'back.out(1.7)' }
      )

      // Animate subtext
      gsap.fromTo('.hero-subtext',
        { opacity: 0, y: 30 },
        { opacity: 1, y: 0, duration: 0.8, delay: 1.2, ease: 'power2.out' }
      )

      // Animate CTA buttons
      gsap.fromTo('.hero-cta',
        { opacity: 0, y: 30, scale: 0.9 },
        { opacity: 1, y: 0, scale: 1, duration: 0.6, delay: 1.5, stagger: 0.1, ease: 'back.out(1.7)' }
      )

      // Animate stats
      gsap.fromTo('.stat-item',
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.6, delay: 1.8, stagger: 0.1, ease: 'power2.out' }
      )

      // Floating orbs animation
      gsap.to('.orb', {
        y: '+=30',
        duration: 3,
        ease: 'sine.inOut',
        yoyo: true,
        repeat: -1,
        stagger: {
          each: 0.5,
          from: 'random'
        }
      })

      gsap.to('.orb', {
        x: '+=20',
        duration: 4,
        ease: 'sine.inOut',
        yoyo: true,
        repeat: -1,
        stagger: {
          each: 0.7,
          from: 'random'
        }
      })

    }, heroRef)

    return () => ctx.revert()
  }, [])

  // Grid magnetic effect
  useEffect(() => {
    const grid = gridRef.current
    if (!grid) return

    const handleMouseMove = (e: MouseEvent) => {
      const rect = grid.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 40
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 40

      gsap.to(grid, {
        x: x,
        y: y,
        duration: 1.2,
        ease: 'power2.out'
      })
    }

    grid.addEventListener('mousemove', handleMouseMove)
    return () => grid.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <div ref={heroRef} className="relative min-h-screen overflow-hidden bg-gradient-to-br from-gray-50 via-white to-red-50">
      {/* Animated Grid Background */}
      <div className="absolute inset-0 overflow-hidden opacity-30">
        <div 
          ref={gridRef}
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgb(255 68 79 / 0.1) 1px, transparent 1px),
              linear-gradient(to bottom, rgb(255 68 79 / 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '80px 80px'
          }}
        />
      </div>

      {/* Floating Orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="orb absolute top-20 left-[10%] w-64 h-64 bg-gradient-to-br from-primary-400/30 to-rose-400/30 rounded-full blur-3xl" />
        <div className="orb absolute top-40 right-[15%] w-96 h-96 bg-gradient-to-br from-red-400/20 to-pink-400/20 rounded-full blur-3xl" />
        <div className="orb absolute bottom-20 left-[20%] w-80 h-80 bg-gradient-to-br from-pink-400/25 to-primary-400/25 rounded-full blur-3xl" />
        <div className="orb absolute bottom-40 right-[10%] w-72 h-72 bg-gradient-to-br from-primary-400/30 to-red-400/30 rounded-full blur-3xl" />
      </div>

      {/* Content */}
      <div className="relative z-10 pt-32 pb-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            {/* Badge */}
            <div className="hero-badge inline-flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-full mb-8">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-primary-700">Open Source • Your LLM Keys • Full Control</span>
            </div>

            {/* Headline with word-by-word animation */}
            <h1 ref={titleRef} className="text-5xl md:text-7xl font-bold text-gray-900 mb-6 leading-tight">
              <span className="word inline-block mr-4">Build</span>
              <span className="word inline-block mr-4">AI</span>
              <span className="word inline-block mr-4">Agents</span>
              <br />
              <span className="word inline-block text-primary-500 mr-4">For</span>
              <span className="word inline-block text-primary-500 mr-4">Every</span>
              <span className="word inline-block text-primary-500">Role</span>
            </h1>

            {/* Subheadline */}
            <p className="hero-subtext text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
              Build AI-powered teammates for your startup or company. From product management to engineering to marketing—deploy intelligent agents that work 24/7.
            </p>

            {/* CTA Buttons */}
            <div className="flex items-center justify-center gap-4 mb-16">
              <Link
                href="/signup"
                className="hero-cta magnetic-button px-8 py-4 bg-primary-500 hover:bg-primary-600 text-white text-lg font-semibold rounded-xl transition-all shadow-xl shadow-primary-500/30 hover:shadow-2xl hover:shadow-primary-500/40 hover:scale-105"
              >
                Start Building Free
              </Link>
              <Link
                href="/signin"
                className="hero-cta magnetic-button px-8 py-4 bg-gray-900 hover:bg-gray-800 text-white text-lg font-semibold rounded-xl transition-all shadow-xl hover:shadow-2xl hover:scale-105"
              >
                View Demo
              </Link>
            </div>

            {/* Role Pills */}
            <div className="flex flex-wrap items-center justify-center gap-3 max-w-2xl mx-auto pt-8 border-t border-gray-200">
              {['Product Manager', 'Software Engineer', 'Marketing Lead', 'Support Agent', 'Data Analyst', 'Content Writer'].map((role, i) => (
                <div key={i} className="stat-item px-4 py-2 bg-white rounded-full border border-gray-200 text-sm font-medium text-gray-700 shadow-sm hover:border-red-300 hover:text-red-600 transition-colors cursor-default">
                  {role}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
