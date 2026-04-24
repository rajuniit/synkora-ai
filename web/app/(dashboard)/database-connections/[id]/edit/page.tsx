'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
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
  status: string
  connection_params: Record<string, any>
}

export default function EditDatabaseConnectionPage() {
  const params = useParams()
  const router = useRouter()
  const [loading, setLoading] = useState(true)
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
    status: 'pending',
    connection_params: {}
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchConnection()
  }, [params.id])

  const fetchConnection = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getDatabaseConnection(params.id as string)
      const connParams = data.connection_params || {}
      // For BigQuery: dataset is stored in connection_params.dataset, not username
      const usernameField = data.type === 'BIGQUERY'
        ? (connParams.dataset || '')
        : (data.username || '')
      setFormData({
        name: data.name,
        description: data.description || '',
        type: data.type,
        host: data.host || '',
        port: data.port || 5432,
        database: data.database || '',
        username: usernameField,
        password: '', // Don't populate password for security
        database_path: data.database_path || '',
        status: data.status || 'pending',
        connection_params: connParams,
      })
    } catch {
      toast.error('Failed to load connection')
      router.push('/database-connections')
    } finally {
      setLoading(false)
    }
  }

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

  const buildBigQueryPayload = (data: typeof formData) => {
    if (!isBigQuery) return data
    const { password: _, connection_params: _cp, username: _u, ...rest } = data
    const newParams: Record<string, any> = {}
    // Only include service_account_json if a new one was provided
    if (data.password) {
      try {
        newParams.service_account_json = JSON.parse(data.password)
      } catch {
        // Invalid JSON — validation toast already shown before submit
      }
    }
    // Always sync dataset from the username field
    if (data.username) newParams.dataset = data.username
    return {
      ...rest,
      // Only include connection_params if there is something to update
      ...(Object.keys(newParams).length > 0 ? { connection_params: newParams } : {}),
    }
  }

  const testConnection = async () => {
    if (isPathBased && !formData.database_path) {
      toast.error('Please provide a database file path')
      return
    }
    if (isBigQuery && !formData.database) {
      toast.error('Please provide a Project ID')
      return
    }
    if (isSnowflake && (!formData.host || !formData.username)) {
      toast.error('Please provide Account and Username')
      return
    }
    if (isSupabase && !formData.host) {
      toast.error('Please provide the Project URL')
      return
    }
    if (!isPathBased && !isCloudOnly && (!formData.host || !formData.port)) {
      toast.error('Please fill in host and port')
      return
    }

    setTesting(true)
    setTestResult(null)

    try {
      const data = await apiClient.testDatabaseConnection(params.id as string)
      if (data.success) {
        setTestResult({ success: true, message: 'Connection successful!' })
        toast.success('Connection test successful')
      } else {
        setTestResult({ success: false, message: data.message || 'Connection failed' })
        toast.error('Connection test failed')
      }
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to test connection')
      setTestResult({ success: false, message })
      toast.error(message)
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
    if (isBigQuery && !formData.database) {
      toast.error('Please provide a Project ID')
      return
    }
    if (isSnowflake && (!formData.host || !formData.username)) {
      toast.error('Please provide Account and Username')
      return
    }
    if (isSupabase && !formData.host) {
      toast.error('Please provide the Project URL')
      return
    }
    if (!isPathBased && !isCloudOnly && (!formData.host || !formData.port)) {
      toast.error('Please fill in host and port')
      return
    }

    setSaving(true)

    try {
      // Only include password if it was changed
      const { password, ...restData } = formData
      const baseData = password ? formData : restData
      let updateData: Record<string, any> = isBigQuery
        ? buildBigQueryPayload(baseData as typeof formData)
        : baseData
      // Convert port=0 (no-port types) to null so backend validation passes
      if ('port' in updateData && (updateData.port === 0 || updateData.port === null)) {
        updateData = { ...updateData, port: null }
      }
      // Don't send connection_params if it's empty — nothing to update
      if (
        updateData.connection_params != null &&
        Object.keys(updateData.connection_params).length === 0
      ) {
        const { connection_params: _, ...withoutParams } = updateData
        updateData = withoutParams
      }

      await apiClient.updateDatabaseConnection(params.id as string, updateData)
      toast.success('Database connection updated successfully')
      router.push(`/database-connections/${params.id}`)
    } catch (error: any) {
      toast.error(extractErrorMessage(error, 'Failed to update connection'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/60 via-white to-rose-50/40 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link
            href={`/database-connections/${params.id}`}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Connection
          </Link>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Database className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 tracking-tight">Edit Database Connection</h1>
              <p className="text-gray-600 mt-1">Update connection settings</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="space-y-6">
            {/* Basic Information */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Connection Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    placeholder="My PostgreSQL Database"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    placeholder="Production database for analytics"
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Database Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) => handleTypeChange(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                      <option value="DATABRICKS">Databricks</option>
                    </optgroup>
                    <optgroup label="Observability &amp; Infrastructure">
                      <option value="DATADOG">Datadog</option>
                      <option value="DOCKER">Docker</option>
                    </optgroup>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => handleInputChange('status', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                    <option value="pending">Pending</option>
                    <option value="error">Error</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Set to "Active" to enable this connection for use
                  </p>
                </div>
              </div>
            </div>

            {/* Connection Details */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Connection Details</h2>
              
              {isPathBased ? (
                /* SQLite / DuckDB — file path */
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Database File Path <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.database_path}
                      onChange={(e) => handleInputChange('database_path', e.target.value)}
                      placeholder={isDuckDB ? '/path/to/data.duckdb or :memory:' : '/path/to/database.db'}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      GCP Project ID <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="my-gcp-project"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Service Account JSON
                    </label>
                    <textarea
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder={'Leave blank to keep current credentials\n{\n  "type": "service_account",\n  ...\n}'}
                      rows={5}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                    />
                    <p className="text-xs text-gray-500 mt-1">Leave blank to keep existing credentials. Stored encrypted.</p>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Default Dataset (Optional)</label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="my_dataset"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
              ) : isSnowflake ? (
                /* Snowflake-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Account Identifier <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="xyz12345.us-east-1"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Username <span className="text-red-500">*</span></label>
                    <input type="text" value={formData.username} onChange={(e) => handleInputChange('username', e.target.value)} placeholder="MYUSER" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
                    <input type="password" value={formData.password} onChange={(e) => handleInputChange('password', e.target.value)} placeholder="Leave blank to keep current" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Database</label>
                    <input type="text" value={formData.database} onChange={(e) => handleInputChange('database', e.target.value)} placeholder="MY_DATABASE" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Warehouse</label>
                    <input type="text" value={formData.connection_params?.warehouse || ''} onChange={(e) => handleConnectionParamChange('warehouse', e.target.value)} placeholder="COMPUTE_WH" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Schema</label>
                    <input type="text" value={formData.connection_params?.schema || ''} onChange={(e) => handleConnectionParamChange('schema', e.target.value)} placeholder="PUBLIC" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Role (Optional)</label>
                    <input type="text" value={formData.connection_params?.role || ''} onChange={(e) => handleConnectionParamChange('role', e.target.value)} placeholder="SYSADMIN" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
                  </div>
                </div>
              ) : formData.type === 'ELASTICSEARCH' ? (
                /* Elasticsearch-specific fields */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Host <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="localhost or elasticsearch.example.com"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Port <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => handleInputChange('port', parseInt(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Index Name (Optional)
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="my-index (leave blank to access all indices)"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Optional: Specify a default index name. Leave blank to access all indices.
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username (Optional)
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="elastic"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Only required if Elasticsearch security is enabled
                    </p>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Password (Optional)
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="Leave blank to keep current password"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Only required if Elasticsearch security is enabled. Leave blank to keep current password.
                    </p>
                  </div>
                </div>
              ) : isSupabase ? (
                /* Supabase — API key auth via PostgREST */
                <div className="grid grid-cols-1 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
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
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Anon / Publishable Key <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="Leave blank to keep existing key"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Supabase Dashboard → Settings → API → Project API Keys → <code>anon</code> public key
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Service Role / Secret Key
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="Leave blank to keep existing key"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
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
                        <p>This connection uses Supabase's REST API (PostgREST) instead of a direct PostgreSQL connection. Only API keys are required.</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                /* Standard database fields (PostgreSQL, MySQL, MongoDB) */
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Host <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => handleInputChange('host', e.target.value)}
                      placeholder="localhost or db.example.com"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Port <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => handleInputChange('port', parseInt(e.target.value))}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Database Name
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) => handleInputChange('database', e.target.value)}
                      placeholder="mydb"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="dbuser"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Password
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="Leave blank to keep current password"
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Leave blank to keep the current password. Enter a new password to update it.
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
            <div className="flex items-center justify-between pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={testConnection}
                disabled={testing || (isPathBased && !formData.database_path) || (isBigQuery && !formData.database) || (isSnowflake && (!formData.host || !formData.username)) || (isSupabase && !formData.host) || (!isPathBased && !isCloudOnly && (!formData.host || !formData.port))}
                className="inline-flex items-center gap-2 px-6 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                  href={`/database-connections/${params.id}`}
                  className="px-6 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </Link>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Save Changes
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
