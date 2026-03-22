/**
 * Profile and User Types
 * Type definitions for user profiles and related entities
 */

export interface Profile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  phone?: string;
  bio?: string;
  company?: string;
  job_title?: string;
  location?: string;
  website?: string;
  two_factor_enabled: boolean;
  two_factor_secret?: string;
  last_login_at?: string;
  last_login_ip?: string;
  is_platform_admin: boolean;
  notification_preferences: NotificationPreferences;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  email_notifications: boolean;
  team_invitations: boolean;
  security_alerts: boolean;
  product_updates: boolean;
  marketing_emails: boolean;
  [key: string]: boolean;
}

export interface UpdateProfileRequest {
  name?: string;
  phone?: string;
  bio?: string;
  company?: string;
  job_title?: string;
  location?: string;
  website?: string;
}

export interface UpdatePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface UpdateNotificationPreferencesRequest {
  preferences: NotificationPreferences;
}

export interface Enable2FAResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export interface Verify2FARequest {
  code: string;
}

export interface Enable2FARequest {
  code: string;
}

export interface Disable2FARequest {
  code: string;
}

export interface TwoFactorSetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export interface DeleteAccountRequest {
  password: string;
  confirmation: string;
}
