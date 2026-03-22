/**
 * Chat History Management Utility
 * Manages multiple chat sessions in localStorage
 */

export interface ChatSession {
  id: string
  title: string
  agentName: string
  messages: any[]
  lastMessage?: string
  timestamp: Date
  createdAt: Date
}

const SESSIONS_KEY_PREFIX = 'chat_sessions_'
const MAX_SESSIONS = 50 // Keep max 50 sessions per agent

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Get all sessions for an agent
 */
export function getAllSessions(agentName: string): ChatSession[] {
  try {
    const key = `${SESSIONS_KEY_PREFIX}${agentName}`
    const data = localStorage.getItem(key)
    if (!data) return []
    
    const sessions = JSON.parse(data)
    return sessions.map((session: any) => ({
      ...session,
      timestamp: new Date(session.timestamp),
      createdAt: new Date(session.createdAt),
    }))
  } catch (error) {
    console.error('Failed to load sessions:', error)
    return []
  }
}

/**
 * Get a specific session by ID
 */
export function getSession(agentName: string, sessionId: string): ChatSession | null {
  const sessions = getAllSessions(agentName)
  return sessions.find(s => s.id === sessionId) || null
}

/**
 * Save or update a session
 */
export function saveSession(agentName: string, session: ChatSession): void {
  try {
    const sessions = getAllSessions(agentName)
    const existingIndex = sessions.findIndex(s => s.id === session.id)
    
    if (existingIndex >= 0) {
      // Update existing session
      sessions[existingIndex] = {
        ...session,
        timestamp: new Date(),
      }
    } else {
      // Add new session
      sessions.unshift({
        ...session,
        timestamp: new Date(),
        createdAt: new Date(),
      })
    }
    
    // Keep only the most recent MAX_SESSIONS
    const trimmedSessions = sessions.slice(0, MAX_SESSIONS)
    
    const key = `${SESSIONS_KEY_PREFIX}${agentName}`
    localStorage.setItem(key, JSON.stringify(trimmedSessions))
  } catch (error) {
    console.error('Failed to save session:', error)
  }
}

/**
 * Delete a session
 */
export function deleteSession(agentName: string, sessionId: string): void {
  try {
    const sessions = getAllSessions(agentName)
    const filtered = sessions.filter(s => s.id !== sessionId)
    
    const key = `${SESSIONS_KEY_PREFIX}${agentName}`
    localStorage.setItem(key, JSON.stringify(filtered))
  } catch (error) {
    console.error('Failed to delete session:', error)
  }
}

/**
 * Get the most recent sessions (for sidebar display)
 */
export function getRecentSessions(agentName: string, limit: number = 10): ChatSession[] {
  const sessions = getAllSessions(agentName)
  return sessions
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    .slice(0, limit)
}

/**
 * Generate a title for a session based on the first user message
 */
export function generateSessionTitle(messages: any[]): string {
  const firstUserMessage = messages.find(m => m.role === 'user')
  if (!firstUserMessage) return 'New Chat'
  
  const content = firstUserMessage.content.trim()
  if (content.length <= 50) return content
  
  return content.substring(0, 47) + '...'
}

/**
 * Migrate old single-session history to new multi-session format
 */
export function migrateOldHistory(agentName: string): void {
  try {
    const oldKey = `chat_history_advanced_${agentName}`
    const oldData = localStorage.getItem(oldKey)
    
    if (!oldData) return
    
    const oldMessages = JSON.parse(oldData)
    if (!oldMessages || oldMessages.length === 0) return
    
    // Check if we already have sessions
    const existingSessions = getAllSessions(agentName)
    if (existingSessions.length > 0) {
      // Already migrated, just remove old key
      localStorage.removeItem(oldKey)
      return
    }
    
    // Create a new session from old messages
    const session: ChatSession = {
      id: generateSessionId(),
      title: generateSessionTitle(oldMessages),
      agentName,
      messages: oldMessages,
      lastMessage: oldMessages[oldMessages.length - 1]?.content?.substring(0, 50),
      timestamp: new Date(),
      createdAt: new Date(),
    }
    
    saveSession(agentName, session)
    
    // Remove old key
    localStorage.removeItem(oldKey)
    
  } catch (error) {
    console.error('Failed to migrate old history:', error)
  }
}
