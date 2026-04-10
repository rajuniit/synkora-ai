'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/hooks/useAuth'
import { apiClient } from '@/lib/api/client'
import Link from 'next/link'
import { Bot, BookOpen, Database, Server, Plus, TrendingUp, Activity } from 'lucide-react'

interface DashboardStats {
  totalAgents: number
  knowledgeBases: number
  dataSources: number
  mcpServers: number
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats>({
    totalAgents: 0,
    knowledgeBases: 0,
    dataSources: 0,
    mcpServers: 0
  })
  const [loading, setLoading] = useState(true)
  const [recentActivity, setRecentActivity] = useState<any[]>([])

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      
      // Fetch all data in parallel
      const [agentsResponse, knowledgeBases, dataSources, mcpServers] = await Promise.all([
        apiClient.getAgents().catch(() => ({ agents: [], pagination: { total: 0 } })),
        apiClient.getKnowledgeBases().catch(() => []),
        apiClient.getDataSources().catch(() => []),
        apiClient.getMCPServers().catch(() => [])
      ])

      // Extract agents array from response
      const agents = Array.isArray(agentsResponse) ? agentsResponse : (agentsResponse.agents || [])
      const totalAgents = agentsResponse.pagination?.total || agents.length

      setStats({
        totalAgents: totalAgents,
        knowledgeBases: Array.isArray(knowledgeBases) ? knowledgeBases.length : 0,
        dataSources: Array.isArray(dataSources) ? dataSources.length : 0,
        mcpServers: Array.isArray(mcpServers) ? mcpServers.length : 0
      })

      // Build recent activity from the data
      const activities: any[] = []
      
      // Add recent agents (last 3) - use data already fetched, no extra round-trip
      if (Array.isArray(agents) && agents.length > 0) {
        agents.slice(0, 3).forEach((agent: any) => {
          activities.push({
            type: 'agent',
            title: 'Agent created',
            description: `${agent.agent_name || agent.name} was created`,
            time: agent.created_at,
            icon: Bot,
            color: 'teal'
          })
        })
      }

      // Add recent knowledge bases (last 2)
      if (Array.isArray(knowledgeBases) && knowledgeBases.length > 0) {
        knowledgeBases.slice(-2).reverse().forEach((kb: any) => {
          activities.push({
            type: 'knowledge_base',
            title: 'Knowledge base updated',
            description: `${kb.name} was updated`,
            time: kb.updated_at || kb.created_at,
            icon: BookOpen,
            color: 'green'
          })
        })
      }

      // Add recent data sources (last 2)
      if (Array.isArray(dataSources) && dataSources.length > 0) {
        dataSources.slice(-2).reverse().forEach((ds: any) => {
          activities.push({
            type: 'data_source',
            title: 'Data source connected',
            description: `${ds.name} was connected`,
            time: ds.created_at,
            icon: Database,
            color: 'purple'
          })
        })
      }

      // Sort by time and take top 3
      activities.sort((a, b) => {
        const timeA = new Date(a.time || 0).getTime()
        const timeB = new Date(b.time || 0).getTime()
        return timeB - timeA
      })

      setRecentActivity(activities.slice(0, 3))
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTimeAgo = (timestamp: string) => {
    if (!timestamp) return 'Recently'
    
    const now = new Date().getTime()
    const time = new Date(timestamp).getTime()
    const diff = now - time
    
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
    if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`
    return `${days} day${days !== 1 ? 's' : ''} ago`
  }

  const statsData = [
    {
      name: 'Total Agents',
      value: loading ? '...' : stats.totalAgents.toString(),
      icon: <Bot className="w-5 h-5" />,
      lightColor: 'bg-red-50',
      textColor: 'text-primary-600',
      href: '/agents'
    },
    {
      name: 'Knowledge Bases',
      value: loading ? '...' : stats.knowledgeBases.toString(),
      icon: <BookOpen className="w-5 h-5" />,
      lightColor: 'bg-red-50',
      textColor: 'text-primary-600',
      href: '/knowledge-bases'
    },
    {
      name: 'Data Sources',
      value: loading ? '...' : stats.dataSources.toString(),
      icon: <Database className="w-5 h-5" />,
      lightColor: 'bg-red-50',
      textColor: 'text-primary-600',
      href: '/data-sources'
    },
    {
      name: 'MCP Servers',
      value: loading ? '...' : stats.mcpServers.toString(),
      icon: <Server className="w-5 h-5" />,
      lightColor: 'bg-red-50',
      textColor: 'text-primary-600',
      href: '/mcp-servers'
    }
  ]

  const quickActions = [
    {
      name: 'Create Agent',
      description: 'Build a new AI agent',
      icon: <Plus className="w-5 h-5" />,
      href: '/agents/create',
      bgColor: 'bg-primary-500',
      hoverColor: 'hover:bg-primary-600',
      textColor: 'text-white',
      descColor: 'text-white/90'
    },
    {
      name: 'Browse Agents',
      description: 'Explore public agents',
      icon: <Activity className="w-5 h-5" />,
      href: '/browse',
      bgColor: 'bg-white',
      hoverColor: 'hover:bg-gray-50',
      textColor: 'text-gray-900',
      descColor: 'text-gray-500',
      borderColor: 'border border-gray-200'
    },
    {
      name: 'Add Knowledge Base',
      description: 'Upload documents',
      icon: <BookOpen className="w-5 h-5" />,
      href: '/knowledge-bases/create',
      bgColor: 'bg-white',
      hoverColor: 'hover:bg-gray-50',
      textColor: 'text-gray-900',
      descColor: 'text-gray-500',
      borderColor: 'border border-gray-200'
    },
    {
      name: 'Connect Data Source',
      description: 'Link external data',
      icon: <Database className="w-5 h-5" />,
      href: '/data-sources/connect',
      bgColor: 'bg-white',
      hoverColor: 'hover:bg-gray-50',
      textColor: 'text-gray-900',
      descColor: 'text-gray-500',
      borderColor: 'border border-gray-200'
    }
  ]

  const getActivityColor = (color: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      teal: { bg: 'bg-red-100', text: 'text-primary-600' },
      green: { bg: 'bg-red-100', text: 'text-primary-600' },
      purple: { bg: 'bg-red-100', text: 'text-primary-600' },
      blue: { bg: 'bg-red-100', text: 'text-primary-600' }
    }
    return colors[color] || colors.teal
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-8">
      <div className="max-w-7xl mx-auto py-4 md:py-6">
        {/* Header */}
        <div className="mb-6 md:mb-8">
          <h1 className="text-2xl md:text-4xl font-extrabold text-gray-900 tracking-tight">
            Welcome back, {user?.name || 'User'}
          </h1>
          <p className="text-sm md:text-lg text-gray-600 mt-2">
            Here's what's happening with your AI platform today.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-6 md:mb-8">
          {statsData.map((stat) => (
            <Link
              key={stat.name}
              href={stat.href}
              className="relative bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1"
            >
              <div className="flex items-start justify-between mb-4">
                <div className={`${stat.lightColor} p-3 rounded-full`}>
                  <div className={`${stat.textColor} w-6 h-6`}>
                    {stat.icon}
                  </div>
                </div>
                <TrendingUp className="w-5 h-5 text-gray-400" />
              </div>
              <h3 className="text-3xl font-extrabold text-gray-900 mb-1">{stat.value}</h3>
              <p className="text-sm text-gray-500 font-medium">{stat.name}</p>
            </Link>
          ))}
        </div>

        {/* Quick Actions */}
        <div className="mb-6 md:mb-8">
          <h2 className="text-xl md:text-2xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            {quickActions.map((action) => (
              <Link
                key={action.name}
                href={action.href}
                className={`${action.bgColor} ${action.hoverColor} ${action.textColor} ${action.borderColor || ''} rounded-xl shadow-lg p-6 transition-all duration-300 transform hover:-translate-y-1`}
              >
                <div className="mb-4">
                  <div className="p-3 rounded-full bg-white/20">
                    {action.icon}
                  </div>
                </div>
                <h3 className="text-lg font-semibold mb-1">{action.name}</h3>
                <p className={`text-sm ${action.descColor || 'text-gray-300'}`}>{action.description}</p>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100">
          <div className="px-4 md:px-6 py-4 border-b border-gray-100">
            <h2 className="text-xl md:text-2xl font-semibold text-gray-900">Recent Activity</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {loading ? (
              <div className="p-6 text-center text-md text-gray-500">Loading activity...</div>
            ) : recentActivity.length === 0 ? (
              <div className="p-6 text-center text-md text-gray-500">
                No recent activity. Start by creating an agent or knowledge base!
              </div>
            ) : (
              recentActivity.map((activity, index) => {
                const colors = getActivityColor(activity.color)
                const Icon = activity.icon
                
                return (
                  <div key={index} className="p-4 md:p-6 hover:bg-gray-50 transition-colors duration-200">
                    <div className="flex items-center gap-3 md:gap-4">
                      <div className={`w-10 h-10 ${colors.bg} rounded-full flex items-center justify-center flex-shrink-0`}>
                        <Icon className={`w-5 h-5 ${colors.text}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-md font-medium text-gray-900 truncate">{activity.title}</p>
                        <p className="text-sm text-gray-500 truncate">{activity.description}</p>
                      </div>
                      <span className="text-sm text-gray-400 whitespace-nowrap">{getTimeAgo(activity.time)}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
