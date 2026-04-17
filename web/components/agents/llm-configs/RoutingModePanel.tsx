'use client'

import { useState } from 'react'
import { RoutingMode, ROUTING_MODE_LABELS, ROUTING_MODE_DESCRIPTIONS } from '@/types/agent-llm-config'

interface RoutingModePanelProps {
  agentName: string
  currentMode: RoutingMode
  routingConfig?: Record<string, any>
  onSave: (mode: RoutingMode, config: Record<string, any>) => Promise<void>
}

const MODE_ICONS: Record<RoutingMode, string> = {
  fixed: '🔒',
  round_robin: '⚖️',
  cost_opt: '💰',
  intent: '🎯',
  latency_opt: '⚡',
}

// Exported as default; import as: import RoutingModePanel from '@/components/agents/llm-configs/RoutingModePanel'
export default function RoutingModePanel({
  agentName,
  currentMode,
  routingConfig = {},
  onSave,
}: RoutingModePanelProps) {
  const [selectedMode, setSelectedMode] = useState<RoutingMode>(currentMode)
  const [qualityFloor, setQualityFloor] = useState<number>(
    routingConfig.quality_floor ?? 0.5
  )
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const modes: RoutingMode[] = ['fixed', 'cost_opt', 'intent', 'latency_opt', 'round_robin']

  const hasChanges =
    selectedMode !== currentMode ||
    (selectedMode === 'cost_opt' && qualityFloor !== (routingConfig.quality_floor ?? 0.5))

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const config: Record<string, any> = {}
      if (selectedMode === 'cost_opt') {
        config.quality_floor = qualityFloor
      }
      await onSave(selectedMode, config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Model Routing</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Control how requests are distributed across your configured models to reduce cost
          </p>
        </div>
        {hasChanges && (
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            {isSaving ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : saved ? (
              '✓ Saved'
            ) : (
              'Save Routing'
            )}
          </button>
        )}
        {!hasChanges && saved && (
          <span className="text-sm text-green-600 font-medium">✓ Saved</span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {modes.map((mode) => {
          const isSelected = selectedMode === mode
          return (
            <button
              key={mode}
              onClick={() => setSelectedMode(mode)}
              className={`relative text-left p-4 rounded-lg border-2 transition-all ${
                isSelected
                  ? 'border-red-500 bg-red-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              {isSelected && (
                <span className="absolute top-2 right-2 w-4 h-4 rounded-full bg-red-500 flex items-center justify-center">
                  <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
                    <path d="M10 3L5 8.5 2 5.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  </svg>
                </span>
              )}
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-lg">{MODE_ICONS[mode]}</span>
                <span className={`text-sm font-semibold ${isSelected ? 'text-red-700' : 'text-gray-800'}`}>
                  {ROUTING_MODE_LABELS[mode]}
                </span>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                {ROUTING_MODE_DESCRIPTIONS[mode]}
              </p>
            </button>
          )
        })}
      </div>

      {/* Cost Opt extra settings */}
      {selectedMode === 'cost_opt' && (
        <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm font-medium text-amber-800 mb-3">Cost Optimization Settings</p>
          <div>
            <label className="flex items-center justify-between text-sm text-gray-700 mb-2">
              <span>Quality floor</span>
              <span className="font-mono text-xs bg-white border border-gray-200 px-2 py-0.5 rounded">
                {qualityFloor.toFixed(1)}
              </span>
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={qualityFloor}
              onChange={(e) => setQualityFloor(parseFloat(e.target.value))}
              className="w-full accent-red-500"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0.0 — cheapest</span>
              <span>1.0 — safest</span>
            </div>
            <p className="text-xs text-amber-700 mt-2">
              Prevents routing complex queries to cheap models. Set higher if accuracy is critical.
            </p>
          </div>
        </div>
      )}

      {/* Round robin note */}
      {selectedMode === 'round_robin' && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-700">
            Set the <span className="font-semibold">Weight</span> on each model config below to control
            how often it gets selected. Higher weight = more traffic.
          </p>
        </div>
      )}

      {/* Intent note */}
      {selectedMode === 'intent' && (
        <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
          <p className="text-xs text-purple-700">
            Assign <span className="font-semibold">Intent Tags</span> on each model config below to
            control which query types it handles (e.g., code, math, simple_qa).
          </p>
        </div>
      )}
    </div>
  )
}
