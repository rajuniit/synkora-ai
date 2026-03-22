/**
 * Load Testing API Module
 *
 * Handles API calls for load test management, test runs, proxy configs, and monitoring.
 */

import { apiClient } from './http'

// ============================================================================
// Types
// ============================================================================

export interface LoadTest {
  id: string
  tenant_id: string
  name: string
  description: string | null
  target_url: string
  target_type: string
  request_config: Record<string, any>
  load_config: Record<string, any>
  proxy_config_id: string | null
  status: 'draft' | 'ready' | 'running' | 'paused'
  schedule_config: Record<string, any> | null
  created_at: string
  updated_at: string
  last_run?: {
    id: string
    status: string
    started_at: string | null
    completed_at: string | null
  } | null
}

export interface LoadTestListResponse {
  items: LoadTest[]
  total: number
  page: number
  page_size: number
}

export interface TestRun {
  id: string
  tenant_id: string
  load_test_id: string
  status: 'pending' | 'initializing' | 'running' | 'stopping' | 'completed' | 'failed' | 'cancelled'
  started_at: string | null
  completed_at: string | null
  summary_metrics: Record<string, any> | null
  error_message: string | null
  peak_vus: number | null
  total_requests: number | null
  duration_seconds: number | null
  is_active: boolean
  k6_script?: string | null
  k6_options?: Record<string, any> | null
  executor_info?: Record<string, any> | null
  created_at: string
  updated_at: string
}

export interface TestRunListResponse {
  items: TestRun[]
  total: number
  page: number
  page_size: number
}

export interface TestScenario {
  id: string
  load_test_id: string
  name: string
  description: string | null
  weight: number
  prompts: Array<{
    role: string
    content: string
    is_template: boolean
  }>
  think_time_config: Record<string, any> | null
  variables: Record<string, any> | null
  request_overrides: Record<string, any> | null
  display_order: number
  created_at: string
  updated_at: string
}

export interface ProxyConfig {
  id: string
  tenant_id: string
  name: string
  provider: string
  api_key_prefix: string
  mock_config: Record<string, any>
  rate_limit: number
  is_active: boolean
  usage_count: number
  total_tokens_generated: number
  created_at: string
  updated_at: string
}

export interface CreateProxyConfigResponse extends ProxyConfig {
  api_key: string
}

export interface MonitoringIntegration {
  id: string
  tenant_id: string
  name: string
  provider: string
  is_active: boolean
  export_settings: Record<string, any> | null
  last_sync_at: string | null
  sync_status: string | null
  sync_error: string | null
  created_at: string
  updated_at: string
}

export interface MetricsSummary {
  http_req_duration_p50?: number
  http_req_duration_p95?: number
  http_req_duration_p99?: number
  http_req_duration_avg?: number
  http_reqs?: number
  http_reqs_per_sec?: number
  http_req_failed?: number
  vus_max?: number
  ttft_p50?: number
  ttft_p95?: number
  tokens_per_sec_avg?: number
}

export interface TestResult {
  id: string
  timestamp: string
  metric_type: string
  metric_value: number
  percentile: string | null
  tags: Record<string, any> | null
}

export interface TestResultsResponse {
  test_run_id: string
  summary: MetricsSummary
  time_series: TestResult[]
  total_points: number
}

// ============================================================================
// Load Tests API
// ============================================================================

