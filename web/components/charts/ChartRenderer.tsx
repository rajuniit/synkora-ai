'use client'

import { useState, useRef, useCallback } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  type ChartOptions,
} from 'chart.js'
import { Line, Bar, Pie, Doughnut, Scatter } from 'react-chartjs-2'
import {
  BarChart,
  Bar as RBar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  Legend as RLegend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Treemap,
  FunnelChart,
  Funnel,
  LabelList,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import dynamic from 'next/dynamic'

const Plot = dynamic(() => import('react-plotly.js') as any, { ssr: false }) as any // eslint-disable-line @typescript-eslint/no-explicit-any

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#06b6d4', '#10b981',
  '#f59e0b', '#ef4444', '#ec4899', '#84cc16',
]

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

  // --- Chart.js renderer ---
  const renderChartJS = () => {
    const options: ChartOptions<'bar'> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        title: { display: false },
      },
      ...(chart.config as object),
    }
    const chartData = chart.data
    if (!chartData || !Array.isArray((chartData as { datasets?: unknown[] }).datasets)) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400 text-sm">
          Chart data unavailable
        </div>
      )
    }
    switch (chart.chart_type) {
      case 'line':
        return <Line data={chartData as any} options={options as ChartOptions<'line'>} />
      case 'bar':
        return <Bar data={chartData as any} options={options} />
      case 'pie':
        return <Pie data={chartData as any} options={options as ChartOptions<'pie'>} />
      case 'doughnut':
        return <Doughnut data={chartData as any} options={options as ChartOptions<'doughnut'>} />
      case 'scatter':
        return <Scatter data={chartData as any} options={options as ChartOptions<'scatter'>} />
      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Unsupported type: {chart.chart_type}
          </div>
        )
    }
  }

  // --- Recharts renderer ---
  const renderRecharts = () => {
    const d = chart.data as Record<string, unknown>
    const data = (d?.data as unknown[]) ?? (Array.isArray(d) ? d : [])
    const xKey = (d?.xKey as string) || (d?.nameKey as string) || 'name'
    const yKey = (d?.yKey as string) || (d?.dataKey as string) || 'value'

    switch (chart.chart_type) {
      case 'area':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data as object[]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <RTooltip />
              <RLegend />
              <Area type="monotone" dataKey={yKey} stroke="#6366f1" fill="#6366f120" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'stacked_bar': {
        const series = (d?.series as string[]) ?? [yKey]
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data as object[]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <RTooltip />
              <RLegend />
              {series.map((s, i) => (
                <RBar key={s} dataKey={s} stackId="a" fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )
      }

      case 'radar':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={data as object[]}>
              <PolarGrid />
              <PolarAngleAxis dataKey={xKey} tick={{ fontSize: 11 }} />
              <PolarRadiusAxis tick={{ fontSize: 10 }} />
              <Radar dataKey={yKey} stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} />
              <RTooltip />
            </RadarChart>
          </ResponsiveContainer>
        )

      case 'treemap':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data as any}
              dataKey={yKey}
              nameKey={xKey}
              aspectRatio={4 / 3}
              stroke="#fff"
              fill="#6366f1"
            />
          </ResponsiveContainer>
        )

      case 'funnel':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <FunnelChart>
              <RTooltip />
              <Funnel dataKey={yKey} data={data as object[]} isAnimationActive>
                {(data as object[]).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
                <LabelList position="right" fill="#555" stroke="none" dataKey={xKey} />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        )

      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Unsupported type: {chart.chart_type}
          </div>
        )
    }
  }

  // --- Plotly renderer ---
  const renderPlotly = () => {
    const d = chart.data as { data?: object[]; layout?: object }
    return (
      <Plot
        data={d?.data ?? []}
        layout={{
          autosize: true,
          margin: { l: 50, r: 30, t: 10, b: 50 },
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { size: 12, family: 'inherit' },
          showlegend: true,
          ...d?.layout,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler
      />
    )
  }

  const renderChart = () => {
    switch (chart.library) {
      case 'recharts':
        return renderRecharts()
      case 'plotly':
        return renderPlotly()
      default:
        return renderChartJS()
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
