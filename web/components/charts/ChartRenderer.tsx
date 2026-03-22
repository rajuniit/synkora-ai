'use client'

import React from 'react'
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
  ChartOptions,
} from 'chart.js'
import { Line, Bar, Pie, Doughnut, Scatter } from 'react-chartjs-2'

// Register Chart.js components
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

export interface ChartData {
  id: string
  title: string
  description?: string
  chart_type: string
  library: string
  config: Record<string, any>
  data: Record<string, any>
  query?: string
  created_at: string
}

interface ChartRendererProps {
  chart: ChartData
  className?: string
}

export function ChartRenderer({ chart, className = '' }: ChartRendererProps) {
  // Prepare chart data based on library
  const getChartComponent = () => {
    if (chart.library === 'chartjs') {
      const options: ChartOptions<any> = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top' as const,
          },
          title: {
            display: true,
            text: chart.title,
          },
          tooltip: {
            enabled: true,
          },
        },
        ...chart.config,
      }

      const chartData = chart.data
      // Guard: Chart.js needs datasets array — skip rendering if data is malformed
      if (!chartData || !Array.isArray((chartData as any).datasets)) {
        return (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Chart data unavailable
          </div>
        )
      }

      switch (chart.chart_type) {
        case 'line':
          return <Line data={chartData as any} options={options} />
        case 'bar':
          return <Bar data={chartData as any} options={options} />
        case 'pie':
          return <Pie data={chartData as any} options={options} />
        case 'doughnut':
          return <Doughnut data={chartData as any} options={options} />
        case 'scatter':
          return <Scatter data={chartData as any} options={options} />
        default:
          return (
            <div className="text-center text-gray-500">
              Unsupported chart type: {chart.chart_type}
            </div>
          )
      }
    }

    return (
      <div className="text-center text-gray-500">
        Unsupported chart library: {chart.library}
      </div>
    )
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      {/* Chart Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">{chart.title}</h3>
        {chart.description && (
          <p className="text-sm text-gray-600 mt-1">{chart.description}</p>
        )}
      </div>

      {/* Chart Canvas */}
      <div className="relative" style={{ height: '400px' }}>
        {getChartComponent()}
      </div>

      {/* Chart Footer */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            <span className="flex items-center">
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              {chart.chart_type}
            </span>
            <span className="flex items-center">
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {new Date(chart.created_at).toLocaleDateString()}
            </span>
          </div>
          {chart.query && (
            <button
              className="text-blue-600 hover:text-blue-800 flex items-center"
              onClick={() => {
                // Show query in modal or copy to clipboard
                navigator.clipboard.writeText(chart.query!)
              }}
              title="Copy query"
            >
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              Query
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChartRenderer
