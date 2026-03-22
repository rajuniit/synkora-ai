/**
 * Type definitions for WhatsApp and Teams bot integrations
 */

// WhatsApp Bot Types
export interface WhatsAppBot {
  bot_id: string;
  bot_name: string;
  agent_id: string;
  agent_name: string;
  phone_number_id?: string;
  business_account_id?: string;
  webhook_url?: string;
  verify_token?: string;
  connection_type?: "cloud_api" | "device_link";
  linked_phone_number?: string;
  is_active: boolean;
  last_message_at?: string;
  created_at: string;
  updated_at: string;
}

// QR Device-Link Session Types
export interface WhatsAppQRSession {
  session_id: string;
}

export type WhatsAppQRStatus = "pending" | "qr_ready" | "scanning" | "connected" | "error";

export interface WhatsAppQREvent {
  type: "qr" | "status" | "connected" | "error";
  qr_data?: string;
  status?: WhatsAppQRStatus;
  phone_number?: string;
  message?: string;
}

export interface CreateWhatsAppBotRequest {
  agent_id: string;
  bot_name: string;
  phone_number_id: string;
  business_account_id: string;
  access_token: string;
  verify_token: string;
  webhook_url?: string;
}

export interface UpdateWhatsAppBotRequest {
  bot_name?: string;
  access_token?: string;
  verify_token?: string;
  webhook_url?: string;
  is_active?: boolean;
}

// Teams Bot Types
export interface TeamsBot {
  bot_id: string;
  bot_name: string;
  agent_id: string;
  agent_name: string;
  app_id: string;
  teams_bot_id: string;
  tenant_id?: string;
  bot_endpoint?: string;
  webhook_url?: string;
  welcome_message?: string;
  is_active: boolean;
  last_message_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTeamsBotRequest {
  agent_id: string;
  bot_name: string;
  app_id: string;
  app_password: string;
  bot_id: string;
  webhook_url?: string;
  welcome_message?: string;
}

export interface UpdateTeamsBotRequest {
  bot_name?: string;
  app_password?: string;
  webhook_url?: string;
  welcome_message?: string;
  is_active?: boolean;
}

// API Response Types
export interface MessagingBotResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

export interface WhatsAppBotListData {
  bots: WhatsAppBot[];
}

export interface TeamsBotListData {
  bots: TeamsBot[];
}
