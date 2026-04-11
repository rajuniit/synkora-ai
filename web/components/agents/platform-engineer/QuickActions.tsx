'use client'

const QUICK_ACTIONS = [
  { label: 'Create an agent', prompt: 'I want to create a new AI agent. Help me design one.' },
  { label: 'List my agents', prompt: 'Show me all my current agents' },
  { label: 'Available tools', prompt: 'What tools and integrations are available on this platform?' },
  { label: 'Code review agent', prompt: 'Help me create a code review agent' },
]

interface Props {
  onSelect: (prompt: string) => void
  disabled?: boolean
}

export function QuickActions({ onSelect, disabled }: Props) {
  return (
    <div className="flex flex-wrap gap-2 px-4 pb-2">
      {QUICK_ACTIONS.map((action) => (
        <button
          key={action.label}
          disabled={disabled}
          onClick={() => onSelect(action.prompt)}
          className="px-3 py-1.5 text-xs bg-primary-50 border border-primary-200 text-primary-700 rounded-full hover:bg-primary-100 hover:border-primary-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {action.label}
        </button>
      ))}
    </div>
  )
}
