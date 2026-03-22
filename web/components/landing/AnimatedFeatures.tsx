'use client'

import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Link from 'next/link'

gsap.registerPlugin(ScrollTrigger)

const features = [
  {
    icon: '🧑‍💼',
    title: 'AI Product Manager',
    description: 'Automate backlog prioritization, sprint planning, and status reports. Your AI PM keeps projects on track around the clock.',
    color: 'from-red-100 to-red-200',
    iconColor: 'bg-primary-500'
  },
  {
    icon: '👨‍💻',
    title: 'AI Software Engineer',
    description: 'Code review, bug triage, documentation generation, and CI/CD monitoring. An AI teammate that never misses a PR.',
    color: 'from-blue-100 to-blue-200',
    iconColor: 'bg-blue-600'
  },
  {
    icon: '📢',
    title: 'AI Marketing Lead',
    description: 'Content creation, campaign analysis, SEO optimization, and social media management. Scale your marketing effortlessly.',
    color: 'from-green-100 to-green-200',
    iconColor: 'bg-green-600'
  }
]

export default function AnimatedFeatures() {
  const sectionRef = useRef<HTMLElement>(null)
  const cardsRef = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const cards = cardsRef.current.filter(Boolean) as HTMLDivElement[]
    const triggers: ScrollTrigger[] = []

    cards.forEach((card, index) => {
      // Fade + slide-up animation on scroll (no 3D — prevents scroll jitter)
      const st = ScrollTrigger.create({
        trigger: card,
        start: 'top 82%',
        onEnter: () => {
          gsap.fromTo(card,
            { opacity: 0, y: 50 },
            { opacity: 1, y: 0, duration: 0.7, delay: index * 0.12, ease: 'power3.out' }
          )
        },
        once: true,
      })
      triggers.push(st)

      // Hover effect
      const onEnterHover = () => gsap.to(card, { y: -10, scale: 1.04, duration: 0.3, ease: 'power2.out' })
      const onLeaveHover = () => gsap.to(card, { y: 0, scale: 1, duration: 0.3, ease: 'power2.out' })

      card.addEventListener('mouseenter', onEnterHover)
      card.addEventListener('mouseleave', onLeaveHover)
    })

    return () => {
      // Only kill triggers we created — not all global ScrollTrigger instances
      triggers.forEach(t => t.kill())
    }
  }, [])

  return (
    <section ref={sectionRef} className="py-20 px-6 bg-gray-50 overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            AI Agents for Every Role
          </h2>
          <p className="text-xl text-gray-600">
            Deploy intelligent teammates that handle real work, not just chat
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              ref={el => { cardsRef.current[index] = el }}
              className="bg-white rounded-2xl p-8 shadow-lg transition-shadow cursor-pointer"
            >
              <div className={`w-14 h-14 ${feature.iconColor} rounded-xl flex items-center justify-center mb-6 text-2xl`}>
                {feature.icon}
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
              <p className="text-gray-600 leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
