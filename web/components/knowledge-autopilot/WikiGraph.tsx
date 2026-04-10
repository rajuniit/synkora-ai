'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { getWikiGraph } from '@/lib/api/knowledge-autopilot'
import type { WikiGraphData } from '@/lib/api/knowledge-autopilot'

const CATEGORY_COLORS: Record<string, { fill: string; glow: string }> = {
  projects: { fill: '#3b82f6', glow: 'rgba(59, 130, 246, 0.5)' },
  people: { fill: '#a855f7', glow: 'rgba(168, 85, 247, 0.5)' },
  decisions: { fill: '#f59e0b', glow: 'rgba(245, 158, 11, 0.5)' },
  processes: { fill: '#10b981', glow: 'rgba(16, 185, 129, 0.5)' },
  architecture: { fill: '#06b6d4', glow: 'rgba(6, 182, 212, 0.5)' },
  general: { fill: '#6b7280', glow: 'rgba(107, 114, 128, 0.4)' },
}

interface WikiGraphProps {
  kbId: string
}

interface NodePosition {
  id: string
  title: string
  slug: string
  category: string
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  connections: number
}

export function WikiGraph({ kbId }: WikiGraphProps) {
  const router = useRouter()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [graphData, setGraphData] = useState<WikiGraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const nodesRef = useRef<NodePosition[]>([])
  const animRef = useRef<number>(0)
  const timeRef = useRef(0)
  const hoveredRef = useRef<string | null>(null)

  // Keep hoveredRef in sync
  useEffect(() => {
    hoveredRef.current = hoveredNode
  }, [hoveredNode])

  useEffect(() => {
    getWikiGraph(kbId)
      .then((data) => setGraphData(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [kbId])

  const initSimulation = useCallback(() => {
    if (!graphData || !canvasRef.current || !containerRef.current) return

    const canvas = canvasRef.current
    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight
    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)

    // Count connections per node for sizing
    const connectionCount = new Map<string, number>()
    for (const link of graphData.links) {
      connectionCount.set(link.source, (connectionCount.get(link.source) || 0) + 1)
      connectionCount.set(link.target, (connectionCount.get(link.target) || 0) + 1)
    }

    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) * 0.35

    nodesRef.current = graphData.nodes.map((node, i) => {
      const angle = (2 * Math.PI * i) / graphData.nodes.length
      const connections = connectionCount.get(node.id) || 0
      return {
        ...node,
        x: centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 60,
        y: centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 60,
        vx: 0,
        vy: 0,
        radius: Math.max(4, Math.min(14, 4 + connections * 2)),
        connections,
      }
    })

    const nodeMap = new Map(nodesRef.current.map((n) => [n.id, n]))
    let iteration = 0

    const tick = () => {
      iteration++
      timeRef.current = iteration
      const alpha = Math.max(0.002, 1 - iteration / 400)
      const nodes = nodesRef.current
      const hovered = hoveredRef.current

      // Physics: repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x
          const dy = nodes[j].y - nodes[i].y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const minDist = nodes[i].radius + nodes[j].radius + 40
          const force = ((minDist * 3) * alpha) / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          nodes[i].vx -= fx
          nodes[i].vy -= fy
          nodes[j].vx += fx
          nodes[j].vy += fy
        }
      }

      // Physics: attraction along links
      for (const link of graphData.links) {
        const source = nodeMap.get(link.source)
        const target = nodeMap.get(link.target)
        if (!source || !target) continue
        const dx = target.x - source.x
        const dy = target.y - source.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const ideal = 120
        const force = (dist - ideal) * 0.008 * alpha
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        source.vx += fx
        source.vy += fy
        target.vx -= fx
        target.vy -= fy
      }

      // Center gravity + velocity damping
      for (const node of nodes) {
        node.vx += (centerX - node.x) * 0.003 * alpha
        node.vy += (centerY - node.y) * 0.003 * alpha
        node.vx *= 0.85
        node.vy *= 0.85
        node.x += node.vx
        node.y += node.vy
        node.x = Math.max(40, Math.min(width - 40, node.x))
        node.y = Math.max(40, Math.min(height - 40, node.y))
      }

      // --- RENDER ---
      // Background
      const bgGrad = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, Math.max(width, height) * 0.7)
      bgGrad.addColorStop(0, '#111827')
      bgGrad.addColorStop(1, '#0a0e1a')
      ctx.fillStyle = bgGrad
      ctx.fillRect(0, 0, width, height)

      // Subtle grid dots
      ctx.fillStyle = 'rgba(255, 255, 255, 0.03)'
      for (let gx = 0; gx < width; gx += 30) {
        for (let gy = 0; gy < height; gy += 30) {
          ctx.fillRect(gx, gy, 1, 1)
        }
      }

      // Find hovered node's connections for highlighting
      const highlightLinks = new Set<string>()
      const highlightNodes = new Set<string>()
      if (hovered) {
        highlightNodes.add(hovered)
        for (const link of graphData.links) {
          if (link.source === hovered || link.target === hovered) {
            highlightLinks.add(`${link.source}-${link.target}`)
            highlightNodes.add(link.source)
            highlightNodes.add(link.target)
          }
        }
      }

      // Links
      for (const link of graphData.links) {
        const source = nodeMap.get(link.source)
        const target = nodeMap.get(link.target)
        if (!source || !target) continue

        const linkId = `${link.source}-${link.target}`
        const isHighlighted = highlightLinks.has(linkId)
        const isDimmed = hovered && !isHighlighted

        // Curved links
        const mx = (source.x + target.x) / 2
        const my = (source.y + target.y) / 2
        const dx = target.x - source.x
        const dy = target.y - source.y
        const offset = Math.min(20, Math.sqrt(dx * dx + dy * dy) * 0.08)
        const cx = mx - dy * offset / Math.sqrt(dx * dx + dy * dy || 1)
        const cy = my + dx * offset / Math.sqrt(dx * dx + dy * dy || 1)

        ctx.beginPath()
        ctx.moveTo(source.x, source.y)
        ctx.quadraticCurveTo(cx, cy, target.x, target.y)

        if (isHighlighted) {
          const sourceColor = CATEGORY_COLORS[source.category] || CATEGORY_COLORS.general
          ctx.strokeStyle = sourceColor.fill + '80'
          ctx.lineWidth = 1.5
        } else {
          ctx.strokeStyle = isDimmed ? 'rgba(255, 255, 255, 0.03)' : 'rgba(255, 255, 255, 0.08)'
          ctx.lineWidth = 0.5
        }
        ctx.stroke()

        // Animated particles along highlighted links
        if (isHighlighted) {
          const t = ((iteration * 0.015) % 1)
          const px = (1 - t) * (1 - t) * source.x + 2 * (1 - t) * t * cx + t * t * target.x
          const py = (1 - t) * (1 - t) * source.y + 2 * (1 - t) * t * cy + t * t * target.y
          const sourceColor = CATEGORY_COLORS[source.category] || CATEGORY_COLORS.general
          ctx.beginPath()
          ctx.arc(px, py, 2, 0, 2 * Math.PI)
          ctx.fillStyle = sourceColor.fill
          ctx.fill()
        }
      }

      // Nodes
      for (const node of nodes) {
        const colors = CATEGORY_COLORS[node.category] || CATEGORY_COLORS.general
        const isHovered = hovered === node.id
        const isConnected = highlightNodes.has(node.id)
        const isDimmed = hovered && !isConnected
        const r = isHovered ? node.radius * 1.4 : node.radius

        // Outer glow
        if (isHovered || isConnected) {
          const glowR = r + (isHovered ? 20 : 10)
          const glow = ctx.createRadialGradient(node.x, node.y, r, node.x, node.y, glowR)
          glow.addColorStop(0, colors.glow)
          glow.addColorStop(1, 'rgba(0,0,0,0)')
          ctx.beginPath()
          ctx.arc(node.x, node.y, glowR, 0, 2 * Math.PI)
          ctx.fillStyle = glow
          ctx.fill()
        }

        // Pulse ring on hover
        if (isHovered) {
          const pulsePhase = (iteration * 0.05) % 1
          const pulseR = r + 8 + pulsePhase * 15
          ctx.beginPath()
          ctx.arc(node.x, node.y, pulseR, 0, 2 * Math.PI)
          ctx.strokeStyle = colors.fill + Math.round((1 - pulsePhase) * 60).toString(16).padStart(2, '0')
          ctx.lineWidth = 1
          ctx.stroke()
        }

        // Node fill
        const nodeGrad = ctx.createRadialGradient(node.x - r * 0.3, node.y - r * 0.3, 0, node.x, node.y, r)
        nodeGrad.addColorStop(0, colors.fill)
        nodeGrad.addColorStop(1, colors.fill + 'cc')
        ctx.beginPath()
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
        ctx.fillStyle = isDimmed ? 'rgba(75, 85, 99, 0.3)' : nodeGrad
        ctx.fill()

        // Inner highlight (glass effect)
        if (!isDimmed) {
          ctx.beginPath()
          ctx.arc(node.x - r * 0.2, node.y - r * 0.2, r * 0.5, 0, 2 * Math.PI)
          ctx.fillStyle = 'rgba(255, 255, 255, 0.15)'
          ctx.fill()
        }

        // Labels
        if (isHovered || isConnected || nodes.length < 25) {
          const label = node.title.length > 25 ? node.title.slice(0, 25) + '...' : node.title
          ctx.font = isHovered
            ? 'bold 12px Inter, system-ui, sans-serif'
            : '10px Inter, system-ui, sans-serif'
          ctx.textAlign = 'center'

          // Text shadow
          ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'
          ctx.fillText(label, node.x + 1, node.y + r + 15)

          // Text
          ctx.fillStyle = isDimmed
            ? 'rgba(156, 163, 175, 0.3)'
            : isHovered
              ? '#ffffff'
              : 'rgba(209, 213, 219, 0.8)'
          ctx.fillText(label, node.x, node.y + r + 14)

          // Connection count badge on hover
          if (isHovered && node.connections > 0) {
            const badge = `${node.connections} connections`
            ctx.font = '9px Inter, system-ui, sans-serif'
            ctx.fillStyle = 'rgba(156, 163, 175, 0.6)'
            ctx.fillText(badge, node.x, node.y + r + 27)
          }
        }
      }

      // Keep animating (slower after physics settle for hover effects)
      animRef.current = requestAnimationFrame(tick)
    }

    animRef.current = requestAnimationFrame(tick)
  }, [graphData])

  useEffect(() => {
    initSimulation()
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current)
    }
  }, [initSimulation])

  // Resize handler
  useEffect(() => {
    const handleResize = () => {
      if (animRef.current) cancelAnimationFrame(animRef.current)
      initSimulation()
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [initSimulation])

  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!canvasRef.current) return
      const rect = canvasRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      for (const node of nodesRef.current) {
        const dx = node.x - x
        const dy = node.y - y
        if (dx * dx + dy * dy < (node.radius + 5) * (node.radius + 5)) {
          router.push(`/knowledge-bases/${kbId}/wiki/${node.slug}`)
          return
        }
      }
    },
    [kbId, router],
  )

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!canvasRef.current) return
      const rect = canvasRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      let found: string | null = null
      for (const node of nodesRef.current) {
        const dx = node.x - x
        const dy = node.y - y
        if (dx * dx + dy * dy < (node.radius + 8) * (node.radius + 8)) {
          found = node.id
          break
        }
      }
      if (found !== hoveredNode) {
        setHoveredNode(found)
      }
    },
    [hoveredNode],
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-[3px] border-gray-700 border-b-primary-500 rounded-full animate-spin" />
          <span className="text-xs font-bold text-gray-500">Loading graph...</span>
        </div>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-900 gap-3">
        <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center border border-gray-700">
          <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        </div>
        <p className="text-sm font-bold text-gray-500">No articles to visualize yet</p>
        <p className="text-xs text-gray-600">Compile your knowledge base first</p>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseMove={handleCanvasMouseMove}
        className={hoveredNode ? 'cursor-pointer' : 'cursor-default'}
      />
      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex flex-wrap gap-3 bg-gray-900/90 backdrop-blur-md rounded-xl px-5 py-3 border border-gray-700/50">
        {Object.entries(CATEGORY_COLORS).map(([cat, colors]) => (
          <div key={cat} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colors.fill, boxShadow: `0 0 6px ${colors.glow}` }} />
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{cat}</span>
          </div>
        ))}
      </div>
      {/* Stats */}
      <div className="absolute top-4 right-4 bg-gray-900/90 backdrop-blur-md rounded-xl px-5 py-3 border border-gray-700/50">
        <div className="flex items-center gap-5 text-xs text-gray-400">
          <span><span className="text-white font-extrabold">{graphData.nodes.length}</span> <span className="font-semibold">articles</span></span>
          <span><span className="text-white font-extrabold">{graphData.links.length}</span> <span className="font-semibold">connections</span></span>
        </div>
      </div>
    </div>
  )
}
