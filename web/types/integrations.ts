export interface IntegrationConfig {
  id: string
  integration_type: string
  provider: string
  config_data: {
    version?: string
    credentials?: Record<string, any>
    settings?: Record<string, any>
    metadata?: {
      description?: string
      tags?: string[]
    }
  }
  is_active: boolean
  is_default: boolean
  is_platform_config: boolean
  created_at: string
  updated_at: string
}

export interface EmailProviderConfig {
  // SMTP
  smtp_host?: string
  smtp_port?: number
  smtp_username?: string
  smtp_password?: string
  use_tls?: boolean
  use_ssl?: boolean
  
  // SendGrid
  api_key?: string
  
  // Common
  from_email?: string
  from_name?: string
  reply_to?: string
}

export interface IntegrationProvider {
  id: string
  name: string
  type: string
  description: string
  icon: string
  fields: IntegrationField[]
}

export interface IntegrationField {
  name: string
  label: string
  type: 'text' | 'password' | 'number' | 'email' | 'select' | 'checkbox'
  required: boolean
  placeholder?: string
  description?: string
  options?: { label: string; value: string | number }[]
  defaultValue?: any
}

export interface TestConnectionResult {
  success: boolean
  message: string
  provider?: string
}
