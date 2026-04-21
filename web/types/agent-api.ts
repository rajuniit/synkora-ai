// Agent API Key Types

export interface AgentApiKey {
  id: string;
  agent_id: string;
  agent_name?: string;
  key_name: string;
  key_prefix: string;
  permissions: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  rate_limit_per_day: number;
  allowed_ips: string[];
  allowed_origins: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  total_requests: number;
  created_at: string;
  updated_at: string;
}

export interface CreateApiKeyRequest {
  agent_id: string;
  key_name: string;
  permissions: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  rate_limit_per_day?: number;
  allowed_ips?: string[];
  allowed_origins?: string[];
  expires_at?: string | null;
}

export interface UpdateApiKeyRequest {
  key_name?: string;
  permissions?: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  rate_limit_per_day?: number;
  allowed_ips?: string[];
  allowed_origins?: string[];
  is_active?: boolean;
  expires_at?: string | null;
}

export interface CreateApiKeyResponse {
  id: string;
  agent_id: string;
  key_name: string;
  api_key: string; // Full key only shown once
  key_prefix: string;
  permissions: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  rate_limit_per_day: number;
  allowed_ips: string[];
  allowed_origins: string[];
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

export interface ApiKeyListResponse {
  keys: AgentApiKey[];
  total: number;
}

// Usage Statistics Types

export interface UsageByEndpoint {
  endpoint: string;
  requests: number;
  avg_response_time_ms: number;
  error_rate: number;
}

export interface UsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  period_start: string;
  period_end: string;
}

export interface UsageStatsResponse {
  overall: UsageStats;
  by_endpoint: UsageByEndpoint[];
}

// Chat Types (for public API)

export interface ChatRequest {
  agent_id: string;
  message: string;
  conversation_id?: string;
  stream?: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  tokens_used: number;
  metadata?: Record<string, any>;
}

// Agent Info Types

export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  is_public: boolean;
}

export interface AgentListResponse {
  agents: AgentInfo[];
  total: number;
}

// Permission Types

export const API_PERMISSIONS = {
  CHAT: 'chat',
  STREAM: 'stream',
  AGENT_READ: 'agent:read',
  CONVERSATION_READ: 'conversation:read',
  CONVERSATION_DELETE: 'conversation:delete',
} as const;

export type ApiPermission = typeof API_PERMISSIONS[keyof typeof API_PERMISSIONS];

// Filter and Sort Types

export interface ApiKeyFilters {
  agent_id?: string;
  is_active?: boolean;
  search?: string;
}

export interface ApiKeySortOptions {
  field: 'key_name' | 'created_at' | 'last_used_at' | 'total_requests';
  direction: 'asc' | 'desc';
}

// Form Types

export interface ApiKeyFormData {
  agent_id: string;
  key_name: string;
  permissions: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  rate_limit_per_day: number;
  allowed_ips: string;
  allowed_origins: string;
  expires_at: string;
}

// Usage Analytics Types

export interface AgentApiUsage {
  timestamp: string;
  request_count: number;
  success_count?: number;
  error_count?: number;
  avg_response_time?: number;
  endpoint?: string;
}

// Error Types

export interface ApiKeyError {
  message: string;
  field?: string;
  code?: string;
}
