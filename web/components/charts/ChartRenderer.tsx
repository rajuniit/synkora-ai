'use client'

import { useState, useRef, useCallback } from 'react'
import dynamic from 'next/dynamic'

// ---------------------------------------------------------------------------
// Lazy-load all three rendering libraries to avoid shipping ~350 KB of
// Chart.js + Recharts on every page load. Each sub-renderer is a separate
// dynamic import so only the bundle matching the chart.library value loads.
// ---------------------------------------------------------------------------

const ChartJSRenderer = dynamic(
  () => import('./renderers/ChartJSRenderer').then((m) => ({ default: m.ChartJSRenderer })),
  { ssr: false, loading: () => <ChartPlaceholder /> }
)

const RechartsRenderer = dynamic(
  () => import('./renderers/RechartsRenderer').then((m) => ({ default: m.RechartsRenderer })),
  { ssr: false, loading: () => <ChartPlaceholder /> }
)

const PlotlyRenderer = dynamic(
  () => import('./renderers/PlotlyRenderer').then((m) => ({ default: m.PlotlyRenderer })),
  { ssr: false, loading: () => <ChartPlaceholder /> }
)

function ChartPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full text-gray-300 text-sm animate-pulse">
      Loading chart…
    </div>
  )
}

export interface ChartData {
  id: string
  title: string
  description?: string
  chart_type: string
  library: string
  config: Record<string, unknown>
  data: Record<string, unknown>
  table_data?: Array<Record<string, unknown>>
  query?: string
  created_at: string
}

interface ChartRendererProps {
  chart: ChartData
  className?: string
}

export function ChartRenderer({ chart, className = '' }: ChartRendererProps) {
  const [showData, setShowData] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)

  const downloadPng = useCallback(() => {
    // Chart.js: canvas-based
    const canvas = chartRef.current?.querySelector('canvas')
    if (canvas) {
      const url = canvas.toDataURL('image/png')
      const a = document.createElement('a')
      a.href = url
      a.download = `${chart.title || 'chart'}.png`
      a.click()
      return
    }
    // Recharts/Plotly: SVG-based
    const svg = chartRef.current?.querySelector('svg')
    if (svg) {
      const svgData = new XMLSerializer().serializeToString(svg)
      const offscreen = document.createElement('canvas')
      const ctx = offscreen.getContext('2d')
      const img = new Image()
      img.onload = () => {
        offscreen.width = img.width * 2
        offscreen.height = img.height * 2
        ctx?.scale(2, 2)
        ctx?.drawImage(img, 0, 0)
        const url = offscreen.toDataURL('image/png')
        const a = document.createElement('a')
        a.href = url
        a.download = `${chart.title || 'chart'}.png`
        a.click()
      }
      img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)))
    }
  }, [chart.title])

  const renderChart = () => {
    switch (chart.library) {
      case 'recharts':
        return <RechartsRenderer chart={chart} />
      case 'plotly':
        return <PlotlyRenderer chart={chart} />
      default:
        return <ChartJSRenderer chart={chart} />
    }
  }

  const tableData = chart.table_data
  const tableColumns = tableData && tableData.length > 0 ? Object.keys(tableData[0]) : []

  const chartBody = (fullscreen = false) => (
    <>
      <div
        ref={fullscreen ? undefined : chartRef}
        className="relative w-full"
        style={{ height: fullscreen ? 'calc(100vh - 160px)' : '320px' }}
      >
        {renderChart()}
      </div>

      {showData && tableData && tableData.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-3 overflow-auto max-h-52">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                {tableColumns.map((col) => (
                  <th
                    key={col}
                    className="text-left px-2 py-1 bg-gray-50 border border-gray-200 font-medium text-gray-600 whitespace-nowrap"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.slice(0, 20).map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                  {tableColumns.map((col) => (
                    <td
                      key={col}
                      className="px-2 py-1 border border-gray-100 text-gray-700 whitespace-nowrap"
                    >
                      {String(row[col] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {tableData.length > 20 && (
            <p className="text-xs text-gray-400 mt-1 px-1">
              Showing first 20 of {tableData.length} rows
            </p>
          )}
        </div>
      )}
    </>
  )

  const toolbar = (
    <div className="flex items-center gap-1 flex-shrink-0 ml-2">
      {tableData && tableData.length > 0 && (
        <button
          onClick={() => setShowData((v) => !v)}
          className={`p-1.5 rounded transition-colors ${
            showData
              ? 'bg-indigo-100 text-indigo-600'
              : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
          }`}
          title={showData ? 'Hide data' : 'Show data table'}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 10h18M3 14h18M10 3v18M14 3v18" />
          </svg>
        </button>
      )}
      <button
        onClick={downloadPng}
        className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        title="Download PNG"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
        </svg>
      </button>
      <button
        onClick={() => setIsFullscreen(true)}
        className="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        title="Fullscreen"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
        </svg>
      </button>
    </div>
  )

  return (
    <>
      <div className={`bg-white rounded-lg border border-gray-200 overflow-hidden ${className}`}>
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 bg-gray-50/50">
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-gray-800 truncate">{chart.title}</h3>
            {chart.description && (
              <p className="text-xs text-gray-500 mt-0.5 truncate">{chart.description}</p>
            )}
          </div>
          {toolbar}
        </div>
        <div className="p-3">{chartBody(false)}</div>
      </div>

      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-white flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <div className="min-w-0 flex-1">
              <h3 className="font-semibold text-gray-800">{chart.title}</h3>
              {chart.description && (
                <p className="text-sm text-gray-500 mt-0.5">{chart.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2 ml-4">
              {tableData && tableData.length > 0 && (
                <button
                  onClick={() => setShowData((v) => !v)}
                  className={`px-3 py-1.5 rounded text-xs flex items-center gap-1.5 transition-colors ${
                    showData
                      ? 'bg-indigo-100 text-indigo-600'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 10h18M3 14h18M10 3v18M14 3v18" />
                  </svg>
                  {showData ? 'Hide data' : 'Show data'}
                </button>
              )}
              <button
                onClick={downloadPng}
                className="px-3 py-1.5 bg-gray-100 text-gray-600 hover:bg-gray-200 rounded text-xs flex items-center gap-1.5 transition-colors"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
                </svg>
                Download PNG
              </button>
              <button
                onClick={() => setIsFullscreen(false)}
                className="p-1.5 rounded text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                title="Exit fullscreen"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M8 3v3a2 2 0 01-2 2H3m18 0h-3a2 2 0 01-2-2V3m0 18v-3a2 2 0 012-2h3M3 16h3a2 2 0 012 2v3" />
                </svg>
              </button>
            </div>
          </div>
          <div className="flex-1 p-6 overflow-auto" ref={chartRef}>
            {chartBody(true)}
          </div>
        </div>
      )}
    </>
  )
}

export default ChartRenderer