export async function getLoadTests(params?: {
  page?: number
  page_size?: number
  status?: string
  search?: string
}): Promise<LoadTestListResponse> {
  const queryParams = new URLSearchParams()
  if (params?.page) queryParams.set('page', params.page.toString())
  if (params?.page_size) queryParams.set('page_size', params.page_size.toString())
  if (params?.status) queryParams.set('status', params.status)
  if (params?.search) queryParams.set('search', params.search)

  const url = `/api/v1/load-tests${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  return apiClient.request('GET', url)
}

export async function getLoadTest(id: string): Promise<LoadTest> {
  return apiClient.request('GET', `/api/v1/load-tests/${id}`)
}

export async function createLoadTest(data: {
  name: string
  description?: string
  target_url: string
  target_type?: string
  auth_config?: Record<string, any>
  request_config?: Record<string, any>
  load_config?: Record<string, any>
  proxy_config_id?: string
}): Promise<LoadTest> {
  return apiClient.request('POST', '/api/v1/load-tests', data)
}

export async function updateLoadTest(id: string, data: Partial<{
  name: string
  description: string
  target_url: string
  target_type: string
  auth_config: Record<string, any>
  request_config: Record<string, any>
  load_config: Record<string, any>
  proxy_config_id: string
  status: string
}>): Promise<LoadTest> {
  return apiClient.request('PUT', `/api/v1/load-tests/${id}`, data)
}

export async function deleteLoadTest(id: string): Promise<void> {
  return apiClient.request('DELETE', `/api/v1/load-tests/${id}`)
}

// ============================================================================
// Test Scenarios API
// ============================================================================

export async function getTestScenarios(loadTestId: string): Promise<TestScenario[]> {
  return apiClient.request('GET', `/api/v1/load-tests/${loadTestId}/scenarios`)
}

export async function createTestScenario(loadTestId: string, data: {
  name: string
  description?: string
  weight?: number
  prompts: Array<{
    role: string
    content: string
    is_template?: boolean
  }>
  think_time_config?: Record<string, any>
  variables?: Record<string, any>
  request_overrides?: Record<string, any>
}): Promise<TestScenario> {
  return apiClient.request('POST', `/api/v1/load-tests/${loadTestId}/scenarios`, data)
}

export async function updateTestScenario(
  loadTestId: string,
  scenarioId: string,
  data: Partial<{
    name: string
    description: string
    weight: number
    prompts: Array<{
      role: string
      content: string
      is_template?: boolean
    }>
    think_time_config: Record<string, any>
    variables: Record<string, any>
    request_overrides: Record<string, any>
    display_order: number
  }>
): Promise<TestScenario> {
  return apiClient.request('PUT', `/api/v1/load-tests/${loadTestId}/scenarios/${scenarioId}`, data)
}

export async function deleteTestScenario(loadTestId: string, scenarioId: string): Promise<void> {
  return apiClient.request('DELETE', `/api/v1/load-tests/${loadTestId}/scenarios/${scenarioId}`)
}

// ============================================================================
// Test Runs API
// ============================================================================

export async function startTestRun(loadTestId: string, options?: {
  k6_options?: Record<string, any>
}): Promise<TestRun> {
  return apiClient.request('POST', `/api/v1/test-runs/${loadTestId}/run`, options || {})
}

export async function getTestRuns(params?: {
  load_test_id?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<TestRunListResponse> {
  const queryParams = new URLSearchParams()
  if (params?.load_test_id) queryParams.set('load_test_id', params.load_test_id)
  if (params?.status) queryParams.set('status', params.status)
  if (params?.page) queryParams.set('page', params.page.toString())
  if (params?.page_size) queryParams.set('page_size', params.page_size.toString())

  const url = `/api/v1/test-runs${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  return apiClient.request('GET', url)
}

export async function getTestRun(id: string): Promise<TestRun> {
  return apiClient.request('GET', `/api/v1/test-runs/${id}`)
}

export async function cancelTestRun(id: string): Promise<TestRun> {
  return apiClient.request('POST', `/api/v1/test-runs/${id}/cancel`)
}

export async function getTestResults(id: string, params?: {
  metric_types?: string[]
  start_time?: string
  end_time?: string
  limit?: number
}): Promise<TestResultsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.metric_types) {
    params.metric_types.forEach(t => queryParams.append('metric_types', t))
  }
  if (params?.start_time) queryParams.set('start_time', params.start_time)
  if (params?.end_time) queryParams.set('end_time', params.end_time)
  if (params?.limit) queryParams.set('limit', params.limit.toString())

  const url = `/api/v1/test-runs/${id}/results${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  return apiClient.request('GET', url)
}

export async function exportTestResults(id: string, options?: {
  format?: 'json' | 'csv' | 'pdf'
  include_time_series?: boolean
  include_k6_script?: boolean
}): Promise<{ download_url: string; expires_at: string; format: string; file_size: number }> {
  return apiClient.request('POST', `/api/v1/test-runs/${id}/export`, options || { format: 'json' })
}

// ============================================================================
// Proxy Config API
// ============================================================================

export async function getProxyConfigs(isActive?: boolean): Promise<{
  items: ProxyConfig[]
  total: number
}> {
  const url = isActive !== undefined
    ? `/api/v1/proxy/configs?is_active=${isActive}`
    : '/api/v1/proxy/configs'
  return apiClient.request('GET', url)
}

export async function getProxyConfig(id: string): Promise<ProxyConfig> {
  return apiClient.request('GET', `/api/v1/proxy/configs/${id}`)
}

export async function createProxyConfig(data: {
  name: string
  provider?: string
  mock_config?: Record<string, any>
  rate_limit?: number
}): Promise<CreateProxyConfigResponse> {
  return apiClient.request('POST', '/api/v1/proxy/configs', data)
}

export async function updateProxyConfig(id: string, data: Partial<{
  name: string
  provider: string
  mock_config: Record<string, any>
  rate_limit: number
  is_active: boolean
}>): Promise<ProxyConfig> {
  return apiClient.request('PUT', `/api/v1/proxy/configs/${id}`, data)
}

export async function deleteProxyConfig(id: string): Promise<void> {
  return apiClient.request('DELETE', `/api/v1/proxy/configs/${id}`)
}

export async function regenerateProxyApiKey(id: string): Promise<CreateProxyConfigResponse> {
  return apiClient.request('POST', `/api/v1/proxy/configs/${id}/regenerate-key`)
}

export async function getProxyUsage(id: string): Promise<{
  proxy_config_id: string
  total_requests: number
  total_tokens: number
  requests_last_hour: number
  requests_last_day: number
  error_rate: number
}> {
  return apiClient.request('GET', `/api/v1/proxy/configs/${id}/usage`)
}

// ============================================================================
// Monitoring Integration API
// ============================================================================

export async function getMonitoringIntegrations(): Promise<{
  items: MonitoringIntegration[]
  total: number
}> {
  return apiClient.request('GET', '/api/v1/monitoring')
}

export async function getMonitoringIntegration(id: string): Promise<MonitoringIntegration> {
  return apiClient.request('GET', `/api/v1/monitoring/${id}`)
}

export async function createMonitoringIntegration(data: {
  name: string
  provider: string
  config: Record<string, any>
  export_settings?: Record<string, any>
}): Promise<MonitoringIntegration> {
  return apiClient.request('POST', '/api/v1/monitoring', data)
}

export async function updateMonitoringIntegration(id: string, data: Partial<{
  name: string
  config: Record<string, any>
  export_settings: Record<string, any>
  is_active: boolean
}>): Promise<MonitoringIntegration> {
  return apiClient.request('PUT', `/api/v1/monitoring/${id}`, data)
}

export async function deleteMonitoringIntegration(id: string): Promise<void> {
  return apiClient.request('DELETE', `/api/v1/monitoring/${id}`)
}

export async function testMonitoringConnection(id: string): Promise<{
  success: boolean
  message: string
  details?: Record<string, any>
}> {
  return apiClient.request('POST', `/api/v1/monitoring/${id}/test`)
}

export async function getMonitoringProviderSchemas(): Promise<Record<string, {
  required: string[]
  optional: string[]
  fields: Record<string, any>
}>> {
  return apiClient.request('GET', '/api/v1/monitoring/providers/schema')
}
