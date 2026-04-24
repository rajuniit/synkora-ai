'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import {
  Database,
  ArrowLeft,
  Save,
  TestTube,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react'
import { apiClient } from '@/lib/api/client'
import { extractErrorMessage } from '@/lib/api/error'

interface ConnectionFormData {
  name: string
  description: string
  type: string
  host: string
  port: number
  database: string
  username: string
  password: string
  database_path: string
  is_global: boolean
  connection_params: Record<string, any>
}

export default function CreateDatabaseConnectionPage() {
  const router = useRouter()
  const [formData, setFormData] = useState<ConnectionFormData>({
    name: '',
    description: '',
    type: 'POSTGRESQL',
    host: '',
    port: 5432,
    database: '',
    username: '',
    password: '',
    database_path: '',
    is_global: false,
    connection_params: {}
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const handleInputChange = (field: keyof ConnectionFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setTestResult(null) // Clear test result when form changes
  }

  const handleTypeChange = (type: string) => {
    const defaultPorts: Record<string, number> = {
      POSTGRESQL: 5432,
      SUPABASE: 0,
      ELASTICSEARCH: 9200,
      MYSQL: 3306,
      MONGODB: 27017,
      SQLITE: 0,
      DUCKDB: 0,
      SQLSERVER: 1433,
      CLICKHOUSE: 8123,
      BIGQUERY: 0,
      SNOWFLAKE: 0,
      DATADOG: 0,
      DATABRICKS: 443,
      DOCKER: 0,
    }
    setFormData(prev => ({
      ...prev,
      type,
      port: defaultPorts[type] ?? 5432,
      connection_params: {}
    }))
    setTestResult(null)
  }

  const handleConnectionParamChange = (key: string, value: string) => {
    // Coerce 'true'/'false' strings to actual booleans for JSON serialization
    const coerced: any = value === 'true' ? true : value === 'false' ? false : value
    setFormData(prev => ({
      ...prev,
      connection_params: { ...prev.connection_params, [key]: coerced }
    }))
  }

  const isSQLite = formData.type === 'SQLITE'
  const isDuckDB = formData.type === 'DUCKDB'
  const isPathBased = isSQLite || isDuckDB
  const isBigQuery = formData.type === 'BIGQUERY'
  const isSnowflake = formData.type === 'SNOWFLAKE'
  const isSupabase = formData.type === 'SUPABASE'
  const isCloudOnly = isBigQuery || isSnowflake || isSupabase

  const buildPayload = (data: ConnectionFormData) => {
    const portOrNull = data.port > 0 ? data.port : null

    if (data.type === 'BIGQUERY') {
      let serviceAccountJson: Record<string, any> | null = null
      try {
        serviceAccountJson = JSON.parse(data.password)
      } catch {
        // Will be caught by the validation toast below
      }
      return {
        ...data,
        port: portOrNull,
        password: undefined,
        connection_params: {
          ...data.connection_params,
          ...(serviceAccountJson ? { service_account_json: serviceAccountJson } : {}),
          ...(data.username ? { dataset: data.username } : {}),
        },
      }
    }
    return { ...data, port: portOrNull }
  }

  const testConnection = async () => {
    if (isPathBased && !formData.database_path) {
      toast.error('Please provide a database file path')
      return
    }
    if (isBigQuery && (!formData.database || !formData.password)) {
      toast.error('Please provide Project ID and Service Account JSON')
      return
    }
    if (isBigQuery) {
      try {
        JSON.parse(formData.password)
      } catch {
        toast.error('Service Account JSON is not valid JSON')
        return
      }
    }
    if (isSnowflake && (!formData.host || !formData.username || !formData.password)) {
      toast.error('Please provide Account, Username and Password')
      return
    }
    if (isSupabase && (!formData.host || !formData.username || !formData.password)) {
      toast.error('Please provide Project URL, Anon Key and Service Role Key')
      return
    }
    if (!isPathBased && !isCloudOnly && (!formData.host || !formData.port)) {
      toast.error('Please fill in host and port')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const result = await apiClient.testDatabaseConnectionDetails(buildPayload(formData))
      
      if (result.success) {
        setTestResult({ success: true, message: result.message || 'Connection successful!' })
        toast.success('Connection test successful')
      } else {
        setTestResult({ success: false, message: result.message || 'Connection failed' })
        toast.error('Connection test failed')
      }
    } catch (error: any) {
      const errorMessage = extractErrorMessage(error, 'Failed to test connection')
      setTestResult({ success: false, message: errorMessage })
      toast.error(errorMessage)
    } finally {
      setTesting(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name) {
      toast.error('Please provide a connection name')
      return
    }

    if (isPathBased && !formData.database_path) {
      toast.error('Please provide a database file path')
      return
    }
    if (isBigQuery && (!formData.database || !formData.password)) {
      toast.error('Please provide Project ID and Service Account JSON')
      return
    }
    if (isBigQuery) {
      try {
        JSON.parse(formData.password)
      } catch {
        toast.error('Service Account JSON is not valid JSON')
        return
      }
    }
    if (isSnowflake && (!formData.host || !formData.username || !formData.password)) {
      toast.error('Please provide Account, Username and Password')
      return
    }
    if (isSupabase && (!formData.host || !formData.username || !formData.password)) {
      toast.error('Please provide Project URL, Anon Key and Service Role Key')
      return
    }
    if (!isPathBased && !isCloudOnly && (!formData.host || !formData.port)) {
      toast.error('Please fill in host and port')
      return
    }

    setSaving(true)

    try {
      await apiClient.createDatabaseConnection(buildPayload(formData))
      toast.success('Database connection created successfully')
      router.push('/database-connections')
    } catch (error: any) {
      toast.error(extractErrorMessage(error, 'Failed to create connection'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header - More Compact */}
        <div className="mb-6">
          <Link
            href="/database-connections"
            className="inline-flex items-center gap-2 text-red-600 hover:text-red-700 font-medium mb-3 transition-colors text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Connections
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-100 rounded-lg">
              <Database className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Create Database Connection</h1>
              <p className="text-gray-600 mt-1 text-sm">Add a new database connection for data analysis</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <div className="space-y-5">
            {/* Basic Information */}
            <div>
              <h2 className="text-base font-semibold text-gray-900 mb-3">Basic Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Connection Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="My PostgreSQL Database"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    placeholder="Production database for analytics"
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Database Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) => handleTypeChange(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    required
                  >
                    <optgroup label="SQL Databases">
                      <option value="POSTGRESQL">PostgreSQL</option>
                      <option value="SUPABASE">Supabase (REST API)</option>
                      <option value="MYSQL">MySQL</option>
                      <option value="SQLSERVER">SQL Server (MSSQL)</option>
                      <option value="SQLITE">SQLite</option>
                      <option value="DUCKDB">DuckDB</option>
                    </optgroup>
                    <optgroup label="NoSQL & Search">
                      <option value="MONGODB">MongoDB</option>
                      <option value="ELASTICSEARCH">Elasticsearch</option>
                      <option value="CLICKHOUSE">ClickHouse</option>
                    </optgroup>
                    <optgroup label="Cloud Data Warehouses">
                      <option value="BIGQUERY">BigQuery (Google)</option>
                      <option value="SNOWFLAKE">Snowflake</option>
                    </optgroup>
                    <optgroup label="Data Analysis Sources">
                      <option value="DATADOG">Datadog (Metrics & Logs)</option>
                      <option value="DATABRICKS">Databricks (SQL Analytics)</option>
                      <option value="DOCKER">Docker (Container Logs)</option>
                    </optgroup>
                  </select>
                </div>

                <div className="flex items-center">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_global}
                      onChange={(e) => handleInputChange('is_global', e.target.checked)}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      Global Connection (Available to all agents)
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Connection Details */}
            <div>
              <h2 className="text-base font-semibold text-gray-900 mb-3">Connection Details</h2>
              
              {formData.type === 'DATADOG' ? (
                /* Datadog-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      API Key <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="••••••••••••••••••••••••••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Get from Datadog → Integrations → APIs → API Keys
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Application Key <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="••••••••••••••••••••••••••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Generate in Datadog → Organization Settings → Application Keys
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Site <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    >
                      <option value="">Select Datadog Site...</option>
                      <option value="datadoghq.com">US1 (datadoghq.com)</option>
                      <option value="us3.datadoghq.com">US3 (us3.datadoghq.com)</option>
                      <option value="us5.datadoghq.com">US5 (us5.datadoghq.com)</option>
                      <option value="datadoghq.eu">EU (datadoghq.eu)</option>
                      <option value="ap1.datadoghq.com">AP1 (ap1.datadoghq.com)</option>
                      <option value="ddog-gov.com">US1-FED (ddog-gov.com)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Select your Datadog site region
                    </p>
                  </div>
                </div>
              ) : formData.type === 'DATABRICKS' ? (
                /* Databricks-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Server Hostname <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="your-workspace.cloud.databricks.com"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Found in your Databricks workspace URL
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      HTTP Path <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.database_path}
                      onChange={(e) => handleInputChange('database_path', e.target.value)}
                      placeholder="/sql/1.0/warehouses/xxxxxxxxxxxxx"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      SQL Warehouse → Connection Details → HTTP Path
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Access Token <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="••••••••••••••••••••••••••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      User Settings → Access Tokens → Generate New Token
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Catalog
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="main"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default catalog name (e.g., 'main')
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Schema
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="default"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Default schema name (e.g., 'default')
                    </p>
                  </div>
                </div>
              ) : formData.type === 'DOCKER' ? (
                /* Docker-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Docker Host <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="unix://var/run/docker.sock or tcp://host:2375"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Local: unix://var/run/docker.sock | Remote: tcp://hostname:2375
                    </p>
                  </div>

                  <div className="md:col-span-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                      <div className="text-xs text-blue-700">
                        <p className="font-medium mb-1">Security Notes:</p>
                        <ul className="list-disc list-inside space-y-0.5">
                          <li>Local: Requires access to Docker socket (may need permissions)</li>
                          <li>Remote: Ensure Docker daemon is configured securely with TLS</li>
                          <li>Only connect to trusted Docker hosts</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              ) : isPathBased ? (
                /* SQLite / DuckDB — file path */
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Database File Path <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.database_path}
                      onChange={(e) => handleInputChange('database_path', e.target.value)}
                      placeholder={isDuckDB ? '/path/to/data.duckdb or :memory:' : '/path/to/database.db'}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {isDuckDB ? 'Path to DuckDB file, or :memory: for an in-memory database' : 'Full path to your SQLite database file'}
                    </p>
                  </div>
                </div>
              ) : isBigQuery ? (
                /* BigQuery-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      GCP Project ID <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="my-gcp-project"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">Your Google Cloud project ID</p>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Service Account JSON <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder={'{\n  "type": "service_account",\n  "project_id": "my-project",\n  ...\n}'}
                      rows={6}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Paste the full contents of your service account key JSON file. Stored encrypted.
                    </p>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Default Dataset (Optional)
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="my_dataset"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">Optional default dataset to query</p>
                  </div>
                </div>
              ) : isSnowflake ? (
                /* Snowflake-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Account Identifier <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="xyz12345.us-east-1"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Found in your Snowflake URL: <code>account.region.snowflakecomputing.com</code>
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Username <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="MYUSER"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Password <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Database
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="MY_DATABASE"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Warehouse
                    </label>
                    <input
                      type="text"
                      value={formData.connection_params?.warehouse || ''}
                      onChange={(e) => handleConnectionParamChange('warehouse', e.target.value)}
                      placeholder="COMPUTE_WH"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Schema
                    </label>
                    <input
                      type="text"
                      value={formData.connection_params?.schema || ''}
                      onChange={(e) => handleConnectionParamChange('schema', e.target.value)}
                      placeholder="PUBLIC"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Role (Optional)
                    </label>
                    <input
                      type="text"
                      value={formData.connection_params?.role || ''}
                      onChange={(e) => handleConnectionParamChange('role', e.target.value)}
                      placeholder="SYSADMIN"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>
                </div>
              ) : formData.type === 'ELASTICSEARCH' ? (
                /* Elasticsearch-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Host <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="localhost or elasticsearch.example.com"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Port <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => handleInputChange('port', parseInt(e.target.value))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Index Name (Optional)
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="my-index (leave blank to access all indices)"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Optional: Specify a default index name. Leave blank to access all indices.
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Username (Optional)
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="elastic"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Only required if Elasticsearch security is enabled
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Password (Optional)
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Only required if Elasticsearch security is enabled. Password will be encrypted and stored securely.
                    </p>
                  </div>
                </div>
              ) : isSupabase ? (
                /* Supabase — API key auth via PostgREST */
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Project URL <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="https://abcdefghij.supabase.co"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Found in Supabase Dashboard → Settings → API → Project URL
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Anon / Publishable Key <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Supabase Dashboard → Settings → API → Project API Keys → <code>anon</code> public key
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Service Role / Secret Key <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Supabase Dashboard → Settings → API → Project API Keys → <code>service_role</code> secret key. Stored encrypted.
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="use_service_role"
                      checked={formData.connection_params?.use_service_role !== false}
                      onChange={(e) => handleConnectionParamChange('use_service_role', e.target.checked ? 'true' : 'false')}
                      className="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
                    />
                    <label htmlFor="use_service_role" className="text-sm text-gray-700">
                      Use service role key (bypasses Row Level Security — recommended for agents)
                    </label>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                      <div className="text-xs text-blue-700">
                        <p className="font-medium mb-1">No database password needed</p>
                        <p>This connection uses Supabase's REST API (PostgREST) instead of a direct PostgreSQL connection. Only API keys are required — no host port, no database password.</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                /* Standard database fields (PostgreSQL, MySQL, MongoDB) */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Host <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="localhost or db.example.com"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Port <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => handleInputChange('port', parseInt(e.target.value))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Database Name
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="mydb"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Username
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="dbuser"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      Password
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Password will be encrypted and stored securely
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Test Connection Result */}
            {testResult && (
              <div className={`p-4 rounded-lg border ${
                testResult.success 
                  ? 'bg-green-50 border-green-200' 
                  : 'bg-red-50 border-red-200'
              }`}>
                <div className="flex items-center gap-3">
                  {testResult.success ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600" />
                  )}
                  <div>
                    <p className={`font-medium ${
                      testResult.success ? 'text-green-900' : 'text-red-900'
                    }`}>
                      {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                    </p>
                    <p className={`text-sm ${
                      testResult.success ? 'text-green-700' : 'text-red-700'
                    }`}>
                      {testResult.message}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between pt-5 border-t border-gray-200">
              <button
                type="button"
                onClick={testConnection}
                disabled={testing || (isPathBased && !formData.database_path) || (isBigQuery && (!formData.database || !formData.password)) || (isSnowflake && (!formData.host || !formData.username)) || (isSupabase && (!formData.host || !formData.username || !formData.password)) || (!isPathBased && !isCloudOnly && (!formData.host || !formData.port))}
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <TestTube className="w-4 h-4" />
                    Test Connection
                  </>
                )}
              </button>

              <div className="flex gap-3">
                <Link
                  href="/database-connections"
                  className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Create Connection
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
