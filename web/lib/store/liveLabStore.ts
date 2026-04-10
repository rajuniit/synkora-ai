import { create } from 'zustand'
import type { ExecutionSummary, ExecutionEvent } from '../api/live-lab'

interface CurrentExecution {
  id: string
  agentName: string
  agentId: string
  triggerSource: string
  triggerDetail: string
  messagePreview: string
  status: 'running' | 'complete' | 'error' | 'cancelled'
  events: ExecutionEvent[]
  workspaceContent: string
  activeTools: string[]
  completedTools: string[]
  metrics: {
    startedAt: string
    completedAt: string
    tokens: number
    toolCount: number
    cost: number
  }
  error: string
}

interface LiveLabState {
  activeExecutions: ExecutionSummary[]
  recentExecutions: ExecutionSummary[]
  currentExecution: CurrentExecution | null
  isLoading: boolean
  hubPollingActive: boolean

  setActiveExecutions: (executions: ExecutionSummary[]) => void
  setRecentExecutions: (executions: ExecutionSummary[]) => void
  setLoading: (loading: boolean) => void
  setHubPolling: (active: boolean) => void

  // Current execution actions
  initCurrentExecution: (exec: ExecutionSummary) => void
  clearCurrentExecution: () => void
  appendEvent: (event: ExecutionEvent) => void
  setCurrentStatus: (status: CurrentExecution['status']) => void
}

export const useLiveLabStore = create<LiveLabState>((set, get) => ({
  activeExecutions: [],
  recentExecutions: [],
  currentExecution: null,
  isLoading: true,
  hubPollingActive: false,

  setActiveExecutions: (executions) => set({ activeExecutions: executions }),
  setRecentExecutions: (executions) => set({ recentExecutions: executions }),
  setLoading: (loading) => set({ isLoading: loading }),
  setHubPolling: (active) => set({ hubPollingActive: active }),

  initCurrentExecution: (exec) =>
    set({
      currentExecution: {
        id: exec.id,
        agentName: exec.agent_name,
        agentId: exec.agent_id,
        triggerSource: exec.trigger_source,
        triggerDetail: exec.trigger_detail,
        messagePreview: exec.message_preview,
        status: exec.status,
        events: [],
        workspaceContent: '',
        activeTools: [],
        completedTools: [],
        metrics: {
          startedAt: exec.started_at,
          completedAt: exec.completed_at,
          tokens: exec.total_tokens,
          toolCount: exec.total_tools,
          cost: exec.cost,
        },
        error: exec.error,
      },
    }),

  clearCurrentExecution: () => set({ currentExecution: null }),

  appendEvent: (event) => {
    const current = get().currentExecution
    if (!current) return

    const updates: Partial<CurrentExecution> = {
      events: [...current.events, event],
    }

    if (event.type === 'chunk' && event.content) {
      updates.workspaceContent = current.workspaceContent + event.content
    }

    if (event.type === 'tool_status' && event.tool_name) {
      if (event.status === 'started') {
        updates.activeTools = [...current.activeTools, event.tool_name]
      } else if (event.status === 'completed' || event.status === 'error') {
        updates.activeTools = current.activeTools.filter((t) => t !== event.tool_name)
        if (!current.completedTools.includes(event.tool_name)) {
          updates.completedTools = [...current.completedTools, event.tool_name]
        }
        updates.metrics = {
          ...current.metrics,
          toolCount: (updates.completedTools || current.completedTools).length,
        }
      }
    }

    if (event.type === 'done') {
      updates.status = 'complete'
      // Populate workspace from stored content (for replay of completed executions)
      if (event.content && !current.workspaceContent) {
        updates.workspaceContent = event.content as string
      }
      const meta = event.metadata as Record<string, number> | undefined
      if (meta) {
        updates.metrics = {
          ...current.metrics,
          ...updates.metrics,
          tokens: meta.total_tokens || current.metrics.tokens,
        }
      }
    }

    if (event.type === 'error') {
      updates.status = 'error'
      updates.error = event.error || ''
    }

    set({ currentExecution: { ...current, ...updates } })
  },

  setCurrentStatus: (status) => {
    const current = get().currentExecution
    if (current) {
      set({ currentExecution: { ...current, status } })
    }
  },
}))
