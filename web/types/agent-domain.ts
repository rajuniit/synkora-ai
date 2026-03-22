/**
 * Agent Domain Types
 * 
 * TypeScript types for agent domain management and chat page customization.
 */

// Right Sidebar Configuration
export interface RightSidebarConfig {
  enabled: boolean;
  content?: string; // HTML/markdown content
  width: 'sm' | 'md' | 'lg';
}

// Header Configuration
export interface HeaderConfig {
  enabled: boolean;
  logo_url?: string;
  title?: string;
  tagline?: string;
  background_color?: string;
  text_color?: string;
  height: 'compact' | 'normal';
}

// Footer Configuration
export interface FooterConfig {
  enabled: boolean;
  content?: string; // HTML/markdown content
  background_color?: string;
  text_color?: string;
  height: 'compact' | 'normal';
}

// Theme Configuration
export interface ThemeConfig {
  primary_color?: string;
  secondary_color?: string;
  background_color?: string;
  user_message_bg?: string;
  agent_message_bg?: string;
  message_style: 'rounded' | 'square';
  font_family?: string;
  font_size: 'sm' | 'md' | 'lg';
  spacing: 'compact' | 'normal' | 'relaxed';
}

// Branding Configuration
export interface BrandingConfig {
  page_title?: string;
  meta_description?: string;
  favicon_url?: string;
}

// Chat Page Configuration
export interface ChatPageConfig {
  // Logo
  logo_url?: string;
  
  // Layout
  show_left_sidebar: boolean;
  right_sidebar?: RightSidebarConfig;
  
  // Header
  header?: HeaderConfig;
  
  // Footer
  footer?: FooterConfig;
  
  // Theme
  theme?: ThemeConfig;
  
  // Branding
  branding?: BrandingConfig;
  
  // Legacy fields (deprecated but kept for backward compatibility)
  title?: string;
  primary_color?: string;
  secondary_color?: string;
  background_color?: string;
  text_color?: string;
  chat_bubble_color?: string;
  user_message_color?: string;
  bot_message_color?: string;
  welcome_message?: string;
  description?: string;
  footer_text?: string;
  custom_css?: string;
  show_branding: boolean;
  enable_file_upload: boolean;
  enable_voice_input: boolean;
  meta_title?: string;
  meta_description?: string;
  meta_keywords?: string;
  favicon_url?: string;
}

export interface AgentDomain {
  id: string;
  agent_id: string;
  tenant_id: string;
  subdomain?: string;
  domain: string;
  is_custom_domain: boolean;
  is_active?: boolean;
  status?: string; // 'pending', 'active', 'failed', etc.
  is_verified: boolean;
  verified_at?: string;
  verification_token?: string;
  chat_page_config?: ChatPageConfig;
  created_at: string;
  updated_at: string;
}

export interface AgentDomainCreate {
  subdomain?: string;
  domain?: string;
  is_custom_domain: boolean;
  is_active?: boolean;
  chat_page_config?: ChatPageConfig;
}

export interface AgentDomainUpdate {
  subdomain?: string;
  domain?: string;
  is_custom_domain?: boolean;
  is_active?: boolean;
  is_verified?: boolean;
  chat_page_config?: ChatPageConfig;
}

export interface DNSRecord {
  type: string;
  name: string;
  value: string;
  ttl: number;
  priority?: number;
}

export interface DNSRecordsResponse {
  records: DNSRecord[]
  platform_domain: string
}

export interface DNSVerificationResponse {
  is_verified: boolean;
}

// Default configurations
export const DEFAULT_HEADER_CONFIG: HeaderConfig = {
  enabled: true,
  height: 'normal',
};

export const DEFAULT_FOOTER_CONFIG: FooterConfig = {
  enabled: true,
  height: 'compact',
};

export const DEFAULT_THEME_CONFIG: ThemeConfig = {
  message_style: 'rounded',
  font_size: 'md',
  spacing: 'compact',
};

export const DEFAULT_RIGHT_SIDEBAR_CONFIG: RightSidebarConfig = {
  enabled: false,
  width: 'md',
};

export const DEFAULT_CHAT_PAGE_CONFIG: ChatPageConfig = {
  show_left_sidebar: true,
  show_branding: true,
  enable_file_upload: true,
  enable_voice_input: false,
  header: DEFAULT_HEADER_CONFIG,
  footer: DEFAULT_FOOTER_CONFIG,
  theme: DEFAULT_THEME_CONFIG,
  right_sidebar: DEFAULT_RIGHT_SIDEBAR_CONFIG,
};

// Color presets for quick selection
export const COLOR_PRESETS = {
  blue: {
    primary_color: '#3B82F6',
    secondary_color: '#60A5FA',
    user_message_bg: '#DBEAFE',
    agent_message_bg: '#F3F4F6',
  },
  purple: {
    primary_color: '#8B5CF6',
    secondary_color: '#A78BFA',
    user_message_bg: '#EDE9FE',
    agent_message_bg: '#F3F4F6',
  },
  green: {
    primary_color: '#10B981',
    secondary_color: '#34D399',
    user_message_bg: '#D1FAE5',
    agent_message_bg: '#F3F4F6',
  },
  orange: {
    primary_color: '#F59E0B',
    secondary_color: '#FBBF24',
    user_message_bg: '#FEF3C7',
    agent_message_bg: '#F3F4F6',
  },
  red: {
    primary_color: '#EF4444',
    secondary_color: '#F87171',
    user_message_bg: '#FEE2E2',
    agent_message_bg: '#F3F4F6',
  },
  slate: {
    primary_color: '#64748B',
    secondary_color: '#94A3B8',
    user_message_bg: '#E2E8F0',
    agent_message_bg: '#F8FAFC',
  },
};

// Font family options
export const FONT_FAMILIES = [
  { value: 'system-ui', label: 'System Default' },
  { value: 'Inter, sans-serif', label: 'Inter' },
  { value: 'Roboto, sans-serif', label: 'Roboto' },
  { value: 'Open Sans, sans-serif', label: 'Open Sans' },
  { value: 'Lato, sans-serif', label: 'Lato' },
  { value: 'Montserrat, sans-serif', label: 'Montserrat' },
  { value: 'Poppins, sans-serif', label: 'Poppins' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: 'Times New Roman, serif', label: 'Times New Roman' },
  { value: 'Courier New, monospace', label: 'Courier New' },
]
