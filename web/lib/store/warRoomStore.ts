import { create } from 'zustand'
import type { DebateSession, DebateMessage, DebateParticipant, DebateEvent } from '../api/war-room'

interface WarRoomState {
  currentDebate: DebateSession | null
  streamingParticipantId: string | null
  streamingContent: string

  setDebate: (debate: DebateSession) => void
  clearDebate: () => void
  handleEvent: (event: DebateEvent) => void
  addMessage: (msg: DebateMessage) => void
  setVerdict: (content: string) => void
  setStatus: (status: DebateSession['status']) => void
}

export const useWarRoomStore = create<WarRoomState>((set, get) => ({
  currentDebate: null,
  streamingParticipantId: null,
  streamingContent: '',

  setDebate: (debate) => set({ currentDebate: debate }),
  clearDebate: () => set({ currentDebate: null, streamingParticipantId: null, streamingContent: '' }),

  handleEvent: (event) => {
    const state = get()
    const debate = state.currentDebate
    if (!debate) return

    switch (event.type) {
      case 'debate_start':
        set({
          currentDebate: {
            ...debate,
            status: 'active',
            current_round: 0,
          },
        })
        break

      case 'round_start':
        set({
          currentDebate: {
            ...debate,
            current_round: event.round || debate.current_round,
          },
        })
        break

      case 'participant_start':
        set({
          streamingParticipantId: event.participant_id || null,
          streamingContent: '',
        })
        break

      case 'participant_chunk':
        set({ streamingContent: state.streamingContent + (event.content || '') })
        break

      case 'participant_done': {
        const participant = debate.participants.find(p => p.id === event.participant_id)
        const msg: DebateMessage = {
          id: `${event.participant_id}-${event.round}`,
          participant_id: event.participant_id || '',
          agent_name: event.agent_name || '',
          round: event.round || 0,
          content: event.content || '',
          is_verdict: false,
          is_external: participant?.is_external || (event as any).is_external || false,
          created_at: new Date().toISOString(),
          color: event.color || '#6366f1',
        }
        set({
          currentDebate: {
            ...debate,
            messages: [...debate.messages, msg],
          },
          streamingParticipantId: null,
          streamingContent: '',
        })
        break
      }

      case 'synthesis_start':
        set({
          currentDebate: { ...debate, status: 'synthesizing' },
          streamingParticipantId: 'synthesizer',
          streamingContent: '',
        })
        break

      case 'synthesis_chunk':
        set({ streamingContent: state.streamingContent + (event.content || '') })
        break

      case 'verdict':
        set({
          currentDebate: { ...debate, verdict: event.content || '', status: 'completed' },
          streamingParticipantId: null,
          streamingContent: '',
        })
        break

      case 'debate_end':
        set({
          currentDebate: { ...debate, status: 'completed' },
          streamingParticipantId: null,
          streamingContent: '',
        })
        break
    }
  },

  addMessage: (msg) => {
    const debate = get().currentDebate
    if (!debate) return
    set({ currentDebate: { ...debate, messages: [...debate.messages, msg] } })
  },

  setVerdict: (content) => {
    const debate = get().currentDebate
    if (!debate) return
    set({ currentDebate: { ...debate, verdict: content } })
  },

  setStatus: (status) => {
    const debate = get().currentDebate
    if (!debate) return
    set({ currentDebate: { ...debate, status } })
  },
}))
