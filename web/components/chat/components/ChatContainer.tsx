'use client'

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface ChatContainerProps {
  children: ReactNode
  className?: string
  showLeftSidebar?: boolean
  showRightSidebar?: boolean
  style?: React.CSSProperties
}

/**
 * ChatContainer - Main layout container for the chat interface
 * Provides a 3-column layout: left sidebar, main chat area, right sidebar
 */
export function ChatContainer({
  children,
  className,
  style,
}: ChatContainerProps) {
  return (
    <div
      className={cn(
        'flex h-screen w-full bg-gradient-to-br from-gray-50 via-white to-gray-50',
        className
      )}
      style={style}
    >
      {children}
    </div>
  )
}

interface ChatContainerSectionProps {
  children: ReactNode
  className?: string
  side?: 'left' | 'center' | 'right'
  onMouseEnter?: () => void
  onMouseLeave?: () => void
}

/**
 * ChatContainerSection - Individual section within the container
 */
export function ChatContainerSection({
  children,
  className,
  side = 'center',
  onMouseEnter,
  onMouseLeave,
}: ChatContainerSectionProps) {
  const sideStyles = {
    left: 'w-56 border-r border-gray-200/60 bg-gray-50/50 flex-shrink-0',
    center: 'flex-1 flex flex-col min-w-0 bg-white',
    right: 'w-72 border-l border-gray-200/60 bg-gray-50/30 flex-shrink-0',
  }

  return (
    <div
      className={cn(sideStyles[side], className)}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {children}
    </div>
  )
}
